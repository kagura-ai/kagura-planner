# kagura-planner Plugin Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the shipped `kagura-planner` CLI as an installable Claude Code plugin (a `skills/` skill + `.claude-plugin/` manifest pair) so a central `kagura-plugins` aggregator marketplace — or a direct `/plugin marketplace add` — can reference and install it.

**Architecture:** Add static plugin assets to the repo with **no change to CLI behavior or PyPI packaging**. The plugin is a thin skill that shells out to the existing `kagura-planner plan --envelope` CLI and reads its JSON envelope (no logic duplication). A pytest module locks version-sync and skill-frontmatter validity so the assets can't rot. Mirrors the sibling `kagura-code-reviewer` plugin-repo shape.

**Tech Stack:** JSON manifests (`plugin.json`, `marketplace.json`), Markdown skill (`SKILL.md` with YAML frontmatter), Python 3.11 + pytest + PyYAML (already deps), hatchling (unchanged).

---

## File Structure

Files created/modified by this plan:

- **Create** `.claude-plugin/plugin.json` — plugin manifest (metadata only; skills auto-discovered).
- **Create** `.claude-plugin/marketplace.json` — self-publishing single-plugin marketplace entry.
- **Create** `skills/plan/SKILL.md` — model-facing instructions: when/how to invoke `kagura-planner plan --envelope` and consume its envelope.
- **Create** `tests/test_plugin.py` — validates JSON manifests, version-sync against `__version__`, and SKILL.md frontmatter.
- **Modify** `README.md` — add a "Use as a Claude Code plugin" section.

No `pyproject.toml` change: the wheel keeps shipping only `src/kagura_planner`; plugin assets ship via the git repo, not PyPI.

---

## Task 1: Plugin manifest (`plugin.json`)

**Files:**
- Create: `.claude-plugin/plugin.json`
- Test: `tests/test_plugin.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_plugin.py` with:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_plugin.py -v`
Expected: FAIL — `test_plugin_json_exists_and_parses` fails with `missing .../.claude-plugin/plugin.json` (the other two error on the missing file too).

- [ ] **Step 3: Create the manifest**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "kagura-planner",
  "version": "0.1.0",
  "description": "Memory-grounded PLAN-layer skill over Claude Code + Kagura Memory — turns an idea into a recallable, memory-grounded plan doc.",
  "author": {
    "name": "Kagura AI, Inc.",
    "url": "https://github.com/kagura-ai"
  },
  "homepage": "https://github.com/kagura-ai/kagura-planner",
  "repository": "https://github.com/kagura-ai/kagura-planner",
  "license": "Apache-2.0",
  "keywords": [
    "planning",
    "memory",
    "claude-code",
    "kagura",
    "ai-agent",
    "developer-tools"
  ]
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_plugin.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json tests/test_plugin.py
git commit -m "feat(plugin): add Claude Code plugin manifest (plugin.json)"
```

---

## Task 2: Self-publishing marketplace entry (`marketplace.json`)

**Files:**
- Create: `.claude-plugin/marketplace.json`
- Modify: `tests/test_plugin.py`

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_plugin.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_plugin.py -v`
Expected: FAIL — the three new tests fail with `missing .../.claude-plugin/marketplace.json`; the Task 1 tests still PASS.

- [ ] **Step 3: Create the marketplace entry**

Create `.claude-plugin/marketplace.json`:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "kagura-planner",
  "description": "Memory-grounded PLAN-layer skill — idea → recallable plan doc, grounded in Kagura Memory.",
  "owner": {
    "name": "Kagura AI, Inc.",
    "url": "https://github.com/kagura-ai"
  },
  "plugins": [
    {
      "name": "kagura-planner",
      "source": "./",
      "version": "0.1.0",
      "category": "ai"
    }
  ]
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_plugin.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/marketplace.json tests/test_plugin.py
git commit -m "feat(plugin): self-publish as single-plugin marketplace (marketplace.json)"
```

---

## Task 3: The `plan` skill (`SKILL.md`)

**Files:**
- Create: `skills/plan/SKILL.md`
- Modify: `tests/test_plugin.py`

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_plugin.py`. This parses the YAML frontmatter with the
already-installed `pyyaml`; no new dependency.

```python
import yaml

SKILL_MD = REPO_ROOT / "skills" / "plan" / "SKILL.md"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md must open with YAML frontmatter"
    _, fm, _body = text.split("---\n", 2)
    return yaml.safe_load(fm)


def test_skill_md_exists():
    assert SKILL_MD.is_file(), f"missing {SKILL_MD}"


def test_skill_frontmatter_has_name_and_description():
    fm = _frontmatter(SKILL_MD)
    assert fm.get("name") == "plan", "skill name must match its directory ('plan')"
    assert isinstance(fm.get("description"), str) and fm["description"].strip()


def test_skill_body_references_envelope_cli_not_markdown_scraping():
    body = SKILL_MD.read_text(encoding="utf-8")
    # The skill must drive the CLI with --envelope and consume JSON, never scrape the doc.
    assert "kagura-planner plan" in body
    assert "--envelope" in body
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_plugin.py -v`
Expected: FAIL — the three new skill tests fail with `missing .../skills/plan/SKILL.md`; the six earlier tests still PASS.

- [ ] **Step 3: Create the skill**

Create `skills/plan/SKILL.md`:

```markdown
---
name: plan
description: Use when the user wants a memory-grounded implementation plan or decision record for an idea — recalls related past decisions and known traps, produces a recallable plan doc, and remembers it. Do NOT use to build or execute the plan (that is the engineer's job).
---

# Memory-Grounded Planning (kagura-planner)

Turn an idea into a **memory-grounded plan doc**: recall related past work first,
run Claude Code's official `brainstorming → writing-plans` skills headless, write a
plan doc, and remember it (with edges to the recalled memories) so the next plan is
better. The real engine is the `kagura-planner` CLI — this skill drives it and reads
its JSON envelope. It never reimplements planning logic.

## When to use

- The user asks to "plan", "design an approach for", or "think through" an idea and
  would benefit from grounding in past decisions / known traps.
- The user wants a durable, recallable decision record, not just a chat answer.

## When NOT to use

- Building or executing a plan → that is the engineer (`run` / `goal`), not the planner.
- A throwaway question that does not warrant a persisted plan.

## Preflight

1. Confirm the CLI is installed: run `kagura-planner --version`.
   - If "command not found", tell the user to install it from PyPI:
     `uv tool install kagura-planner` (or `pipx install kagura-planner`).
     This skill is instructions only — it cannot install the Python package itself.
2. If you are unsure the environment is ready (Claude on PATH, Memory Cloud
   reachable, planning skills present), run `kagura-planner doctor`.
   Exit code 0 means go; non-zero means fix what doctor reports before planning.

## Run

```bash
kagura-planner plan "<the idea, quoted>" --envelope
```

- Add `--no-remember` ONLY if the user explicitly wants an ephemeral plan
  (recall still happens; the plan is just not persisted).
- Point at an alternate config with `-c <path/to/repo.yaml>` if the user has one.

## Consume the result

Read the **JSON envelope** printed on stdout — do NOT scrape the Markdown plan doc.
The envelope carries:

- `plan_doc_path` — where the plan doc was written (surface this to the user).
- `summary` — one-line summary of the plan.
- `memory_id` — the remembered plan (a recallable decision record).
- `edges` — links created to recalled memories (refines / supersedes / depends_on).

Report `summary` and `plan_doc_path` to the user, and mention the plan was
remembered (`memory_id`) so future plans can build on it.

## Exit codes

- `0` — plan written successfully.
- `1` — infra failure (e.g. Memory Cloud or the headless Claude run failed).
- `2` — blocked by the environment guard (run `kagura-planner doctor` to see why).

On a non-zero exit, explain the failing phase from the envelope/output rather than
blindly re-running the same command.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_plugin.py -v`
Expected: PASS (9 passed).

- [ ] **Step 5: Commit**

```bash
git add skills/plan/SKILL.md tests/test_plugin.py
git commit -m "feat(plugin): add kagura-planner:plan skill (drives plan --envelope)"
```

---

## Task 4: README — "Use as a Claude Code plugin" section

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the plugin section**

Append to `README.md` (after the existing Setup section):

```markdown

## Use as a Claude Code plugin

`kagura-planner` also ships as a Claude Code plugin (a `kagura-planner:plan` skill)
that drives the CLI from inside a session.

```bash
# 1. add this repo as a marketplace
/plugin marketplace add kagura-ai/kagura-planner

# 2. install the plugin
/plugin install kagura-planner@kagura-planner

# 3. ensure the CLI is installed (the skill shells out to it)
uv tool install kagura-planner   # or: pipx install kagura-planner
```

Then ask Claude to plan an idea — the `kagura-planner:plan` skill recalls related
past work, produces a memory-grounded plan doc, and remembers it. The skill reads
the CLI's JSON envelope (`plan --envelope`); it never reimplements planning logic.
```

- [ ] **Step 2: Verify the full test suite still passes**

Run: `pytest -q`
Expected: PASS — all existing tests plus the 9 new `tests/test_plugin.py` tests green.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): document Claude Code plugin install"
```

---

## Task 5: Full verification gate

**Files:** none (verification only)

- [ ] **Step 1: Run the complete quality gate**

Run:
```bash
pytest -q && mypy && ruff check .
```
Expected: pytest all green (coverage `fail_under=90` still satisfied — the new
tests add coverage of `src/` nothing and cannot lower the gate); `mypy` clean
(it checks `src` only, unaffected); `ruff check` clean.

> If `ruff` flags `tests/test_plugin.py` (e.g. import ordering), fix the lint
> inline and re-run — do not suppress.

- [ ] **Step 2: Confirm plugin assets are tracked and NOT bundled in the wheel**

Run:
```bash
git ls-files .claude-plugin skills
uv build && tar -tzf dist/kagura_planner-*.tar.gz | grep -E 'claude-plugin|skills/' || echo "OK: plugin assets correctly excluded from sdist"
```
Expected: `git ls-files` lists `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `skills/plan/SKILL.md`; the wheel/sdist check prints `OK: plugin assets correctly excluded from sdist` (the wheel ships only `src/kagura_planner`).

- [ ] **Step 3: Final commit (if any lint fixes were made)**

```bash
git add -A
git commit -m "chore(plugin): satisfy lint/type gates for plugin packaging"
```

---

## Self-Review (completed by plan author)

**Spec coverage:**
- §3.1 plugin.json → Task 1 ✓
- §3.2 marketplace.json → Task 2 ✓
- §3.3 SKILL.md (preflight/run/consume/exit codes, when/when-not) → Task 3 ✓
- §4 validation (JSON parse, required keys, version-sync, frontmatter) → Tasks 1–3 tests ✓
- §5 README plugin section → Task 4 ✓
- §2 wheel-exclusion trap → Task 5 Step 2 asserts it ✓
- §6 single `plan` skill, no doctor skill, no pyproject change → honored ✓
- §7 traps (version drift, wheel bundling, no logic dup, install hint) → Tasks 1–3 + 5 ✓

**Placeholder scan:** none — every code/JSON/markdown block is complete.

**Type/name consistency:** `_load` helper defined in Task 1, reused in Task 2; `_frontmatter` defined in Task 3; module-level path constants `REPO_ROOT`/`PLUGIN_JSON` (Task 1), `MARKETPLACE_JSON` (Task 2), `SKILL_MD` (Task 3) each defined before use. Skill `name: plan` matches dir `skills/plan/` and the test assertion. Version `0.1.0` consistent across both JSON files and `__version__`.
