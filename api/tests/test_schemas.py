from apply_track.schemas import ResumeJSON, assign_ids, resolve


def test_unknown_section_kind_becomes_custom():
    resume = ResumeJSON.model_validate(
        {"sections": [{"kind": "Volunteering", "title": "Volunteering", "items": []}]}
    )
    assert resume.sections[0].kind == "custom"


def test_kind_aliases_are_normalised():
    resume = ResumeJSON.model_validate(
        {
            "sections": [
                {"kind": "Work Experience", "title": "Work", "items": []},
                {"kind": "Capstone Projects", "title": "Capstone", "items": []},
                {"kind": "TECHNICAL_SKILLS", "title": "Skills", "items": []},
            ]
        }
    )
    assert [s.kind for s in resume.sections] == ["experience", "projects", "skills"]


def test_extra_keys_from_the_model_are_dropped():
    resume = ResumeJSON.model_validate(
        {
            "basics": {"name": "A", "confidence": 0.9},
            "sections": [],
            "notes": "chatty model",
        }
    )
    assert resume.basics.name == "A"


def test_assign_ids_is_unique_across_every_node(sample_resume):
    resume = assign_ids(ResumeJSON.model_validate(sample_resume))
    ids = [s.id for s in resume.sections]
    for section in resume.sections:
        ids.extend(i.id for i in section.items)
        for item in section.items:
            ids.extend(b.id for b in item.bullets)
    assert len(ids) == len(set(ids))


def test_resolve_drops_excluded_nodes(sample_resume):
    resume = ResumeJSON.model_validate(sample_resume)
    resume.sections[1].include = False
    resume.sections[0].items[0].bullets[0].include = False

    out = resolve(resume)

    assert [s.kind for s in out.sections] == ["experience"]
    assert [b.text for b in out.sections[0].items[0].bullets] == [
        "Documented Bernoulli number computation."
    ]


def test_resolve_drops_a_section_left_with_no_items(sample_resume):
    resume = ResumeJSON.model_validate(sample_resume)
    for item in resume.sections[0].items:
        item.include = False

    out = resolve(resume)

    assert all(s.kind != "experience" for s in out.sections)


def test_resolve_does_not_mutate_the_input(sample_resume):
    resume = ResumeJSON.model_validate(sample_resume)
    resume.sections[0].items[0].bullets[0].include = False

    resolve(resume)

    # The stored variant must keep every node so the toggle can be undone.
    assert len(resume.sections[0].items[0].bullets) == 2
