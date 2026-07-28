"""Index of lessons in the applied-ml-academy repository.

The repo lays lessons out as content/<course>/NN-slug.md, so a path is enough
to build a course name, a readable title and a GitHub blob URL. Only the tree
listing is fetched -- never 434 individual files -- and the result is cached on
disk so the analysis does not depend on network access on every run.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import COURSE_BRANCH, COURSE_REPO, DATA_DIR, ensure_dirs

logger = logging.getLogger(__name__)

CACHE_PATH = DATA_DIR / "courses.json"
TREE_URL = "https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
BLOB_URL = "https://github.com/{repo}/blob/{branch}/{path}"

# Courses are inconsistent about the separator: most use NN-slug-words.md, but
# ml-system-design, principal-ml-engineer and vlm-guide use NN_slug_words.md.
# Accept either, or those three courses drop out of the index silently.
_LESSON = re.compile(r"^content/(?P<course>[^/]+)/(?P<num>\d+[a-z]?)[-_](?P<slug>.+)\.md$")
FETCH_TIMEOUT = 20


class CourseIndexError(RuntimeError):
    pass


@dataclass(frozen=True)
class Lesson:
    course: str
    number: str
    title: str
    path: str
    url: str


def _titleise(slug: str) -> str:
    words = slug.replace("-", " ").replace("_", " ").strip()
    # A few courses name their intro file README_and_roadmap or README_syllabus.
    # Stripping the token alone leaves "and roadmap", so relabel the whole thing.
    if "readme" in words.lower():
        return "Course overview"
    return words[:1].upper() + words[1:] if words else slug


def _course_label(name: str) -> str:
    return name.replace("-", " ")


def _parse_tree(payload: dict) -> list[Lesson]:
    if "tree" not in payload:
        raise CourseIndexError(
            f"GitHub returned no tree: {payload.get('message', 'unknown error')}"
        )

    lessons: list[Lesson] = []
    for entry in payload["tree"]:
        if entry.get("type") != "blob":
            continue
        match = _LESSON.match(entry["path"])
        if not match:
            continue
        lessons.append(
            Lesson(
                course=match["course"],
                number=match["num"],
                title=_titleise(match["slug"]),
                path=entry["path"],
                url=BLOB_URL.format(
                    repo=COURSE_REPO, branch=COURSE_BRANCH, path=entry["path"]
                ),
            )
        )

    lessons.sort(key=lambda x: (x.course, x.number))
    return lessons


def fetch_index() -> list[Lesson]:
    """Pull the lesson list from GitHub. Public repo, so no token needed."""
    url = TREE_URL.format(repo=COURSE_REPO, branch=COURSE_BRANCH)
    request = urllib.request.Request(  # noqa: S310 -- fixed https host
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": "apply-track"}
    )
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise CourseIndexError(
            f"GitHub returned {exc.code} for {COURSE_REPO}. If the repo is "
            "private, the index cannot be built without a token."
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise CourseIndexError(f"Could not reach GitHub: {exc}") from exc

    lessons = _parse_tree(payload)
    if not lessons:
        raise CourseIndexError(
            f"No lessons matched content/<course>/NN-slug.md in {COURSE_REPO}."
        )
    return lessons


def save_index(lessons: list[Lesson]) -> None:
    ensure_dirs()
    CACHE_PATH.write_text(
        json.dumps(
            {"repo": COURSE_REPO, "branch": COURSE_BRANCH,
             "lessons": [asdict(x) for x in lessons]},
            indent=1,
        ),
        encoding="utf-8",
    )


def load_cached() -> list[Lesson]:
    if not CACHE_PATH.exists():
        return []
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return [Lesson(**x) for x in payload.get("lessons", [])]
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("Course cache is unreadable, ignoring it: %s", exc)
        return []


def get_index(refresh: bool = False) -> list[Lesson]:
    """Cached lesson index, fetching only when empty or explicitly refreshed."""
    if not refresh:
        cached = load_cached()
        if cached:
            return cached
    lessons = fetch_index()
    save_index(lessons)
    logger.info("Indexed %d lessons from %s", len(lessons), COURSE_REPO)
    return lessons


def courses(lessons: list[Lesson]) -> dict[str, int]:
    out: dict[str, int] = {}
    for lesson in lessons:
        out[lesson.course] = out.get(lesson.course, 0) + 1
    return dict(sorted(out.items()))


def as_prompt_index(lessons: list[Lesson]) -> str:
    """Compact catalogue for the model: one line per lesson, grouped by course."""
    lines: list[str] = []
    current = ""
    for lesson in lessons:
        if lesson.course != current:
            current = lesson.course
            lines.append(f"\n## {_course_label(current)}")
        lines.append(f"{lesson.path} :: {lesson.title}")
    return "\n".join(lines).strip()
