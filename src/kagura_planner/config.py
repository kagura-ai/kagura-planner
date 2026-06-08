from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError, model_validator


class ConfigError(Exception):
    """Raised when repo.yaml is missing, unparseable, or fails validation."""


class Config(BaseModel):
    profile: str
    memory_cloud_url: str = ""
    workspace_id: str = ""
    context_id: str = ""
    memory_backend: Literal["cloud", "local"] = "cloud"
    local_memory_path: str = ".kagura/memory.db"
    # Directory (relative to the caller's repo) for generated plan docs.
    # Gitignored — plan docs are decision records persisted to Memory Cloud.
    plan_dir: str = "docs/plans"

    @model_validator(mode="after")
    def _require_cloud_fields(self) -> "Config":
        if self.memory_backend == "cloud":
            missing = [
                n for n in ("memory_cloud_url", "workspace_id", "context_id")
                if not getattr(self, n)
            ]
            if missing:
                raise ValueError("memory_backend='cloud' requires: " + ", ".join(missing))
        return self


def load_config(path: str | Path) -> Config:
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"config not found: {p}")
    try:
        text = p.read_text()
    except OSError as exc:
        raise ConfigError(f"could not read config {p}: {exc}") from exc
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML: {exc}") from exc
    try:
        return Config.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"config validation failed: {exc}") from exc
