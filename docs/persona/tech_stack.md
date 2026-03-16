# Tech Stack Selection

## Hardware Context

- Machine: MacBook, Apple M5, 24GB RAM
- OS: macOS 26.3
- Runtime: Python 3.12 (via uv)
- Constraint: local-only development, MacBook is primary

---

## 1. LLM

### Options

| Model | Input/Output per 1M tokens | Strength | Weakness |
|-------|---------------------------|----------|----------|
| Claude Haiku 4.5 | $1 / $5 | Cheapest, fast, 90% of Sonnet quality | Less nuance in personality |
| Claude Sonnet 4.6 | $3 / $15 | Best coding/reasoning balance | 3x Haiku cost |
| Claude Opus 4.6 | $15 / $75 | Deepest reasoning | 15x Haiku cost, overkill for daily loop |
| GPT-4o mini | ~$0.15 / $0.60 | Cheapest overall | Different ecosystem, less familiar |
| Local (Llama etc.) | Free | No API cost, full privacy | Quality gap, M5 24GB limits model size |

### Decision: Claude Haiku 4.5 for the autonomous loop, Sonnet 4.6 for interactions

**Rationale:**

The autonomous loop runs multiple times per day. At Phase 0, each cycle is
short (observe → short post → diary). Estimated token usage per cycle:

```
Observation prompt + timeline context:  ~2,000 input tokens
Post generation:                        ~200 output tokens
Diary generation:                       ~300 output tokens
Memory read/write overhead:             ~1,000 input tokens
───────────────────────────────────────────────
Total per cycle:                        ~3,000 input + ~500 output

Daily cost (4 cycles/day):
  Input:  12,000 tokens × $1/1M  = $0.012
  Output:  2,000 tokens × $5/1M  = $0.010
  Daily total:                      ~$0.02
  Monthly total:                    ~$0.60
```

With Batch API (50% discount), monthly cost drops to ~$0.30.

Sonnet is reserved for reply generation where personality nuance matters more.
Estimated 5-10 replies/day at ~$0.05/day = ~$1.50/month.

**Total estimated monthly LLM cost: ~$2-3**

### API Setup

```
pip install anthropic
```

Environment variable: `ANTHROPIC_API_KEY`

---

## 2. SNS Platform

### Options

| Platform | API Cost | Read Access | Write Access | Bot Policy |
|----------|----------|-------------|--------------|------------|
| Bluesky (AT Protocol) | Free | Full, no auth needed | Free, account-based auth | Bots welcome, opt-in interaction required |
| X (Twitter) Free tier | $0 | None (write-only) | 500 posts/month | Usable for posting only |
| X (Twitter) Basic tier | $200/month | Limited | 3,000 posts/month | Full bot capability |
| Mastodon | Free | Full | Free | Instance-dependent |

### Decision: Bluesky first, X later

**Rationale:**

This AI needs to READ the timeline (observation phase) AND write posts.

- X free tier is write-only. Can't observe. Useless for this design.
- X basic tier costs $200/month. Absurd for a Phase 0 experiment.
- Bluesky is fully free for both read and write.
- Bluesky's developer culture is more receptive to experimental AI bots.
- Bluesky's AT Protocol is open and well-documented.
- Python SDK exists: `atproto` package.

X can be added later (Phase 3+) if reach becomes important.
But the growth narrative works better on a smaller platform where
early followers actually see the posts.

```
pip install atproto
```

### Bluesky Bot Rules (must follow)

- Automated posting on a schedule: allowed
- Replying to mentions: allowed (opt-in only)
- Unsolicited interaction with users: not allowed
- Must not spam or mass-follow

These rules align perfectly with the design:
the AI observes, posts its own diary, and replies only when addressed.

---

## 3. Memory Storage

### Options

| Storage | Complexity | Query Capability | Fits Project Philosophy |
|---------|-----------|------------------|------------------------|
| Local JSON files | Minimal | Glob + load | Yes (current project pattern) |
| SQLite | Low | Full SQL | Yes (stdlib, single file) |
| Vector DB (ChromaDB etc.) | Medium | Semantic search | Overkill for Phase 0 |
| Markdown files | Minimal | Grep | Yes, human-readable |

### Decision: SQLite for structured data, Markdown for diary

**Rationale:**

Two different storage needs:

**Structured data → SQLite**
- Vocabulary notebook, curiosity list, trial log, naming dictionary
- Needs filtering (by date, by status, by frequency)
- Needs counting (for phase transition detection)
- SQLite is Python stdlib (`sqlite3`), zero dependencies
- Single file: `data/memory.db`

**Diary → Markdown files**
- One file per day: `data/diary/2026-03-16.md`
- Human-readable (important: the diary IS content)
- Easy to publish or review
- Consistent with current project's file-based approach

**Phase transition detection → SQL query**
```sql
-- Check if Phase 0 → 1 transition should happen
SELECT
  (SELECT COUNT(*) FROM vocabulary) AS vocab_count,
  (SELECT COUNT(*) FROM curiosity) AS curiosity_count;
-- If vocab_count > 50 AND curiosity_count > 20 → Phase 1
```

**Vector DB: deferred**
Not needed until the memory grows large enough that keyword search
isn't sufficient. Estimated threshold: Phase 3+ (thousands of entries).
Can add ChromaDB or similar at that point without changing the schema.

### Schema (initial)

```sql
CREATE TABLE vocabulary (
    id INTEGER PRIMARY KEY,
    expression TEXT NOT NULL,
    context TEXT,
    structure_note TEXT,
    date_found TEXT NOT NULL,
    source TEXT
);

CREATE TABLE curiosity (
    id INTEGER PRIMARY KEY,
    phenomenon TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    times_seen INTEGER DEFAULT 1,
    status TEXT DEFAULT 'unnamed',  -- unnamed / attempted / named
    notes TEXT
);

CREATE TABLE trial_log (
    id INTEGER PRIMARY KEY,
    attempted_expression TEXT NOT NULL,
    date TEXT NOT NULL,
    context TEXT,
    response_quality TEXT,  -- qualitative note, not a score
    adopted_by_others INTEGER DEFAULT 0
);

CREATE TABLE naming_dictionary (
    id INTEGER PRIMARY KEY,
    term TEXT NOT NULL,
    definition TEXT,
    date_coined TEXT NOT NULL,
    origin_curiosity_id INTEGER REFERENCES curiosity(id),
    times_used INTEGER DEFAULT 0,
    adopted INTEGER DEFAULT 0  -- boolean: used by others
);

CREATE TABLE perspective_patterns (
    id INTEGER PRIMARY KEY,
    pattern_name TEXT,
    description TEXT NOT NULL,
    source TEXT,
    date_learned TEXT NOT NULL,
    times_used INTEGER DEFAULT 0
);
```

---

## 4. Autonomous Loop Execution

### Options

| Method | Complexity | Reliability | MacBook Constraint |
|--------|-----------|-------------|-------------------|
| cron | Minimal | High (OS-level) | Must be awake |
| launchd (macOS native) | Low | Higher than cron on macOS | Must be awake, runs on wake |
| Python APScheduler | Medium | Process must stay running | Needs terminal open |
| Serverless (AWS Lambda etc.) | High | Always-on | Breaks local-only constraint |

### Decision: launchd for the schedule, Python script for the loop

**Rationale:**

- `launchd` is macOS-native and superior to cron on macOS
- Runs missed jobs when machine wakes from sleep (cron doesn't)
- No external dependencies
- Single Python script invoked on schedule
- If MacBook is closed all day, jobs accumulate and run on open

### Architecture

```
launchd (every 6 hours)
  └── python -m persona run
        ├── 1. Read timeline (Bluesky API)
        ├── 2. Update memory (SQLite)
        ├── 3. Generate post (Claude Haiku API)
        ├── 4. Post to Bluesky (AT Protocol)
        ├── 5. Check for mentions → reply if any (Claude Sonnet API)
        ├── 6. Write diary entry (Markdown)
        └── 7. Check phase transition (SQL query, log only)
```

### Schedule

```
Phase 0: 2-3 times per day (every 8 hours)
  → Low activity matches "blank slate" personality
  → ~2 posts/day + diary

Phase 1+: 3-4 times per day (every 6 hours)
  → Increased activity as vocabulary grows
  → ~3-4 posts/day + diary + replies

Adjustable via launchd plist, no code change needed.
```

---

## Dependency Summary

### Production dependencies

```
anthropic     # Claude API client
atproto       # Bluesky AT Protocol SDK
```

### Standard library (no install needed)

```
sqlite3       # Memory storage
pathlib       # File operations
datetime      # Timestamps
json          # Data serialization
```

### Dev dependencies (existing)

```
pytest        # Testing
pytest-cov    # Coverage
ruff          # Linting
```

### Total new dependencies: 2

This breaks the "zero external dependencies" rule of the benchmark framework.
However, the persona system is a separate module from the benchmark framework.
Recommendation: keep them in separate dependency groups in pyproject.toml.

```toml
[project.optional-dependencies]
persona = [
    "anthropic>=0.40.0",
    "atproto>=0.0.55",
]
```

---

## Cost Summary

| Item | Monthly Cost |
|------|-------------|
| Claude Haiku (loop) | ~$0.60 |
| Claude Sonnet (replies) | ~$1.50 |
| Bluesky API | $0 |
| SQLite | $0 |
| launchd | $0 |
| **Total** | **~$2-3/month** |

---

## Implementation Order

```
Step 1: SQLite schema + memory module
        (read/write vocabulary, curiosity, diary)

Step 2: Bluesky client module
        (authenticate, read timeline, post, read mentions)

Step 3: LLM client module
        (observation prompt, post generation, diary generation)

Step 4: Autonomous loop script
        (wire Steps 1-3 together)

Step 5: launchd plist
        (schedule the loop)

Step 6: Phase transition detector
        (SQL queries, logging only, no action)
```

Each step is independently testable.
Step 1 needs zero API keys — can develop and test fully offline.
