"""Runtime settings and cross-platform process resolution."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("APPLY_TRACK_DATA", REPO_ROOT / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "apply_track.db"

# Model used for the resume -> JSON extraction step.
PARSE_MODEL = os.environ.get("APPLY_TRACK_MODEL", "claude-opus-5")

# Seconds to wait for one `claude -p` invocation before giving up.
PARSE_TIMEOUT = int(os.environ.get("APPLY_TRACK_PARSE_TIMEOUT", "240"))

# Explicit override, e.g. APPLY_TRACK_CLAUDE_BIN=C:\Users\me\claude.exe
CLAUDE_BIN = os.environ.get("APPLY_TRACK_CLAUDE_BIN", "")

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class ClaudeCliNotFound(RuntimeError):
    """Raised when the Claude Code CLI cannot be located on PATH."""


def ensure_dirs() -> None:
    for d in (DATA_DIR, UPLOAD_DIR, EXPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)


def find_claude() -> str:
    """Absolute path to the Claude Code CLI, or raise."""
    exe = CLAUDE_BIN or shutil.which("claude")
    if not exe:
        raise ClaudeCliNotFound(
            "Claude Code CLI not found on PATH. Install it and run `claude` once "
            "to log in, or set APPLY_TRACK_CLAUDE_BIN to its full path."
        )
    return exe


def claude_argv(args: list[str]) -> list[str]:
    """Build an argv list that launches the CLI on this platform.

    On Windows an npm-installed `claude` resolves to `claude.cmd`, which
    CreateProcess refuses to execute directly, so it needs a `cmd /c` prefix.
    Untrusted content is never passed here -- resume text goes over stdin.
    """
    exe = find_claude()
    if os.name == "nt" and Path(exe).suffix.lower() in {".cmd", ".bat"}:
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        return [comspec, "/c", exe, *args]
    return [exe, *args]
