"""Applications you are tracking."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import Application, AppStatus, Variant, utcnow

router = APIRouter(prefix="/api/applications", tags=["applications"])


class ApplicationIn(BaseModel):
    company: str
    role: str
    job_url: str = ""
    job_description: str = ""
    status: AppStatus = AppStatus.wishlist
    notes: str = ""
    applied_at: datetime | None = None


class ApplicationPatch(BaseModel):
    company: str | None = None
    role: str | None = None
    job_url: str | None = None
    job_description: str | None = None
    status: AppStatus | None = None
    notes: str | None = None
    applied_at: datetime | None = None


class ApplicationOut(BaseModel):
    id: int
    company: str
    role: str
    job_url: str
    job_description: str
    status: AppStatus
    notes: str
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime
    variant_id: int | None = None


def _out(app: Application, variant_id: int | None) -> ApplicationOut:
    return ApplicationOut(**app.model_dump(), variant_id=variant_id)


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
    for key, value in changes.items():
        setattr(app, key, value)

    # Moving out of wishlist is the moment it actually got sent.
    if (
        changes.get("status") not in (None, AppStatus.wishlist)
        and app.applied_at is None
        and "applied_at" not in changes
    ):
        app.applied_at = utcnow()

    app.updated_at = utcnow()
    session.add(app)
    session.commit()
    session.refresh(app)
    return _out(app, _variant_id(session, application_id))


@router.delete("/{application_id}", status_code=204)
def delete(application_id: int, session: Session = Depends(get_session)) -> None:
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")
    for variant in session.exec(
        select(Variant).where(Variant.application_id == application_id)
    ).all():
        session.delete(variant)
    session.delete(app)
    session.commit()
