"""Deterministic ResumeJSON -> HTML -> PDF.

One template drives both the on-screen preview and the exported PDF, so the
preview cannot drift from the file. Chromium ships with Playwright, which keeps
output consistent between macOS and Windows without a system PDF stack.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .config import EXPORT_DIR, ensure_dirs
from .schemas import Item, ResumeJSON, resolve

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
PAGE_SIZE = "Letter"
MARGIN = "0.55in"
# Continuation pages need room in the top margin for the running header.
MARGIN_TOP_WITH_HEADER = "0.8in"
DEFAULT_FONT = "sans"

# Dots are dropped along with everything else odd: the ".pdf" is added here, so
# nothing in the stem needs one, and this keeps ".." out of the name entirely.
_UNSAFE = re.compile(r"[^A-Za-z0-9_-]+")
_DASH_RUN = re.compile(r"-{2,}")


class RenderError(RuntimeError):
    pass


def _daterange(item: Item) -> str:
    start, end = item.start.strip(), item.end.strip()
    if item.current:
        end = "Present"
    if start and end:
        return f"{start} – {end}"
    return start or end


def _href(url: str) -> str:
    """Make a bare domain into a usable link.

    Resumes write "github.com/me", and extraction copies that verbatim. Emitted
    as-is it becomes a relative URL and the link is dead in the PDF.
    """
    url = url.strip()
    if not url:
        return ""
    if url.startswith("mailto:") or "://" in url:
        return url
    if "@" in url and "/" not in url:
        return f"mailto:{url}"
    return f"https://{url}"


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        # Escape unconditionally. select_autoescape() keys off the filename
        # suffix, and "resume.html.j2" ends in .j2, so it would leave resume
        # content unescaped and let markup run inside the preview iframe.
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["daterange"] = _daterange
    env.filters["href"] = _href
    return env


def render_html(resume: ResumeJSON, font: str = DEFAULT_FONT) -> str:
    """Resolve include flags, then render the single resume template."""
    template = _env().get_template("resume.html.j2")
    return template.render(
        r=resolve(resume), page_size=PAGE_SIZE, margin=MARGIN, font=font
    )


def safe_filename(*parts: str) -> str:
    stem = "-".join(p.strip() for p in parts if p and p.strip())
    stem = _DASH_RUN.sub("-", _UNSAFE.sub("-", stem)).strip("-")[:120]
    return f"{stem or 'resume'}.pdf"


def _running_header(resume: ResumeJSON) -> str:
    """One line for continuation pages: name, one contact point, page number.

    Chromium has no @page margin boxes, but its print header template does
    substitute .pageNumber and .totalPages, which is the only way to number
    pages here. In a PDF this is ordinary positioned text, so a parser reading
    the page still sees it.
    """
    from html import escape

    bits = [escape(resume.basics.name or "Resume")]
    contact = resume.basics.email or resume.basics.phone
    if contact:
        bits.append(escape(contact))
    label = " &nbsp;·&nbsp; ".join(bits)
    return (
        '<div style="width:100%;font:9pt Helvetica,Arial,sans-serif;color:#444;'
        f'padding:0 0.55in;display:flex;justify-content:space-between;">'
        f"<span>{label}</span>"
        '<span>Page <span class="pageNumber"></span> of '
        '<span class="totalPages"></span></span></div>'
    )


async def render_pdf(
    resume: ResumeJSON, filename: str, font: str = DEFAULT_FONT
) -> Path:
    """Write a PDF for this resume and return its path.

    Rendered twice when the resume runs past one page: the first pass only
    establishes the page count, the second adds the running header. A
    one-page resume never gets one, so it stays clean. Both passes are pure
    functions of the same JSON, so the result is still deterministic.
    """
    import pymupdf
    from playwright.async_api import Error as PlaywrightError
    from playwright.async_api import async_playwright

    ensure_dirs()
    out_path = EXPORT_DIR / filename
    html = render_html(resume, font=font)

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_content(html, wait_until="load")
                # emulate_media("print") drops the screen-only preview styles
                # so the PDF uses the @page rules.
                await page.emulate_media(media="print")

                pdf_bytes = await page.pdf(
                    format=PAGE_SIZE,
                    print_background=True,
                    prefer_css_page_size=True,
                    margin={
                        "top": MARGIN,
                        "bottom": MARGIN,
                        "left": MARGIN,
                        "right": MARGIN,
                    },
                )

                with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
                    page_count = len(doc)

                if page_count > 1:
                    pdf_bytes = await page.pdf(
                        format=PAGE_SIZE,
                        print_background=True,
                        prefer_css_page_size=True,
                        display_header_footer=True,
                        header_template=_running_header(resume),
                        footer_template="<span></span>",
                        margin={
                            "top": MARGIN_TOP_WITH_HEADER,
                            "bottom": MARGIN,
                            "left": MARGIN,
                            "right": MARGIN,
                        },
                    )
            finally:
                await browser.close()
    except PlaywrightError as exc:
        raise RenderError(
            f"PDF rendering failed: {exc}. If Chromium is missing, run "
            f"`python -m playwright install chromium` inside the api venv."
        ) from exc

    out_path.write_bytes(pdf_bytes)
    logger.info("Rendered %s (%d page(s))", out_path, page_count)
    return out_path
