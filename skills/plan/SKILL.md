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
- `memory_id` — the remembered plan (a recallable decision record), or **`null`**
  when persist failed (a degraded / exit-3 run — see below).
- `edges` — links created to recalled memories (refines / supersedes / depends_on).

Report `summary` and `plan_doc_path` to the user. If `memory_id` is non-null,
mention the plan was remembered so future plans can build on it. If `memory_id`
is `null` (status `warn` / exit 3), tell the user the plan doc was written but was
**NOT** persisted to memory — do not claim a recallable record exists.

## Exit codes

- `0` — plan written successfully and persisted.
- `1` — hard failure (the headless Claude run failed, recall raised, or the doc
  could not be written); no plan doc.
- `2` — blocked by the environment guard (run `kagura-planner doctor` to see why).
- `3` — degraded: the plan doc **was** written (`plan_doc_path` is valid), but the
  best-effort persist to Memory Cloud failed, so `memory_id` is `null`. The plan
  exists — surface it; do **not** re-run.

On a non-zero exit, explain the failing phase from the envelope/output rather than
blindly re-running the same command. Exit `3` is **not** a failure to re-run: the
plan doc landed; only persistence was lost.
