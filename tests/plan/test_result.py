from kagura_planner.plan import STATUS_EXIT
from kagura_planner.plan.render import _ICON
from kagura_planner.plan.result import _WORST, PhaseResult, PlanReport, PlanStatus


def test_status_is_worst_phase():
    r = PlanReport(idea="x", phases=[
        PhaseResult("recall", PlanStatus.OK, ""),
        PhaseResult("brain", PlanStatus.FAIL, "claude exited 1"),
    ])
    assert r.status is PlanStatus.FAIL


def test_empty_report_is_ok():
    assert PlanReport(idea="x").status is PlanStatus.OK


# issue #14 — a degraded-but-not-fatal outcome (best-effort persist failed) needs
# its own status between OK and the hard failures, so it stays visible in the
# worst-of-phases roll-up, the envelope, and the exit code.
def test_warn_status_exists():
    assert PlanStatus.WARN.value == "warn"


def test_warn_ranks_above_ok_below_hard_failures():
    # OK + WARN → WARN (a persist failure must not be masked as OK)
    degraded = PlanReport(idea="x", phases=[
        PhaseResult("recall", PlanStatus.OK, ""),
        PhaseResult("persist", PlanStatus.WARN, "remember failed (non-fatal)"),
    ])
    assert degraded.status is PlanStatus.WARN
    # WARN + FAIL → FAIL (a real failure still outranks a degraded persist)
    failed = PlanReport(idea="x", phases=[
        PhaseResult("persist", PlanStatus.WARN, ""),
        PhaseResult("brain", PlanStatus.FAIL, ""),
    ])
    assert failed.status is PlanStatus.FAIL
    # WARN + BLOCKED → BLOCKED
    blocked = PlanReport(idea="x", phases=[
        PhaseResult("persist", PlanStatus.WARN, ""),
        PhaseResult("guard", PlanStatus.BLOCKED, ""),
    ])
    assert blocked.status is PlanStatus.BLOCKED


def test_warn_exit_code_is_nonzero():
    # operator-confirmed: a degraded persist must make the CLI exit non-zero so a
    # downstream agent gating on the exit code detects the silent memory-write loss.
    assert STATUS_EXIT[PlanStatus.WARN] == 3
    assert STATUS_EXIT[PlanStatus.OK] == 0


def test_every_status_is_total_across_the_three_maps():
    # contract: every PlanStatus must appear in all three PlanStatus-keyed maps,
    # or a status added later KeyErrors at runtime (the exact trap #14 is about).
    for status in PlanStatus:
        assert status in _WORST, f"{status} missing from _WORST"
        assert status in STATUS_EXIT, f"{status} missing from STATUS_EXIT"
        assert status in _ICON, f"{status} missing from _ICON"
