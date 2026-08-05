"""Recommended reading: what this job wants that this resume does not show.

Nothing here is a button any more. Saving a job description or editing a resume
schedules the analysis, and this router reports whatever the background queue
has produced -- plus a force-refresh for when you want it right now.

Deliberately never touches the rendered resume. The gap list is a list of things
the candidate cannot claim yet, which is the last thing you would print on a
resume you are about to send.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..courses import CourseIndexError, courses, get_index, load_cached
from ..db import get_session
from ..gap import GapResult, source_hash
from ..models import Application, GapAnalysis, Variant
from ..schemas import ResumeJSON
from ..tasks import analyse_now, queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["coach"])


def _current_hash(session: Session, app: Application) -> str:
    """Hash of what an analysis would run against right now.

    Empty when there is no variant yet, which simply means nothing can be out
    of date.
    """
    variant = session.exec(
        select(Variant).where(Variant.application_id == app.id)
    ).first()
    if variant is None:
        return ""
    resume = ResumeJSON.model_validate(variant.data or {})
    return source_hash(app.job_description, resume)


def _out(row: GapAnalysis, current_hash: str, state: str) -> dict[str, Any]:
    # Validate on the way out, never hand back the raw stored blob. Analyses
    # saved under an older shape -- basics as bare strings, no lessons on
    # covered -- are normalised here rather than reaching the UI half-formed.
    analysis = GapResult.model_validate(row.data or {}).model_dump()
    return {
        "application_id": row.application_id,
        "created_at": row.created_at,
        "lesson_count": row.lesson_count,
        # No hash means there is nothing to compare against -- a variant was
        # deleted -- so the saved analysis is the best answer available rather
        # than a stale one.
        "stale": bool(current_hash) and row.source_hash != current_hash,
        "state": state,
        "error": "",
        **analysis,
    }


@router.get("/courses")
def course_index() -> dict[str, Any]:
    """Status of the local lesson index, without hitting GitHub."""
    lessons = load_cached()
    return {
        "lesson_count": len(lessons),
        "courses": courses(lessons),
        "indexed": bool(lessons),
    }


@router.post("/courses/refresh")
def refresh_courses() -> dict[str, Any]:
    try:
        lessons = get_index(refresh=True)
    except CourseIndexError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"lesson_count": len(lessons), "courses": courses(lessons), "indexed": True}


@router.get("/applications/{application_id}/reading")
def get_reading(
    application_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """Whatever the queue has produced for this application so far."""
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")

    row = session.exec(
        select(GapAnalysis).where(GapAnalysis.application_id == application_id)
    ).first()
    state = queue.state(application_id)

    if row is None:
        # Never having run is not an error -- it is the normal state of a job
        # you added thirty seconds ago.
        return {
            "application_id": application_id,
            "created_at": None,
            "lesson_count": 0,
            "stale": False,
            "state": state,
            "error": queue.error(application_id),
            "gaps": [],
            "covered": [],
            "basics": [],
            "note": "",
        }

    return _out(row, _current_hash(session, app), state)


@router.post("/applications/{application_id}/reading")
def run_reading(
    application_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """Run it now rather than waiting for the queue."""
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")
    if not app.job_description.strip():
        raise HTTPException(
            400,
            "Paste the job description for this application first — there is "
            "nothing to compare the resume against.",
        )
    variant = session.exec(
        select(Variant).where(Variant.application_id == application_id)
    ).first()
    if variant is None:
        raise HTTPException(
            404,
            "Compose a resume for this application first — the analysis compares "
            "the job description against the resume you intend to send.",
        )

    try:
        analyse_now(application_id)
    except CourseIndexError as exc:
        raise HTTPException(502, str(exc)) from exc
    except RuntimeError as exc:
        # GapError and CliError both land here.
        raise HTTPException(502, str(exc)) from exc

    row = session.exec(
        select(GapAnalysis).where(GapAnalysis.application_id == application_id)
    ).first()
    if row is None:
        raise HTTPException(502, "The analysis produced no result.")
    return _out(row, _current_hash(session, app), "idle")


@router.delete("/applications/{application_id}/reading", status_code=204)
def delete_reading(
    application_id: int, session: Session = Depends(get_session)
) -> None:
    row = session.exec(
        select(GapAnalysis).where(GapAnalysis.application_id == application_id)
    ).first()
    if row is None:
        raise HTTPException(404, "No analysis to delete.")
    session.delete(row)
    session.commit()
