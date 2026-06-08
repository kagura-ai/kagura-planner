# kagura-planner

Memory-grounded PLAN-layer CLI over Claude Code + Kagura Memory.

## Setup

```bash
# 1. copy the template (your real config is gitignored, never committed)
cp repo.yaml.example repo.yaml

# 2. edit repo.yaml with your own values:
#    memory_cloud_url, workspace_id, context_id

# 3. authenticate the Kagura Memory client (OAuth profile), or set KAGURA_API_KEY
kagura auth login

# 4. verify the dependency chain
kagura-planner doctor
```

`repo.yaml` is gitignored so your real `workspace_id` / `context_id` stay out of
version control. Point any command at an alternate config with `-c/--config`
(e.g. `kagura-planner plan "..." -c ~/.kagura/planner.yaml`).

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
