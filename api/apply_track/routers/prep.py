"""Two things you make per job: something to build, and answers to rehearse.

Both are explicit acts rather than background work. You will build one project
in ten applications, and you only prep for an interview you actually have --
generating either automatically would burn calls on jobs that never get there.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..gap import source_hash
from ..interview import InterviewError, prepare
from ..models import (
    Application,
    InterviewPrep,
    LibraryItem,
    ProjectPitch,
    Variant,
    utcnow,
)
from ..projects import ProjectError, propose
from ..schemas import Bullet, Item, ResumeJSON, Section
from ..tasks import queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/applications", tags=["prep"])

BUILD_STATES = ("idea", "building", "built")


class StatusIn(BaseModel):
    status: str


class AdoptIn(BaseModel):
    """Where the project goes and how much of it.

    item_id folds it into an entry that already exists -- normally the role you
    built it in, so it reads as work rather than a bolted-on side project. Left
    empty it becomes its own entry under Projects.
    """

    item_id: str | None = None
    bullets: list[str] = []  # empty means all of them
    add_skills: bool = True


def _find_item(resume: ResumeJSON, item_id: str) -> Item | None:
    for section in resume.sections:
        for item in section.items:
            if item.id == item_id:
                return item
    return None


def _merge_skills(resume: ResumeJSON, stack: str) -> list[str]:
    """Fold the project's stack into the skills tags, keeping what is there."""
    wanted = [t.strip() for t in stack.split(",") if t.strip()]
    if not wanted:
        return []

    section = next((s for s in resume.sections if s.kind == "skills"), None)
    if section is None:
        section = Section(kind="skills", title="Skills", items=[])
        resume.sections.append(section)
    if not section.items:
        section.items.append(Item())

    target = section.items[0]
    have = {t.strip().lower() for t in target.tags}
    added = []
    for tag in wanted:
        if tag.lower() not in have:
            target.tags.append(tag)
            have.add(tag.lower())
            added.append(tag)
    return added


def _job(session: Session, application_id: int) -> Application:
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")
    return app


def _variant(session: Session, application_id: int) -> Variant | None:
    return session.exec(
        select(Variant).where(Variant.application_id == application_id)
    ).first()


def _resume_for(session: Session, app: Application) -> ResumeJSON:
    """The resume being sent for this job, which is the one that matters."""
    variant = _variant(session, app.id or 0)
    if variant is None:
        raise HTTPException(
            404,
            "Compose a resume for this job first — both of these are built "
            "against the resume you are actually sending.",
        )
    return ResumeJSON.model_validate(variant.data or {})


def _require_jd(app: Application) -> None:
    if not app.job_description.strip():
        raise HTTPException(400, "Paste the job description for this job first.")


# -- the project ------------------------------------------------------------


@router.get("/{application_id}/project")
def get_project(
    application_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    row = session.exec(
        select(ProjectPitch).where(ProjectPitch.application_id == application_id)
    ).first()
    if row is None:
        raise HTTPException(404, "No project designed for this job yet.")
    return {
        "application_id": row.application_id,
        "status": row.status,
        "created_at": row.created_at,
        **(row.data or {}),
    }


@router.post("/{application_id}/project")
def make_project(
    application_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """Design the project this company would be impressed by."""
    app = _job(session, application_id)
    _require_jd(app)
    resume = _resume_for(session, app)

    built = [
        row.data or {}
        for row in session.exec(
            select(LibraryItem).where(LibraryItem.section_kind == "projects")
        ).all()
    ]

    try:
        spec = propose(app.company, app.role, app.job_description, resume, built)
    except ProjectError as exc:
        raise HTTPException(502, str(exc)) from exc

    row = session.exec(
        select(ProjectPitch).where(ProjectPitch.application_id == application_id)
    ).first()
    if row is None:
        row = ProjectPitch(application_id=application_id)
    row.data = spec.model_dump()
    row.created_at = utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)

    return {
        "application_id": row.application_id,
        "status": row.status,
        "created_at": row.created_at,
        **(row.data or {}),
    }


@router.patch("/{application_id}/project")
def set_project_status(
    application_id: int,
    payload: StatusIn,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    if payload.status not in BUILD_STATES:
        raise HTTPException(400, f"Status must be one of {', '.join(BUILD_STATES)}.")
    row = session.exec(
        select(ProjectPitch).where(ProjectPitch.application_id == application_id)
    ).first()
    if row is None:
        raise HTTPException(404, "No project designed for this job yet.")
    row.status = payload.status
    session.add(row)
    session.commit()
    return {"application_id": application_id, "status": row.status}


@router.post("/{application_id}/project/adopt")
def adopt_project(
    application_id: int,
    payload: AdoptIn | None = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Put the project onto this job's resume, once it exists.

    With no body it does the simple thing: every bullet, its own entry under
    Projects, skills merged.
    """
    payload = payload or AdoptIn()
    row = session.exec(
        select(ProjectPitch).where(ProjectPitch.application_id == application_id)
    ).first()
    if row is None:
        raise HTTPException(404, "No project designed for this job yet.")
    if row.status != "built":
        raise HTTPException(
            409,
            "Mark the project built first. An interviewer will ask about "
            "anything on this resume, so it needs to exist before it goes on.",
        )

    variant = _variant(session, application_id)
    if variant is None:
        raise HTTPException(404, "This job has no tailored resume yet.")

    spec = row.data or {}
    resume = ResumeJSON.model_validate(variant.data or {})
    lines = payload.bullets or list(spec.get("bullets", []))

    if payload.item_id:
        # Into a role you already have, as extra bullets on that job.
        item = _find_item(resume, payload.item_id)
        if item is None:
            raise HTTPException(404, "That resume entry is no longer there.")
        have = {b.text.strip() for b in item.bullets}
        added = [t for t in lines if t.strip() and t.strip() not in have]
        item.bullets.extend(Bullet(text=t) for t in added)
        landed_in, added_bullets = item.title or item.subtitle, len(added)
    else:
        # Or as its own entry under Projects.
        section = next((s for s in resume.sections if s.kind == "projects"), None)
        if section is None:
            section = Section(kind="projects", title="Projects", items=[])
            resume.sections.append(section)

        entry = Item(
            title=spec.get("title", "Project"),
            subtitle=spec.get("stack", ""),
            description=spec.get("problem", ""),
            bullets=[Bullet(text=t) for t in lines],
        )
        # Adopting twice, or again after a redesign, rewrites the entry rather
        # than stacking up near-identical copies.
        at = next(
            (i for i, x in enumerate(section.items) if x.title == entry.title), None
        )
        if at is None:
            section.items.append(entry)
        else:
            entry.id = section.items[at].id
            section.items[at] = entry
        landed_in, added_bullets = "Projects", len(lines)

    skills = _merge_skills(resume, spec.get("stack", "")) if payload.add_skills else []

    variant.data = resume.model_dump()
    variant.updated_at = utcnow()
    session.add(variant)
    session.commit()

    # The resume just changed, so the prep is out of date.
    queue.schedule(application_id)
    return {
        "ok": True,
        "landed_in": landed_in,
        "bullets_added": added_bullets,
        "skills_added": skills,
    }


@router.delete("/{application_id}/project", status_code=204)
def delete_project(
    application_id: int, session: Session = Depends(get_session)
) -> None:
    row = session.exec(
        select(ProjectPitch).where(ProjectPitch.application_id == application_id)
    ).first()
    if row is None:
        raise HTTPException(404, "No project to delete.")
    session.delete(row)
    session.commit()


# -- the interview ----------------------------------------------------------


def _prep_out(row: InterviewPrep, current_hash: str) -> dict[str, Any]:
    return {
        "application_id": row.application_id,
        "created_at": row.created_at,
        # The resume moved on since this was written, so the questions are
        # about a document you are no longer sending.
        "stale": bool(current_hash) and row.source_hash != current_hash,
        **(row.data or {}),
    }


@router.get("/{application_id}/interview")
def get_interview(
    application_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    app = _job(session, application_id)
    row = session.exec(
        select(InterviewPrep).where(InterviewPrep.application_id == application_id)
    ).first()
    if row is None:
        raise HTTPException(404, "No interview prep for this job yet.")

    variant = _variant(session, application_id)
    current = (
        source_hash(
            app.job_description, ResumeJSON.model_validate(variant.data or {})
        )
        if variant
        else ""
    )
    return _prep_out(row, current)


@router.post("/{application_id}/interview")
def make_interview(
    application_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """Work out what they are going to ask."""
    app = _job(session, application_id)
    _require_jd(app)
    resume = _resume_for(session, app)

    try:
        prep = prepare(app.company, app.role, app.job_description, resume)
    except InterviewError as exc:
        raise HTTPException(502, str(exc)) from exc

    row = session.exec(
        select(InterviewPrep).where(InterviewPrep.application_id == application_id)
    ).first()
    if row is None:
        row = InterviewPrep(application_id=application_id)
    row.data = prep.model_dump()
    row.source_hash = source_hash(app.job_description, resume)
    row.created_at = utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)

    return _prep_out(row, row.source_hash)


@router.delete("/{application_id}/interview", status_code=204)
def delete_interview(
    application_id: int, session: Session = Depends(get_session)
) -> None:
    row = session.exec(
        select(InterviewPrep).where(InterviewPrep.application_id == application_id)
    ).first()
    if row is None:
        raise HTTPException(404, "No interview prep to delete.")
    session.delete(row)
    session.commit()
