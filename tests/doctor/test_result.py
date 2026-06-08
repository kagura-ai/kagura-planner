from kagura_planner.doctor.result import CheckResult, Status


def test_fail_is_blocking():
    assert CheckResult("x", Status.FAIL, "bad").is_blocking
    assert not CheckResult("x", Status.OK, "ok").is_blocking
    assert not CheckResult("x", Status.WARN, "meh").is_blocking
