from __future__ import annotations

from pathlib import Path, PureWindowsPath
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError, field_validator, model_validator


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

    @field_validator("plan_dir")
    @classmethod
    def _plan_dir_must_be_relative(cls, v: str) -> str:
        # plan_dir is joined onto the repo root (root / cfg.plan_dir); an
        # absolute path would silently escape the repo, so reject it. Check both
        # POSIX (/x) and Windows (C:\x, \\x, \x) absolute forms regardless of host
        # OS so a config authored on one platform is validated the same on another.
        if Path(v).is_absolute() or PureWindowsPath(v).is_absolute():
            raise ValueError(f"plan_dir must be repo-relative, got absolute path: {v!r}")
        return v

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
        # Pinned: the locale default (cp932 on Windows-JP) cannot decode a
        # UTF-8 config containing non-ASCII (#18).
        text = p.read_text(encoding="utf-8")
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
