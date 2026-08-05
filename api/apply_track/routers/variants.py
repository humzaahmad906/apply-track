"""Flow two, the main one: compose a tailored resume for an application.

A variant is a full snapshot of ResumeJSON forked from a base resume. The
composer sends the whole tree back on save, and the renderer resolves the
include flags. Nothing here calls the model -- this half is deterministic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import Application, Resume, Variant, utcnow
from ..render import RenderError, render_html, render_pdf, safe_filename
from ..schemas import ResumeJSON
from ..tasks import queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["variants"])


class VariantCreate(BaseModel):
    base_resume_id: int
    title: str = ""


class VariantUpdate(BaseModel):
    title: str | None = None
    data: ResumeJSON


def _load(session: Session, variant_id: int) -> Variant:
    variant = session.get(Variant, variant_id)
    if variant is None:
        raise HTTPException(404, "Variant not found.")
    return variant


def _resume_json(variant: Variant) -> ResumeJSON:
    return ResumeJSON.model_validate(variant.data or {})


def _out(variant: Variant) -> dict[str, Any]:
    return {
        "id": variant.id,
        "application_id": variant.application_id,
        "base_resume_id": variant.base_resume_id,
        "title": variant.title,
        "data": variant.data,
        "last_export": variant.last_export,
        "updated_at": variant.updated_at,
    }


@router.post("/applications/{application_id}/variant", status_code=201)
def fork(
    application_id: int,
    payload: VariantCreate,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Snapshot a base resume into this application's variant."""
    app = session.get(Application, application_id)
    if app is None:
        raise HTTPException(404, "Application not found.")

    existing = session.exec(
        select(Variant).where(Variant.application_id == application_id)
    ).first()
    if existing is not None:
        raise HTTPException(
            409, f"This application already has a variant (id {existing.id})."
        )

    base = session.get(Resume, payload.base_resume_id)
    if base is None:
        raise HTTPException(404, "Base resume not found.")

    # Deep copy through the schema: the variant is independent of the base from
    # here on, so editing the base never rewrites a resume already sent.
    snapshot = ResumeJSON.model_validate(base.data or {})

    variant = Variant(
        application_id=application_id,
        base_resume_id=base.id,
        title=payload.title.strip() or f"{app.company} — {app.role}",
        data=snapshot.model_dump(),
    )
    session.add(variant)
    session.commit()
    session.refresh(variant)

    # There is now a resume to compare the job description against.
    queue.schedule(application_id)
    return _out(variant)


@router.get("/variants/{variant_id}")
def get_one(variant_id: int, session: Session = Depends(get_session)) -> dict[str, Any]:
    return _out(_load(session, variant_id))


@router.put("/variants/{variant_id}")
def update(
    variant_id: int, payload: VariantUpdate, session: Session = Depends(get_session)
) -> dict[str, Any]:
    variant = _load(session, variant_id)
    if payload.title is not None:
        variant.title = payload.title.strip() or variant.title
    variant.data = payload.data.model_dump()
    variant.updated_at = utcnow()
    session.add(variant)
    session.commit()
    session.refresh(variant)

    # The composer autosaves constantly; the queue coalesces the storm into one
    # analysis once the editing stops.
    queue.schedule(variant.application_id)
    return _out(variant)


@router.delete("/variants/{variant_id}", status_code=204)
def delete(variant_id: int, session: Session = Depends(get_session)) -> None:
    variant = _load(session, variant_id)
    session.delete(variant)
    session.commit()


@router.get("/variants/{variant_id}/preview", response_class=Response)
def preview(variant_id: int, session: Session = Depends(get_session)) -> Response:
    """The exact HTML the PDF is made from -- the composer iframes this."""
    variant = _load(session, variant_id)
    html = render_html(_resume_json(variant))
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.post("/variants/{variant_id}/export")
async def export(
    variant_id: int, session: Session = Depends(get_session)
) -> Response:
    """Render this variant to PDF and return the file."""
    variant = _load(session, variant_id)
    app = session.get(Application, variant.application_id)
    resume = _resume_json(variant)

    filename = safe_filename(
        resume.basics.name or "resume",
        app.company if app else "",
        app.role if app else "",
    )

    try:
        path = await render_pdf(resume, filename)
    except RenderError as exc:
        # Chromium may still be downloading, or missing on a fresh machine.
        # The preview endpoint plus browser print keeps the app usable meanwhile.
        raise HTTPException(503, str(exc)) from exc

    variant.last_export = str(path)
    variant.updated_at = utcnow()
    session.add(variant)
    session.commit()

    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/resumes/{resume_id}/preview", response_class=Response)
def preview_base(resume_id: int, session: Session = Depends(get_session)) -> Response:
    """Same renderer, pointed at a base resume."""
    resume = session.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(404, "Resume not found.")
    html = render_html(ResumeJSON.model_validate(resume.data or {}))
    return Response(content=html, media_type="text/html; charset=utf-8")
