# Workflow for ChatGPT

Guidelines for ChatGPT when collaborating on this project.

## Role

ChatGPT assists with planning, research, prompt drafting, and design decisions. Claude Code handles all code implementation, testing, and git operations directly in the repo.

## Key Context

- This repo is **ECC-driven only**. Do not suggest removing or bypassing ECC agents/skills/rules.
- The comparison target (vanilla Claude Code) lives in a **separate older project**, not here.
- All data and processing is **local-only**. Do not suggest cloud services, databases, or deployments.
- Production code has **zero external dependencies** (stdlib only).

## Machine Context

| Machine | Role | Status |
|---------|------|--------|
| MacBook | Primary dev | Active |
| Mac mini | Benchmark runner | Inactive (paused) |

Do not assume Mac mini availability unless explicitly told it's reactivated.

## Conventions

- **Commits**: conventional format (`feat:`, `fix:`, `docs:`, etc.)
- **Tests**: pytest, aim for 80%+ coverage, TDD preferred
- **Data**: session JSON in `data/sessions/`, reports in `data/reports/`
- **Prompts**: frozen in `docs/prompts/`, never edited after creation

## What to Do

- Propose concrete, scoped tasks (one feature or fix at a time)
- Reference existing files and structure accurately
- Check `docs/current_status.md` before suggesting next steps
- Keep suggestions compatible with the ECC workflow

## What to Avoid

- Suggesting features that require external services or dependencies
- Proposing changes to frozen prompts or protocol
- Assuming both machines are active
- Over-engineering: this project values simplicity and incremental progress
- Generating code directly (Claude Code handles implementation)
