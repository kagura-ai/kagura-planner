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
    PlanStatus.OK: 0, PlanStatus.WARN: 3, PlanStatus.FAIL: 1, PlanStatus.BLOCKED: 2,
}

_EDGE_RELATION = "depends_on"  # plan → recalled memory it builds on (server edge_type)
_SUMMARY_MAX = 500  # Memory Cloud caps RememberRequest.summary at 500 chars (issue #6)
_SUMMARY_PREFIX = "plan: "  # marker kept verbatim; only the idea is truncated


def _plan_summary(idea: str) -> str:
    """Bounded summary for the persisted decision record. The raw idea is
    arbitrary length, but Memory Cloud rejects a RememberRequest whose summary
    exceeds 500 chars — which silently dropped the persisted plan + edges for
    any idea over ~493 chars (issue #6). Truncate the *idea* (never the marker)
    with an ellipsis so the result always fits AND keeps the leading 'plan: '
    marker, regardless of _SUMMARY_MAX or prefix length."""
    summary = f"{_SUMMARY_PREFIX}{idea}"
    if len(summary) <= _SUMMARY_MAX:
        return summary
    keep = max(_SUMMARY_MAX - len(_SUMMARY_PREFIX) - 1, 0)  # room for prefix + "…"
    return f"{_SUMMARY_PREFIX}{idea[:keep]}…"


def _safe_close(mem: MemoryClient) -> None:
    """Best-effort teardown of a memory client plan_idea OWNS. Closing must
    never turn a successful plan into a failure, so swallow everything (and
    skip clients that expose no close())."""
    closer = getattr(mem, "close", None)
    if closer is None:
        return
    try:
        closer()
    except Exception:  # noqa: BLE001 — teardown must never raise
        _log.exception("plan memory close failed (non-fatal)")


def plan_idea(
    cfg: Config, idea: str, *, date: str,
    memory: MemoryClient | None = None, repo_root: Path | None = None,
    no_remember: bool = False,
) -> PlanReport:
    # Ownership: if the caller injected a client they own its lifecycle; only a
    # client we resolve ourselves gets closed here (it holds a persistent event
    # loop + httpx client that would otherwise leak — issue #2).
    owns_mem = memory is None
    mem = memory if memory is not None else resolve_memory_client(cfg)
    root = repo_root if repo_root is not None else Path.cwd()
    started = time.monotonic()
    phases: list[PhaseResult] = []

    def _finish(**kw: object) -> PlanReport:
        return PlanReport(idea=idea, phases=phases, duration_s=time.monotonic() - started, **kw)  # type: ignore[arg-type]

    try:
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
            # claude -p writes auth/errors to stdout, not stderr; fall back so the
            # cause isn't hidden as a blank "claude exited 1:".
            tail = "timed out" if brain.timed_out else (brain.stderr or brain.stdout or "").strip()[-200:]
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

        # 4. persist — remember + refines edges + feedback (best-effort; doc already landed).
        memory_id: str | None = None
        edges: list[str] = []
        if not no_remember:
            try:
                memory_id = mem.remember(
                    cfg.context_id,
                    summary=_plan_summary(idea),
                    content=brain.plan_md,
                    type="decision",
                    tags=[f"repo:{root.name}", "plan", "kagura-planner"],
                )
                if memory_id:
                    phases.append(PhaseResult("persist", PlanStatus.OK, f"remembered {memory_id}"))
                else:
                    # remember() returned no id — nothing was written. Best-effort,
                    # but it must not read as OK (#14): an agent gating on memory_id
                    # would proceed as if the plan were persisted.
                    memory_id = None
                    phases.append(PhaseResult("persist", PlanStatus.WARN, "remember returned no memory_id"))
            except Exception as exc:  # noqa: BLE001 — doc exists; persist is best-effort
                # Degraded, not fatal: the doc already landed. But WARN (not OK) so the
                # report status / envelope / exit code reflect the silent write loss (#14).
                _log.exception("plan persist failed (non-fatal)")
                phases.append(PhaseResult("persist", PlanStatus.WARN, f"remember failed (non-fatal): {type(exc).__name__}"))
            # wire refines edges to the recalled memories this plan builds on,
            # and reinforce them (Hebbian). Best-effort: a graph/feedback hiccup
            # must not fail a run whose doc + memory already landed.
            if memory_id:
                for mid, _ in recalled:
                    try:
                        mem.create_edge(cfg.context_id, memory_id, mid, _EDGE_RELATION)
                        edges.append(f"{memory_id}->{mid}:{_EDGE_RELATION}")
                    except Exception:  # noqa: BLE001
                        _log.exception("plan create_edge failed (non-fatal)")
                    try:
                        mem.feedback(cfg.context_id, mid)
                    except Exception:  # noqa: BLE001
                        _log.exception("plan feedback failed (non-fatal)")

        return _finish(plan_doc_path=doc_path, memory_id=memory_id, edges=edges)
    finally:
        # Close the client on EVERY return path — but only if we own it.
        if owns_mem:
            _safe_close(mem)
