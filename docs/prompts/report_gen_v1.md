# Prompt: report_gen_v1

> This file contains the frozen prompt text. Copy-paste the section between the
> `---` fences verbatim into Claude Code for both the old and ECC runs.
> Do not modify the prompt between runs.

---

Implement a report generator that reads all session JSON files from `data/sessions/`
and produces a Markdown summary report.

Requirements:

1. Create `src/report/generator.py` with a function `generate_report(sessions_dir: str) -> str`
   that:
   - Reads every `*.json` file in the given directory
   - Parses each file into a `Session` object (use `src/models.py`)
   - Returns a Markdown string containing:
     - A title line: `# Benchmark Report`
     - A summary table with one row per session showing:
       workflow, task_id, duration_seconds, outcome, error_count,
       human_interventions, tests_passed, tests_failed
     - A "Totals" section at the bottom showing:
       total sessions, average duration, total errors, total human interventions

2. Create `src/report/__init__.py` that exports `generate_report`.

3. Add a CLI entry point so that running `python -m src report` calls
   `generate_report("data/sessions")` and prints the result to stdout.

4. Write tests in `tests/test_report.py` that:
   - Test with zero session files (empty directory)
   - Test with one session file
   - Test with multiple session files
   - Verify the Markdown output contains the expected table headers
   - Verify totals are calculated correctly

5. All tests must pass. Target 80%+ coverage for the new code.

---
