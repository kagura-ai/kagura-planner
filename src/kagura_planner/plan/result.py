from __future__ import annotations

import enum
from dataclasses import dataclass, field


class PlanStatus(enum.Enum):
    OK = "ok"
    BLOCKED = "blocked"
    FAIL = "fail"


_WORST = {PlanStatus.OK: 0, PlanStatus.BLOCKED: 1, PlanStatus.FAIL: 2}


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
