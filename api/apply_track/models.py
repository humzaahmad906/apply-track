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


# The board shows these, left to right. Everything else is archive.
ACTIVE_STATUSES: list[AppStatus] = [
    AppStatus.wishlist,
    AppStatus.applied,
    AppStatus.screen,
    AppStatus.interview,
    AppStatus.offer,
]

# Reaching one of these means the application actually went out, which is what
# applied_at records. Being rejected without applying is not applying.
SENT_STATUSES: set[AppStatus] = {
    AppStatus.applied,
    AppStatus.screen,
    AppStatus.interview,
    AppStatus.offer,
}

# A closed application never needs anything from you again.
TERMINAL_STATUSES: set[AppStatus] = {AppStatus.rejected, AppStatus.withdrawn}


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
    source: str = ""
    applied_at: datetime | None = None
    # What happens next and when -- the two fields that drive the dashboard's
    # overdue and due-soon actions. Everything else it reports is derived.
    next_action: str = ""
    next_action_at: datetime | None = None
    # When you last spoke to them, so a follow-up is measured from the
    # conversation rather than from the day you applied.
    last_contact_at: datetime | None = None
    # Suppresses every action for this job until the date passes.
    snoozed_until: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class StageEvent(SQLModel, table=True):
    """One transition in a job's life.

    An Application only stores where it is now. This is where the timeline and
    "twelve days in this stage" come from.
    """

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", index=True)
    status: AppStatus
    at: datetime = Field(default_factory=utcnow)
    note: str = ""


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


class ProjectPitch(SQLModel, table=True):
    """The portfolio project designed for one application.

    status gates whether it may go on the resume. A project you have not built
    has no business on a document an interviewer will ask you about.
    """

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", unique=True, index=True)
    status: str = "idea"  # idea | building | built
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class InterviewPrep(SQLModel, table=True):
    """Questions to expect, for one application.

    Built from the exact resume variant that was sent plus the job description,
    because those two documents are what the interviewer will have read.
    """

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", unique=True, index=True)
    source_hash: str = ""
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
