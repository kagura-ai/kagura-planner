import pytest

from kagura_planner.config import Config, ConfigError, load_config


def test_cloud_backend_requires_fields():
    with pytest.raises(ValueError):
        Config(profile="default", memory_backend="cloud")


def test_local_backend_needs_no_cloud_fields():
    cfg = Config(profile="default", memory_backend="local")
    assert cfg.plan_dir == "docs/plans"


def test_absolute_plan_dir_is_rejected():
    """An absolute plan_dir could write outside the repo root; reject it."""
    with pytest.raises(ValueError):
        Config(
            profile="default",
            memory_cloud_url="https://m.example.com",
            workspace_id="ws",
            context_id="ctx",
            plan_dir="/tmp/x",
        )


def test_relative_plan_dir_is_accepted():
    cfg = Config(
        profile="default",
        memory_cloud_url="https://m.example.com",
        workspace_id="ws",
        context_id="ctx",
        plan_dir="custom/plans",
    )
    assert cfg.plan_dir == "custom/plans"


def test_default_plan_dir_is_valid():
    cfg = Config(
        profile="default",
        memory_cloud_url="https://m.example.com",
        workspace_id="ws",
        context_id="ctx",
    )
    assert cfg.plan_dir == "docs/plans"


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.yaml")


def test_load_config_read_pins_utf8(tmp_path, spy_text_opens):
    """Regression (#18): the config read must pin encoding='utf-8' — the OS
    default codec (cp932 on Windows-JP) raises UnicodeDecodeError on a UTF-8
    repo.yaml containing non-ASCII (e.g. a Japanese comment)."""
    p = tmp_path / "repo.yaml"
    p.write_text(
        "profile: default\nmemory_backend: local\n# メモ 🎉\n", encoding="utf-8"
    )
    seen = spy_text_opens("repo.yaml")
    cfg = load_config(p)
    assert cfg.profile == "default"
    assert seen, "expected repo.yaml to be opened as text"
    assert all(e == "utf-8" for e in seen), f"unpinned open observed: {seen}"


def test_load_config_invalid_utf8_raises_config_error(tmp_path):
    """A repo.yaml that is not valid UTF-8 (e.g. saved as cp932/latin-1) must
    surface as ConfigError — load_config's whole error contract — not as a raw
    UnicodeDecodeError, which is a ValueError subclass the OSError clause
    cannot catch."""
    p = tmp_path / "repo.yaml"
    p.write_bytes("profile: default\n# メモ\n".encode("cp932"))
    with pytest.raises(ConfigError, match="could not read config"):
        load_config(p)


def test_load_config_valid(tmp_path):
    p = tmp_path / "repo.yaml"
    p.write_text(
        "profile: default\n"
        "memory_cloud_url: https://m.example.com\n"
        "workspace_id: ws\ncontext_id: ctx\n"
    )
    cfg = load_config(p)
    assert cfg.context_id == "ctx" and cfg.plan_dir == "docs/plans"
