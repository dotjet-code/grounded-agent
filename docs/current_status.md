# Current Status

Last updated: 2026-03-16

## Project Direction

**Primary goal:** 成長する自律型AIペルソナを作る。
**Secondary:** ベンチマーク/ログ/レポートは支援インフラとして残す。ECC比較は当面行わない。

## Completed (main branch)

### Benchmark Framework (support infrastructure)
- CLI benchmark logger — `record`, `list` subcommands
- Markdown report generator — `report` subcommand with `--save` option
- Comparison protocol — frozen for `report_gen_v1` (`docs/protocol.md`)
- Project context files — `PROJECT_OVERVIEW.md`, `docs/decisions.md`, `docs/workflow_for_chatgpt.md`

### Persona Design (main branch)
- Design documents — `docs/persona/` (growth engine, personality seed, phases, anti-patterns, system prompt, tech stack)
- SQLite memory module — `src/persona/memory.py` (vocabulary, curiosity, diary, phase detection)

## Experimental (feat/persona-bluesky-exp branch)

以下は実験ブランチ上の作業。main には未マージ。

- **PersonaCore** — `src/persona/core.py` (observe, reflect, context — LLM抽象化済み)
- **PersonaState** — `src/persona/state.py` (フェーズ判定、関心事、summary生成 — Memory読み取り専用)
- **Bluesky client** — `src/persona/bluesky.py` (タイムライン取得、投稿 — 外部アダプター)
- **Test suite** — 115 tests passing (benchmark: 39, memory: 21, core: 20, state: 23, bluesky: 12)

## Persona Implementation Progress

| Step | Description | Status | Branch |
|------|-------------|--------|--------|
| 1 | SQLite memory module | Done | main |
| 2 | PersonaCore (brain) | Done | experiment |
| 3 | PersonaState (internal state) | Done | experiment |
| 4 | Bluesky client (adapter) | Done | experiment |
| 5 | Local execution loop (CLI) | Not started | — |
| 6 | LLM adapter (Claude API) | Not started | — |
| 7 | launchd schedule | Not started | — |

## Active Machine

- **MacBook** — primary development
- **Mac mini** — inactive, paused

## Branches

- `main` — stable: benchmark framework + persona design docs + memory module
- `feat/persona-bluesky-exp` — experimental: PersonaCore + Bluesky client
