"""Subprocess helpers shared by the brain wrapper."""
from __future__ import annotations


def as_text(value: bytes | str | None) -> str:
    """Normalize subprocess stdout/stderr to str (TimeoutExpired carries raw
    bytes even under text=True)."""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value or ""
