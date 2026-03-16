# Decisions

Architectural and process decisions made in this project.

## 1. ECC-Driven Only

This repo is developed exclusively under the ECC workflow. The "old" vanilla Claude Code workflow runs in a separate project for comparison. We do not mix workflows within this repo.

## 2. Local-Only

No cloud services, no deployment, no external APIs. All data stays on disk as JSON and Markdown. This keeps the project simple and removes infrastructure as a variable.

## 3. Zero External Dependencies

Production code uses only the Python standard library. Dev dependencies (pytest, black, ruff) are optional. This avoids dependency noise in benchmark measurements.

## 4. Frozen Prompts for Reproducibility

Each benchmark task has a frozen prompt file in `docs/prompts/`. Both ECC and old workflows receive the identical prompt text. The comparison protocol in `docs/protocol.md` locks down model, machine, commit, and human behavior.

## 5. Session-Based Recording

Each benchmark run produces one JSON file in `data/sessions/`. Files are named `{workflow}_{task_id}_{session_id}.json`. This flat structure is simple to query and diff.

## 6. Immutable Data Models

`Session` and `ErrorRecord` use frozen dataclasses. Once recorded, session data is not modified.

## 7. MacBook as Primary Dev Machine

As of 2026-03-16, MacBook is the active development machine. Mac mini is paused and should be treated as inactive until explicitly reactivated.

## 8. Commit Convention

Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `ci:`. No co-author attribution (disabled globally).
