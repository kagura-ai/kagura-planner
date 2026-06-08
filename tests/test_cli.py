"""CLI tests for kagura_planner.cli — uses typer.testing.CliRunner, all offline."""
from __future__ import annotations

import json

from typer.testing import CliRunner

from kagura_planner import __version__
from kagura_planner.cli import app
from kagura_planner.doctor.result import CheckResult, Status
from kagura_planner.plan.result import PhaseResult, PlanReport, PlanStatus

runner = CliRunner()


def _write_repo_yaml(tmp_path):
    """Write a minimal valid repo.yaml and return its path as str."""
    cfg_file = tmp_path / "repo.yaml"
    cfg_file.write_text(
        "profile: test\n"
        "memory_cloud_url: https://memory.example.com\n"
        "workspace_id: 11111111-1111-1111-1111-111111111111\n"
        "context_id: 22222222-2222-2222-2222-222222222222\n"
    )
    return str(cfg_file)


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


def test_version_flag_prints_version_and_exits_0():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


# ---------------------------------------------------------------------------
# doctor — config errors
# ---------------------------------------------------------------------------


def test_doctor_bad_config_exits_2(tmp_path):
    bad = str(tmp_path / "nonexistent.yaml")
    result = runner.invoke(app, ["doctor", "--config", bad])
    assert result.exit_code == 2
    assert "doctor" in result.stdout or "doctor" in (result.stderr or "")


def test_doctor_json_all_ok(tmp_path, monkeypatch):
    cfg_path = _write_repo_yaml(tmp_path)
    monkeypatch.setattr(
        "kagura_planner.cli.run_all",
        lambda cfg: [CheckResult("git", Status.OK, "inside a git work tree")],
    )
    result = runner.invoke(app, ["doctor", "--config", cfg_path, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert data[0]["status"] == "ok"


def test_doctor_exit_1_on_fail(tmp_path, monkeypatch):
    cfg_path = _write_repo_yaml(tmp_path)
    monkeypatch.setattr(
        "kagura_planner.cli.run_all",
        lambda cfg: [CheckResult("git", Status.FAIL, "git not found", "install git")],
    )
    result = runner.invoke(app, ["doctor", "--config", cfg_path, "--json"])
    assert result.exit_code == 1


def test_doctor_table_no_fail_exits_0(tmp_path, monkeypatch):
    cfg_path = _write_repo_yaml(tmp_path)
    monkeypatch.setattr(
        "kagura_planner.cli.run_all",
        lambda cfg: [CheckResult("memory-cloud", Status.WARN, "http 403")],
    )
    result = runner.invoke(app, ["doctor", "--config", cfg_path])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# plan — config errors
# ---------------------------------------------------------------------------


def test_plan_bad_config_exits_2(tmp_path):
    bad = str(tmp_path / "nonexistent.yaml")
    result = runner.invoke(app, ["plan", "add some feature", "--config", bad])
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# plan — happy path (table output)
# ---------------------------------------------------------------------------


def _ok_report():
    return PlanReport(
        idea="add some feature",
        phases=[
            PhaseResult("guard", PlanStatus.OK, "all checks passed"),
            PhaseResult("recall", PlanStatus.OK, "2 memories"),
            PhaseResult("brain", PlanStatus.OK, "plan produced"),
            PhaseResult("write", PlanStatus.OK, "docs/plans/plan.md"),
        ],
        plan_doc_path="docs/plans/plan.md",
        memory_id="mem-123",
    )


def test_plan_table_exit_0_on_ok(tmp_path, monkeypatch):
    cfg_path = _write_repo_yaml(tmp_path)
    monkeypatch.setattr("kagura_planner.cli.plan_idea", lambda *a, **kw: _ok_report())
    result = runner.invoke(app, ["plan", "add some feature", "--config", cfg_path])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# plan — --json output
# ---------------------------------------------------------------------------


def test_plan_json_output(tmp_path, monkeypatch):
    cfg_path = _write_repo_yaml(tmp_path)
    monkeypatch.setattr("kagura_planner.cli.plan_idea", lambda *a, **kw: _ok_report())
    result = runner.invoke(app, ["plan", "add some feature", "--config", cfg_path, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert data["idea"] == "add some feature"
    assert "phases" in data


# ---------------------------------------------------------------------------
# plan — --envelope output
# ---------------------------------------------------------------------------


def test_plan_envelope_output(tmp_path, monkeypatch):
    cfg_path = _write_repo_yaml(tmp_path)
    monkeypatch.setattr("kagura_planner.cli.plan_idea", lambda *a, **kw: _ok_report())
    result = runner.invoke(
        app, ["plan", "add some feature", "--config", cfg_path, "--envelope"]
    )
    assert result.exit_code == 0
    envelope = json.loads(result.stdout)
    assert envelope["schema_version"] == 1
    assert envelope["status"] == "ok"
    assert "plan_doc_path" in envelope
    assert "memory_id" in envelope
    assert "edges" in envelope
    assert "summary" in envelope


# ---------------------------------------------------------------------------
# plan — exit code mapping (BLOCKED → 2, FAIL → 1)
# ---------------------------------------------------------------------------


def test_plan_exit_2_on_blocked(tmp_path, monkeypatch):
    cfg_path = _write_repo_yaml(tmp_path)
    blocked_report = PlanReport(
        idea="blocked idea",
        phases=[PhaseResult("guard", PlanStatus.BLOCKED, "checks failed: git")],
    )
    monkeypatch.setattr("kagura_planner.cli.plan_idea", lambda *a, **kw: blocked_report)
    result = runner.invoke(app, ["plan", "blocked idea", "--config", cfg_path])
    assert result.exit_code == 2


def test_plan_exit_1_on_fail(tmp_path, monkeypatch):
    cfg_path = _write_repo_yaml(tmp_path)
    fail_report = PlanReport(
        idea="failing idea",
        phases=[PhaseResult("recall", PlanStatus.FAIL, "memory error")],
    )
    monkeypatch.setattr("kagura_planner.cli.plan_idea", lambda *a, **kw: fail_report)
    result = runner.invoke(app, ["plan", "failing idea", "--config", cfg_path])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# plan -- envelope exit codes
# ---------------------------------------------------------------------------


def test_plan_envelope_exit_2_on_blocked(tmp_path, monkeypatch):
    cfg_path = _write_repo_yaml(tmp_path)
    blocked_report = PlanReport(
        idea="blocked",
        phases=[PhaseResult("guard", PlanStatus.BLOCKED, "checks failed")],
    )
    monkeypatch.setattr("kagura_planner.cli.plan_idea", lambda *a, **kw: blocked_report)
    result = runner.invoke(
        app, ["plan", "blocked", "--config", cfg_path, "--envelope"]
    )
    assert result.exit_code == 2
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "blocked"


def test_plan_envelope_exit_1_on_fail(tmp_path, monkeypatch):
    cfg_path = _write_repo_yaml(tmp_path)
    fail_report = PlanReport(
        idea="failing",
        phases=[PhaseResult("recall", PlanStatus.FAIL, "memory down")],
    )
    monkeypatch.setattr("kagura_planner.cli.plan_idea", lambda *a, **kw: fail_report)
    result = runner.invoke(
        app, ["plan", "failing", "--config", cfg_path, "--envelope"]
    )
    assert result.exit_code == 1
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "fail"
