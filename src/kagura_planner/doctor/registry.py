from __future__ import annotations

import logging

from ..config import Config
from . import checks
from .result import CheckResult, Status

_log = logging.getLogger(__name__)
_WORST = {Status.OK: 0, Status.WARN: 1, Status.FAIL: 2}

# Official planning skills `plan` drives via headless claude.
_REQUIRED_SKILLS = ("brainstorming", "writing-plans")

_CHECKS: list[tuple[str, object]] = [
    ("git", lambda c: checks.check_git()),
    ("claude-code", lambda c: checks.check_claude_code()),
    ("memory", lambda c: checks.check_memory_cloud(c.memory_cloud_url)),
    ("skills", lambda c: checks.check_skills(_REQUIRED_SKILLS)),
]


def run_all(cfg: Config) -> list[CheckResult]:
    results: list[CheckResult] = []
    for name, fn in _CHECKS:
        try:
            results.append(fn(cfg))
        except Exception as exc:  # noqa: BLE001 — a buggy check must not abort doctor
            _log.exception("doctor check %r raised", name)
            results.append(CheckResult(
                name, Status.FAIL, f"check raised {type(exc).__name__}: {exc}",
                "this is a doctor bug; please report it",
            ))
    return results


def overall_status(results: list[CheckResult]) -> Status:
    if not results:
        return Status.OK
    return max(results, key=lambda r: _WORST[r.status]).status
