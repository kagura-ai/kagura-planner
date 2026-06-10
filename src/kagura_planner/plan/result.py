from __future__ import annotations

import enum
from dataclasses import dataclass, field


class PlanStatus(enum.Enum):
    OK = "ok"
    WARN = "warn"  # degraded but not fatal — e.g. best-effort persist failed (#14)
    BLOCKED = "blocked"
    FAIL = "fail"


# WARN ranks just above OK: a degraded persist must outrank OK (so it is never
# masked) yet stay below the hard failures (a real FAIL/BLOCKED still wins the
# worst-of-phases roll-up). Every PlanStatus MUST have an entry here — see the
# totality contract test in tests/plan/test_result.py (#14).
_WORST = {PlanStatus.OK: 0, PlanStatus.WARN: 1, PlanStatus.BLOCKED: 2, PlanStatus.FAIL: 3}


@dataclass(frozen=True)
class PhaseResult:
    name: str
    status: PlanStatus
    detail: str
    duration_s: float = 0.0


@dataclass(frozen=True)
class PlanReport:
    idea: str
    phases: list[PhaseResult] = field(default_factory=list)
    plan_doc_path: str | None = None
    memory_id: str | None = None
    edges: list[str] = field(default_factory=list)
    duration_s: float = 0.0

    @property
    def status(self) -> PlanStatus:
        if not self.phases:
            return PlanStatus.OK
        return max(self.phases, key=lambda p: _WORST[p.status]).status
