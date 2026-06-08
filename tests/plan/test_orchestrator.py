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


def test_persist_wires_edges_to_recalled(valid_config, tmp_path, monkeypatch):
    valid_config = valid_config.model_copy(update={"plan_dir": str(tmp_path / "p")})
    monkeypatch.setattr("kagura_planner.plan.run_all", lambda cfg: [])
    monkeypatch.setattr("kagura_planner.plan.invoke_brain", _ok_brain)

    class _Mem(_FakeMem):
        def __init__(self):
            super().__init__()
            self.edges = []
        def create_edge(self, ctx, src, dst, relation):
            self.edges.append((src, dst, relation))

    mem = _Mem()
    report = plan_idea(valid_config, "idea", date="2026-06-08", memory=mem)
    assert mem.edges == [("mem-new", "m1", "refines")]
    assert report.edges == ["mem-new->m1:refines"]


# ---------------------------------------------------------------------------
# §6 fault-path isolation tests
# ---------------------------------------------------------------------------


def test_recall_exception_is_hard_fail(valid_config, tmp_path, monkeypatch):
    """recall_detailed raising must surface as PlanStatus.FAIL (hard fail)."""
    valid_config = valid_config.model_copy(update={"plan_dir": str(tmp_path / "p")})
    monkeypatch.setattr("kagura_planner.plan.run_all", lambda cfg: [])

    class _BoomMem(_FakeMem):
        def recall_detailed(self, ctx, query, *, k=5, tags=None, min_importance=0.0):
            raise RuntimeError("boom")

    report = plan_idea(valid_config, "idea", date="2026-06-08", memory=_BoomMem())
    assert report.status is PlanStatus.FAIL
    recall_phases = [p for p in report.phases if p.name == "recall"]
    assert recall_phases, "expected a 'recall' phase in report"
    assert recall_phases[0].status is PlanStatus.FAIL


def test_brain_nonzero_returncode_is_fail(valid_config, tmp_path, monkeypatch):
    """Brain returning non-zero exit code must yield PlanStatus.FAIL (phase 'brain')."""
    valid_config = valid_config.model_copy(update={"plan_dir": str(tmp_path / "p")})
    monkeypatch.setattr("kagura_planner.plan.run_all", lambda cfg: [])
    monkeypatch.setattr(
        "kagura_planner.plan.invoke_brain",
        lambda *a, **k: BrainResult(2, "", "boom", None),
    )
    report = plan_idea(valid_config, "idea", date="2026-06-08", memory=_FakeMem())
    assert report.status is PlanStatus.FAIL
    brain_phases = [p for p in report.phases if p.name == "brain"]
    assert brain_phases, "expected a 'brain' phase in report"
    assert brain_phases[0].status is PlanStatus.FAIL


def test_brain_oserror_is_fail(valid_config, tmp_path, monkeypatch):
    """OSError from invoke_brain (claude not found) must yield PlanStatus.FAIL
    (phase 'brain') with a detail mentioning launch."""
    valid_config = valid_config.model_copy(update={"plan_dir": str(tmp_path / "p")})
    monkeypatch.setattr("kagura_planner.plan.run_all", lambda cfg: [])

    def _raise(*a, **k):
        raise OSError("no claude")

    monkeypatch.setattr("kagura_planner.plan.invoke_brain", _raise)
    report = plan_idea(valid_config, "idea", date="2026-06-08", memory=_FakeMem())
    assert report.status is PlanStatus.FAIL
    brain_phases = [p for p in report.phases if p.name == "brain"]
    assert brain_phases, "expected a 'brain' phase in report"
    assert brain_phases[0].status is PlanStatus.FAIL
    assert "launch" in brain_phases[0].detail


def test_persist_remember_failure_is_nonfatal(valid_config, tmp_path, monkeypatch):
    """remember() raising must be non-fatal: doc written, overall OK,
    persist phase OK with 'non-fatal' note, memory_id is None, no edges wired."""
    valid_config = valid_config.model_copy(update={"plan_dir": str(tmp_path / "p")})
    monkeypatch.setattr("kagura_planner.plan.run_all", lambda cfg: [])
    monkeypatch.setattr("kagura_planner.plan.invoke_brain", _ok_brain)

    class _BoomRememberMem(_FakeMem):
        def remember(self, ctx, *, summary, content, type, tags=None):
            raise RuntimeError("remember exploded")

    report = plan_idea(valid_config, "idea", date="2026-06-08", memory=_BoomRememberMem())
    assert report.status is PlanStatus.OK, f"expected OK, got {report.status}"
    persist_phases = [p for p in report.phases if p.name == "persist"]
    assert persist_phases, "expected a 'persist' phase in report"
    assert persist_phases[0].status is PlanStatus.OK
    assert "non-fatal" in persist_phases[0].detail
    assert report.memory_id is None
    assert report.edges == []
