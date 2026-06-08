from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from .result import PhaseResult, PlanReport, PlanStatus

_ICON = {PlanStatus.OK: "✅", PlanStatus.BLOCKED: "⏸", PlanStatus.FAIL: "❌"}


def _phase_to_dict(p: PhaseResult) -> dict[str, object]:
    return {"name": p.name, "status": p.status.value, "detail": p.detail,
            "duration_s": round(p.duration_s, 3)}


def to_json(report: PlanReport) -> str:
    return json.dumps(
        {
            "idea": report.idea,
            "status": report.status.value,
            "plan_doc_path": report.plan_doc_path,
            "memory_id": report.memory_id,
            "edges": report.edges,
            "phases": [_phase_to_dict(p) for p in report.phases],
            "duration_s": round(report.duration_s, 3),
        },
        ensure_ascii=False,
    )


def print_table(report: PlanReport) -> None:
    table = Table(title=f"kagura-planner plan — {report.status.value}")
    table.add_column("")
    table.add_column("phase")
    table.add_column("status")
    table.add_column("detail")
    for p in report.phases:
        table.add_row(_ICON[p.status], p.name, p.status.value, p.detail)
    console = Console()
    console.print(table)
    if report.plan_doc_path:
        console.print(f"plan: {report.plan_doc_path}")
