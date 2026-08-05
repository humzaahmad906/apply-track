"""Work that happens without being asked for.

The point of this module is that nobody presses a button and nobody watches a
spinner. Pasting a job description or editing a resume is enough; the analysis
catches up on its own and the dashboard shows the result when it lands.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Literal

from sqlmodel import Session, select

from . import courses, gap
from .config import ANALYSE_DELAY, AUTO_ANALYSE, COURSE_MAX_AGE_DAYS
from .db import engine
from .models import Application, GapAnalysis, Variant, utcnow
from .schemas import ResumeJSON

logger = logging.getLogger(__name__)

State = Literal["idle", "pending", "running", "error"]

# How long the loop dozes when it has nothing scheduled. Only a backstop -- a
# real schedule() wakes it immediately.
_IDLE_POLL = 60.0


class AnalysisQueue:
    """Coalesces resume and job-description edits into one gap analysis.

    The composer autosaves every 1.2 seconds, so a ten-minute tailoring session
    has to cost one CLI call rather than several hundred. Each save pushes the
    deadline out instead of starting more work, and only the last one lands.
    """

    def __init__(self, delay: float = ANALYSE_DELAY, enabled: bool = AUTO_ANALYSE):
        self._delay = delay
        self._enabled = enabled
        self._deadline: dict[int, float] = {}
        self._state: dict[int, State] = {}
        self._error: dict[int, str] = {}
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._worker: threading.Thread | None = None

    def schedule(self, application_id: int | None) -> None:
        """Note that this application's inputs changed."""
        if not self._enabled or application_id is None:
            return
        with self._lock:
            self._deadline[application_id] = time.monotonic() + self._delay
            self._state[application_id] = "pending"
            self._error.pop(application_id, None)
            self._start_worker()
        self._wake.set()

    def state(self, application_id: int | None) -> State:
        with self._lock:
            return self._state.get(application_id or 0, "idle")

    def error(self, application_id: int | None) -> str:
        with self._lock:
            return self._error.get(application_id or 0, "")

    def states(self) -> dict[int, State]:
        """Every application the queue is currently busy with."""
        with self._lock:
            return {k: v for k, v in self._state.items() if v != "idle"}

    # -- worker ------------------------------------------------------------

    def _start_worker(self) -> None:
        """Caller holds the lock."""
        if self._worker is None or not self._worker.is_alive():
            self._worker = threading.Thread(
                target=self._loop, name="apply-track-analysis", daemon=True
            )
            self._worker.start()

    def _loop(self) -> None:
        while True:
            application_id, wait = self._next_due()
            if application_id is None:
                self._wake.wait(timeout=_IDLE_POLL)
                self._wake.clear()
                continue
            if wait > 0:
                # A save inside this window moves the deadline, so wake up and
                # work out what is due again rather than running early.
                self._wake.wait(timeout=wait)
                self._wake.clear()
                continue
            self._run_one(application_id)

    def _next_due(self) -> tuple[int | None, float]:
        with self._lock:
            if not self._deadline:
                return None, 0.0
            application_id = min(self._deadline, key=self._deadline.__getitem__)
            return application_id, self._deadline[application_id] - time.monotonic()

    def _run_one(self, application_id: int) -> None:
        with self._lock:
            self._deadline.pop(application_id, None)
            self._state[application_id] = "running"

        try:
            analyse_now(application_id)
        except Exception as exc:  # noqa: BLE001 -- worker boundary; never die
            logger.warning("Auto-analysis for application %d failed: %s", application_id, exc)
            with self._lock:
                self._state[application_id] = "error"
                self._error[application_id] = str(exc)
            return

        with self._lock:
            # Only clear if nothing rescheduled us while the call was in flight.
            if application_id not in self._deadline:
                self._state[application_id] = "idle"


def analyse_now(application_id: int) -> bool:
    """Run the comparison if it is still needed. Says whether it ran.

    The preconditions are checked here rather than at schedule time because the
    quiet period gives the user half a minute to invalidate any of them.
    """
    with Session(engine) as session:
        app = session.get(Application, application_id)
        if app is None or not app.job_description.strip():
            return False

        variant = session.exec(
            select(Variant).where(Variant.application_id == application_id)
        ).first()
        if variant is None:
            return False

        resume = ResumeJSON.model_validate(variant.data or {})
        current = gap.source_hash(app.job_description, resume)

        row = session.exec(
            select(GapAnalysis).where(GapAnalysis.application_id == application_id)
        ).first()
        if row is not None and row.source_hash == current:
            return False  # nothing changed, so nothing to spend a call on

        lessons = courses.get_index()
        result = gap.analyse(app.job_description, resume, lessons)

        if row is None:
            row = GapAnalysis(application_id=application_id)
        row.data = result.model_dump()
        row.source_hash = current
        row.lesson_count = len(lessons)
        row.created_at = utcnow()
        session.add(row)
        session.commit()

    logger.info("Analysed application %d", application_id)
    return True


def warm_course_index() -> None:
    """Fetch the lesson catalogue ahead of time, off the request path.

    Every analysis needs it, and nobody should find that out by watching an
    analysis stall on a GitHub round trip.
    """
    if not AUTO_ANALYSE:
        return
    threading.Thread(
        target=_warm_course_index, name="apply-track-courses", daemon=True
    ).start()


def _warm_course_index() -> None:
    max_age = COURSE_MAX_AGE_DAYS * 86400
    try:
        cached = courses.CACHE_PATH
        if cached.exists() and time.time() - cached.stat().st_mtime < max_age:
            return
        lessons = courses.get_index(refresh=True)
        logger.info("Warmed the course index: %d lessons", len(lessons))
    except courses.CourseIndexError as exc:
        # An empty catalogue only blocks the analysis, so log it and move on.
        logger.warning("Could not warm the course index: %s", exc)


queue = AnalysisQueue()
