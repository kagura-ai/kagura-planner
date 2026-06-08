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
