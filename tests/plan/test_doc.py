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


def test_write_plan_doc_pins_utf8(tmp_path, spy_text_opens):
    """Regression (#18): plan_md is LLM-generated and routinely contains
    Japanese, so an unpinned write_text crashes with UnicodeEncodeError on a
    non-UTF-8 default locale (cp932 on Windows-JP). Assert the explicit
    encoding instead of the locale default — fails on the bug everywhere."""
    seen = spy_text_opens(".md")
    p = write_plan_doc(
        plan_dir=tmp_path / "plans", idea="dark mode",
        plan_md="## 手順\n- 日本語を含む計画 🎌", date="2026-06-11",
    )
    assert seen, "expected the plan doc to be opened as text"
    assert all(e == "utf-8" for e in seen), f"unpinned open observed: {seen}"
    assert "手順" in Path(p).read_text(encoding="utf-8")


def test_write_plan_doc_is_collision_safe(tmp_path):
    """Writing twice with the same date+idea must not overwrite: the second
    write lands at a distinct path with a -2 suffix, and both files exist."""
    out = tmp_path / "docs/plans"
    p1 = write_plan_doc(
        plan_dir=out, idea="Add dark mode", plan_md="# Plan 1", date="2026-06-08",
    )
    p2 = write_plan_doc(
        plan_dir=out, idea="Add dark mode", plan_md="# Plan 2", date="2026-06-08",
    )
    assert p1 != p2
    assert Path(p1).is_file() and Path(p2).is_file()
    assert Path(p1).name == "2026-06-08-add-dark-mode.md"
    assert Path(p2).name == "2026-06-08-add-dark-mode-2.md"
    # original content preserved (not overwritten)
    assert "# Plan 1" in Path(p1).read_text()
    assert "# Plan 2" in Path(p2).read_text()


def test_write_plan_doc_collision_increments_beyond_two(tmp_path):
    """A third collision yields -3."""
    out = tmp_path / "p"
    paths = [
        write_plan_doc(plan_dir=out, idea="x", plan_md="c", date="2026-06-08")
        for _ in range(3)
    ]
    assert len(set(paths)) == 3
    assert Path(paths[2]).name == "2026-06-08-x-3.md"
