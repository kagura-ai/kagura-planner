from kagura_planner.doctor import checks
from kagura_planner.doctor.result import Status


def test_skills_ok_when_all_present(tmp_path, monkeypatch):
    plugins = tmp_path / "plugins"
    for name in ("brainstorming", "writing-plans"):
        (plugins / "superpowers" / "skills" / name).mkdir(parents=True)
    monkeypatch.setenv("KAGURA_PLUGINS_DIR", str(plugins))
    res = checks.check_skills(("brainstorming", "writing-plans"))
    assert res.status is Status.OK


def test_skills_fail_when_missing(tmp_path, monkeypatch):
    plugins = tmp_path / "plugins"
    (plugins / "superpowers" / "skills" / "brainstorming").mkdir(parents=True)
    monkeypatch.setenv("KAGURA_PLUGINS_DIR", str(plugins))
    res = checks.check_skills(("brainstorming", "writing-plans"))
    assert res.status is Status.FAIL
    assert "writing-plans" in res.detail
