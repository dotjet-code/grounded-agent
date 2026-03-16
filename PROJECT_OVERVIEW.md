# Project Overview: grounded-agent

## What This Is

A local-only benchmark framework for measuring autonomous AI workflow performance.
This repo is built and maintained entirely under the **ECC (Everything Claude Code)** workflow.

## What ECC Means Here

ECC = Claude Code enhanced with specialized agents, skills, hooks, and project rules.
This repo itself is an ECC project. The "old workflow" (vanilla Claude Code) is the comparison target, run in a **separate older project**, not inside this repo.

## Comparison Model

| Aspect | This Repo (grounded-agent) | Separate Project |
|--------|---------------------------|------------------|
| Workflow | ECC (agents, skills, rules) | Vanilla Claude Code |
| Purpose | Primary development | Comparison baseline |
| Status | Active | Run on-demand for benchmarks |

Both workflows are measured on identical frozen tasks (same prompt, same starting commit, same model) and results are recorded as session JSON files.

## Machine Roles

| Machine | Role | Status |
|---------|------|--------|
| MacBook | Primary development machine | **Active** |
| Mac mini | Execution / benchmark runner | **Inactive** (paused) |

## Tech Stack

- Python 3.11+, zero external dependencies
- pytest for testing
- CLI via argparse (`python -m src`)
- Data stored as JSON in `data/sessions/`
- Reports generated as Markdown

## Repo Structure

```
src/
  __main__.py        # CLI entry point (record, list, report)
  config.py          # Paths, constants, dimensions
  models.py          # Session and ErrorRecord dataclasses
  logger/            # Session save/load/list
  report/            # Markdown report generation
tests/               # pytest test suite
data/
  sessions/          # Recorded benchmark session JSON files
  reports/           # Generated report files
docs/
  benchmark.md       # Comparison dimensions (Japanese)
  protocol.md        # Frozen comparison protocol
  prompts/           # Frozen task prompts for reproducible benchmarks
```

## Key Metrics Tracked

duration, outcome, error_count, human_interventions, files_created, tests_passed, tests_failed, autonomy_ratio

## CLI Commands

```bash
python -m src record   # Interactively record a benchmark session
python -m src list     # List recorded sessions (--workflow, --task filters)
python -m src report   # Generate Markdown summary report
```
