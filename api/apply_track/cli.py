"""One headless turn of the Claude Code CLI.

Both callers -- resume extraction and gap analysis -- want the same thing: run
`claude -p`, feed the whole prompt over stdin, and get a JSON object back. They
differ only in how long they are willing to wait, so that is the only knob here.

Nothing ever lands on argv. That keeps resume and job-description text off the
command line, which is also what makes the Windows `cmd /c` shim safe: it has
nothing to mis-quote.
"""

from __future__ import annotations

import json
import re
import subprocess

from .config import PARSE_MODEL, claude_argv

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


class CliError(RuntimeError):
    """One CLI turn failed. Callers translate this into their own error."""


def run(prompt: str, timeout: int) -> str:
    """Run one turn and return the model's text."""
    argv = claude_argv(
        ["-p", "--output-format", "json", "--model", PARSE_MODEL, "--max-turns", "1"]
    )
    try:
        proc = subprocess.run(  # noqa: S603 -- fixed argv, no shell, content on stdin
            argv,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CliError(f"Claude CLI timed out after {timeout}s") from exc
    except OSError as exc:
        raise CliError(f"Could not launch the Claude CLI: {exc}") from exc

    if proc.returncode != 0:
        raise CliError(
            f"Claude CLI exited {proc.returncode}: "
            f"{(proc.stderr or proc.stdout or '').strip()[:600]}"
        )

    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise CliError(
            f"Claude CLI returned non-JSON output: {proc.stdout.strip()[:600]}"
        ) from exc

    if envelope.get("is_error") or envelope.get("subtype") != "success":
        detail = (
            envelope.get("result")
            or envelope.get("api_error_status")
            or envelope.get("subtype")
            or "unknown error"
        )
        raise CliError(f"Claude CLI reported an error: {detail}")

    result = envelope.get("result") or ""
    if not result.strip():
        raise CliError("Claude CLI returned an empty result.")
    return result


def only_json(raw: str) -> dict:
    """Pull the JSON object out of the model's reply."""
    cleaned = _FENCE.sub("", raw).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"No JSON object found in reply: {cleaned[:300]}")
    return json.loads(cleaned[start : end + 1])
