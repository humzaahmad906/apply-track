"""An existing database must survive the upgrade with its rows.

create_all() adds missing tables but never missing columns, so the schema is
brought forward by hand. This builds a database in the old shape and checks
that nothing is lost bringing it to the new one.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlmodel import create_engine

from apply_track import db

OLD_SCHEMA = """
CREATE TABLE application (
    id INTEGER NOT NULL PRIMARY KEY,
    company VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    job_url VARCHAR NOT NULL,
    job_description VARCHAR NOT NULL,
    status VARCHAR(9) NOT NULL,
    notes VARCHAR NOT NULL,
    applied_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
INSERT INTO application VALUES
    (1, 'Old Wishlist Co', 'MLE', '', 'a job description', 'wishlist', 'notes',
     NULL, '2026-07-01 10:00:00.000000', '2026-07-01 10:00:00.000000'),
    (2, 'Old Applied Co', 'Senior MLE', 'https://x', '', 'interview', '',
     '2026-07-10 09:00:00.000000', '2026-07-02 10:00:00.000000',
     '2026-07-11 10:00:00.000000');
"""


def build_old_database(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(OLD_SCHEMA)
    conn.commit()
    conn.close()


def upgrade(path: Path, monkeypatch) -> None:
    monkeypatch.setattr(db, "engine", create_engine(f"sqlite:///{path.as_posix()}"))
    db.init_db()


def rows(path: Path, sql: str) -> list[tuple]:
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def test_existing_applications_survive(tmp_path, monkeypatch):
    old = tmp_path / "old.db"
    build_old_database(old)

    upgrade(old, monkeypatch)

    assert rows(old, "SELECT company FROM application ORDER BY id") == [
        ("Old Wishlist Co",),
        ("Old Applied Co",),
    ]


def test_the_new_columns_arrive_with_usable_defaults(tmp_path, monkeypatch):
    old = tmp_path / "old.db"
    build_old_database(old)

    upgrade(old, monkeypatch)

    names = {r[1] for r in rows(old, "PRAGMA table_info(application)")}
    assert {
        "source",
        "next_action",
        "next_action_at",
        "last_contact_at",
        "snoozed_until",
    } <= names
    assert rows(
        old,
        "SELECT source, next_action, next_action_at, snoozed_until "
        "FROM application WHERE id = 1",
    ) == [("", "", None, None)]


def test_history_is_reconstructed_from_what_the_old_rows_carried(
    tmp_path, monkeypatch
):
    old = tmp_path / "old.db"
    build_old_database(old)

    upgrade(old, monkeypatch)

    events = rows(
        old, "SELECT application_id, status, at FROM stageevent ORDER BY id"
    )
    # A wishlist row only ever opened. An interviewing row also went out, and
    # applied_at is the only date recording when.
    assert [(e[0], e[1]) for e in events] == [
        (1, "wishlist"),
        (2, "wishlist"),
        (2, "interview"),
    ]
    assert events[0][2].startswith("2026-07-01")
    assert events[2][2].startswith("2026-07-10")


def test_upgrading_twice_changes_nothing(tmp_path, monkeypatch):
    old = tmp_path / "old.db"
    build_old_database(old)

    upgrade(old, monkeypatch)
    before = rows(old, "SELECT id, application_id, status FROM stageevent ORDER BY id")
    db.init_db()

    assert rows(old, "SELECT id, application_id, status FROM stageevent ORDER BY id") == before


def test_a_brand_new_database_needs_no_backfill(tmp_path, monkeypatch):
    fresh = tmp_path / "fresh.db"

    upgrade(fresh, monkeypatch)

    assert rows(fresh, "SELECT count(*) FROM application") == [(0,)]
    assert rows(fresh, "SELECT count(*) FROM stageevent") == [(0,)]
