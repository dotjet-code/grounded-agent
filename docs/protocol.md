# Comparison Protocol

## Purpose

Compare "old workflow" (vanilla Claude Code) against "ECC workflow" (Claude Code + Everything Claude Code) on an identical task to measure differences in autonomy, speed, error rate, and output quality.

## Definitions

### Old Workflow
Claude Code with zero ECC configuration:
- No ECC skills invoked (no `/tdd`, `/plan`, `/python-review`, etc.)
- No specialized subagent types (`code-reviewer`, `tdd-guide`, `planner`, etc.)
- Standard Claude Code capabilities only: Read, Edit, Write, Bash, Grep, Glob, Agent (general-purpose)
- `.claude/rules/` project rules remain loaded (they are project-owned, not ECC)

### ECC Workflow
Claude Code with full ECC configuration:
- All ECC skills, agents, hooks, and rules active
- Specialized subagents available and used proactively

## Task

- task_id: `report_gen_v1`
- prompt_file: `docs/prompts/report_gen_v1.md`
- starting_commit: `69b25e49fe1f53179bfd402e91b5df76755385a5`

## Controlled Variables

| Variable         | Value                                      |
|------------------|--------------------------------------------|
| model            | claude-opus-4-6 (Opus 4.6, 1M context)    |
| machine          | mac_mini                                   |
| python           | 3.9.6                                      |
| repo state       | commit `69b25e4` (both runs start here)    |
| prompt           | identical text from `docs/prompts/report_gen_v1.md` |
| human behavior   | approve all tool calls; do not volunteer extra info |
| network          | online for both runs                       |

## Run Order

1. **Run 1: old** (no ECC) — runs first to avoid ECC knowledge biasing evaluation
2. **Run 2: ecc** (full ECC) — runs second on a clean checkout of the same commit

After each run, record the session JSON to `data/sessions/` before resetting for the next run.

## Metrics

| Metric                | Description                                              |
|-----------------------|----------------------------------------------------------|
| `duration_seconds`    | Wall-clock time from first prompt to final working state |
| `outcome`             | `success` / `partial` / `failure`                        |
| `error_count`         | Build failures, test failures, wrong output              |
| `human_interventions` | Times the operator corrected, clarified, or redirected   |
| `tests_passed`        | Final test suite pass count                              |
| `tests_failed`        | Final test suite fail count                              |
| `files_created`       | Files created or modified                                |
| `tool_calls_total`    | Total tool invocations in the session                    |
| `autonomy_ratio`      | `1 - (human_interventions / tool_calls_total)`           |
| `notes`               | Qualitative observations                                 |

## Hypothesis

ECC workflow will show:
- Fewer human interventions (higher autonomy)
- More files with tests written proactively
- Comparable or faster wall-clock time despite additional agent overhead

## Status

- [x] Protocol defined
- [x] Prompt written and frozen
- [ ] Old run completed
- [ ] ECC run completed
- [ ] Comparison recorded
