"""Put a built project onto the portfolio site.

The site is plain Jekyll with hand-written Bootstrap cards, so this writes the
same markup by hand rather than introducing a data file the site would have to
learn to read. One card, inserted into one of the two existing grids.

Nothing is committed. The change lands in the working tree so the diff can be
read before anything reaches a public page.
"""

from __future__ import annotations

import logging
import re
from html import escape
from pathlib import Path

from .config import SITE_DIR

logger = logging.getLogger(__name__)

PROJECTS_PAGE = "projects.html"

# The two card grids on the page, keyed by the heading above each.
SECTIONS = {"featured": "/ featured", "earlier": "/ earlier"}

# Where a grid ends. Cards are inserted just before this line.
_GRID_END = re.compile(r"^\s*</div>\s*$")


class PortfolioError(RuntimeError):
    pass


def _page() -> Path:
    if not SITE_DIR.exists():
        raise PortfolioError(
            f"No portfolio checkout at {SITE_DIR}. Clone the site there, or "
            "point APPLY_TRACK_SITE somewhere else."
        )
    page = SITE_DIR / PROJECTS_PAGE
    if not page.exists():
        raise PortfolioError(f"{page} is missing — is that the right checkout?")
    return page


# The resume bullets carry <throughput>-style gaps until real numbers exist.
# On a resume that is a visible reminder; on a public page it is embarrassing.
_PLACEHOLDER = re.compile(r"<[A-Za-z][A-Za-z0-9 _/+-]*>")


def default_tags(stack: str, limit: int = 3) -> str:
    """The site writes tags as "Org · Thing · Thing".

    Deliberately no organisation: the only company this module knows about is
    the one being applied to, and tagging a personal project with it would
    imply the work was done there. Add the real one when it belongs to a job.
    """
    return " · ".join([t.strip() for t in stack.split(",") if t.strip()][:limit])


def default_blurb(spec: dict) -> str:
    """The strongest line, which is the one carrying a result.

    The problem paragraph is three times longer than any card on the page, so
    it is a poor default -- the bullets are already written to be scanned.
    """
    bullets = [b.strip() for b in spec.get("bullets", []) if b.strip()]
    if bullets:
        return " ".join(bullets[:2])
    problem = (spec.get("problem") or "").strip()
    return problem.split(". ")[0] + "." if problem else ""


def card_html(title: str, blurb: str, tags: str) -> str:
    """One card, matching the markup already on the page."""
    dotted = " &middot; ".join(escape(t.strip()) for t in tags.split("·") if t.strip())
    return (
        '      <div class="card">\n'
        f'        <div class="tags">{dotted}</div>\n'
        f"        <h3>{escape(title.strip())}</h3>\n"
        f"        <p>{escape(blurb.strip())}</p>\n"
        "      </div>\n"
    )


def already_there(title: str) -> bool:
    return f"<h3>{escape(title.strip())}</h3>" in _page().read_text(encoding="utf-8")


def _grid_bounds(lines: list[str], section: str) -> tuple[int, int]:
    """Find the card grid under the given heading."""
    label = SECTIONS[section]
    start = next((i for i, l in enumerate(lines) if label in l), None)
    if start is None:
        raise PortfolioError(f"No '{label}' heading in {PROJECTS_PAGE}.")

    grid = next(
        (i for i in range(start, len(lines)) if 'class="card-grid' in lines[i]), None
    )
    if grid is None:
        raise PortfolioError(f"No card grid under '{label}'.")

    # The grid closes at the first </div> sitting at its own indentation.
    depth = 0
    for i in range(grid + 1, len(lines)):
        if '<div class="card"' in lines[i]:
            depth += 1
        elif _GRID_END.match(lines[i]):
            if depth == 0:
                return grid, i
            depth -= 1
    raise PortfolioError(f"Could not find the end of the '{label}' grid.")


def publish(
    title: str, blurb: str, tags: str, section: str = "featured"
) -> dict[str, object]:
    """Insert the card and leave the change uncommitted."""
    if section not in SECTIONS:
        raise PortfolioError(f"Section must be one of {', '.join(SECTIONS)}.")

    title, blurb = title.strip(), blurb.strip()
    if not title:
        raise PortfolioError("Give the card a title.")
    if not blurb:
        raise PortfolioError("Give the card a description.")

    leftover = _PLACEHOLDER.findall(f"{title} {blurb}")
    if leftover:
        raise PortfolioError(
            f"Still has placeholders: {', '.join(sorted(set(leftover)))}. "
            "Put the real numbers in before this goes on a public page."
        )

    if already_there(title):
        raise PortfolioError(
            f"“{title}” is already on the projects page. Edit it there instead."
        )

    page = _page()
    lines = page.read_text(encoding="utf-8").splitlines(keepends=True)
    _, end = _grid_bounds(lines, section)

    # The page separates cards with one blank line and closes the grid on the
    # line after the last one.
    lines.insert(end, f"{card_html(title, blurb, tags)}\n")
    page.write_text("".join(lines), encoding="utf-8")

    logger.info("Added %s to the portfolio under %s", title, section)
    return {
        "ok": True,
        "path": str(page),
        "section": section,
        "title": title,
        "committed": False,
    }
