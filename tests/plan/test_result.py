from kagura_planner.plan.result import PhaseResult, PlanReport, PlanStatus


def test_status_is_worst_phase():
    r = PlanReport(idea="x", phases=[
        PhaseResult("recall", PlanStatus.OK, ""),
        PhaseResult("brain", PlanStatus.FAIL, "claude exited 1"),
    ])
    assert r.status is PlanStatus.FAIL


def test_empty_report_is_ok():
    assert PlanReport(idea="x").status is PlanStatus.OK
