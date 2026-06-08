import json

from kagura_planner.plan.render import to_json
from kagura_planner.plan.result import PhaseResult, PlanReport, PlanStatus


def test_to_json_shape():
    r = PlanReport(
        idea="x", phases=[PhaseResult("recall", PlanStatus.OK, "2 memories")],
        plan_doc_path="docs/plans/d.md", memory_id="mem-1", edges=["mem-1->m0:refines"],
    )
    out = json.loads(to_json(r))
    assert out["idea"] == "x" and out["status"] == "ok"
    assert out["plan_doc_path"] == "docs/plans/d.md"
    assert out["memory_id"] == "mem-1"
    assert out["edges"] == ["mem-1->m0:refines"]
    assert out["phases"][0]["name"] == "recall"
