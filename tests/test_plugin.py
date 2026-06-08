import json
from pathlib import Path

import kagura_planner

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_plugin_json_exists_and_parses():
    assert PLUGIN_JSON.is_file(), f"missing {PLUGIN_JSON}"
    _load(PLUGIN_JSON)  # raises if not valid JSON


def test_plugin_json_required_keys():
    data = _load(PLUGIN_JSON)
    for key in ("name", "version", "description", "author", "license"):
        assert key in data, f"plugin.json missing '{key}'"
    assert data["name"] == "kagura-planner"
    assert data["license"] == "Apache-2.0"


def test_plugin_json_version_matches_package():
    data = _load(PLUGIN_JSON)
    assert data["version"] == kagura_planner.__version__


MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def test_marketplace_json_exists_and_parses():
    assert MARKETPLACE_JSON.is_file(), f"missing {MARKETPLACE_JSON}"
    _load(MARKETPLACE_JSON)


def test_marketplace_required_keys_and_plugin_entry():
    data = _load(MARKETPLACE_JSON)
    for key in ("name", "description", "owner", "plugins"):
        assert key in data, f"marketplace.json missing '{key}'"
    assert data["name"] == "kagura-planner"
    assert isinstance(data["plugins"], list) and len(data["plugins"]) == 1
    entry = data["plugins"][0]
    assert entry["name"] == "kagura-planner"
    assert entry["source"] == "./"


def test_marketplace_version_synced_everywhere():
    plugin = _load(PLUGIN_JSON)
    market = _load(MARKETPLACE_JSON)
    assert (
        plugin["version"]
        == market["plugins"][0]["version"]
        == kagura_planner.__version__
    ), "version drift across plugin.json / marketplace.json / __version__"
