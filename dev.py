#!/usr/bin/env python3
"""Start the API and the web dev server together.

Works the same on macOS and Windows:

    python dev.py

Ctrl-C stops both. Run `python install.py` first if you have not installed yet.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_DIR = ROOT / "api"
WEB_DIR = ROOT / "web"
IS_WINDOWS = os.name == "nt"


def venv_python() -> Path:
    """The API venv interpreter for this platform."""
    if IS_WINDOWS:
        return API_DIR / ".venv" / "Scripts" / "python.exe"
    return API_DIR / ".venv" / "bin" / "python"


def launcher(name: str) -> list[str]:
    """Resolve an executable, adding a `cmd /c` shim for Windows .cmd shims."""
    exe = shutil.which(name)
    if not exe:
        sys.exit(f"'{name}' is not on PATH. Install it and try again.")
    if IS_WINDOWS and Path(exe).suffix.lower() in {".cmd", ".bat"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", exe]
    return [exe]


def main() -> int:
    python = venv_python()
    if not python.exists():
        sys.exit(f"No venv at {python}. Run: python install.py")
    if not (WEB_DIR / "node_modules").exists():
        sys.exit(f"No node_modules in {WEB_DIR}. Run: python install.py")

    api_cmd = [
        str(python),
        "-m",
        "uvicorn",
        "apply_track.main:app",
        "--reload",
        "--port",
        "8000",
    ]
    web_cmd = [*launcher("npm"), "run", "dev"]

    print("api  -> http://127.0.0.1:8000")
    print("web  -> http://localhost:5173")
    print("Ctrl-C to stop both.\n")

    procs: list[subprocess.Popen] = []
    try:
        procs.append(subprocess.Popen(api_cmd, cwd=API_DIR))
        procs.append(subprocess.Popen(web_cmd, cwd=WEB_DIR))
        while True:
            for proc in procs:
                if proc.poll() is not None:
                    print(f"\nA process exited with {proc.returncode}; shutting down.")
                    return proc.returncode or 1
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("\nStopping…")
        return 0
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
