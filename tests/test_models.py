"""Tests for data models."""

from __future__ import annotations

import json

import pytest

from src.models import ErrorRecord, Session, new_session_id, now_iso


@pytest.mark.unit
class TestErrorRecord:
    def test_frozen(self, sample_error: ErrorRecord) -> None:
        with pytest.raises(AttributeError):
            sample_error.description = "changed"  # type: ignore[misc]

    def test_fields(self, sample_error: ErrorRecord) -> None:
        assert sample_error.recovered is True
        assert sample_error.recovery_method == "auto-fix"


@pytest.mark.unit
class TestSession:
    def test_frozen(self, sample_session: Session) -> None:
        with pytest.raises(AttributeError):
            sample_session.outcome = "failure"  # type: ignore[misc]

    def test_to_dict_roundtrip(self, sample_session: Session) -> None:
        data = sample_session.to_dict()
        restored = Session.from_dict(data)
        assert restored == sample_session

    def test_to_json_roundtrip(self, sample_session: Session) -> None:
        json_str = sample_session.to_json()
        restored = Session.from_json(json_str)
        assert restored == sample_session

    def test_json_is_valid(self, sample_session: Session) -> None:
        parsed = json.loads(sample_session.to_json())
        assert parsed["workflow"] == "ecc"
        assert parsed["outcome"] == "success"
        assert len(parsed["errors"]) == 1

    def test_from_dict_defaults(self) -> None:
        minimal = {
            "session_id": "x",
            "workflow": "old",
            "task_id": "t1",
            "machine": "macbook",
            "started_at": "2026-01-01T00:00:00+00:00",
            "ended_at": "2026-01-01T00:05:00+00:00",
            "duration_seconds": 300.0,
            "outcome": "failure",
        }
        s = Session.from_dict(minimal)
        assert s.error_count == 0
        assert s.errors == ()
        assert s.notes == ""


@pytest.mark.unit
class TestHelpers:
    def test_new_session_id_unique(self) -> None:
        ids = {new_session_id() for _ in range(100)}
        assert len(ids) == 100

    def test_new_session_id_length(self) -> None:
        assert len(new_session_id()) == 12

    def test_now_iso_format(self) -> None:
        from datetime import datetime

        ts = now_iso()
        dt = datetime.fromisoformat(ts)
        assert dt.tzinfo is not None
