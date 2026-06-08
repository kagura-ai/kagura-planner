"""`plan` — memory-grounded PLAN loop (idea → plan doc).

Phase sequence: guard → recall → brain → write → persist. Edges are wired in
persist (Task 11). External boundaries (doctor run_all, memory SDK, claude
launch, file write) are wrapped so an infra error returns a clean FAIL report
instead of a traceback — the isolation invariant ported from kagura-engineer.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from ..config import Config
from ..doctor.registry import run_all
from .brain import invoke_brain
from .doc import write_plan_doc
from .memory import MemoryClient, resolve_memory_client
from .result import PhaseResult, PlanReport, PlanStatus

_log = logging.getLogger(__name__)

STATUS_EXIT: dict[PlanStatus, int] = {
    PlanStatus.OK: 0, PlanStatus.FAIL: 1, PlanStatus.BLOCKED: 2,
}

_EDGE_RELATION = "refines"  # plan → recalled memory it builds on


def plan_idea(
    cfg: Config, idea: str, *, date: str,
    memory: MemoryClient | None = None, repo_root: Path | None = None,
    no_remember: bool = False,
) -> PlanReport:
    mem = memory if memory is not None else resolve_memory_client(cfg)
    root = repo_root if repo_root is not None else Path.cwd()
    started = time.monotonic()
    phases: list[PhaseResult] = []

    def _finish(**kw: object) -> PlanReport:
        return PlanReport(idea=idea, phases=phases, duration_s=time.monotonic() - started, **kw)  # type: ignore[arg-type]

    # 0. guard — verify environment; do not auto-provision.
    blocking = [c for c in run_all(cfg) if c.is_blocking]
    if blocking:
        names = ", ".join(c.name for c in blocking)
        phases.append(PhaseResult("guard", PlanStatus.BLOCKED, f"blocking checks failed: {names}"))
        return _finish()
    phases.append(PhaseResult("guard", PlanStatus.OK, "all blocking checks passed"))

    # 1. recall — grounding. Memory is core: a failure is a hard FAIL.
    recalled: list[tuple[str, str]] = []
    try:
        recalled = mem.recall_detailed(cfg.context_id, f"plan for: {idea}", k=5)
    except Exception as exc:  # noqa: BLE001 — convert SDK leak to FAIL phase
        _log.exception("plan recall phase failed")
        phases.append(PhaseResult("recall", PlanStatus.FAIL, f"memory recall failed: {type(exc).__name__}: {exc}"))
        return _finish()
    grounding = [s for _, s in recalled]
    phases.append(PhaseResult("recall", PlanStatus.OK, f"{len(grounding)} memories"))

    # 2. brain — claude -p planning skills.
    try:
        brain = invoke_brain(idea, grounding, cwd=root)
    except OSError as exc:
        _log.exception("plan brain failed to launch claude")
        phases.append(PhaseResult("brain", PlanStatus.FAIL, f"failed to launch claude: {exc}"))
        return _finish()
    if brain.returncode != 0:
        tail = "timed out" if brain.timed_out else (brain.stderr or "").strip()[-200:]
        phases.append(PhaseResult("brain", PlanStatus.FAIL, f"claude exited {brain.returncode}: {tail}"))
        return _finish()
    if not brain.plan_md:
        phases.append(PhaseResult("brain", PlanStatus.FAIL, "no plan block in claude output"))
        return _finish()
    phases.append(PhaseResult("brain", PlanStatus.OK, "plan produced"))

    # 3. write doc.
    try:
        doc_path = write_plan_doc(plan_dir=root / cfg.plan_dir, idea=idea, plan_md=brain.plan_md, date=date)
    except OSError as exc:
        _log.exception("plan doc write failed")
        phases.append(PhaseResult("write", PlanStatus.FAIL, f"could not write plan doc: {exc}"))
        return _finish()
    phases.append(PhaseResult("write", PlanStatus.OK, doc_path))

    # 4. persist — remember; edges + feedback added in Task 11.
    memory_id: str | None = None
    edges: list[str] = []
    if not no_remember:
        try:
            memory_id = mem.remember(
                cfg.context_id,
                summary=f"plan: {idea}",
                content=brain.plan_md,
                type="decision",
                tags=[f"repo:{root.name}", "plan", "kagura-planner"],
            )
            phases.append(PhaseResult("persist", PlanStatus.OK, f"remembered {memory_id}"))
        except Exception as exc:  # noqa: BLE001 — doc exists; persist is best-effort
            _log.exception("plan persist failed (non-fatal)")
            phases.append(PhaseResult("persist", PlanStatus.OK, f"remember failed (non-fatal): {type(exc).__name__}"))

    return _finish(plan_doc_path=doc_path, memory_id=memory_id, edges=edges)
