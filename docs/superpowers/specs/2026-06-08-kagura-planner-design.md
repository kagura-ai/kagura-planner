# kagura-planner Design

**Date:** 2026-06-08
**Status:** Approved (design) — pending implementation plan
**Supersedes:** decision `ea65af66` ("kagura-planner は作らない") and the deferred framing in `ce10599f` (planner-as-memory-harness = deferred candidate). This spec activates that harness as a thin standalone CLI.

## 1. Purpose & Positioning

`kagura-planner` is a thin, standalone Python CLI that grounds Claude Code's
**official planning skills** (`brainstorming` → `writing-plans`) in **Kagura
Memory Cloud**. It is consumed on demand by `kagura-agent` as a separate CLI —
the same "thin consumption" relationship `kagura-engineer` has when it shells
out to `kagura-code-reviewer` via `review`.

It fills the **PLAN** edge of the memory-grounding loop:

| role | command | transform |
|---|---|---|
| kagura-engineer | `run` | issue# → PR |
| kagura-code-reviewer | (review) | PR → JSON verdict |
| **kagura-planner** | **`plan`** | **idea → memory-grounded plan doc (→ optional milestone)** |

The differentiator is **not planning intelligence** (Claude's official skills
already provide that) but **cross-session memory grounding**: recall before,
remember + edges after. A planner without memory is a thin wrapper; with memory
it makes every plan a recallable decision record that improves the next plan.

## 2. Architecture (engineer-isomorphic, 3-layer)

| layer | implementation |
|---|---|
| **actor** | `kagura-planner` — `src/kagura_planner/`, Typer CLI, **Apache-2.0 open-core** (sibling of engineer/reviewer; not Proprietary like kagura-agent) |
| **brain** | Claude Code launched headless via `claude -p`, running official `brainstorming` → `writing-plans` skills. **Runs on the Claude Code subscription auth** (not API-key billing). |
| **persistence** | Kagura Memory Cloud — `recall` / `remember` / `create_edge` |
| **workflow** (optional path only) | `gh-issue-driven:propose` (MIT, explicit dependency) — engaged **only** under `plan --populate` |

The default `plan` path closes over `brain + persistence` only. `gh-issue-driven`
is an optional dependency for the `--populate` extension.

## 3. CLI Surface (thin: 2 commands)

- **`doctor`** — environment assurance: `claude` CLI on PATH, Memory Cloud
  reachable + authenticated (rides existing `kagura` CLI auth — no separate
  `setup`), required skills present (`brainstorming`, `writing-plans`; plus
  `gh-issue-driven:propose` when `--populate` is requested). Per-phase isolation
  (engineer `doctor.run_all` pattern).
- **`plan <idea>`** — the body. `--populate` flag extends the pipeline to
  issues/milestone.

## 4. Data Flow — `plan <idea>`

```
guard (lightweight doctor; resolve memory context_id)
  → recall    : similar plans / past decisions / known traps (k results)   [grounding #1]
  → brain     : claude -p [brainstorming → writing-plans], fed idea + recalled grounding
  → write doc : plan markdown → <plan-dir>/YYYY-MM-DD-<slug>.md (gitignored)
  → remember  : plan summary + rationale + assumptions (type=decision)      [grounding #2]
  → edges     : create_edge to recalled memories (refines / supersedes / depends_on) [grounding #3]
  → emit      : JSON envelope on stdout (for agent consumption)
[--populate only]
  → decompose plan steps
  → for each step: claude -p [gh-issue-driven:propose] → issue#
  → assemble ordered milestone  (= produces the input that engineer `goal` consumes)
```

Generated plan docs live at a **default directory `docs/plans/` (relative to the
caller's repo) that is `.gitignore`d** — they are working artifacts that also
persist into Memory Cloud, so they are not committed to git. The path is
overridable via planner config / a `--out` flag.

## 5. Agent Consumption Boundary

`kagura-planner` emits a **JSON envelope on stdout** (engineer `review`
contract, isomorphic) plus an **exit code**. The envelope carries:

- `plan_doc_path`
- `summary`
- `memory_id` (the remembered plan) and `edges` created
- optionally `milestone` / `issue` references (when `--populate`)

Exit codes: `0` ok / `1` infra failure / `2` plan not produced. `kagura-agent`
consumes via subprocess and reads the JSON only — **Markdown scraping is
forbidden** (same discipline as engineer↔reviewer).

## 6. Error Handling

Engineer pattern (`dc9abf84`): every external boundary (claude subprocess,
Memory SDK, `gh`) is wrapped in `try/except` and converted into a clean FAIL
phase in a `PhaseReport` — no tracebacks leak. Per-phase isolation mirrors
`doctor.run_all` / `setup.run_plan`.

## 7. Testing & Quality

TDD. `pytest` + `mypy --strict` + `ruff`, coverage gate ~95% (engineer parity).
Memory SDK and the `claude` subprocess are mocked in unit tests; a thin
integration smoke exercises a real `claude -p` plan end-to-end.

## 8. Scope & Staged Delivery (YAGNI)

- **Plan 1** — repo init + package scaffold + `doctor`
- **Plan 2** — `plan` default path (recall → brain → write doc → remember)
- **Plan 3** — edges + JSON envelope finalize
- **Plan 4** — `--populate` (decompose → `propose` → ordered milestone)

`--populate` is the "optional" terminus (the user chose plan-doc as the default
output, milestone population as an opt-in flag). It is intentionally last so the
default planner ships without a hard `gh-issue-driven` dependency.

## 9. Open / Deferred (explicitly out of scope for v0.1)

- `trust-tier` filtering on recall, `quarantine`/graduation on remember
  (inherit from kagura-agent memory-access design later if needed).
- Multi-context planning, plan diffing, plan templates.
- Any TUI / web surface.
