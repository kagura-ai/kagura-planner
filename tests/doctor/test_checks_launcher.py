"""Regression (#18, sibling of kagura-brain#17): doctor's local launcher.

On native Windows, ``CreateProcess`` only auto-appends ``.exe`` — it does NOT
apply ``PATHEXT`` — so ``subprocess.run(["claude", ...], shell=False)`` cannot
find an npm ``claude.cmd`` shim and dies with WinError 2, while the pre-flight
``shutil.which("claude")`` (which DOES apply ``PATHEXT``) passes. ``_run`` must
spawn the which-resolved path and route ``.cmd``/``.bat`` shims through the
command interpreter (``COMSPEC /c``) explicitly, keeping ``shell=False``.
"""
from __future__ import annotations

import subprocess
import sys

from kagura_planner.doctor import checks


def _capture_run(monkeypatch) -> dict:
    captured: dict = {}

    def _capture(*a, **k):
        captured["argv"] = a[0]
        captured["kwargs"] = k
        return subprocess.CompletedProcess(
            args=a[0], returncode=0, stdout="ok", stderr=""
        )

    monkeypatch.setattr(checks.subprocess, "run", _capture)
    return captured


class TestRunResolvesArgv0:
    def test_spawns_which_resolved_path(self, monkeypatch):
        # Always launch the which-resolved absolute path so the pre-flight
        # check and the actual spawn can never diverge (POSIX included).
        monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/local/bin/claude")
        captured = _capture_run(monkeypatch)
        checks._run(["claude", "--version"])
        assert captured["argv"] == ["/usr/local/bin/claude", "--version"]

    def test_unresolvable_argv0_left_as_is(self, monkeypatch):
        # argv[0] not on PATH → leave it untouched so the OSError surfaces
        # with the caller's own name; the tail is never modified.
        monkeypatch.setattr(checks.shutil, "which", lambda _: None)
        captured = _capture_run(monkeypatch)
        checks._run(["claude", "--version"])
        assert captured["argv"] == ["claude", "--version"]

    def test_cmd_shim_wrapped_with_comspec_on_windows(self, monkeypatch):
        monkeypatch.setattr(checks.shutil, "which", lambda _: r"C:\npm\claude.CMD")
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
        captured = _capture_run(monkeypatch)
        checks._run(["claude", "--version"])
        assert captured["argv"] == [
            r"C:\Windows\System32\cmd.exe", "/c", r"C:\npm\claude.CMD", "--version",
        ]

    def test_bat_shim_uses_cmd_exe_when_comspec_unset(self, monkeypatch):
        monkeypatch.setattr(checks.shutil, "which", lambda _: r"C:\npm\claude.bat")
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.delenv("COMSPEC", raising=False)
        captured = _capture_run(monkeypatch)
        checks._run(["claude", "--version"])
        assert captured["argv"] == ["cmd.exe", "/c", r"C:\npm\claude.bat", "--version"]

    def test_cmd_suffix_not_wrapped_off_windows(self, monkeypatch):
        # A POSIX file merely named *.cmd is a regular executable — no wrap.
        monkeypatch.setattr(checks.shutil, "which", lambda _: "/odd/claude.cmd")
        monkeypatch.setattr(sys, "platform", "linux")
        captured = _capture_run(monkeypatch)
        checks._run(["claude", "--version"])
        assert captured["argv"] == ["/odd/claude.cmd", "--version"]

    def test_output_decoded_as_utf8(self, monkeypatch):
        # Same bug class as the file I/O sites: decoding subprocess output with
        # the locale codec can raise on UTF-8 bytes; pin utf-8 with replace.
        monkeypatch.setattr(checks.shutil, "which", lambda _: None)
        captured = _capture_run(monkeypatch)
        checks._run(["claude", "--version"])
        assert captured["kwargs"].get("encoding") == "utf-8"
        assert captured["kwargs"].get("errors") == "replace"
