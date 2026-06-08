"""Tests for plan/render.py print_table — covers all PlanStatus branches
and the plan_doc_path conditional."""
from __future__ import annotations

from kagura_planner.plan.render import print_table
from kagura_planner.plan.result import PhaseResult, PlanReport, PlanStatus


def test_print_table_all_statuses_no_doc_path():
    report = PlanReport(
        idea="test idea",
        phases=[
            PhaseResult("guard", PlanStatus.OK, "all checks passed"),
            PhaseResult("recall", PlanStatus.BLOCKED, "env guard blocked"),
            PhaseResult("brain", PlanStatus.FAIL, "claude exited 1"),
        ],
        plan_doc_path=None,
    )
    result = print_table(report)
    assert result is None


def test_print_table_with_doc_path():
    report = PlanReport(
        idea="add feature X",
        phases=[
            PhaseResult("guard", PlanStatus.OK, "all ok"),
            PhaseResult("recall", PlanStatus.OK, "3 memories"),
            PhaseResult("brain", PlanStatus.OK, "plan produced"),
        ],
        plan_doc_path="docs/plans/2026-06-08-add-feature-x.md",
    )
    result = print_table(report)
    assert result is None


def test_print_table_empty_phases():
    report = PlanReport(idea="empty plan", phases=[])
    result = print_table(report)
    assert result is None


def test_print_table_ok_only():
    report = PlanReport(
        idea="simple idea",
        phases=[PhaseResult("guard", PlanStatus.OK, "passed")],
    )
    result = print_table(report)
    assert result is None


def test_print_table_blocked_status():
    report = PlanReport(
        idea="blocked plan",
        phases=[PhaseResult("guard", PlanStatus.BLOCKED, "doctor checks blocked")],
    )
    result = print_table(report)
    assert result is None


def test_print_table_fail_status():
    report = PlanReport(
        idea="failing plan",
        phases=[PhaseResult("recall", PlanStatus.FAIL, "memory error")],
    )
    result = print_table(report)
    assert result is None
