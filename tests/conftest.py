"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.models import ErrorRecord, Session


@pytest.fixture
def sample_error() -> ErrorRecord:
    return ErrorRecord(
        timestamp="2026-03-16T10:00:00+00:00",
        description="Build failed: missing import",
        recovered=True,
        recovery_method="auto-fix",
    )


@pytest.fixture
def sample_session(sample_error: ErrorRecord) -> Session:
    return Session(
        session_id="abc123def456",
        workflow="ecc",
        task_id="scaffold_v1",
        machine="mac_mini",
        started_at="2026-03-16T10:00:00+00:00",
        ended_at="2026-03-16T10:15:30+00:00",
        duration_seconds=930.0,
        outcome="success",
        error_count=1,
        errors=(sample_error,),
        human_interventions=0,
        files_created=8,
        tests_passed=5,
        tests_failed=0,
        notes="Clean run",
    )


@pytest.fixture
def tmp_sessions_dir(tmp_path: Path) -> Path:
    d = tmp_path / "sessions"
    d.mkdir()
    return d
