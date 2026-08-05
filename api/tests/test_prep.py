"""The project generator and the interview bank. CLI stubbed, so offline."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apply_track import cli

JD = (
    "Senior MLE for our logistics platform. You will own document extraction "
    "at scale: Kubernetes serving, Terraform, and on-device inference."
)

PROJECT = {
    "mode": "design",
    "based_on": "",
    "title": "Conveyor-belt label reader",
    "stack": "PyTorch, MLX, FastAPI, Kubernetes",
    "problem": "Parcels move past a line-scan camera faster than OCR can keep up.",
    "why_them": "It is exactly the bottleneck their logistics platform has.",
    "architecture": [
        {"name": "Frame picker", "what": "Chooses the sharpest frame", "tech": "OpenCV"},
        {"name": "Serving tier", "what": "Autoscaled inference", "tech": "Kubernetes"},
    ],
    "covers": [
        {"requirement": "Kubernetes serving", "where": "Serving tier"},
        {"requirement": "On-device inference", "where": "Frame picker"},
    ],
    "milestones": [
        {"name": "Frame selection", "effort": "a weekend", "outcome": "Sharpest frame"},
        {"name": "Serving", "effort": "2 evenings", "outcome": "Autoscaling demo"},
    ],
    "done_means": "A video of parcels being read live.",
    "bullets": [
        "Built a line-scan label reader serving <throughput> parcels a minute.",
        "Cut end-to-end latency to <latency> ms with a frame-selection stage.",
    ],
    "risks": "Getting realistic line-scan footage.",
}

INTERVIEW = {
    "rounds": [
        {
            "name": "Your resume",
            "focus": "The claims you made",
            "questions": [
                {
                    "question": "How did you measure the 94% F1?",
                    "tests": "Whether the number is yours or inherited.",
                    "anchor": "Achieved a 94% F1 score",
                    "strong_answer": "Name the eval set, its size and how it was split.",
                }
            ],
        },
        {
            "name": "The stack",
            "focus": "What the job asks for",
            "questions": [
                {
                    "question": "How would you autoscale this on Kubernetes?",
                    "tests": "Whether K8s is real or a CV line.",
                    "anchor": "Kubernetes serving",
                    "strong_answer": "Talk about HPA on a custom metric, and cold starts.",
                }
            ],
        },
    ],
    "weak_spots": ["No Kubernetes anywhere on the resume."],
    "ask_them": ["What does the on-device roadmap look like?"],
}


class FakeCompleted:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def stub(monkeypatch, payload: dict) -> list[str]:
    """Answer the next CLI call with this object; record the prompts."""
    prompts: list[str] = []

    def fake_run(argv, **kwargs):
        prompts.append(kwargs.get("input", ""))
        return FakeCompleted(
            json.dumps(
                {
                    "is_error": False,
                    "subtype": "success",
                    "result": json.dumps(payload),
                }
            )
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "claude_argv", lambda args: ["claude", *args])
    return prompts


def ready_job(client: TestClient, sample_resume: dict, company: str) -> int:
    """A job with a description and a tailored resume."""
    app_id = client.post(
        "/api/applications",
        json={"company": company, "role": "Senior MLE", "job_description": JD},
    ).json()["id"]
    resume_id = client.post(
        "/api/resumes", json={"name": f"base-{company}", "data": sample_resume}
    ).json()["id"]
    client.post(
        f"/api/applications/{app_id}/variant", json={"base_resume_id": resume_id}
    )
    return app_id


# -- the project ------------------------------------------------------------


def test_a_project_is_designed_from_the_job(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_job(client, sample_resume, "Belt Co")
    prompts = stub(monkeypatch, PROJECT)

    body = client.post(f"/api/applications/{app_id}/project").json()

    assert body["title"] == "Conveyor-belt label reader"
    assert body["status"] == "idea"
    assert len(body["covers"]) == 2
    # The company, the job and the resume all have to reach the model.
    assert "Belt Co" in prompts[0]
    assert "Kubernetes serving" in prompts[0]
    assert "Ada Lovelace" in prompts[0] or "Analytical Engine" in prompts[0]


def test_the_job_needs_a_description_first(client: TestClient, sample_resume: dict):
    app_id = client.post(
        "/api/applications", json={"company": "Bare Co", "role": "MLE"}
    ).json()["id"]

    assert client.post(f"/api/applications/{app_id}/project").status_code == 400


def test_the_job_needs_a_resume_first(client: TestClient):
    app_id = client.post(
        "/api/applications",
        json={"company": "No Resume Co", "role": "MLE", "job_description": JD},
    ).json()["id"]

    assert client.post(f"/api/applications/{app_id}/project").status_code == 404


def test_an_unbuilt_project_cannot_go_on_the_resume(
    client: TestClient, sample_resume: dict, monkeypatch
):
    """An interviewer will ask about anything on there, so it has to exist."""
    app_id = ready_job(client, sample_resume, "Unbuilt Co")
    stub(monkeypatch, PROJECT)
    client.post(f"/api/applications/{app_id}/project")

    res = client.post(f"/api/applications/{app_id}/project/adopt")

    assert res.status_code == 409
    assert "built" in res.json()["detail"]


def test_a_built_project_lands_in_the_resume(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_job(client, sample_resume, "Built Co")
    stub(monkeypatch, PROJECT)
    client.post(f"/api/applications/{app_id}/project")

    client.patch(f"/api/applications/{app_id}/project", json={"status": "built"})
    assert client.post(f"/api/applications/{app_id}/project/adopt").status_code == 200

    variant_id = client.get(f"/api/applications/{app_id}").json()["variant_id"]
    data = client.get(f"/api/variants/{variant_id}").json()["data"]
    projects = [s for s in data["sections"] if s["kind"] == "projects"]
    assert len(projects) == 1
    assert projects[0]["items"][-1]["title"] == "Conveyor-belt label reader"

    # And it reaches the rendered resume, not just the JSON.
    html = client.get(f"/api/variants/{variant_id}/preview").text
    assert "Conveyor-belt label reader" in html


def test_an_unknown_status_is_refused(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_job(client, sample_resume, "Status Co")
    stub(monkeypatch, PROJECT)
    client.post(f"/api/applications/{app_id}/project")

    res = client.patch(
        f"/api/applications/{app_id}/project", json={"status": "shipped-ish"}
    )

    assert res.status_code == 400


# -- the interview ----------------------------------------------------------


def test_the_bank_is_built_from_the_resume_that_was_sent(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_job(client, sample_resume, "Grill Co")
    prompts = stub(monkeypatch, INTERVIEW)

    body = client.post(f"/api/applications/{app_id}/interview").json()

    assert [r["name"] for r in body["rounds"]] == ["Your resume", "The stack"]
    assert body["rounds"][0]["questions"][0]["anchor"] == "Achieved a 94% F1 score"
    assert body["weak_spots"]
    assert body["stale"] is False
    # The variant's contents, not the base resume's name, drive the questions.
    assert "Wrote the first algorithm." in prompts[0]


def test_editing_the_resume_marks_the_bank_out_of_date(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_job(client, sample_resume, "Drifted Co")
    stub(monkeypatch, INTERVIEW)
    client.post(f"/api/applications/{app_id}/interview")

    variant_id = client.get(f"/api/applications/{app_id}").json()["variant_id"]
    data = client.get(f"/api/variants/{variant_id}").json()["data"]
    data["basics"]["headline"] = "Staff Machine Learning Engineer"
    client.put(f"/api/variants/{variant_id}", json={"data": data})

    assert client.get(f"/api/applications/{app_id}/interview").json()["stale"] is True


def test_no_bank_yet_is_a_404(client: TestClient):
    app_id = client.post(
        "/api/applications", json={"company": "Quiet Co", "role": "MLE"}
    ).json()["id"]

    assert client.get(f"/api/applications/{app_id}/interview").status_code == 404


def test_deleting_a_job_takes_its_prep(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_job(client, sample_resume, "Swept Co")
    stub(monkeypatch, PROJECT)
    client.post(f"/api/applications/{app_id}/project")
    stub(monkeypatch, INTERVIEW)
    client.post(f"/api/applications/{app_id}/interview")

    assert client.delete(f"/api/applications/{app_id}").status_code == 204

    assert client.get(f"/api/applications/{app_id}/project").status_code == 404
    assert client.get(f"/api/applications/{app_id}/interview").status_code == 404
