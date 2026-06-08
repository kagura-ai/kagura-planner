from __future__ import annotations

import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .result import CheckResult, Status

_TIMEOUT = 5


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT)


def check_git() -> CheckResult:
    if shutil.which("git") is None:
        return CheckResult(
            "git",
            Status.FAIL,
            "git not found on PATH",
            "install git via your package manager (brew/apt/dnf/pacman) and re-run doctor",
        )
    try:
        proc = _run(["git", "rev-parse", "--is-inside-work-tree"])
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult("git", Status.FAIL, f"git invocation failed: {exc}", None)
    if proc.returncode == 0 and proc.stdout.strip() == "true":
        return CheckResult("git", Status.OK, "inside a git work tree")
    return CheckResult(
        "git",
        Status.WARN,
        "not inside a git work tree",
        "cd into the target repo before running",
    )


def check_claude_code() -> CheckResult:
    if shutil.which("claude") is None:
        return CheckResult(
            "claude-code",
            Status.FAIL,
            "claude not found on PATH",
            "install Claude Code (https://claude.ai/download) and re-run doctor",
        )
    try:
        proc = _run(["claude", "--version"])
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(
            "claude-code", Status.FAIL, f"claude invocation failed: {exc}", None
        )
    if proc.returncode != 0:
        return CheckResult(
            "claude-code",
            Status.FAIL,
            f"`claude --version` exited {proc.returncode}",
            "reinstall/repair Claude Code",
        )
    version = proc.stdout.strip() or "unknown"
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key is not None and key == "":
        return CheckResult(
            "claude-code",
            Status.FAIL,
            f"v{version}, ANTHROPIC_API_KEY is set to empty string",
            "unset it to fall back to your `claude login` subscription "
            "(recommended), or set a real value (`export ANTHROPIC_API_KEY=sk-ant-...`)",
        )
    if key:
        return CheckResult("claude-code", Status.OK, f"v{version}, auth=api_key")
    return CheckResult(
        "claude-code",
        Status.WARN,
        f"v{version}, auth=subscription (unverified)",
        "run `claude` once interactively to confirm subscription login",
    )


def _http_reach(url: str) -> None:
    """Open url to confirm reachability; raises on connection/HTTP error. Body ignored."""
    with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:  # noqa: S310 (trusted config URL)
        resp.read()  # body discarded; open succeeding is sufficient proof of reachability


def check_memory_cloud(base_url: str) -> CheckResult:
    # Extract host-only form so that any userinfo (basic auth) embedded in
    # `memory_cloud_url` is NOT echoed into the doctor detail string —
    # `doctor --json` is a common artefact in CI logs and chat pastes.
    # `urlparse(...).hostname` drops username:password@ automatically.
    try:
        host_only = urlparse(base_url).hostname or base_url
    except (ValueError, TypeError):
        host_only = base_url
    try:
        _http_reach(f"{base_url.rstrip('/')}/health")
    except urllib.error.HTTPError as exc:
        # An HTTP response (even 4xx/5xx) proves the host is reachable; this is a
        # reachability probe, not an auth/health check. Full authed recall smoke is Plan 3.
        return CheckResult(
            "memory-cloud",
            Status.WARN,
            f"reachable but /health returned HTTP {exc.code}",
            "auth/endpoint verified later by setup / Plan 3 recall smoke",
        )
    except (urllib.error.URLError, OSError, ValueError) as exc:
        # ValueError covers a malformed/schemeless memory_cloud_url
        # ("unknown url type" / "Invalid IPv6 URL"); urlopen raises it
        # before any network attempt. Match check_ollama, which already
        # guards ValueError, so a bad URL FAILs cleanly instead of
        # crashing the whole doctor command (run_all has no isolation).
        return CheckResult(
            "memory-cloud",
            Status.FAIL,
            f"unreachable: {exc}",
            "check config.memory_cloud_url / network",
        )
    return CheckResult("memory-cloud", Status.OK, f"reachable at {host_only}")


def check_skills(required: tuple[str, ...]) -> CheckResult:
    """Verify the official planning skills are installed under the Claude
    plugins dir. `plan` drives them via headless claude; without them the
    session dies mid-run, so a missing skill is blocking (Status.FAIL).
    Plugin root overridable via KAGURA_PLUGINS_DIR for tests."""
    root = Path(os.environ.get("KAGURA_PLUGINS_DIR") or str(Path.home() / ".claude" / "plugins"))
    present = {p.name for p in root.glob("**/skills/*") if p.is_dir()} if root.exists() else set()
    missing = [s for s in required if s not in present]
    if missing:
        return CheckResult(
            "skills", Status.FAIL,
            f"missing planning skills: {', '.join(missing)}",
            "install the superpowers plugin (brainstorming + writing-plans)",
        )
    return CheckResult("skills", Status.OK, f"{len(required)} planning skills present")
