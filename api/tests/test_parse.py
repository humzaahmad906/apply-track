"""Parser tests. The CLI is stubbed, so these never hit the network."""

from __future__ import annotations

import json
import subprocess

import pytest

from apply_track import cli
from apply_track.parse import ParseError, parse_resume

GOOD = {
    "basics": {"name": "Ada Lovelace"},
    "sections": [
        {
            "kind": "experience",
            "title": "Experience",
            "items": [{"title": "Analyst", "bullets": [{"text": "Did the thing."}]}],
        }
    ],
}


def envelope(result: str, **overrides) -> str:
    payload = {"is_error": False, "subtype": "success", "result": result}
    payload.update(overrides)
    return json.dumps(payload)


class FakeCompleted:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def stub_cli(monkeypatch, *responses: FakeCompleted) -> list[dict]:
    """Replace subprocess.run, returning each response in turn."""
    calls: list[dict] = []
    queue = list(responses)

    def fake_run(argv, **kwargs):
        calls.append({"argv": argv, "input": kwargs.get("input", "")})
        return queue.pop(0) if queue else FakeCompleted(envelope("{}"))

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "claude_argv", lambda args: ["claude", *args])
    return calls


def test_happy_path_assigns_ids(monkeypatch):
    stub_cli(monkeypatch, FakeCompleted(envelope(json.dumps(GOOD))))

    resume = parse_resume("Ada Lovelace\nAnalyst")

    assert resume.basics.name == "Ada Lovelace"
    assert resume.sections[0].items[0].id
    assert resume.sections[0].items[0].bullets[0].id


def test_resume_text_travels_on_stdin_not_argv(monkeypatch):
    calls = stub_cli(monkeypatch, FakeCompleted(envelope(json.dumps(GOOD))))

    parse_resume("SECRET RESUME BODY")

    argv, stdin = calls[0]["argv"], calls[0]["input"]
    assert "SECRET RESUME BODY" in stdin
    assert not any("SECRET RESUME BODY" in str(a) for a in argv)


def test_markdown_fence_is_stripped(monkeypatch):
    fenced = f"```json\n{json.dumps(GOOD)}\n```"
    stub_cli(monkeypatch, FakeCompleted(envelope(fenced)))

    assert parse_resume("text").basics.name == "Ada Lovelace"


def test_prose_around_the_object_is_tolerated(monkeypatch):
    chatty = f"Here you go:\n{json.dumps(GOOD)}\nHope that helps."
    stub_cli(monkeypatch, FakeCompleted(envelope(chatty)))

    assert parse_resume("text").sections[0].kind == "experience"


def test_invalid_json_retries_once_then_succeeds(monkeypatch):
    calls = stub_cli(
        monkeypatch,
        FakeCompleted(envelope("not json at all")),
        FakeCompleted(envelope(json.dumps(GOOD))),
    )

    resume = parse_resume("text")

    assert len(calls) == 2
    assert "could not be used" in calls[1]["input"]
    assert resume.basics.name == "Ada Lovelace"


def test_empty_sections_retries(monkeypatch):
    calls = stub_cli(
        monkeypatch,
        FakeCompleted(envelope(json.dumps({"basics": {}, "sections": []}))),
        FakeCompleted(envelope(json.dumps(GOOD))),
    )

    parse_resume("text")

    assert len(calls) == 2


def test_gives_up_after_the_retry(monkeypatch):
    stub_cli(
        monkeypatch,
        FakeCompleted(envelope("garbage")),
        FakeCompleted(envelope("still garbage")),
    )

    with pytest.raises(ParseError):
        parse_resume("text")


def test_cli_error_envelope_is_surfaced(monkeypatch):
    stub_cli(
        monkeypatch,
        FakeCompleted(
            json.dumps({"is_error": True, "subtype": "error", "result": "rate limited"})
        ),
        FakeCompleted(
            json.dumps({"is_error": True, "subtype": "error", "result": "rate limited"})
        ),
    )

    with pytest.raises(ParseError, match="rate limited"):
        parse_resume("text")


def test_non_zero_exit_is_surfaced(monkeypatch):
    stub_cli(
        monkeypatch,
        FakeCompleted("", returncode=1, stderr="not logged in"),
        FakeCompleted("", returncode=1, stderr="not logged in"),
    )

    with pytest.raises(ParseError, match="not logged in"):
        parse_resume("text")


def test_timeout_is_surfaced(monkeypatch):
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=1)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "claude_argv", lambda args: ["claude", *args])

    with pytest.raises(ParseError, match="timed out"):
        parse_resume("text")


def test_empty_input_never_calls_the_cli(monkeypatch):
    calls = stub_cli(monkeypatch)

    with pytest.raises(ParseError, match="No text"):
        parse_resume("   \n  ")

    assert calls == []
