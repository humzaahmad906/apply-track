"""Stage history. Every status change has to leave a trace."""

from __future__ import annotations

from fastapi.testclient import TestClient


def make_application(client: TestClient, company: str) -> int:
    res = client.post(
        "/api/applications", json={"company": company, "role": "ML Engineer"}
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def timeline(client: TestClient, app_id: int) -> list[dict]:
    res = client.get(f"/api/applications/{app_id}/timeline")
    assert res.status_code == 200, res.text
    return res.json()


def test_a_new_application_starts_its_history(client: TestClient):
    app_id = make_application(client, "Opening Co")

    events = timeline(client, app_id)

    assert [e["status"] for e in events] == ["wishlist"]


def test_each_status_change_appends_an_event(client: TestClient):
    app_id = make_application(client, "Moving Co")

    for status in ("applied", "screen", "interview"):
        client.patch(f"/api/applications/{app_id}", json={"status": status})

    events = timeline(client, app_id)

    assert [e["status"] for e in events] == [
        "wishlist",
        "applied",
        "screen",
        "interview",
    ]
    # Ordered oldest first, so the page can read it top to bottom.
    assert [e["at"] for e in events] == sorted(e["at"] for e in events)


def test_repeating_the_same_status_adds_nothing(client: TestClient):
    app_id = make_application(client, "Idle Co")

    client.patch(f"/api/applications/{app_id}", json={"status": "applied"})
    client.patch(f"/api/applications/{app_id}", json={"status": "applied"})
    client.patch(f"/api/applications/{app_id}", json={"notes": "unrelated edit"})

    assert [e["status"] for e in timeline(client, app_id)] == ["wishlist", "applied"]


def test_applying_stamps_the_date(client: TestClient):
    app_id = make_application(client, "Sent Co")

    body = client.patch(f"/api/applications/{app_id}", json={"status": "applied"}).json()

    assert body["applied_at"] is not None
    # A stage change is contact, so the follow-up clock restarts from here.
    assert body["last_contact_at"] is not None


def test_rejection_off_the_wishlist_is_not_an_application(client: TestClient):
    """You cannot be rejected from a job you never applied to."""
    app_id = make_application(client, "Never Sent Co")

    body = client.patch(
        f"/api/applications/{app_id}", json={"status": "rejected"}
    ).json()

    assert body["status"] == "rejected"
    assert body["applied_at"] is None


def test_withdrawing_off_the_wishlist_is_not_an_application(client: TestClient):
    app_id = make_application(client, "Withdrawn Co")

    body = client.patch(
        f"/api/applications/{app_id}", json={"status": "withdrawn"}
    ).json()

    assert body["applied_at"] is None


def test_rejection_after_applying_keeps_the_date(client: TestClient):
    app_id = make_application(client, "Real Rejection Co")
    client.patch(f"/api/applications/{app_id}", json={"status": "applied"})
    applied_at = client.get(f"/api/applications/{app_id}").json()["applied_at"]

    body = client.patch(
        f"/api/applications/{app_id}", json={"status": "rejected"}
    ).json()

    assert body["applied_at"] == applied_at


def test_deleting_an_application_takes_its_history(client: TestClient):
    app_id = make_application(client, "Doomed Co")
    client.patch(f"/api/applications/{app_id}", json={"status": "applied"})

    assert client.delete(f"/api/applications/{app_id}").status_code == 204

    assert client.get(f"/api/applications/{app_id}/timeline").status_code == 404


def test_timeline_of_an_unknown_application_is_404(client: TestClient):
    assert client.get("/api/applications/999999/timeline").status_code == 404
