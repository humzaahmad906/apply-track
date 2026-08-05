"""SQLite engine, session plumbing and in-place schema upkeep."""

from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine, select

from . import models  # noqa: F401  -- registers tables on SQLModel.metadata
from .config import DB_PATH, ensure_dirs
from .models import Application, AppStatus, StageEvent

logger = logging.getLogger(__name__)

ensure_dirs()

# as_posix() keeps the URL valid on Windows, where a raw path has backslashes.
engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)

# Columns added to `application` after the first release. create_all() creates
# missing tables but never missing columns, so these go on by hand -- otherwise
# an existing database breaks the first time the ORM selects one of them.
_ADDED_COLUMNS: dict[str, str] = {
    "source": "TEXT NOT NULL DEFAULT ''",
    "next_action": "TEXT NOT NULL DEFAULT ''",
    "next_action_at": "DATETIME",
    "last_contact_at": "DATETIME",
    "snoozed_until": "DATETIME",
}


def init_db() -> None:
    """Create what is missing and bring an older database up to date.

    Every step is idempotent, so this runs on each boot.
    """
    SQLModel.metadata.create_all(engine)
    _add_missing_columns()
    _backfill_stage_events()


def _add_missing_columns() -> None:
    with engine.begin() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(application)")
        have = {row[1] for row in rows}
        for name, ddl in _ADDED_COLUMNS.items():
            if name not in have:
                conn.exec_driver_sql(f"ALTER TABLE application ADD COLUMN {name} {ddl}")
                logger.info("Added column application.%s", name)


def _backfill_stage_events() -> None:
    """Give applications that predate the timeline the history it reads.

    All an old row carries is created_at and applied_at, so that is the whole
    of what can honestly be reconstructed: opened, and sent.
    """
    with Session(engine) as session:
        already = set(session.exec(select(StageEvent.application_id)).all())
        applications = session.exec(select(Application)).all()

        backfilled = 0
        for app in applications:
            if app.id is None or app.id in already:
                continue
            session.add(
                StageEvent(
                    application_id=app.id,
                    status=AppStatus.wishlist,
                    at=app.created_at,
                    note="backfilled",
                )
            )
            if app.status != AppStatus.wishlist:
                session.add(
                    StageEvent(
                        application_id=app.id,
                        status=app.status,
                        at=app.applied_at or app.updated_at,
                        note="backfilled",
                    )
                )
            backfilled += 1

        if backfilled:
            session.commit()
            logger.info("Backfilled stage history for %d application(s)", backfilled)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
