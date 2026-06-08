from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from .result import CheckResult, Status

_ICON = {Status.OK: "✅", Status.WARN: "⚠️", Status.FAIL: "❌"}


def to_json(results: list[CheckResult]) -> str:
    return json.dumps(
        [{"name": r.name, "status": r.status.value, "detail": r.detail,
          "fix_hint": r.fix_hint} for r in results],
        ensure_ascii=False,
    )


def print_table(results: list[CheckResult]) -> None:
    table = Table(title="kagura-planner doctor")
    table.add_column("")
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail")
    for r in results:
        table.add_row(_ICON[r.status], r.name, r.status.value, r.detail)
    Console().print(table)
