"""End-to-end over the HTTP surface: base resume -> application -> variant."""

from __future__ import annotations

from fastapi.testclient import TestClient


def save_resume(client: TestClient, sample_resume: dict, name: str = "Base") -> int:
    res = client.post("/api/resumes", json={"name": name, "data": sample_resume})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def make_application(client: TestClient, company: str = "Acme") -> int:
    res = client.post(
        "/api/applications", json={"company": company, "role": "ML Engineer"}
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_health_reports_optional_pieces(client: TestClient):
    body = client.get("/api/health").json()

    assert body["ok"] is True
    assert "pdf_export" in body
    assert "claude_cli" in body


def test_resume_crud(client: TestClient, sample_resume: dict):
    resume_id = save_resume(client, sample_resume, "Ada base")

    listed = client.get("/api/resumes").json()
    assert any(r["id"] == resume_id and r["section_count"] == 2 for r in listed)

    detail = client.get(f"/api/resumes/{resume_id}").json()
    assert detail["data"]["basics"]["name"] == "Ada Lovelace"

    assert client.delete(f"/api/resumes/{resume_id}").status_code == 204
    assert client.get(f"/api/resumes/{resume_id}").status_code == 404


def test_application_requires_company_and_role(client: TestClient):
    res = client.post("/api/applications", json={"company": "  ", "role": "Dev"})
    assert res.status_code == 400


def test_status_change_stamps_applied_at(client: TestClient):
    app_id = make_application(client, "Stamped")
    assert client.get(f"/api/applications/{app_id}").json()["applied_at"] is None

    body = client.patch(f"/api/applications/{app_id}", json={"status": "applied"}).json()

    assert body["status"] == "applied"
    assert body["applied_at"] is not None


def test_upload_rejects_unsupported_type(client: TestClient):
    res = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.pages", b"data", "application/octet-stream")},
    )
    assert res.status_code == 415


def test_upload_rejects_empty_file(client: TestClient):
    res = client.post(
        "/api/resumes/upload", files={"file": ("resume.txt", b"", "text/plain")}
    )
    assert res.status_code == 400


def test_unknown_job_is_404(client: TestClient):
    assert client.get("/api/resumes/jobs/nope").status_code == 404


def test_compose_flow(client: TestClient, sample_resume: dict):
    resume_id = save_resume(client, sample_resume, "Compose base")
    app_id = make_application(client, "Composer Co")

    forked = client.post(
        f"/api/applications/{app_id}/variant", json={"base_resume_id": resume_id}
    )
    assert forked.status_code == 201, forked.text
    variant = forked.json()
    assert variant["title"] == "Composer Co — ML Engineer"
    assert len(variant["data"]["sections"]) == 2

    # The application now advertises its variant.
    assert client.get(f"/api/applications/{app_id}").json()["variant_id"] == variant["id"]

    # One variant per application.
    dup = client.post(
        f"/api/applications/{app_id}/variant", json={"base_resume_id": resume_id}
    )
    assert dup.status_code == 409

    # Tailor it: switch a bullet off and bolt on a capstone project.
    data = variant["data"]
    data["sections"][0]["items"][0]["bullets"][0]["include"] = False
    data["sections"].append(
        {
            "id": "capstone01",
            "kind": "projects",
            "title": "Capstone",
            "include": True,
            "items": [
                {
                    "id": "cap-item",
                    "include": True,
                    "title": "On-device VLM",
                    "subtitle": "Swift, MLX",
                    "bullets": [{"id": "cap-b1", "text": "4-bit quantised.", "include": True}],
                    "tags": [],
                }
            ],
        }
    )
    saved = client.put(f"/api/variants/{variant['id']}", json={"data": data})
    assert saved.status_code == 200, saved.text

    html = client.get(f"/api/variants/{variant['id']}/preview").text
    assert "On-device VLM" in html
    assert "4-bit quantised." in html
    assert "Wrote the first algorithm." not in html
    assert "Documented Bernoulli number computation." in html


def test_variant_is_a_snapshot_not_a_live_link(client: TestClient, sample_resume: dict):
    resume_id = save_resume(client, sample_resume, "Snapshot base")
    app_id = make_application(client, "Snapshot Co")
    variant_id = client.post(
        f"/api/applications/{app_id}/variant", json={"base_resume_id": resume_id}
    ).json()["id"]

    # Rewrite the base resume after forking.
    mutated = {**sample_resume}
    mutated["basics"] = {**sample_resume["basics"], "name": "Someone Else"}
    client.put(
        f"/api/resumes/{resume_id}", json={"name": "Snapshot base", "data": mutated}
    )

    variant = client.get(f"/api/variants/{variant_id}").json()

    # A resume already sent must not change under you.
    assert variant["data"]["basics"]["name"] == "Ada Lovelace"


def test_deleting_the_base_resume_keeps_the_variant(
    client: TestClient, sample_resume: dict
):
    resume_id = save_resume(client, sample_resume, "Doomed base")
    app_id = make_application(client, "Outlives Co")
    variant_id = client.post(
        f"/api/applications/{app_id}/variant", json={"base_resume_id": resume_id}
    ).json()["id"]

    assert client.delete(f"/api/resumes/{resume_id}").status_code == 204

    assert client.get(f"/api/variants/{variant_id}").status_code == 200


def test_deleting_an_application_removes_its_variant(
    client: TestClient, sample_resume: dict
):
    resume_id = save_resume(client, sample_resume, "Cascade base")
    app_id = make_application(client, "Cascade Co")
    variant_id = client.post(
        f"/api/applications/{app_id}/variant", json={"base_resume_id": resume_id}
    ).json()["id"]

    assert client.delete(f"/api/applications/{app_id}").status_code == 204

    assert client.get(f"/api/variants/{variant_id}").status_code == 404


def test_library_instance_gets_fresh_ids(client: TestClient):
    created = client.post(
        "/api/library",
        json={
            "label": "On-device VLM",
            "section_kind": "projects",
            "data": {
                "id": "original-id",
                "title": "On-device VLM",
                "bullets": [{"id": "original-bullet", "text": "Ran at 30fps."}],
            },
        },
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    instance = client.get(f"/api/library/{item_id}/instance").json()

    # Fresh ids, or pulling the same item twice would collide in one variant.
    assert instance["id"] != "original-id"
    assert instance["bullets"][0]["id"] != "original-bullet"
    assert instance["bullets"][0]["text"] == "Ran at 30fps."
    assert instance["include"] is True


def test_forking_from_a_missing_resume_is_404(client: TestClient):
    app_id = make_application(client, "No Base Co")

    res = client.post(
        f"/api/applications/{app_id}/variant", json={"base_resume_id": 999999}
    )

    assert res.status_code == 404
