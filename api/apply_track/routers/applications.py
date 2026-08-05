"""Applications you are tracking.

Status lives on the Application; every change to it also writes a StageEvent,
because "twelve days in this stage" and the whole activity log are read off
that history rather than off the single current value.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import (
    SENT_STATUSES,
    Application,
    AppStatus,
    GapAnalysis,
    InterviewPrep,
    ProjectPitch,
    StageEvent,
    Variant,
    utcnow,
)
from ..tasks import queue

router = APIRouter(prefix="/api/applications", tags=["applications"])


class ApplicationIn(BaseModel):
    company: str
    role: str
    job_url: str = ""
    job_description: str = ""
    status: AppStatus = AppStatus.wishlist
    notes: str = ""
    source: str = ""
    applied_at: datetime | None = None


class ApplicationPatch(BaseModel):
    company: str | None = None
    role: str | None = None
    job_url: str | None = None
    job_description: str | None = None
    status: AppStatus | None = None
    notes: str | None = None
    source: str | None = None
    applied_at: datetime | None = None
    next_action: str | None = None
    next_action_at: datetime | None = None
    last_contact_at: datetime | None = None
    snoozed_until: datetime | None = None


class ApplicationOut(BaseModel):
    id: int
    company: str
    role: str
    job_url: str
    job_description: str
    status: AppStatus
    notes: str
    source: str
    applied_at: datetime | None
    next_action: str
    next_action_at: datetime | None
    last_contact_at: datetime | None
    snoozed_until: datetime | None
    created_at: datetime
    updated_at: datetime
    variant_id: int | None = None
    analysis: str = "idle"


class StageEventOut(BaseModel):
    status: AppStatus
    at: datetime
    note: str


def _out(app: Application, variant_id: int | None) -> ApplicationOut:
    return ApplicationOut(
        **app.model_dump(),
        variant_id=variant_id,
        analysis=queue.state(app.id),
    )


def _variant_id(session: Session, application_id: int) -> int | None:
    return session.exec(
        select(Variant.id).where(Variant.application_id == application_id)
    ).first()


@router.post("", response_model=ApplicationOut, status_code=201)
def create(
    payload: ApplicationIn, session: Session = Depends(get_session)
) -> ApplicationOut:
    if not payload.company.strip() or not payload.role.strip():
        raise HTTPException(400, "Company and role are both required.")
    app = Application(**payload.model_dump())
    app.company = app.company.strip()
    app.role = app.role.strip()
    session.add(app)
    session.commit()
    session.refresh(app)

    session.add(
        StageEvent(application_id=app.id or 0, status=app.status, at=app.created_at)
    )
    session.commit()

    if app.job_description.strip():
        queue.schedule(app.id)
    return _out(app, None)


@router.get("", response_model=list[ApplicationOut])
def list_all(session: Session = Depends(get_session)) -> list[ApplicationOut]:
    apps = session.exec(
        select(Application).order_by(Application.updated_at.desc())
    ).all()
    variant_by_app = {
        app_id: vid
        for vid, app_id in session.exec(select(Variant.id, Variant.application_id)).all()
    }
    return [_out(a, variant_by_app.get(a.id or 0)) for a in apps]


@router.get("/{application_id}", response_model=ApplicationOut)
def get_one(
    application_id: int, session: Session = Depends(get_session)
) -> ApplicationOut:
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")
    return _out(app, _variant_id(session, application_id))


@router.get("/{application_id}/timeline", response_model=list[StageEventOut])
def timeline(
    application_id: int, session: Session = Depends(get_session)
) -> list[StageEvent]:
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")
    return list(
        session.exec(
            select(StageEvent)
            .where(StageEvent.application_id == application_id)
            .order_by(StageEvent.at)
        ).all()
    )


@router.patch("/{application_id}", response_model=ApplicationOut)
def update(
    application_id: int,
    payload: ApplicationPatch,
    session: Session = Depends(get_session),
) -> ApplicationOut:
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")

    changes = payload.model_dump(exclude_unset=True)
    was = app.status
    for key, value in changes.items():
        setattr(app, key, value)

    if app.status != was:
        session.add(StageEvent(application_id=application_id, status=app.status))
        if app.status in SENT_STATUSES:
            # Reaching one of these is the moment it actually went out. Being
            # rejected off the wishlist is not applying.
            if app.applied_at is None and "applied_at" not in changes:
                app.applied_at = utcnow()
            # A stage change is contact, so the follow-up clock starts again.
            if "last_contact_at" not in changes:
                app.last_contact_at = utcnow()

    app.updated_at = utcnow()
    session.add(app)
    session.commit()
    session.refresh(app)

    if "job_description" in changes:
        queue.schedule(application_id)
    return _out(app, _variant_id(session, application_id))


@router.delete("/{application_id}", status_code=204)
def delete(application_id: int, session: Session = Depends(get_session)) -> None:
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")

    # SQLite does not enforce the foreign keys, and orphans would keep showing
    # up in the dashboard's history.
    for variant in session.exec(
        select(Variant).where(Variant.application_id == application_id)
    ).all():
        session.delete(variant)
    for event in session.exec(
        select(StageEvent).where(StageEvent.application_id == application_id)
    ).all():
        session.delete(event)
    for analysis in session.exec(
        select(GapAnalysis).where(GapAnalysis.application_id == application_id)
    ).all():
        session.delete(analysis)
    for pitch in session.exec(
        select(ProjectPitch).where(ProjectPitch.application_id == application_id)
    ).all():
        session.delete(pitch)
    for prep in session.exec(
        select(InterviewPrep).where(InterviewPrep.application_id == application_id)
    ).all():
        session.delete(prep)

    session.delete(app)
    session.commit()
