from kagura_planner.doctor import registry
from kagura_planner.doctor.result import CheckResult, Status


def test_run_all_isolates_a_raising_check(valid_config, monkeypatch):
    def boom():
        raise RuntimeError("kaboom")
    monkeypatch.setattr(registry.checks, "check_git", boom)
    results = registry.run_all(valid_config)
    git = next(r for r in results if r.name == "git")
    assert git.status is Status.FAIL and "kaboom" in git.detail


def test_overall_status_is_worst():
    rs = [CheckResult("a", Status.OK, ""), CheckResult("b", Status.FAIL, "")]
    assert registry.overall_status(rs) is Status.FAIL
    assert registry.overall_status([]) is Status.OK
