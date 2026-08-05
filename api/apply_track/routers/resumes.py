"""Flow one: upload a resume file, extract its sections, review, save."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from ..config import UPLOAD_DIR, ClaudeCliNotFound, ensure_dirs
from ..db import get_session
from ..extract import SUPPORTED, UnsupportedFile, extract_text
from ..jobs import store
from ..models import Resume, utcnow
from ..parse import ParseError, parse_resume
from ..schemas import ResumeJSON

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resumes", tags=["resumes"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024

# An upload is only needed until its parse finishes. Keeping a day of them is
# enough to debug a bad extraction; keeping every resume ever uploaded is not.
UPLOAD_MAX_AGE_SECONDS = 24 * 3600


def _prune_uploads() -> None:
    cutoff = time.time() - UPLOAD_MAX_AGE_SECONDS
    for path in UPLOAD_DIR.glob("*"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError as exc:
            logger.warning("Could not remove old upload %s: %s", path, exc)


class ResumeSave(BaseModel):
    name: str
    source_filename: str = ""
    data: ResumeJSON


class ResumeSummary(BaseModel):
    id: int
    name: str
    source_filename: str
    section_count: int
    updated_at: Any


def _summary(resume: Resume) -> ResumeSummary:
    return ResumeSummary(
        id=resume.id or 0,
        name=resume.name,
        source_filename=resume.source_filename,
        section_count=len((resume.data or {}).get("sections", [])),
        updated_at=resume.updated_at,
    )


def _run_parse(job_id: str, stored: Path) -> None:
    """Extract text then sections. Runs in a worker thread."""
    store.mark_running(job_id)
    try:
        text = extract_text(stored)
        resume = parse_resume(text)
    except (UnsupportedFile, ParseError, ClaudeCliNotFound) as exc:
        logger.warning("Parse job %s failed: %s", job_id, exc)
        store.mark_error(job_id, str(exc))
        return
    except Exception as exc:  # noqa: BLE001 -- job boundary; surface, never crash
        logger.exception("Parse job %s crashed", job_id)
        store.mark_error(job_id, f"Unexpected error: {exc}")
        return
    store.mark_done(job_id, resume.model_dump())


@router.post("/upload", status_code=202)
async def upload(background: BackgroundTasks, file: UploadFile) -> dict[str, str]:
    """Accept a resume file and start extraction. Poll the returned job id."""
    original = Path(file.filename or "resume")
    if original.suffix.lower() not in SUPPORTED:
        raise HTTPException(
            415,
            f"Unsupported file type '{original.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED))}",
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File larger than 15 MB.")

    ensure_dirs()
    _prune_uploads()
    # Never trust the client's filename for the path we write to.
    stored = UPLOAD_DIR / f"{uuid.uuid4().hex[:12]}{original.suffix.lower()}"
    stored.write_bytes(payload)

    job = store.create(original.name)
    background.add_task(_run_parse, job.id, stored)
    return {"job_id": job.id}


@router.get("/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown or expired job.")
    return job.as_dict()


@router.post("", response_model=ResumeSummary, status_code=201)
def create(payload: ResumeSave, session: Session = Depends(get_session)) -> ResumeSummary:
    """Persist a reviewed resume."""
    resume = Resume(
        name=payload.name.strip() or "Untitled resume",
        source_filename=payload.source_filename,
        data=payload.data.model_dump(),
    )
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return _summary(resume)


@router.get("", response_model=list[ResumeSummary])
def list_all(session: Session = Depends(get_session)) -> list[ResumeSummary]:
    rows = session.exec(select(Resume).order_by(Resume.updated_at.desc())).all()
    return [_summary(r) for r in rows]


@router.get("/{resume_id}")
def get_one(resume_id: int, session: Session = Depends(get_session)) -> dict[str, Any]:
    resume = session.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(404, "Resume not found.")
    return {
        "id": resume.id,
        "name": resume.name,
        "source_filename": resume.source_filename,
        "updated_at": resume.updated_at,
        "data": resume.data,
    }


@router.put("/{resume_id}", response_model=ResumeSummary)
def update(
    resume_id: int, payload: ResumeSave, session: Session = Depends(get_session)
) -> ResumeSummary:
    resume = session.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(404, "Resume not found.")
    resume.name = payload.name.strip() or resume.name
    resume.data = payload.data.model_dump()
    resume.updated_at = utcnow()
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return _summary(resume)


@router.delete("/{resume_id}", status_code=204)
def delete(resume_id: int, session: Session = Depends(get_session)) -> None:
    resume = session.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(404, "Resume not found.")
    session.delete(resume)
    session.commit()
