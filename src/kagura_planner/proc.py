"""Subprocess helpers — re-exported from the shared kagura-brain package.

`as_text` now lives in `kagura_brain.core` and `mcp_args` in `kagura_brain.claude`
so the launcher seam is defined in exactly one place. Re-exported here to keep the
existing `kagura_planner.proc` import path stable.
"""
from __future__ import annotations

from kagura_brain.claude import mcp_args
from kagura_brain.core import as_text

__all__ = ["as_text", "mcp_args"]
