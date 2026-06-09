"""Subprocess helpers — re-exported from the shared claude-harness package.

`as_text`/`mcp_args` now live in `kagura_claude_harness.proc` so the launcher
seam is defined in exactly one place. Re-exported here to keep the existing
`kagura_planner.proc` import path stable.
"""
from __future__ import annotations

from kagura_claude_harness.proc import as_text, mcp_args

__all__ = ["as_text", "mcp_args"]
