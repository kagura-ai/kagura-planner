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
