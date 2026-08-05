"""Point the app at a throwaway data directory before it is ever imported."""

from __future__ import annotations

import os
import tempfile

os.environ["APPLY_TRACK_DATA"] = tempfile.mkdtemp(prefix="apply-track-test-")
# Saving a job description or a variant would otherwise schedule a real
# analysis. Tests that want the queue build their own with it switched on.
os.environ["APPLY_TRACK_AUTO_ANALYSE"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from apply_track.db import init_db  # noqa: E402
from apply_track.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database() -> None:
    init_db()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_resume() -> dict:
    return {
        "basics": {
            "name": "Ada Lovelace",
            "headline": "Analytical Engineer",
            "email": "ada@example.com",
            "phone": "+44 20 7000 0000",
            "location": "London, UK",
            "links": [{"label": "GitHub", "url": "https://github.com/ada"}],
            "summary": "Builds engines that compute.",
        },
        "sections": [
            {
                "kind": "experience",
                "title": "Experience",
                "items": [
                    {
                        "title": "Analyst",
                        "subtitle": "Analytical Engine Co",
                        "start": "1842",
                        "end": "1843",
                        "bullets": [
                            {"text": "Wrote the first algorithm."},
                            {"text": "Documented Bernoulli number computation."},
                        ],
                    }
                ],
            },
            {
                "kind": "skills",
                "title": "Skills",
                "items": [{"title": "Languages", "tags": ["Mathematics", "Notation"]}],
            },
        ],
    }
