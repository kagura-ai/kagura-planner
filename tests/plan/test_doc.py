from pathlib import Path

from kagura_planner.plan.doc import slugify, write_plan_doc


def test_slugify_basic():
    assert slugify("Add Dark Mode!") == "add-dark-mode"
    assert slugify("  multiple   spaces ") == "multiple-spaces"


def test_slugify_drops_non_ascii():
    assert slugify("日本語 idea") == "idea"


def test_slugify_empty_falls_back():
    assert slugify("!!!") == "plan"


def test_write_plan_doc_creates_file(tmp_path):
    p = write_plan_doc(
        plan_dir=tmp_path / "docs/plans", idea="Add dark mode",
        plan_md="# Plan\n- step", date="2026-06-08",
    )
    assert Path(p).is_file()
    assert Path(p).name == "2026-06-08-add-dark-mode.md"
    assert "# Plan" in Path(p).read_text()
