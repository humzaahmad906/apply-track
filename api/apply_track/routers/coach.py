"""Recommended reading: what this job wants that this resume does not show.

Deliberately never touches the rendered resume. The gap list is a list of things
the candidate does not know yet, which is the last thing you would print on a
resume you are about to send.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..courses import CourseIndexError, courses, get_index, load_cached
from ..db import get_session
from ..gap import GapError, analyse
from ..models import Application, GapAnalysis, Variant, utcnow
from ..schemas import ResumeJSON

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["coach"])


def _resume_for(session: Session, application_id: int) -> ResumeJSON:
    """The variant if one exists, since that is what will actually be sent."""
    variant = session.exec(
        select(Variant).where(Variant.application_id == application_id)
    ).first()
    if variant is None:
        raise HTTPException(
            404,
            "Compose a resume for this application first — the analysis compares "
            "the job description against the resume you intend to send.",
        )
    return ResumeJSON.model_validate(variant.data or {})


def _source_hash(job_description: str, resume: ResumeJSON) -> str:
    digest = hashlib.sha256()
    digest.update(job_description.strip().encode("utf-8"))
    digest.update(resume.model_dump_json().encode("utf-8"))
    return digest.hexdigest()[:16]


def _out(row: GapAnalysis, current_hash: str) -> dict[str, Any]:
    return {
        "application_id": row.application_id,
        "created_at": row.created_at,
        "lesson_count": row.lesson_count,
        # Lets the UI offer a refresh instead of presenting old advice as current.
        "stale": row.source_hash != current_hash,
        **(row.data or {}),
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
    """The saved analysis, or 404 if it has never been run."""
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")

    row = session.exec(
        select(GapAnalysis).where(GapAnalysis.application_id == application_id)
    ).first()
    if row is None:
        raise HTTPException(404, "No analysis yet for this application.")

    resume = _resume_for(session, application_id)
    return _out(row, _source_hash(app.job_description, resume))


@router.post("/applications/{application_id}/reading")
def run_reading(
    application_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """Run the comparison and save it against this application."""
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")
    if not app.job_description.strip():
        raise HTTPException(
            400,
            "Paste the job description for this application first — there is "
            "nothing to compare the resume against.",
        )

    resume = _resume_for(session, application_id)

    try:
        lessons = get_index()
    except CourseIndexError as exc:
        raise HTTPException(502, str(exc)) from exc

    try:
        result = analyse(app.job_description, resume, lessons)
    except GapError as exc:
        raise HTTPException(502, str(exc)) from exc

    row = session.exec(
        select(GapAnalysis).where(GapAnalysis.application_id == application_id)
    ).first()
    if row is None:
        row = GapAnalysis(application_id=application_id)

    row.data = result.model_dump()
    row.source_hash = _source_hash(app.job_description, resume)
    row.lesson_count = len(lessons)
    row.created_at = utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)

    return _out(row, row.source_hash)


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
