"""Tests for doctor/render.py print_table — covers the rich table rendering."""
from __future__ import annotations

from kagura_planner.doctor.render import print_table
from kagura_planner.doctor.result import CheckResult, Status


def test_print_table_returns_none_for_all_statuses():
    results = [
        CheckResult("git", Status.OK, "inside a git work tree"),
        CheckResult("claude-code", Status.WARN, "subscription unverified", "run claude"),
        CheckResult("memory-cloud", Status.FAIL, "unreachable", "check config"),
    ]
    # print_table should return None and not raise
    result = print_table(results)
    assert result is None


def test_print_table_empty_list():
    result = print_table([])
    assert result is None


def test_print_table_single_ok():
    results = [CheckResult("git", Status.OK, "all good")]
    result = print_table(results)
    assert result is None


def test_print_table_only_warn():
    results = [CheckResult("memory-cloud", Status.WARN, "http 403")]
    result = print_table(results)
    assert result is None


def test_print_table_only_fail():
    results = [CheckResult("memory-cloud", Status.FAIL, "dns down", "check config")]
    result = print_table(results)
    assert result is None
