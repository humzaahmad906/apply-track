"""FastAPI entrypoint. Single user, no auth -- run it on your own machine."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, PARSE_MODEL, ClaudeCliNotFound, find_claude
from .db import init_db
from .routers import applications, coach, library, resumes, variants

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        logger.info("Claude CLI: %s (model %s)", find_claude(), PARSE_MODEL)
    except ClaudeCliNotFound as exc:
        # Parsing is one of two flows; everything else still works without it.
        logger.warning("%s Resume parsing will fail until this is fixed.", exc)
    yield


app = FastAPI(title="apply-track", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resumes.router)
app.include_router(applications.router)
app.include_router(variants.router)
app.include_router(library.router)
app.include_router(coach.router)


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Reports which optional pieces are actually available on this machine."""
    try:
        cli: str | None = find_claude()
        cli_error = ""
    except ClaudeCliNotFound as exc:
        cli, cli_error = None, str(exc)

    chromium = False
    chromium_error = ""
    try:
        from pathlib import Path

        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            # executable_path is the expected location, installed or not.
            chromium = Path(pw.chromium.executable_path).exists()
        if not chromium:
            chromium_error = (
                "Chromium is not installed. Run "
                "`python -m playwright install chromium` in the api venv. "
                "Until then, use the preview and print to PDF from the browser."
            )
    except Exception as exc:  # noqa: BLE001 -- health probe, never raise
        chromium_error = str(exc)

    return {
        "ok": True,
        "claude_cli": cli,
        "claude_cli_error": cli_error,
        "parse_model": PARSE_MODEL,
        "pdf_export": chromium,
        "pdf_export_error": chromium_error,
    }
