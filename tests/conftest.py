from __future__ import annotations

import pytest

from kagura_planner.config import Config
from tests._constants import (
    VALID_CONTEXT_UUID, VALID_MEMORY_URL, VALID_PROFILE, VALID_WORKSPACE,
)


@pytest.fixture
def valid_config() -> Config:
    return Config(
        profile=VALID_PROFILE,
        memory_cloud_url=VALID_MEMORY_URL,
        workspace_id=VALID_WORKSPACE,
        context_id=VALID_CONTEXT_UUID,
    )
