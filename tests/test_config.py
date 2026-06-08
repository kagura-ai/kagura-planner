import pytest

from kagura_planner.config import Config, ConfigError, load_config


def test_cloud_backend_requires_fields():
    with pytest.raises(ValueError):
        Config(profile="default", memory_backend="cloud")


def test_local_backend_needs_no_cloud_fields():
    cfg = Config(profile="default", memory_backend="local")
    assert cfg.plan_dir == "docs/plans"


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.yaml")


def test_load_config_valid(tmp_path):
    p = tmp_path / "repo.yaml"
    p.write_text(
        "profile: default\n"
        "memory_cloud_url: https://m.example.com\n"
        "workspace_id: ws\ncontext_id: ctx\n"
    )
    cfg = load_config(p)
    assert cfg.context_id == "ctx" and cfg.plan_dir == "docs/plans"
