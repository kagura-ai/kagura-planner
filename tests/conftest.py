from __future__ import annotations

import io

import pytest

from kagura_planner.config import Config
from tests._constants import (
    VALID_CONTEXT_UUID, VALID_MEMORY_URL, VALID_PROFILE, VALID_WORKSPACE,
)


@pytest.fixture
def spy_text_opens(monkeypatch):
    """Factory spying ``io.open``: records the encoding of every TEXT-mode open
    whose filename ends with the given suffix, forwarding the call verbatim.

    Locale-independent regression seam for the utf-8 pinning fix (#18): an
    unpinned ``read_text``/``write_text`` shows up here as the ``'locale'``
    sentinel (or ``None``) instead of ``'utf-8'``, so the assertion fails on
    the bug on every runner, not only on a cp932 default locale."""
    real_open = io.open

    def _install(suffix: str) -> list:
        seen: list = []

        def spy(*args, **kwargs):
            # pathlib calls io.open(file, mode, buffering, encoding, errors,
            # newline) positionally; read encoding from arg 3 (or the kwarg)
            # and forward everything to avoid a dup-argument TypeError.
            file = args[0] if args else kwargs.get("file", "")
            mode = args[1] if len(args) > 1 else kwargs.get("mode", "r")
            enc = args[3] if len(args) > 3 else kwargs.get("encoding")
            if "b" not in mode and str(file).endswith(suffix):
                seen.append(enc)
            return real_open(*args, **kwargs)

        monkeypatch.setattr(io, "open", spy)
        return seen

    return _install


@pytest.fixture
def valid_config() -> Config:
    return Config(
        profile=VALID_PROFILE,
        memory_cloud_url=VALID_MEMORY_URL,
        workspace_id=VALID_WORKSPACE,
        context_id=VALID_CONTEXT_UUID,
    )
