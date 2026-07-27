"""Link handling. Extraction copies URLs verbatim, so bare domains show up."""

from apply_track.render import _href, render_html
from apply_track.schemas import ResumeJSON


def test_bare_domain_gets_a_scheme():
    # Without this the anchor is a relative URL and the link is dead in the PDF.
    assert _href("github.com/priyar") == "https://github.com/priyar"


def test_existing_scheme_is_left_alone():
    assert _href("https://example.com") == "https://example.com"
    assert _href("http://example.com") == "http://example.com"
    assert _href("mailto:a@b.com") == "mailto:a@b.com"


def test_bare_email_becomes_mailto():
    assert _href("someone@example.com") == "mailto:someone@example.com"


def test_blank_stays_blank():
    assert _href("   ") == ""


def test_rendered_links_are_absolute(sample_resume):
    resume = ResumeJSON.model_validate(sample_resume)
    resume.basics.links = [{"label": "GitHub", "url": "github.com/ada"}]
    resume.sections[0].items[0].url = "acme.example/project"

    html = render_html(resume)

    assert 'href="https://github.com/ada"' in html
    assert 'href="https://acme.example/project"' in html
