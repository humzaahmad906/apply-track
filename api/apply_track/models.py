"""Database tables.

A Variant holds a full snapshot of ResumeJSON, forked from a base Resume at
creation time. It is deliberately not a diff: a resume you already sent must
not silently change when you later edit the base.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AppStatus(str, Enum):
    wishlist = "wishlist"
    applied = "applied"
    screen = "screen"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"
    withdrawn = "withdrawn"


class Resume(SQLModel, table=True):
    """A parsed base resume -- the master record."""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    source_filename: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Application(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    company: str
    role: str
    job_url: str = ""
    job_description: str = ""
    status: AppStatus = Field(default=AppStatus.wishlist, index=True)
    notes: str = ""
    applied_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Variant(SQLModel, table=True):
    """The tailored resume for one application."""

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", unique=True, index=True)
    # Nullable so deleting a base resume does not destroy variants sent already.
    base_resume_id: int | None = Field(default=None, foreign_key="resume.id")
    title: str = ""
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    last_export: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class GapAnalysis(SQLModel, table=True):
    """Saved JD-versus-resume comparison for one application.

    source_hash covers the job description plus the resume it was run against,
    so the UI can say the analysis is out of date instead of quietly showing a
    stale one.
    """

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", unique=True, index=True)
    source_hash: str = ""
    lesson_count: int = 0
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class LibraryItem(SQLModel, table=True):
    """A reusable Item -- a capstone project, a role, a skill group.

    Lets the same capstone be pulled into many variants without retyping.
    """

    id: int | None = Field(default=None, primary_key=True)
    label: str
    section_kind: str = "projects"
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
