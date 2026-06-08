import json

from kagura_planner.plan.envelope import SCHEMA_VERSION, to_envelope
from kagura_planner.plan.result import PhaseResult, PlanReport, PlanStatus


def test_envelope_shape():
    r = PlanReport(
        idea="x", phases=[PhaseResult("brain", PlanStatus.OK, "")],
        plan_doc_path="docs/plans/d.md", memory_id="mem-1",
        edges=["mem-1->m0:refines"],
    )
    env = json.loads(to_envelope(r))
    assert env["schema_version"] == SCHEMA_VERSION
    assert env["status"] == "ok"
    assert env["plan_doc_path"] == "docs/plans/d.md"
    assert env["memory_id"] == "mem-1"
    assert env["edges"] == ["mem-1->m0:refines"]


def test_envelope_blocked_status():
    r = PlanReport(idea="x", phases=[PhaseResult("guard", PlanStatus.BLOCKED, "missing skills")])
    env = json.loads(to_envelope(r))
    assert env["status"] == "blocked" and env["plan_doc_path"] is None
