"""Extended doctor checks tests — covers check_git, check_claude_code,
check_memory_cloud branches not exercised by the base test_checks.py."""
from __future__ import annotations

import subprocess
import urllib.error

from kagura_planner.doctor import checks
from kagura_planner.doctor.result import Status


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


# ---------------------------------------------------------------------------
# check_git
# ---------------------------------------------------------------------------


def test_git_ok_inside_worktree(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/git")
    monkeypatch.setattr(
        checks.subprocess, "run", lambda *a, **k: _completed(0, "true\n")
    )
    r = checks.check_git()
    assert r.status is Status.OK


def test_git_fail_not_on_path(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda _: None)
    r = checks.check_git()
    assert r.status is Status.FAIL
    assert r.fix_hint is not None
    assert "re-run doctor" in r.fix_hint


def test_git_warn_not_in_worktree(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/git")
    monkeypatch.setattr(
        checks.subprocess, "run", lambda *a, **k: _completed(128, "", "not a git repository")
    )
    r = checks.check_git()
    assert r.status is Status.WARN
    assert "cd" in (r.fix_hint or "")


# ---------------------------------------------------------------------------
# check_claude_code
# ---------------------------------------------------------------------------


def test_claude_ok_with_api_key(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/claude")
    monkeypatch.setattr(
        checks.subprocess, "run", lambda *a, **k: _completed(0, "1.2.3\n")
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxx")
    r = checks.check_claude_code()
    assert r.status is Status.OK
    assert "api_key" in r.detail


def test_claude_warn_subscription(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/claude")
    monkeypatch.setattr(
        checks.subprocess, "run", lambda *a, **k: _completed(0, "1.2.3\n")
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = checks.check_claude_code()
    assert r.status is Status.WARN
    assert "subscription" in r.detail


def test_claude_fail_not_on_path(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda _: None)
    r = checks.check_claude_code()
    assert r.status is Status.FAIL


def test_claude_fail_empty_api_key(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/claude")
    monkeypatch.setattr(
        checks.subprocess, "run", lambda *a, **k: _completed(0, "1.2.3\n")
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    r = checks.check_claude_code()
    assert r.status is Status.FAIL
    assert "empty" in r.detail.lower()


def test_claude_fail_nonzero_version(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/claude")
    monkeypatch.setattr(
        checks.subprocess, "run", lambda *a, **k: _completed(1, "", "crash")
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = checks.check_claude_code()
    assert r.status is Status.FAIL


# ---------------------------------------------------------------------------
# check_memory_cloud
# ---------------------------------------------------------------------------


class _FakeResp:
    def read(self):
        return b"OK"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_memory_cloud_ok_when_reachable(monkeypatch):
    monkeypatch.setattr(
        checks.urllib.request, "urlopen", lambda *a, **k: _FakeResp()
    )
    r = checks.check_memory_cloud("https://memory.example.com")
    assert r.status is Status.OK
    assert "memory.example.com" in r.detail


def test_memory_cloud_warn_on_http_error(monkeypatch):
    def _boom(*a, **k):
        raise urllib.error.HTTPError(
            "https://memory.example.com/health", 403, "Forbidden", {}, None
        )

    monkeypatch.setattr(checks.urllib.request, "urlopen", _boom)
    r = checks.check_memory_cloud("https://memory.example.com")
    assert r.status is Status.WARN
    assert "403" in r.detail


def test_memory_cloud_fail_when_unreachable(monkeypatch):
    def _boom(*a, **k):
        raise urllib.error.URLError("dns failure")

    monkeypatch.setattr(checks.urllib.request, "urlopen", _boom)
    r = checks.check_memory_cloud("https://memory.example.com")
    assert r.status is Status.FAIL


def test_memory_cloud_strips_credentials(monkeypatch):
    monkeypatch.setattr(
        checks.urllib.request, "urlopen", lambda *a, **k: _FakeResp()
    )
    r = checks.check_memory_cloud("https://user:s3cret@memory.example.com")
    assert r.status is Status.OK
    assert "s3cret" not in r.detail
    assert "memory.example.com" in r.detail


def test_http_reach_sends_non_default_user_agent(monkeypatch):
    """The reachability probe must send an explicit User-Agent — Cloudflare's WAF
    rejects urllib's default `Python-urllib/*` UA with 403, turning a healthy
    endpoint into a spurious WARN."""
    captured = {}

    def _capture(req, *a, **k):
        captured["req"] = req
        return _FakeResp()

    monkeypatch.setattr(checks.urllib.request, "urlopen", _capture)
    checks._http_reach("https://memory.example.com/health")

    req = captured["req"]
    assert isinstance(req, checks.urllib.request.Request)
    ua = req.get_header("User-agent")
    assert ua is not None
    assert "Python-urllib" not in ua
    assert "kagura-planner" in ua
