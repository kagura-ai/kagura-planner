import json

from kagura_planner.doctor.render import to_json
from kagura_planner.doctor.result import CheckResult, Status


def test_to_json_round_trips():
    out = json.loads(to_json([CheckResult("git", Status.OK, "fine", None)]))
    assert out == [{"name": "git", "status": "ok", "detail": "fine", "fix_hint": None}]
