"""The action rules -- one case each.

Assertions are scoped to the application under test, because every test in the
suite shares one database and the dashboard reports on all of it.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from apply_track.db import engine
from apply_track.models import Variant, utcnow

JD = "We need someone who has shipped inference on device."


def days_ago(n: int) -> str:
    return (utcnow() - timedelta(days=n)).isoformat()


def days_ahead(n: int) -> str:
    return (utcnow() + timedelta(days=n)).isoformat()


def make(client: TestClient, company: str, **fields) -> int:
    body = {"company": company, "role": "ML Engineer", **fields}
    res = client.post("/api/applications", json=body)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def fork(client: TestClient, app_id: int, sample_resume: dict) -> int:
    resume_id = client.post(
        "/api/resumes", json={"name": f"base-{app_id}", "data": sample_resume}
    ).json()["id"]
    res = client.post(
        f"/api/applications/{app_id}/variant", json={"base_resume_id": resume_id}
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def mark_exported(variant_id: int) -> None:
    """Stand in for an export without needing Chromium."""
    with Session(engine) as session:
        variant = session.get(Variant, variant_id)
        assert variant is not None
        variant.last_export = "/exports/pretend.pdf"
        session.add(variant)
        session.commit()


def make_sent(client: TestClient, company: str, sample_resume: dict) -> int:
    """A job that has genuinely gone out: JD, tailored resume, exported.

    Tests about what happens *after* applying use this so no earlier rule --
    "add a JD", "compose a resume", "export it" -- can fire instead of the one
    under test.
    """
    app_id = make(client, company, job_description=JD)
    mark_exported(fork(client, app_id, sample_resume))
    return app_id


def dashboard(client: TestClient) -> dict:
    res = client.get("/api/dashboard")
    assert res.status_code == 200, res.text
    return res.json()


def action_for(client: TestClient, app_id: int) -> dict | None:
    return next(
        (a for a in dashboard(client)["actions"] if a["application_id"] == app_id),
        None,
    )


def card_for(client: TestClient, app_id: int) -> tuple[str, dict] | None:
    data = dashboard(client)
    for column, cards in data["board"].items():
        for card in cards:
            if card["id"] == app_id:
                return column, card
    for card in data["archive"]:
        if card["id"] == app_id:
            return "archive", card
    return None


# -- one test per rule -----------------------------------------------------


def test_wishlist_without_a_job_description_asks_for_one(client: TestClient):
    app_id = make(client, "No JD Co")

    action = action_for(client, app_id)

    assert action["kind"] == "needs_jd"
    assert action["urgency"] == 7


def test_a_saved_jd_with_no_resume_asks_you_to_compose(client: TestClient):
    app_id = make(client, "Needs Resume Co", job_description=JD)

    action = action_for(client, app_id)

    assert action["kind"] == "needs_resume"


def test_a_composed_resume_that_never_shipped_asks_you_to_send_it(
    client: TestClient, sample_resume: dict
):
    app_id = make(client, "Ready Co", job_description=JD)
    fork(client, app_id, sample_resume)

    action = action_for(client, app_id)

    assert action["kind"] == "ready_to_send"


def test_an_exported_resume_still_on_the_wishlist_asks_if_you_sent_it(
    client: TestClient, sample_resume: dict
):
    app_id = make(client, "Exported Co", job_description=JD)
    mark_exported(fork(client, app_id, sample_resume))

    action = action_for(client, app_id)

    assert action["kind"] == "not_marked_sent"


def test_silence_after_applying_becomes_a_follow_up(
    client: TestClient, sample_resume: dict
):
    app_id = make_sent(client, "Silent Co", sample_resume)
    client.patch(
        f"/api/applications/{app_id}",
        json={
            "status": "applied",
            "applied_at": days_ago(12),
            "last_contact_at": days_ago(12),
        },
    )

    action = action_for(client, app_id)

    assert action["kind"] == "follow_up"
    assert "12 days ago" in action["detail"]


def test_a_recent_application_is_left_alone(client: TestClient, sample_resume: dict):
    app_id = make_sent(client, "Patient Co", sample_resume)
    client.patch(f"/api/applications/{app_id}", json={"status": "applied"})

    assert action_for(client, app_id) is None


def test_talking_to_them_resets_the_follow_up_clock(
    client: TestClient, sample_resume: dict
):
    app_id = make_sent(client, "Chatty Co", sample_resume)
    client.patch(
        f"/api/applications/{app_id}",
        json={"status": "applied", "applied_at": days_ago(30)},
    )

    client.patch(f"/api/applications/{app_id}", json={"last_contact_at": days_ago(1)})

    assert action_for(client, app_id) is None


def test_a_live_stage_with_nothing_scheduled_asks_for_a_next_step(
    client: TestClient,
):
    app_id = make(client, "Interviewing Co", job_description=JD)
    client.patch(f"/api/applications/{app_id}", json={"status": "interview"})

    action = action_for(client, app_id)

    assert action["kind"] == "no_next_step"


def test_something_coming_up_soon_surfaces(client: TestClient):
    app_id = make(client, "Soon Co", job_description=JD)
    client.patch(
        f"/api/applications/{app_id}",
        json={
            "status": "interview",
            "next_action": "Panel with the infra team",
            "next_action_at": days_ahead(2),
        },
    )

    action = action_for(client, app_id)

    assert action["kind"] == "due_soon"
    assert action["title"] == "Panel with the infra team"
    assert action["detail"] == "In 2 days."


def test_something_far_off_does_not(client: TestClient, sample_resume: dict):
    app_id = make_sent(client, "Distant Co", sample_resume)
    client.patch(
        f"/api/applications/{app_id}",
        json={
            "status": "interview",
            "next_action": "Final round",
            "next_action_at": days_ahead(30),
        },
    )

    assert action_for(client, app_id) is None


def test_a_missed_date_is_the_most_urgent_thing_there_is(client: TestClient):
    app_id = make(client, "Missed Co", job_description=JD)
    client.patch(
        f"/api/applications/{app_id}",
        json={
            "status": "screen",
            "next_action": "Send the take-home",
            "next_action_at": days_ago(3),
        },
    )

    action = action_for(client, app_id)

    assert action["kind"] == "overdue"
    assert action["urgency"] == 0
    assert "3 days ago" in action["detail"]


def test_snoozing_silences_an_application(client: TestClient):
    app_id = make(client, "Snoozed Co")
    assert action_for(client, app_id)["kind"] == "needs_jd"

    client.patch(f"/api/applications/{app_id}", json={"snoozed_until": days_ahead(3)})

    assert action_for(client, app_id) is None


def test_an_expired_snooze_wakes_back_up(client: TestClient):
    app_id = make(client, "Woken Co")
    client.patch(f"/api/applications/{app_id}", json={"snoozed_until": days_ago(1)})

    assert action_for(client, app_id)["kind"] == "needs_jd"


def test_a_closed_application_never_needs_anything(client: TestClient):
    app_id = make(client, "Closed Co")
    client.patch(f"/api/applications/{app_id}", json={"status": "rejected"})

    assert action_for(client, app_id) is None


# -- board and numbers -----------------------------------------------------


def test_the_board_files_a_card_under_its_stage(client: TestClient):
    app_id = make(client, "Filed Co", job_description=JD)
    client.patch(f"/api/applications/{app_id}", json={"status": "screen"})

    column, card = card_for(client, app_id)

    assert column == "screen"
    assert card["company"] == "Filed Co"
    assert card["has_jd"] is True
    assert card["variant_id"] is None


def test_closed_applications_go_to_the_archive(client: TestClient):
    app_id = make(client, "Archived Co")
    client.patch(f"/api/applications/{app_id}", json={"status": "withdrawn"})

    column, _ = card_for(client, app_id)

    assert column == "archive"


def test_the_board_always_offers_every_active_column(client: TestClient):
    assert set(dashboard(client)["board"]) == {
        "wishlist",
        "applied",
        "screen",
        "interview",
        "offer",
    }


def test_a_card_carries_its_top_action(client: TestClient):
    app_id = make(client, "Labelled Co")

    _, card = card_for(client, app_id)

    assert card["action_kind"] == "needs_jd"
    assert card["urgency"] == 7


def test_the_funnel_counts_a_new_application(client: TestClient):
    before = {f["status"]: f["count"] for f in dashboard(client)["funnel"]}

    make(client, "Counted Co")

    after = {f["status"]: f["count"] for f in dashboard(client)["funnel"]}
    assert after["wishlist"] == before["wishlist"] + 1


def test_reply_rate_counts_applications_that_got_a_reply(client: TestClient):
    before = dashboard(client)["stats"]

    app_id = make(client, "Replied Co", job_description=JD)
    client.patch(f"/api/applications/{app_id}", json={"status": "applied"})
    client.patch(f"/api/applications/{app_id}", json={"status": "screen"})

    after = dashboard(client)["stats"]
    assert after["sent"] == before["sent"] + 1
    assert after["replies"] == before["replies"] + 1


def test_the_queue_puts_the_most_urgent_thing_first(client: TestClient):
    quiet = make(client, "Quiet Co")
    urgent = make(client, "Urgent Co", job_description=JD)
    client.patch(
        f"/api/applications/{urgent}",
        json={"status": "screen", "next_action": "Reply", "next_action_at": days_ago(1)},
    )

    order = [a["application_id"] for a in dashboard(client)["actions"]]

    assert order.index(urgent) < order.index(quiet)
