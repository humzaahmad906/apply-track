from apply_track.render import render_html, safe_filename
from apply_track.schemas import ResumeJSON


def test_render_includes_basics_and_bullets(sample_resume):
    html = render_html(ResumeJSON.model_validate(sample_resume))

    assert "Ada Lovelace" in html
    assert "Analytical Engine Co" in html
    assert "Wrote the first algorithm." in html
    assert "Mathematics, Notation" in html


def test_excluded_nodes_never_reach_the_page(sample_resume):
    resume = ResumeJSON.model_validate(sample_resume)
    resume.sections[0].items[0].bullets[0].include = False
    resume.sections[1].include = False

    html = render_html(resume)

    assert "Wrote the first algorithm." not in html
    assert "Documented Bernoulli number computation." in html
    assert "Mathematics, Notation" not in html


def test_dates_use_present_for_current_roles(sample_resume):
    resume = ResumeJSON.model_validate(sample_resume)
    item = resume.sections[0].items[0]
    item.current = True
    item.end = "1843"

    html = render_html(resume)

    assert "Present" in html


def test_html_is_escaped(sample_resume):
    resume = ResumeJSON.model_validate(sample_resume)
    resume.basics.name = "<script>alert(1)</script>"

    html = render_html(resume)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_same_input_renders_identically(sample_resume):
    resume = ResumeJSON.model_validate(sample_resume)

    assert render_html(resume) == render_html(resume)


def test_safe_filename_strips_path_and_odd_characters():
    name = safe_filename("Ada Lovelace", "Acme/Corp", "../ML Engineer")

    assert name.endswith(".pdf")
    assert "/" not in name
    assert ".." not in name.removesuffix(".pdf")
