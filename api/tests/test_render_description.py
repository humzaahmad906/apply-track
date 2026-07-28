"""Entries whose content is prose rather than a bulleted list.

Real resumes often write a paragraph under each role instead of bullets. That
prose belongs in `description`; rendering it as a bullet point puts a glyph in
front of a paragraph and reads wrong.
"""

from apply_track.render import render_html
from apply_track.schemas import ResumeJSON

TWO_PARAGRAPHS = (
    "Leading development of an on-premise document pipeline.\n"
    "Tracks documents on a moving belt and applies a custom OCR engine."
)


def _resume(**item_overrides) -> ResumeJSON:
    return ResumeJSON.model_validate(
        {
            "basics": {"name": "Test"},
            "sections": [
                {
                    "kind": "experience",
                    "title": "Experience",
                    "items": [
                        {
                            "title": "Senior ML Engineer",
                            "subtitle": "PackageX",
                            "location": "Islamabad",
                            **item_overrides,
                        }
                    ],
                }
            ],
        }
    )


def test_description_renders_without_a_bullet_glyph():
    html = render_html(_resume(description="A paragraph of prose about the role."))

    assert "A paragraph of prose about the role." in html
    # The prose must sit in a paragraph, not inside a list item.
    assert "<li>A paragraph of prose" not in html


def test_multi_paragraph_description_keeps_its_line_breaks():
    html = render_html(_resume(description=TWO_PARAGRAPHS))

    assert "white-space: pre-line" in html
    assert "custom OCR engine." in html
    assert "on-premise document pipeline.\n" in html


def test_description_and_bullets_can_coexist():
    html = render_html(
        _resume(
            description="Prose summary of the role.",
            bullets=[{"text": "A genuine bullet point."}],
        )
    )

    assert "Prose summary of the role." in html
    assert "<li>A genuine bullet point.</li>" in html


def test_location_renders_separately_from_the_employer():
    """The parser splits "PackageX (Islamabad)"; the two must not re-merge."""
    html = render_html(_resume(start="July 2024", current=True))

    assert "PackageX" in html
    assert "Islamabad" in html
    # Employer sits in the title line, place in the date/meta column.
    assert "PackageX (Islamabad)" not in html
