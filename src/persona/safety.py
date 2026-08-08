"""Run-level safety for autonomous operation.

Complements SafetyGuard (content/policy checks in outbox.py) with
process-level protections:

- RunGuard: run lock (prevents overlapping/runaway runs) + heartbeat
  (lets an external checker detect silence, hangs, and anomalies).
- with_call_budget: hard cap on LLM calls per run.

State lives under data/state/ (gitignored):
    run.lock        {"pid": int, "started_at": iso8601}
    heartbeat.json  {"finished_at": iso8601, "exit_code": int, "posts_today": int}
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

LlmCall = Callable[[str, str], str]

# A lock older than this is considered stale (crashed/hung run) and may be
# broken by the next run. The heartbeat checker alerts on locks older than
# this too, since a healthy run finishes in well under 30 minutes.
STALE_LOCK_MINUTES = 30

EXIT_LOCK_HELD = 4


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BudgetExceeded(RuntimeError):
    """Raised when a run tries to exceed its LLM call budget."""


def with_call_budget(llm: LlmCall, max_calls: int) -> LlmCall:
    """Wrap an LLM callable with a hard per-run call cap.

    A single autopost run needs 1-2 calls; the cap exists so a future bug
    (retry loop, recursive compose) fails fast instead of burning budget.
    """
    calls = 0

    def call(system: str, user: str) -> str:
        nonlocal calls
        calls += 1
        if calls > max_calls:
            raise BudgetExceeded(
                f"LLM call budget exceeded ({calls} > {max_calls} per run)"
            )
        return llm(system, user)

    return call


class RunGuard:
    """Context manager: acquire run lock on enter, heartbeat + unlock on exit.

    Usage:
        with RunGuard(Path("data/state")) as guard:
            try:
                do_run()
                guard.finish(0, posts_today=n)
            except SystemExit as e:
                guard.finish(int(e.code or 0))
                raise
    """

    def __init__(self, state_dir: str | Path = Path("data/state")) -> None:
        self._dir = Path(state_dir)
        self._lock = self._dir / "run.lock"
        self._heartbeat = self._dir / "heartbeat.json"
        self._finished = False

    # -- lock ---------------------------------------------------------------

    def _lock_age_minutes(self) -> float | None:
        try:
            data = json.loads(self._lock.read_text(encoding="utf-8"))
            started = datetime.fromisoformat(data["started_at"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return None
        return (_now() - started).total_seconds() / 60

    def __enter__(self) -> "RunGuard":
        self._dir.mkdir(parents=True, exist_ok=True)
        if self._lock.exists():
            age = self._lock_age_minutes()
            if age is not None and age < STALE_LOCK_MINUTES:
                print(
                    f"Skipped: another run holds the lock ({age:.0f} min old)",
                    file=sys.stderr,
                )
                sys.exit(EXIT_LOCK_HELD)
            # Stale or unreadable lock: previous run crashed. Break it and
            # continue; the checker has already had a chance to alert.
        self._lock.write_text(
            json.dumps({"pid": os.getpid(), "started_at": _now().isoformat()}),
            encoding="utf-8",
        )
        return self

    # -- heartbeat ----------------------------------------------------------

    def finish(self, exit_code: int, posts_today: int | None = None) -> None:
        """Record the run outcome. Safe to call once per run."""
        payload = {
            "finished_at": _now().isoformat(),
            "exit_code": exit_code,
        }
        if posts_today is not None:
            payload["posts_today"] = posts_today
        self._heartbeat.write_text(json.dumps(payload), encoding="utf-8")
        self._finished = True

    def __exit__(self, exc_type, exc, tb) -> bool:
        # Crash path: make sure the silence is still observable as a fresh
        # heartbeat with a failure code rather than a stale file.
        if not self._finished and exc_type not in (None, SystemExit):
            self.finish(1)
        try:
            self._lock.unlink()
        except OSError:
            pass
        return False
