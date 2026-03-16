"""SQLite-backed memory for the persona system.

Phase 0 stores: vocabulary notebook, curiosity list, diary (markdown files).
Additional stores (trial_log, naming_dictionary, perspective_patterns)
will be added when Phase 2+ features are implemented.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expression TEXT NOT NULL,
    context TEXT,
    structure_note TEXT,
    date_found TEXT NOT NULL,
    source TEXT
);

CREATE TABLE IF NOT EXISTS curiosity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phenomenon TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    times_seen INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'unnamed',
    notes TEXT
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Memory:
    """Persona memory backed by SQLite + markdown diary files."""

    def __init__(self, db_path: str | Path, diary_dir: str | Path) -> None:
        self._db_path = Path(db_path)
        self._diary_dir = Path(diary_dir)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._diary_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Vocabulary notebook
    # ------------------------------------------------------------------

    def add_vocabulary(
        self,
        expression: str,
        context: str = "",
        structure_note: str = "",
        source: str = "",
    ) -> int:
        """Add an expression to the vocabulary notebook. Returns row id."""
        cur = self._conn.execute(
            "INSERT INTO vocabulary (expression, context, structure_note, date_found, source) "
            "VALUES (?, ?, ?, ?, ?)",
            (expression, context, structure_note, _now_iso(), source),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def list_vocabulary(self, limit: int = 50) -> list[dict]:
        """Return recent vocabulary entries, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM vocabulary ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def vocabulary_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM vocabulary").fetchone()
        return row[0]

    # ------------------------------------------------------------------
    # Curiosity list
    # ------------------------------------------------------------------

    def add_curiosity(self, phenomenon: str, notes: str = "") -> int:
        """Add a curious phenomenon. Returns row id."""
        cur = self._conn.execute(
            "INSERT INTO curiosity (phenomenon, first_seen, notes) VALUES (?, ?, ?)",
            (phenomenon, _now_iso(), notes),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def bump_curiosity(self, curiosity_id: int) -> None:
        """Increment times_seen for a curiosity item."""
        self._conn.execute(
            "UPDATE curiosity SET times_seen = times_seen + 1 WHERE id = ?",
            (curiosity_id,),
        )
        self._conn.commit()

    def list_curiosity(self, status: str | None = None, limit: int = 50) -> list[dict]:
        """Return curiosity items, optionally filtered by status."""
        if status:
            rows = self._conn.execute(
                "SELECT * FROM curiosity WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM curiosity ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def update_curiosity_status(self, curiosity_id: int, status: str) -> None:
        """Update status of a curiosity item (unnamed/attempted/named)."""
        self._conn.execute(
            "UPDATE curiosity SET status = ? WHERE id = ?",
            (status, curiosity_id),
        )
        self._conn.commit()

    def curiosity_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM curiosity").fetchone()
        return row[0]

    # ------------------------------------------------------------------
    # Diary (markdown files)
    # ------------------------------------------------------------------

    def write_diary(self, date: str, content: str) -> Path:
        """Write a diary entry for a given date (YYYY-MM-DD). Returns file path."""
        path = self._diary_dir / f"{date}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def read_diary(self, date: str) -> str | None:
        """Read a diary entry for a given date. Returns None if not found."""
        path = self._diary_dir / f"{date}.md"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def list_diary_dates(self) -> list[str]:
        """Return sorted list of dates that have diary entries."""
        return sorted(p.stem for p in self._diary_dir.glob("*.md"))

    # ------------------------------------------------------------------
    # Phase detection
    # ------------------------------------------------------------------

    def phase_counts(self) -> dict[str, int]:
        """Return counts used for phase transition detection."""
        return {
            "vocabulary": self.vocabulary_count(),
            "curiosity": self.curiosity_count(),
            "diary": len(self.list_diary_dates()),
        }
