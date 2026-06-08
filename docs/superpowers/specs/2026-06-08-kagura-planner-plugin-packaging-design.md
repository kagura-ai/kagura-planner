# kagura-planner as a Claude Code Plugin — Design

**Date:** 2026-06-08
**Status:** Approved (design) — pending implementation plan
**Builds on:** `2026-06-08-kagura-planner-design.md` (the CLI). This spec adds the
**plugin distribution layer** on top of the shipped v0.1.0 CLI; it does not change
any CLI behavior.

## 1. Purpose

Make `kagura-planner` installable as a Claude Code **plugin** so its
memory-grounded planning is reachable from inside a Claude Code session (not only
as a shell CLI). Concretely: add a `skills/` directory + a `.claude-plugin/`
manifest pair to the repo, mirroring the sibling **kagura-code-reviewer** plugin
repo, so that a (future) central **kagura-plugins** aggregator marketplace — or a
direct `/plugin marketplace add kagura-ai/kagura-planner` — can reference and
install it.

The CLI stays the engine; the plugin is a thin **skill wrapper** that teaches
Claude *when* and *how* to invoke the already-installed `kagura-planner` CLI and
consume its JSON envelope.

### Relationship to the CLI (no duplication)

```
Claude Code session
  └─ skill: kagura-planner:plan   ──shells out──▶  `kagura-planner plan "<idea>" --envelope`
       (markdown instructions only)                 (the real engine: recall→brain→write→remember)
                                                              │ JSON envelope on stdout
                                                              ▼
                                          plan_doc_path · summary · memory_id · edges · exit code
```

The skill is **instructions, not logic**. It never reimplements recall/plan/
remember — it calls the CLI and reads the envelope. This matches the
engineer↔reviewer "thin consumption" discipline already established in the CLI spec.

## 2. Distribution split (the key boundary)

Two artifacts ship from one repo, by two channels — keep them separate:

| artifact | channel | consumed by | contains |
|---|---|---|---|
| `kagura-planner` **CLI** | **PyPI** (`pip`/`uv`/`pipx`) | the shell / `kagura-agent` subprocess | the Python engine |
| `kagura-planner` **plugin** | **git repo / marketplace** | Claude Code `/plugin` | `skills/` + `.claude-plugin/` (markdown + JSON) |

**Trap (explicit):** do **not** bundle `skills/` or `.claude-plugin/` into the
PyPI wheel/sdist. They are Claude Code plugin assets read from the git repo by the
marketplace, not Python package data. No `pyproject.toml` packaging change is
needed; the wheel keeps shipping only `src/kagura_planner`.

## 3. Files added

```
kagura-planner/
├─ .claude-plugin/
│  ├─ plugin.json          # the plugin manifest (name, version, metadata)
│  └─ marketplace.json     # self-publishing single-plugin marketplace
└─ skills/
   └─ plan/
      └─ SKILL.md          # model-facing: when/how to invoke `kagura-planner plan`
```

Skills are **auto-discovered** from `skills/` (as in the superpowers plugin —
its `plugin.json` lists no `commands`/`skills` key). So `plugin.json` carries
metadata only; no command/skill pointer is required.

### 3.1 `.claude-plugin/plugin.json`

Mirrors kagura-code-reviewer's manifest shape:

```json
{
  "name": "kagura-planner",
  "version": "0.1.0",
  "description": "Memory-grounded PLAN-layer skill over Claude Code + Kagura Memory — turns an idea into a recallable, memory-grounded plan doc.",
  "author": { "name": "Kagura AI, Inc.", "url": "https://github.com/kagura-ai" },
  "homepage": "https://github.com/kagura-ai/kagura-planner",
  "repository": "https://github.com/kagura-ai/kagura-planner",
  "license": "Apache-2.0",
  "keywords": ["planning", "memory", "claude-code", "kagura", "ai-agent", "developer-tools"]
}
```

### 3.2 `.claude-plugin/marketplace.json`

Lets the repo be added directly as its own marketplace (kagura-code-reviewer
parity), and is equally referenceable by a central aggregator:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "kagura-planner",
  "description": "Memory-grounded PLAN-layer skill — idea → recallable plan doc, grounded in Kagura Memory.",
  "owner": { "name": "Kagura AI, Inc.", "url": "https://github.com/kagura-ai" },
  "plugins": [
    { "name": "kagura-planner", "source": "./", "version": "0.1.0", "category": "ai" }
  ]
}
```

> A future **kagura-plugins** aggregator references this repo with
> `{ "name": "kagura-planner", "source": { "source": "github", "repo": "kagura-ai/kagura-planner" } }`
> — Claude Code then reads this repo's `.claude-plugin/plugin.json`. That repo is
> out of scope here; this spec only makes kagura-planner *referenceable*.

### 3.3 `skills/plan/SKILL.md`

Frontmatter (`name`, `description`) + body. Invoked in-session as
`kagura-planner:plan`. The body instructs Claude to:

1. **Preflight** — if unsure the CLI/env is ready, run `kagura-planner doctor`
   (exit 0 = go). If `kagura-planner` is not on PATH, tell the user to install it
   (`uv tool install kagura-planner` / `pipx install kagura-planner`) — the skill
   markdown cannot install the Python package itself.
2. **Run** — `kagura-planner plan "<idea>" --envelope` (add `--no-remember` only
   if the user asks for an ephemeral plan).
3. **Consume the envelope** — parse the JSON on stdout; surface `plan_doc_path`,
   `summary`, `memory_id`, and any `edges`. **Never scrape the markdown plan doc**
   — read the envelope only (same discipline the CLI spec mandates for agents).
4. **Exit codes** — `0` plan written · `1` infra failure · `2` blocked by env
   guard; explain the failure phase from the envelope rather than retrying blindly.

**When to use** (the `description`): the user wants a memory-grounded
implementation plan / decision record for an idea, grounded in past decisions and
known traps. **When not to:** building/executing the plan (that is engineer
`run`/`goal`, not planner).

## 4. Validation (pytest — no asset rot, no version drift)

A new `tests/test_plugin.py` validates the static assets (kept green under the
existing TDD + ruff + mypy gates; coverage `source` is `src/` only, so these tests
add coverage of nothing and cannot lower the gate):

- `plugin.json` and `marketplace.json` parse as JSON and carry required keys
  (`name`, `version`, `description`, `license`/`owner`, …).
- `name` is `"kagura-planner"` consistently across both JSON files.
- **Version sync:** `plugin.json.version` == `marketplace.json.plugins[0].version`
  == `kagura_planner.__version__`. `__init__.py` is the single source of truth;
  the test fails the build on drift (the central trap when a repo carries the same
  version in three places).
- `skills/plan/SKILL.md` exists, has YAML frontmatter with non-empty `name` +
  `description`, and `name` matches the directory (`plan`).

Optionally a tiny frontmatter helper is factored so the test reads cleanly; no new
runtime dependency (use stdlib + the already-present `pyyaml`).

## 5. Docs

README gains a short **"Use as a Claude Code plugin"** section: add the
marketplace (`/plugin marketplace add kagura-ai/kagura-planner`), install, ensure
the `kagura-planner` CLI is installed from PyPI, then invoke `kagura-planner:plan`.
Keeps the existing CLI setup section.

## 6. Scope & YAGNI

**In scope:** one `plan` skill, `plugin.json`, `marketplace.json`, version-sync +
frontmatter tests, README section.

**Out of scope (deferred):**
- A second `doctor` skill — the CLI's `doctor` is documented as a preflight inside
  the `plan` skill; a standalone skill is a trivial later add if first-run setup
  needs it.
- Creating the central **kagura-plugins** aggregator repo — separate effort; this
  spec only makes kagura-planner referenceable.
- Bundling skills into the PyPI wheel — explicitly rejected (§2 trap).
- Hooks / agents / MCP servers in the manifest — not needed for a skill wrapper.

## 7. Risks / traps captured

1. **Version drift** across `__init__.py` / `plugin.json` / `marketplace.json` →
   pinned by the §4 version-sync test.
2. **Bundling plugin assets into the wheel** → rejected; wheel stays `src/` only.
3. **Skill reimplementing CLI logic** → forbidden; skill is instructions that
   shell out and read the envelope (markdown-scraping banned).
4. **CLI not installed when skill runs** → skill preflights `doctor` and gives a
   PyPI install hint; the plugin cannot install the Python package itself.
5. **PyPI publish still pending** (per project status) → the plugin is shippable
   independently; the skill's install hint works once v0.1.0 is on PyPI. No
   ordering dependency blocks this work.
