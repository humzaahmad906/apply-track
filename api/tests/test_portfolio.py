"""Writing a card onto the portfolio site.

Every test runs against a throwaway copy of the page, never a real checkout.
"""

from __future__ import annotations

import pytest

from apply_track import portfolio

PAGE = """\
---
layout: default
title: Projects
---

<section>
  <div class="container-wide">

    <div class="section-heading reveal">
      <div><span class="label">/ featured</span><h2>Featured</h2></div>
    </div>
    <div class="card-grid reveal">

      <div class="card">
        <div class="tags">PackageX &middot; CV</div>
        <h3>An existing thing</h3>
        <p>Already here.</p>
      </div>

    </div>

    <div class="section-heading reveal">
      <div><span class="label">/ earlier</span><h2>Earlier work</h2></div>
    </div>
    <div class="card-grid reveal">

      <div class="card">
        <div class="tags">RevolveAI &middot; NLP</div>
        <h3>Something older</h3>
        <p>From before.</p>
      </div>

    </div>
  </div>
</section>
"""

SPEC = {
    "title": "LedgerAgent",
    "stack": "Python, FastAPI, Postgres",
    "problem": "Finance teams sit on scanned invoices. Numbers exist only as pixels.",
    "bullets": ["Built a document-to-SQL service.", "Cut wrong answers sharply."],
}


@pytest.fixture
def site(tmp_path, monkeypatch):
    (tmp_path / "projects.html").write_text(PAGE, encoding="utf-8")
    monkeypatch.setattr(portfolio, "SITE_DIR", tmp_path)
    return tmp_path


def page(site) -> str:
    return (site / "projects.html").read_text(encoding="utf-8")


def test_a_card_lands_in_the_featured_grid(site):
    portfolio.publish("LedgerAgent", "Turns invoices into a warehouse.", "PackageX · RAG")

    body = page(site)
    assert "<h3>LedgerAgent</h3>" in body
    # In the featured grid, after the card already there.
    featured = body.index("/ featured")
    earlier = body.index("/ earlier")
    assert featured < body.index("<h3>LedgerAgent</h3>") < earlier


def test_it_can_go_under_earlier_work_instead(site):
    portfolio.publish("Old thing", "A description.", "RevolveAI", section="earlier")

    body = page(site)
    assert body.index("/ earlier") < body.index("<h3>Old thing</h3>")


def test_the_markup_matches_the_pages_own_cards(site):
    portfolio.publish("LedgerAgent", "Turns invoices into a warehouse.", "PackageX · RAG")

    assert (
        '      <div class="card">\n'
        '        <div class="tags">PackageX &middot; RAG</div>\n'
        "        <h3>LedgerAgent</h3>\n"
        "        <p>Turns invoices into a warehouse.</p>\n"
        "      </div>\n"
    ) in page(site)


def test_unfilled_placeholders_never_reach_a_public_page(site):
    """<throughput> is a useful reminder on a resume and a disaster on a site."""
    with pytest.raises(portfolio.PortfolioError, match="placeholders"):
        portfolio.publish(
            "LedgerAgent", "Served <N> documents at <F1> F1.", "PackageX"
        )

    assert "LedgerAgent" not in page(site)


def test_the_same_project_is_not_added_twice(site):
    portfolio.publish("LedgerAgent", "A description.", "PackageX")

    with pytest.raises(portfolio.PortfolioError, match="already on"):
        portfolio.publish("LedgerAgent", "A different description.", "PackageX")

    assert page(site).count("<h3>LedgerAgent</h3>") == 1


def test_an_empty_title_or_blurb_is_refused(site):
    with pytest.raises(portfolio.PortfolioError):
        portfolio.publish("  ", "A description.", "PackageX")
    with pytest.raises(portfolio.PortfolioError):
        portfolio.publish("LedgerAgent", "   ", "PackageX")


def test_an_unknown_section_is_refused(site):
    with pytest.raises(portfolio.PortfolioError, match="Section must be"):
        portfolio.publish("LedgerAgent", "A description.", "PackageX", "sidebar")


def test_the_wording_is_escaped_into_the_page(site):
    portfolio.publish('Tool & Co "v2"', "Handles A & B, 5 > 3.", "PackageX & Co")

    body = page(site)
    assert '<h3>Tool &amp; Co &quot;v2&quot;</h3>' in body
    assert "<p>Handles A &amp; B, 5 &gt; 3.</p>" in body
    assert "PackageX &amp; Co" in body


def test_angle_brackets_are_refused_outright(site):
    """They are either a leftover placeholder or markup that would be escaped
    into visible junk. Neither belongs on the page."""
    with pytest.raises(portfolio.PortfolioError, match="placeholders"):
        portfolio.publish("Tool", "Handles <b>bold</b> input.", "PackageX")


def test_a_missing_checkout_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(portfolio, "SITE_DIR", tmp_path / "nowhere")

    with pytest.raises(portfolio.PortfolioError, match="No portfolio checkout"):
        portfolio.publish("LedgerAgent", "A description.", "PackageX")


def test_the_default_blurb_uses_the_bullets_not_the_essay(site):
    """The problem paragraph is three times longer than any card on the page."""
    blurb = portfolio.default_blurb(SPEC)

    assert blurb == "Built a document-to-SQL service. Cut wrong answers sharply."


def test_the_default_blurb_falls_back_to_the_problem(site):
    blurb = portfolio.default_blurb({**SPEC, "bullets": []})

    assert blurb == "Finance teams sit on scanned invoices."


def test_default_tags_do_not_name_the_company_being_applied_to(site):
    """Tagging a personal project "Northbay" would imply it was work for them."""
    tags = portfolio.default_tags("Python, FastAPI, Postgres, Redis")

    assert tags == "Python · FastAPI · Postgres"
