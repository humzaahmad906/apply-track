"""Course index parsing. No network: the GitHub tree payload is supplied."""

from apply_track import courses as mod
from apply_track.courses import _parse_tree, as_prompt_index, courses

TREE = {
    "tree": [
        {"type": "blob", "path": "README.md"},
        {"type": "blob", "path": "COURSE_GAP_AUDIT.md"},
        {"type": "tree", "path": "content/aws-for-ml"},
        {"type": "blob", "path": "content/aws-for-ml/09-sagemaker-training.md"},
        {"type": "blob", "path": "content/aws-for-ml/12b-terraform-for-aws.md"},
        # Three courses in the repo use underscores, not hyphens.
        {"type": "blob", "path": "content/principal-ml-engineer/01_the_principal_delta.md"},
        {"type": "blob", "path": "content/principal-ml-engineer/00_syllabus.md"},
        {"type": "blob", "path": "content/vlm-guide/00_README_and_roadmap.md"},
        {"type": "blob", "path": "content/aws-for-ml/notes.txt"},
        {"type": "blob", "path": "content/aws-for-ml/diagram.png"},
    ]
}


def test_only_lesson_files_are_indexed():
    lessons = _parse_tree(TREE)

    paths = {x.path for x in lessons}
    assert "README.md" not in paths
    assert "COURSE_GAP_AUDIT.md" not in paths
    assert "content/aws-for-ml/notes.txt" not in paths
    assert len(lessons) == 5


def test_underscore_named_courses_are_not_dropped():
    """These courses were silently missing while the regex demanded a hyphen."""
    lessons = _parse_tree(TREE)

    found = courses(lessons)
    assert found["principal-ml-engineer"] == 2
    assert found["vlm-guide"] == 1


def test_titles_are_readable():
    by_path = {x.path: x for x in _parse_tree(TREE)}

    assert by_path["content/aws-for-ml/09-sagemaker-training.md"].title == (
        "Sagemaker training"
    )
    assert by_path["content/principal-ml-engineer/01_the_principal_delta.md"].title == (
        "The principal delta"
    )
    # Stripping the README token alone would leave "and roadmap".
    assert by_path["content/vlm-guide/00_README_and_roadmap.md"].title == (
        "Course overview"
    )


def test_urls_point_at_github_blobs():
    lesson = next(
        x for x in _parse_tree(TREE) if x.path.endswith("12b-terraform-for-aws.md")
    )

    assert lesson.url == (
        f"https://github.com/{mod.COURSE_REPO}/blob/{mod.COURSE_BRANCH}/"
        "content/aws-for-ml/12b-terraform-for-aws.md"
    )


def test_lettered_lesson_numbers_survive():
    lesson = next(
        x for x in _parse_tree(TREE) if x.path.endswith("12b-terraform-for-aws.md")
    )

    assert lesson.number == "12b"


def test_prompt_index_groups_by_course_and_keeps_paths():
    text = as_prompt_index(_parse_tree(TREE))

    assert "## aws for ml" in text
    # The model must be able to copy an exact path back out.
    assert "content/aws-for-ml/09-sagemaker-training.md :: Sagemaker training" in text
