"""Where every application stands, and what needs you today.

The rules here are the product. An application is never just a row in a table:
at any moment there is one most-important thing to do about it, and working out
what that is -- so nobody has to keep it in their head -- is the whole job of
this module.

Each application yields at most one action. A queue that lists three things per
job is a queue nobody reads.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel
from sqlmodel import Session, select

from .models import (
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    Application,
    AppStatus,
    GapAnalysis,
    StageEvent,
    Variant,
    utcnow,
)
from .tasks import queue

# Silence from an employer this long means it is your move again.
FOLLOW_UP_DAYS = 10

# How far ahead something has to be before it stops being your problem today.
DUE_SOON_DAYS = 7

# Applications a week worth aiming at. Something to make progress visible --
# a job hunt with no target just feels like an unbounded pile.
WEEKLY_GOAL = 5


class Action(BaseModel):
    application_id: int
    company: str
    role: str
    kind: str
    title: str
    detail: str
    urgency: int
    due: datetime | None = None


class BoardCard(BaseModel):
    id: int
    company: str
    role: str
    status: AppStatus
    job_url: str
    days_in_stage: int
    stage_since: datetime
    next_action: str
    next_action_at: datetime | None
    has_jd: bool
    variant_id: int | None
    exported: bool
    analysis: str
    # How far along the five active stages, so a card can show its own progress.
    stage_index: int
    prep_gaps: int | None = None
    action_kind: str = ""
    action_title: str = ""
    action_detail: str = ""
    urgency: int | None = None
    due: datetime | None = None


class Funnel(BaseModel):
    status: AppStatus
    count: int


class Stats(BaseModel):
    active: int
    sent: int
    replies: int
    reply_rate: float
    needs_action: int
    # Momentum, rather than just totals.
    this_week: int
    weekly_goal: int
    streak: int
    offers: int


class DashboardPayload(BaseModel):
    stats: Stats
    funnel: list[Funnel]
    actions: list[Action]
    board: dict[str, list[BoardCard]]
    archive: list[BoardCard]


def _aware(value: datetime) -> datetime:
    """SQLite hands datetimes back with no timezone; treat those as UTC.

    Everything was written by utcnow(), so that is genuinely what they are --
    but comparing a naive one against an aware one raises rather than merely
    being off by a few hours.
    """
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _when(due: datetime, now: datetime) -> str:
    days = (due.date() - now.date()).days
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days == -1:
        return "yesterday"
    return f"{-days} days ago" if days < 0 else f"in {days} days"


class _Context:
    """One application with everything the rules need to judge it."""

    def __init__(
        self,
        app: Application,
        variant: Variant | None,
        stage_since: datetime,
        now: datetime,
    ):
        self.app = app
        self.variant = variant
        self.stage_since = stage_since
        self.now = now
        self.exported = bool(variant and variant.last_export)
        self.has_jd = bool(app.job_description.strip())
        self.days_in_stage = max(0, (now - stage_since).days)


def _action(
    ctx: _Context, kind: str, urgency: int, title: str, detail: str,
    due: datetime | None = None,
) -> Action:
    return Action(
        application_id=ctx.app.id or 0,
        company=ctx.app.company,
        role=ctx.app.role,
        kind=kind,
        title=title,
        detail=detail,
        urgency=urgency,
        due=due,
    )


def top_action(ctx: _Context) -> Action | None:
    """The single most important thing to do about this application."""
    app, now = ctx.app, ctx.now

    if app.status in TERMINAL_STATUSES:
        return None
    if app.snoozed_until and _aware(app.snoozed_until) > now:
        return None

    due = _aware(app.next_action_at) if app.next_action_at else None
    if due is not None:
        label = app.next_action.strip()
        if due < now:
            return _action(
                ctx, "overdue", 0, label or "Something was due",
                f"Was due {_when(due, now)}.", due,
            )
        if (due - now) <= timedelta(days=DUE_SOON_DAYS):
            return _action(
                ctx, "due_soon", 1, label or "Coming up",
                f"{_when(due, now).capitalize()}.", due,
            )

    if app.status in {AppStatus.screen, AppStatus.interview, AppStatus.offer}:
        if not app.next_action.strip():
            return _action(
                ctx, "no_next_step", 2, "Set what happens next",
                f"In {app.status.value} for {ctx.days_in_stage} days "
                "with nothing scheduled.",
            )

    if app.status == AppStatus.applied:
        last = app.last_contact_at or app.applied_at
        since = _aware(last) if last else ctx.stage_since
        silent = max(0, (now - since).days)
        if silent >= FOLLOW_UP_DAYS:
            return _action(
                ctx, "follow_up", 3, "Follow up",
                f"Applied {silent} days ago, no reply.",
            )

    if ctx.exported and app.status == AppStatus.wishlist:
        return _action(
            ctx, "not_marked_sent", 4, "Mark as applied",
            "The resume was exported but this is still on the wishlist.",
        )

    if ctx.variant is not None and ctx.has_jd and not ctx.exported:
        return _action(
            ctx, "ready_to_send", 5, "Export and send",
            "The tailored resume is ready but has never been exported.",
        )

    if ctx.has_jd and ctx.variant is None:
        return _action(
            ctx, "needs_resume", 6, "Compose the resume",
            "Job description saved, no tailored resume yet.",
        )

    if app.status == AppStatus.wishlist and not ctx.has_jd:
        return _action(
            ctx, "needs_jd", 7, "Add the job description",
            "Nothing to tailor against yet.",
        )

    return None


class _History:
    """One pass over the stage log, which answers four separate questions."""

    def __init__(self, session: Session, now: datetime):
        self.since: dict[int, datetime] = {}
        self.reached: dict[int, set[AppStatus]] = {}
        self.active_days: set[date] = set()
        self.this_week = 0

        cutoff = now - timedelta(days=7)
        for event in session.exec(select(StageEvent).order_by(StageEvent.at)).all():
            at = _aware(event.at)
            self.since[event.application_id] = at
            self.reached.setdefault(event.application_id, set()).add(event.status)
            self.active_days.add(at.date())
            if event.status == AppStatus.applied and at >= cutoff:
                self.this_week += 1

    def streak(self, today: date) -> int:
        """Consecutive days, counting back, on which something happened.

        Yesterday counts as the anchor when today is still empty, so a streak
        does not appear broken at breakfast.
        """
        if not self.active_days:
            return 0
        cursor = today if today in self.active_days else today - timedelta(days=1)
        length = 0
        while cursor in self.active_days:
            length += 1
            cursor -= timedelta(days=1)
        return length


def build(session: Session) -> DashboardPayload:
    now = utcnow()
    applications = session.exec(select(Application)).all()
    variants = {v.application_id: v for v in session.exec(select(Variant)).all()}
    history = _History(session, now)
    since, reached = history.since, history.reached
    analysing = queue.states()
    gap_counts = {
        row.application_id: len((row.data or {}).get("gaps", []))
        for row in session.exec(select(GapAnalysis)).all()
    }
    stage_order = {status: i for i, status in enumerate(ACTIVE_STATUSES)}

    actions: list[Action] = []
    board: dict[str, list[BoardCard]] = {s.value: [] for s in ACTIVE_STATUSES}
    archive: list[BoardCard] = []
    counts = {s: 0 for s in AppStatus}

    for app in applications:
        app_id = app.id or 0
        counts[app.status] += 1
        ctx = _Context(
            app=app,
            variant=variants.get(app_id),
            stage_since=since.get(app_id, _aware(app.created_at)),
            now=now,
        )

        action = top_action(ctx)
        if action is not None:
            actions.append(action)

        card = BoardCard(
            id=app_id,
            company=app.company,
            role=app.role,
            status=app.status,
            job_url=app.job_url,
            days_in_stage=ctx.days_in_stage,
            stage_since=ctx.stage_since,
            next_action=app.next_action,
            next_action_at=app.next_action_at,
            has_jd=ctx.has_jd,
            variant_id=ctx.variant.id if ctx.variant else None,
            exported=ctx.exported,
            analysis=analysing.get(app_id, "idle"),
            stage_index=stage_order.get(app.status, len(ACTIVE_STATUSES)),
            prep_gaps=gap_counts.get(app_id),
            action_kind=action.kind if action else "",
            action_title=action.title if action else "",
            action_detail=action.detail if action else "",
            urgency=action.urgency if action else None,
            due=action.due if action else None,
        )
        if app.status in TERMINAL_STATUSES:
            archive.append(card)
        else:
            board[app.status.value].append(card)

    # Most urgent first, then longest-waiting, so the top of the list is always
    # the thing to do next.
    actions.sort(key=lambda a: (a.urgency, a.due or now))
    for column in board.values():
        column.sort(key=lambda c: (c.urgency if c.urgency is not None else 99,
                                   -c.days_in_stage))
    archive.sort(key=lambda c: c.stage_since, reverse=True)

    sent = sum(1 for a in applications if a.applied_at is not None)
    replies = sum(
        1
        for a in applications
        if reached.get(a.id or 0, set())
        & {AppStatus.screen, AppStatus.interview, AppStatus.offer}
    )

    return DashboardPayload(
        stats=Stats(
            active=sum(1 for a in applications if a.status not in TERMINAL_STATUSES),
            sent=sent,
            replies=replies,
            reply_rate=round(replies / sent, 3) if sent else 0.0,
            needs_action=len(actions),
            this_week=history.this_week,
            weekly_goal=WEEKLY_GOAL,
            streak=history.streak(now.date()),
            offers=sum(1 for a in applications if a.status == AppStatus.offer),
        ),
        funnel=[Funnel(status=s, count=counts[s]) for s in AppStatus],
        actions=actions,
        board=board,
        archive=archive,
    )
