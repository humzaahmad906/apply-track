"""SQLite engine and session plumbing."""

from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401  -- registers tables on SQLModel.metadata
from .config import DB_PATH, ensure_dirs

ensure_dirs()

# as_posix() keeps the URL valid on Windows, where a raw path has backslashes.
engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
