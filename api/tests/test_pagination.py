"""Multi-page fragmentation guards.

These render real PDFs through Chromium, so they are skipped when it is not
installed. They exist because the first cut of the stylesheet produced two ugly
artefacts on any resume longer than one page:

  * `break-inside: avoid` on a whole entry punted anything taller than the
    remaining space to the next page, leaving inches of blank paper.
  * without `break-after: avoid`, a section heading was stranded alone at the
    foot of a page with its items overleaf.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from apply_track.render import render_pdf
from apply_track.schemas import ResumeJSON

pymupdf = pytest.importorskip("pymupdf")

SECTION_TITLES = {"EXPERIENCE", "PROJECTS", "EDUCATION", "CERTIFICATIONS"}
LONG_BULLET = (
    "Drove a measurable outcome across several teams, shipping the "
    "instrumentation and cutting tail latency against a frozen benchmark."
)


def _resume(items_per_section: int, bullets_per_item: int) -> ResumeJSON:
    sections = []
    for kind, title in [
        ("experience", "EXPERIENCE"),
        ("projects", "PROJECTS"),
        ("education", "EDUCATION"),
        ("certifications", "CERTIFICATIONS"),
    ]:
        sections.append(
            {
                "kind": kind,
                "title": title,
                "items": [
                    {
                        "title": f"{title[:4]} Role {i}",
                        "subtitle": f"{title[:4]} Employer {i}",
                        "start": f"Jan {2010 + i}",
                        "end": f"Dec {2011 + i}",
                        "bullets": [
                            {"text": f"{title[:4]}{i}.{b} {LONG_BULLET}"}
                            for b in range(bullets_per_item)
                        ],
                    }
                    for i in range(items_per_section)
                ],
            }
        )
    return ResumeJSON.model_validate({"basics": {"name": "Long Resume"}, "sections": sections})


def _pages(path: Path) -> list[list[tuple[float, str]]]:
    """Per page, the text lines sorted top to bottom."""
    doc = pymupdf.open(path)
    out: list[list[tuple[float, str]]] = []
    for page in doc:
        lines: list[tuple[float, str]] = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"]).strip()
                if text:
                    lines.append((line["bbox"][1], text))
        lines.sort(key=lambda t: t[0])
        out.append(lines)
    doc.close()
    return out


def _render(resume: ResumeJSON, name: str) -> Path:
    try:
        return asyncio.run(render_pdf(resume, name))
    except Exception as exc:  # noqa: BLE001 -- Chromium absent is a skip, not a failure
        if "Executable doesn't exist" in str(exc) or "playwright install" in str(exc):
            pytest.skip("Chromium not installed; run `python -m playwright install chromium`")
        raise


@pytest.fixture(scope="module")
def long_pdf() -> Path:
    return _render(_resume(5, 6), "test-pagination-long.pdf")


def test_actually_spans_several_pages(long_pdf: Path):
    assert len(_pages(long_pdf)) > 1, "fixture is meant to overflow one page"


def test_no_section_heading_is_stranded_at_a_page_foot(long_pdf: Path):
    pages = _pages(long_pdf)
    stranded = [
        (n, lines[-1][1])
        for n, lines in enumerate(pages[:-1], start=1)
        if lines and lines[-1][1].strip() in SECTION_TITLES
    ]
    assert stranded == [], f"headings stranded at page foot: {stranded}"


def test_no_page_ends_with_a_large_blank_gap(long_pdf: Path):
    doc = pymupdf.open(long_pdf)
    height = doc[0].rect.height
    doc.close()

    pages = _pages(long_pdf)
    # A normal foot margin plus one line is well under 140pt; more than that
    # means an unbreakable block was pushed wholesale to the next page.
    holes = [
        (n, round(height - lines[-1][0]))
        for n, lines in enumerate(pages[:-1], start=1)
        if lines and (height - lines[-1][0]) > 140
    ]
    assert holes == [], f"pages with a large trailing gap (page, pt): {holes}"


def test_an_entry_taller_than_a_page_still_flows(long_pdf: Path):
    """One huge entry must split across pages rather than blank out a page."""
    pdf = _render(_resume(1, 30), "test-pagination-huge-item.pdf")
    pages = _pages(pdf)

    assert len(pages) > 1
    first_page_lines = len(pages[0])
    assert first_page_lines > 10, (
        f"page 1 has only {first_page_lines} lines; the oversized entry was "
        "pushed off instead of flowing"
    )
