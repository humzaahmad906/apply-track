"""Gap analysis. The CLI is stubbed, so these run offline."""

from __future__ import annotations

import json

import pytest

from apply_track import cli
from apply_track.courses import Lesson
from apply_track.gap import GapError, _resume_digest, analyse
from apply_track.schemas import ResumeJSON

LESSONS = [
    Lesson(
        course="kubernetes-for-ml",
        number="03",
        title="Scheduling and autoscaling",
        path="content/kubernetes-for-ml/03-scheduling-and-autoscaling.md",
        url="https://github.com/x/y/blob/main/content/kubernetes-for-ml/03-scheduling-and-autoscaling.md",
    ),
    Lesson(
        course="aws-for-ml",
        number="12b",
        title="Terraform for aws",
        path="content/aws-for-ml/12b-terraform-for-aws.md",
        url="https://github.com/x/y/blob/main/content/aws-for-ml/12b-terraform-for-aws.md",
    ),
]

K8S = "content/kubernetes-for-ml/03-scheduling-and-autoscaling.md"
TERRAFORM = "content/aws-for-ml/12b-terraform-for-aws.md"

REPLY = {
    "gaps": [
        {
            "skill": "Kubernetes",
            "why": "Job wants autoscaled serving; resume shows none.",
            "lessons": [{"path": K8S}],
        }
    ],
    "covered": [
        {"skill": "OCR", "evidence": "PackageX role", "lessons": [{"path": TERRAFORM}]}
    ],
    "basics": [{"skill": "Python", "lessons": [{"path": TERRAFORM}]}],
}


def envelope(result: str) -> str:
    return json.dumps({"is_error": False, "subtype": "success", "result": result})


class FakeCompleted:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def stub(monkeypatch, *responses: FakeCompleted) -> list[dict]:
    calls: list[dict] = []
    queue = list(responses)

    def fake_run(argv, **kwargs):
        calls.append({"argv": argv, "input": kwargs.get("input", "")})
        return queue.pop(0) if queue else FakeCompleted(envelope("{}"))

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "claude_argv", lambda args: ["claude", *args])
    return calls


@pytest.fixture
def resume(sample_resume: dict) -> ResumeJSON:
    return ResumeJSON.model_validate(sample_resume)


def test_happy_path_returns_three_buckets(monkeypatch, resume: ResumeJSON):
    stub(monkeypatch, FakeCompleted(envelope(json.dumps(REPLY))))

    result = analyse("Kubernetes required.", resume, LESSONS)

    assert [g.skill for g in result.gaps] == ["Kubernetes"]
    assert [c.skill for c in result.covered] == ["OCR"]
    assert [b.skill for b in result.basics] == ["Python"]


def test_every_bucket_gets_lessons(monkeypatch, resume: ResumeJSON):
    """Already knowing something is not a reason to withhold the reading."""
    stub(monkeypatch, FakeCompleted(envelope(json.dumps(REPLY))))

    result = analyse("Kubernetes required.", resume, LESSONS)

    assert result.gaps[0].lessons[0].path == K8S
    assert result.covered[0].lessons[0].path == TERRAFORM
    assert result.basics[0].lessons[0].path == TERRAFORM


def test_invented_paths_are_dropped_from_covered_and_basics_too(
    monkeypatch, resume: ResumeJSON
):
    reply = json.loads(json.dumps(REPLY))
    reply["covered"][0]["lessons"] = [{"path": "content/made-up/99-nope.md"}]
    reply["basics"][0]["lessons"] = [{"path": "content/also-made-up/01-nope.md"}]
    stub(monkeypatch, FakeCompleted(envelope(json.dumps(reply))))

    result = analyse("Kubernetes required.", resume, LESSONS)

    assert result.covered[0].lessons == []
    assert result.basics[0].lessons == []


def test_basics_saved_as_plain_strings_still_load(monkeypatch, resume: ResumeJSON):
    """Analyses stored before basics carried lessons must still be readable."""
    reply = json.loads(json.dumps(REPLY))
    reply["basics"] = ["Python", "Git"]
    stub(monkeypatch, FakeCompleted(envelope(json.dumps(reply))))

    result = analyse("Kubernetes required.", resume, LESSONS)

    assert [b.skill for b in result.basics] == ["Python", "Git"]
    assert result.basics[0].lessons == []


def test_lesson_metadata_comes_from_the_catalogue_not_the_model(
    monkeypatch, resume: ResumeJSON
):
    """Titles and URLs are looked up locally, so the model cannot fake a link."""
    reply = json.loads(json.dumps(REPLY))
    reply["gaps"][0]["lessons"][0]["title"] = "TOTALLY WRONG TITLE"
    reply["gaps"][0]["lessons"][0]["url"] = "https://evil.example/phish"
    stub(monkeypatch, FakeCompleted(envelope(json.dumps(reply))))

    lesson = analyse("Kubernetes required.", resume, LESSONS).gaps[0].lessons[0]

    assert lesson.title == "Scheduling and autoscaling"
    assert lesson.url == LESSONS[0].url


def test_invented_lesson_paths_are_discarded(monkeypatch, resume: ResumeJSON):
    reply = json.loads(json.dumps(REPLY))
    reply["gaps"][0]["lessons"] = [
        {"path": "content/kubernetes-for-ml/99-does-not-exist.md"},
        {"path": "content/aws-for-ml/12b-terraform-for-aws.md"},
    ]
    stub(monkeypatch, FakeCompleted(envelope(json.dumps(reply))))

    lessons = analyse("Kubernetes required.", resume, LESSONS).gaps[0].lessons

    assert [x.path for x in lessons] == ["content/aws-for-ml/12b-terraform-for-aws.md"]


def test_duplicate_lessons_within_a_gap_are_deduped(monkeypatch, resume: ResumeJSON):
    reply = json.loads(json.dumps(REPLY))
    path = "content/aws-for-ml/12b-terraform-for-aws.md"
    reply["gaps"][0]["lessons"] = [{"path": path}, {"path": path}]
    stub(monkeypatch, FakeCompleted(envelope(json.dumps(reply))))

    assert len(analyse("x", resume, LESSONS).gaps[0].lessons) == 1


def test_jd_and_resume_travel_on_stdin_not_argv(monkeypatch, resume: ResumeJSON):
    calls = stub(monkeypatch, FakeCompleted(envelope(json.dumps(REPLY))))

    analyse("SECRET JD TEXT", resume, LESSONS)

    argv, stdin = calls[0]["argv"], calls[0]["input"]
    assert "SECRET JD TEXT" in stdin
    assert not any("SECRET JD TEXT" in str(a) for a in argv)
    # The catalogue must reach the model or it cannot cite real paths.
    assert "content/kubernetes-for-ml/03-scheduling-and-autoscaling.md" in stdin


def test_empty_job_description_never_calls_the_cli(monkeypatch, resume: ResumeJSON):
    calls = stub(monkeypatch)

    with pytest.raises(GapError, match="no job description"):
        analyse("   ", resume, LESSONS)

    assert calls == []


def test_empty_catalogue_is_refused(monkeypatch, resume: ResumeJSON):
    calls = stub(monkeypatch)

    with pytest.raises(GapError, match="course index is empty"):
        analyse("Kubernetes required.", resume, [])

    assert calls == []


def test_cli_error_is_surfaced(monkeypatch, resume: ResumeJSON):
    stub(monkeypatch, FakeCompleted("", returncode=1, stderr="not logged in"))

    with pytest.raises(GapError, match="not logged in"):
        analyse("x", resume, LESSONS)


def test_unparseable_reply_is_surfaced(monkeypatch, resume: ResumeJSON):
    stub(monkeypatch, FakeCompleted(envelope("not json")))

    with pytest.raises(GapError):
        analyse("x", resume, LESSONS)


def test_resume_digest_only_contains_included_nodes(resume: ResumeJSON):
    resume.sections[0].items[0].bullets[0].include = False

    digest = _resume_digest(resume)

    # The analysis must judge the resume being sent, not the full base record.
    assert "Wrote the first algorithm." not in digest
    assert "Documented Bernoulli number computation." in digest
    assert "Analytical Engine Co" in digest
