"""Data models for benchmark sessions."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ErrorRecord:
    """A single error observed during a session."""

    timestamp: str  # ISO 8601
    description: str
    recovered: bool = False
    recovery_method: str | None = None


@dataclass(frozen=True)
class Session:
    """One run of one workflow on one task."""

    session_id: str
    workflow: str  # "ecc" | "old"
    task_id: str
    machine: str  # "mac_mini" | "macbook"
    started_at: str  # ISO 8601
    ended_at: str  # ISO 8601
    duration_seconds: float
    outcome: str  # "success" | "partial" | "failure"
    error_count: int = 0
    errors: tuple[ErrorRecord, ...] = ()
    human_interventions: int = 0
    files_created: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-safe)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Deserialize from a dict."""
        errors = tuple(
            ErrorRecord(**e) for e in data.get("errors", ())
        )
        return cls(
            session_id=data["session_id"],
            workflow=data["workflow"],
            task_id=data["task_id"],
            machine=data["machine"],
            started_at=data["started_at"],
            ended_at=data["ended_at"],
            duration_seconds=data["duration_seconds"],
            outcome=data["outcome"],
            error_count=data.get("error_count", 0),
            errors=errors,
            human_interventions=data.get("human_interventions", 0),
            files_created=data.get("files_created", 0),
            tests_passed=data.get("tests_passed", 0),
            tests_failed=data.get("tests_failed", 0),
            notes=data.get("notes", ""),
        )

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> Session:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


def new_session_id() -> str:
    """Generate a new unique session ID."""
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    """Current time as ISO 8601 string in UTC."""
    return datetime.now(timezone.utc).isoformat()
