"""Outbox and safety guard for the persona posting pipeline.

The Outbox records every post candidate before it is sent.
The SafetyGuard validates candidates against guardrails.

Status lifecycle: ready → posted / failed / blocked
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_OUTBOX_SCHEMA = """\
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ready',
    posted_uri TEXT,
    block_reason TEXT,
    error TEXT
);
"""

# Default safety limits
DEFAULT_MAX_DAILY = 6
DEFAULT_COOLDOWN_MINUTES = 120
BLUESKY_MAX_LENGTH = 300

# Words that must never appear in posts
DEFAULT_FORBIDDEN_WORDS: tuple[str, ...] = (
    "死ね",
    "殺す",
    "自殺",
    "テロ",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class Outbox:
    """Persistent log of all post candidates and their outcomes."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_OUTBOX_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def save(self, text: str, status: str = "ready", block_reason: str = "") -> int:
        """Save a post candidate. Returns the row id."""
        cur = self._conn.execute(
            "INSERT INTO outbox (text, created_at, status, block_reason) "
            "VALUES (?, ?, ?, ?)",
            (text, _now_iso(), status, block_reason),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def mark_posted(self, outbox_id: int, uri: str) -> None:
        """Mark a candidate as successfully posted."""
        self._conn.execute(
            "UPDATE outbox SET status = 'posted', posted_uri = ? WHERE id = ?",
            (uri, outbox_id),
        )
        self._conn.commit()

    def mark_failed(self, outbox_id: int, error: str) -> None:
        """Mark a candidate as failed to post."""
        self._conn.execute(
            "UPDATE outbox SET status = 'failed', error = ? WHERE id = ?",
            (error, outbox_id),
        )
        self._conn.commit()

    def today_posted_count(self) -> int:
        """Count posts with status 'posted' created today (UTC)."""
        prefix = _today_prefix()
        row = self._conn.execute(
            "SELECT COUNT(*) FROM outbox "
            "WHERE status = 'posted' AND created_at LIKE ?",
            (f"{prefix}%",),
        ).fetchone()
        return row[0]

    def last_posted_at(self) -> str | None:
        """Return ISO timestamp of the most recent posted entry, or None."""
        row = self._conn.execute(
            "SELECT created_at FROM outbox WHERE status = 'posted' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    def recent_posted_texts(self, hours: int = 24) -> list[str]:
        """Return texts of posts made in the last N hours."""
        rows = self._conn.execute(
            "SELECT text FROM outbox WHERE status = 'posted' "
            "ORDER BY id DESC LIMIT 100"
        ).fetchall()
        # Simple approach: return all recent posts, filter by time in Python
        # since SQLite datetime comparisons with ISO strings work lexicographically
        cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # For simplicity, just return the last 100 posted texts
        # The caller (SafetyGuard) does the similarity check
        return [r[0] for r in rows]

    def get(self, outbox_id: int) -> dict | None:
        """Get a single outbox entry by id."""
        row = self._conn.execute(
            "SELECT * FROM outbox WHERE id = ?", (outbox_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_recent(self, limit: int = 20) -> list[dict]:
        """Return recent outbox entries, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM outbox ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


class SafetyGuard:
    """Validates post candidates against guardrails.

    Returns (passed: bool, reason: str) for each check.
    """

    def __init__(
        self,
        outbox: Outbox,
        stop_file: str | Path = "data/STOP",
        max_daily: int = DEFAULT_MAX_DAILY,
        cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES,
        forbidden_words: tuple[str, ...] = DEFAULT_FORBIDDEN_WORDS,
        max_length: int = BLUESKY_MAX_LENGTH,
    ) -> None:
        self._outbox = outbox
        self._stop_file = Path(stop_file)
        self._max_daily = max_daily
        self._cooldown_minutes = cooldown_minutes
        self._forbidden_words = forbidden_words
        self._max_length = max_length

    def pre_check(self) -> tuple[bool, str]:
        """Run pre-compose checks (no candidate text needed).

        Checks: emergency stop, daily cap, cooldown.
        Call this before LLM compose to avoid wasting API calls.
        """
        passed, reason = self._check_emergency_stop("")
        if not passed:
            return False, reason
        passed, reason = self._check_daily_cap("")
        if not passed:
            return False, reason
        passed, reason = self._check_cooldown("")
        if not passed:
            return False, reason
        return True, "pre-checks passed"

    def check(self, candidate: str) -> tuple[bool, str]:
        """Run all safety checks. Returns (passed, reason).

        If passed is False, reason explains which check failed.
        """
        checks = [
            self._check_emergency_stop,
            lambda c: self._check_length(c),
            lambda c: self._check_forbidden(c),
            lambda c: self._check_daily_cap(c),
            lambda c: self._check_cooldown(c),
            lambda c: self._check_duplicate(c),
        ]
        for check_fn in checks:
            passed, reason = check_fn(candidate)
            if not passed:
                return False, reason
        return True, "all checks passed"

    def _check_emergency_stop(self, _candidate: str) -> tuple[bool, str]:
        """Check if emergency stop file exists."""
        if self._stop_file.exists():
            return False, f"emergency stop: {self._stop_file} exists"
        return True, ""

    def _check_length(self, candidate: str) -> tuple[bool, str]:
        """Check platform character limit."""
        if len(candidate) > self._max_length:
            return False, f"too long: {len(candidate)} > {self._max_length}"
        return True, ""

    def _check_forbidden(self, candidate: str) -> tuple[bool, str]:
        """Check for forbidden words."""
        for word in self._forbidden_words:
            if word in candidate:
                return False, f"forbidden word: {word!r}"
        return True, ""

    def _check_daily_cap(self, _candidate: str) -> tuple[bool, str]:
        """Check if daily post limit is reached."""
        count = self._outbox.today_posted_count()
        if count >= self._max_daily:
            return False, f"daily cap reached: {count} >= {self._max_daily}"
        return True, ""

    def _check_cooldown(self, _candidate: str) -> tuple[bool, str]:
        """Check if enough time has passed since last post."""
        last = self._outbox.last_posted_at()
        if last is None:
            return True, ""
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        except ValueError:
            return True, ""
        now = datetime.now(timezone.utc)
        elapsed = (now - last_dt).total_seconds() / 60
        if elapsed < self._cooldown_minutes:
            remaining = int(self._cooldown_minutes - elapsed)
            return False, f"cooldown: {remaining} minutes remaining"
        return True, ""

    def _check_duplicate(self, candidate: str) -> tuple[bool, str]:
        """Check if candidate is too similar to recent posts."""
        recent = self._outbox.recent_posted_texts(hours=24)
        for prev in recent:
            if candidate.strip() == prev.strip():
                return False, "duplicate: exact match with recent post"
            # Simple similarity: if 80%+ characters overlap
            if len(candidate) > 10 and len(prev) > 10:
                shorter = min(len(candidate), len(prev))
                common = sum(a == b for a, b in zip(candidate, prev))
                if common / shorter > 0.8:
                    return False, "duplicate: too similar to recent post"
        return True, ""
