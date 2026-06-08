from kagura_planner.plan.brain import build_prompt, extract_plan, invoke_brain


def test_build_prompt_injects_grounding_and_markers():
    p = build_prompt("add dark mode", ["past plan A", "trap: race in cache"])
    assert "add dark mode" in p
    assert "past plan A" in p
    assert "KAGURA_PLAN_BEGIN" in p and "KAGURA_PLAN_END" in p


def test_build_prompt_handles_empty_grounding():
    assert "(no prior memory)" in build_prompt("idea", [])


def test_extract_plan_pulls_between_markers():
    out = "noise\nKAGURA_PLAN_BEGIN\n# Plan\n- step 1\nKAGURA_PLAN_END\ntrailing"
    assert extract_plan(out) == "# Plan\n- step 1"


def test_extract_plan_returns_none_when_absent():
    assert extract_plan("no markers here") is None


def test_invoke_brain_parses_subprocess(monkeypatch):
    import subprocess

    class _Proc:
        returncode = 0
        stdout = "KAGURA_PLAN_BEGIN\n# P\nKAGURA_PLAN_END"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc())
    res = invoke_brain("idea", ["g"], cwd=None)
    assert res.returncode == 0 and res.plan_md == "# P"
