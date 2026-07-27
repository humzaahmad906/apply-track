#!/usr/bin/env python3
"""One-shot install for macOS and Windows.

    python install.py

Creates the API venv, installs Python and npm dependencies, and downloads the
Chromium build used for PDF export. Safe to re-run.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_DIR = ROOT / "api"
WEB_DIR = ROOT / "web"
IS_WINDOWS = os.name == "nt"


def venv_python() -> Path:
    if IS_WINDOWS:
        return API_DIR / ".venv" / "Scripts" / "python.exe"
    return API_DIR / ".venv" / "bin" / "python"


def launcher(name: str) -> list[str]:
    exe = shutil.which(name)
    if not exe:
        sys.exit(f"'{name}' is not on PATH. Install it and try again.")
    if IS_WINDOWS and Path(exe).suffix.lower() in {".cmd", ".bat"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", exe]
    return [exe]


def run(cmd: list[str], cwd: Path, label: str) -> None:
    print(f"\n=== {label} ===")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        sys.exit(f"{label} failed with exit code {result.returncode}.")


def main() -> int:
    if sys.version_info < (3, 11):
        sys.exit(f"Python 3.11+ required; this is {sys.version.split()[0]}.")

    python = venv_python()
    if not python.exists():
        run([sys.executable, "-m", "venv", ".venv"], API_DIR, "Creating API venv")

    # uv is much faster when available, but plain pip is a fine fallback.
    if shutil.which("uv"):
        run(
            [*launcher("uv"), "pip", "install", "--python", str(python), "-e", ".[dev]"],
            API_DIR,
            "Installing Python dependencies (uv)",
        )
    else:
        run(
            [str(python), "-m", "pip", "install", "--upgrade", "pip"],
            API_DIR,
            "Upgrading pip",
        )
        run(
            [str(python), "-m", "pip", "install", "-e", ".[dev]"],
            API_DIR,
            "Installing Python dependencies (pip)",
        )

    run([*launcher("npm"), "install"], WEB_DIR, "Installing web dependencies")

    # ~130 MB. Without it everything works except server-side PDF export; the
    # preview page can still be printed to PDF from the browser.
    print("\n=== Downloading Chromium for PDF export (~130 MB) ===")
    chromium = subprocess.run(
        [str(python), "-m", "playwright", "install", "chromium"], cwd=API_DIR
    )
    if chromium.returncode != 0:
        print(
            "\nChromium download failed. Everything else is installed --\n"
            "PDF export will return a 503 until you re-run:\n"
            f"  {python} -m playwright install chromium\n"
            "Meanwhile use the preview page and print to PDF from your browser."
        )

    print("\nDone. Start it with:  python dev.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
