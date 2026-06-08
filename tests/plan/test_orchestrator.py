from pathlib import Path

from kagura_planner.plan import plan_idea
from kagura_planner.plan.brain import BrainResult
from kagura_planner.plan.result import PlanStatus


class _FakeMem:
    def __init__(self):
        self.remembered = []

    def recall_detailed(self, ctx, query, *, k=5, tags=None, min_importance=0.0):
        return [("m1", "past plan A")]

    def remember(self, ctx, *, summary, content, type, tags=None):
        self.remembered.append((summary, type))
        return "mem-new"

    def create_edge(self, ctx, src, dst, relation):
        pass

    def feedback(self, ctx, mid, *, weight=1.0):
        pass


def _ok_brain(idea, grounding, *, cwd, timeout=1800):
    return BrainResult(0, "", "", "# Plan\n- step 1")


def test_happy_path_writes_doc_and_remembers(valid_config, tmp_path, monkeypatch):
    valid_config = valid_config.model_copy(update={"plan_dir": str(tmp_path / "p")})
    monkeypatch.setattr("kagura_planner.plan.run_all", lambda cfg: [])
    monkeypatch.setattr("kagura_planner.plan.invoke_brain", _ok_brain)
    mem = _FakeMem()
    report = plan_idea(valid_config, "Add dark mode", date="2026-06-08", memory=mem)
    assert report.status is PlanStatus.OK
    assert Path(report.plan_doc_path).is_file()
    assert report.memory_id == "mem-new"
    assert mem.remembered and mem.remembered[0][1] == "decision"


def test_brain_failure_is_fail(valid_config, tmp_path, monkeypatch):
    valid_config = valid_config.model_copy(update={"plan_dir": str(tmp_path / "p")})
    monkeypatch.setattr("kagura_planner.plan.run_all", lambda cfg: [])
    monkeypatch.setattr(
        "kagura_planner.plan.invoke_brain",
        lambda *a, **k: BrainResult(0, "", "", None),
    )
    report = plan_idea(valid_config, "idea", date="2026-06-08", memory=_FakeMem())
    assert report.status is PlanStatus.FAIL


def test_guard_blocks_on_failing_check(valid_config, monkeypatch):
    from kagura_planner.doctor.result import CheckResult, Status
    monkeypatch.setattr(
        "kagura_planner.plan.run_all",
        lambda cfg: [CheckResult("skills", Status.FAIL, "missing")],
    )
    report = plan_idea(valid_config, "idea", date="2026-06-08", memory=_FakeMem())
    assert report.status is PlanStatus.BLOCKED
