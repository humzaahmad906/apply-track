"""The debounce. The point of the queue is that editing never costs a call.

The composer autosaves every 1.2 seconds, so without coalescing a ten-minute
tailoring session would fire hundreds of analyses. The CLI is stubbed here, so
nothing reaches the network.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi.testclient import TestClient

from apply_track import tasks
from apply_track.courses import Lesson
from apply_track.gap import GapResult

JD = "Ship inference on device. Kubernetes a plus."

LESSONS = [
    Lesson(
        course="kubernetes-for-ml",
        number="03",
        title="Scheduling and autoscaling",
        path="content/kubernetes-for-ml/03-scheduling-and-autoscaling.md",
        url="https://example.invalid/lesson",
    )
]


def stub_analysis(monkeypatch) -> list[str]:
    """Record every analysis that actually happens."""
    calls: list[str] = []

    def fake_analyse(job_description, resume, lessons):
        calls.append(job_description)
        return GapResult(gaps=[], covered=[], basics=[])

    monkeypatch.setattr(tasks.gap, "analyse", fake_analyse)
    monkeypatch.setattr(tasks.courses, "get_index", lambda refresh=False: LESSONS)
    return calls


def wait_for(predicate: Callable[[], bool], timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def ready_application(client: TestClient, sample_resume: dict, company: str) -> int:
    """An application the analysis can actually run on: JD plus a variant."""
    app_id = client.post(
        "/api/applications",
        json={"company": company, "role": "MLE", "job_description": JD},
    ).json()["id"]
    resume_id = client.post(
        "/api/resumes", json={"name": f"base-{company}", "data": sample_resume}
    ).json()["id"]
    client.post(
        f"/api/applications/{app_id}/variant", json={"base_resume_id": resume_id}
    )
    return app_id


def test_a_burst_of_saves_costs_exactly_one_call(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_application(client, sample_resume, "Burst Co")
    calls = stub_analysis(monkeypatch)
    queue = tasks.AnalysisQueue(delay=0.1, enabled=True)

    for _ in range(5):
        queue.schedule(app_id)
        time.sleep(0.02)

    assert wait_for(lambda: len(calls) == 1)
    # Give a straggler every chance to show up before declaring one call.
    time.sleep(0.3)
    assert len(calls) == 1


def test_each_save_pushes_the_deadline_out(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_application(client, sample_resume, "Deadline Co")
    calls = stub_analysis(monkeypatch)
    queue = tasks.AnalysisQueue(delay=0.3, enabled=True)

    queue.schedule(app_id)
    time.sleep(0.2)
    queue.schedule(app_id)
    time.sleep(0.2)

    # 0.4s of typing has passed; the original deadline would have fired by now.
    assert calls == []
    assert wait_for(lambda: len(calls) == 1)


def test_nothing_changing_spends_nothing(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_application(client, sample_resume, "Unchanged Co")
    calls = stub_analysis(monkeypatch)
    queue = tasks.AnalysisQueue(delay=0.05, enabled=True)

    queue.schedule(app_id)
    assert wait_for(lambda: len(calls) == 1)

    # Same job description, same resume: the saved hash still matches.
    queue.schedule(app_id)
    time.sleep(0.4)

    assert len(calls) == 1


def test_an_application_with_no_resume_is_skipped(client: TestClient, monkeypatch):
    app_id = client.post(
        "/api/applications",
        json={"company": "No Resume Co", "role": "MLE", "job_description": JD},
    ).json()["id"]
    calls = stub_analysis(monkeypatch)
    queue = tasks.AnalysisQueue(delay=0.05, enabled=True)

    queue.schedule(app_id)
    time.sleep(0.4)

    assert calls == []


def test_an_application_with_no_job_description_is_skipped(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = client.post(
        "/api/applications", json={"company": "No JD Co", "role": "MLE"}
    ).json()["id"]
    resume_id = client.post(
        "/api/resumes", json={"name": "base-nojd", "data": sample_resume}
    ).json()["id"]
    client.post(
        f"/api/applications/{app_id}/variant", json={"base_resume_id": resume_id}
    )
    calls = stub_analysis(monkeypatch)
    queue = tasks.AnalysisQueue(delay=0.05, enabled=True)

    queue.schedule(app_id)
    time.sleep(0.4)

    assert calls == []


def test_switching_the_queue_off_makes_it_manual_again(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_application(client, sample_resume, "Manual Co")
    calls = stub_analysis(monkeypatch)
    queue = tasks.AnalysisQueue(delay=0.05, enabled=False)

    queue.schedule(app_id)
    time.sleep(0.3)

    assert calls == []
    assert queue.state(app_id) == "idle"


def test_a_failing_analysis_is_reported_not_raised(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_application(client, sample_resume, "Broken Co")
    stub_analysis(monkeypatch)

    def explode(job_description, resume, lessons):
        raise RuntimeError("not logged in")

    monkeypatch.setattr(tasks.gap, "analyse", explode)
    queue = tasks.AnalysisQueue(delay=0.05, enabled=True)

    queue.schedule(app_id)

    assert wait_for(lambda: queue.state(app_id) == "error")
    assert "not logged in" in queue.error(app_id)


def test_the_result_is_saved_and_readable(
    client: TestClient, sample_resume: dict, monkeypatch
):
    app_id = ready_application(client, sample_resume, "Saved Co")
    calls = stub_analysis(monkeypatch)
    queue = tasks.AnalysisQueue(delay=0.05, enabled=True)

    queue.schedule(app_id)
    assert wait_for(lambda: len(calls) == 1)

    body = client.get(f"/api/applications/{app_id}/reading").json()
    assert body["stale"] is False
    assert body["lesson_count"] == 1


def test_reading_before_anything_has_run_is_not_an_error(client: TestClient):
    app_id = client.post(
        "/api/applications", json={"company": "Fresh Co", "role": "MLE"}
    ).json()["id"]

    res = client.get(f"/api/applications/{app_id}/reading")

    assert res.status_code == 200
    assert res.json()["gaps"] == []
    assert res.json()["state"] == "idle"
