"""Tests for session logger."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.logger.session_logger import list_sessions, load_session, save_session
from src.models import Session


@pytest.mark.unit
class TestSaveLoad:
    def test_save_creates_file(
        self, sample_session: Session, tmp_sessions_dir: Path
    ) -> None:
        path = save_session(sample_session, base_dir=tmp_sessions_dir)
        assert path.exists()
        assert path.suffix == ".json"

    def test_save_load_roundtrip(
        self, sample_session: Session, tmp_sessions_dir: Path
    ) -> None:
        path = save_session(sample_session, base_dir=tmp_sessions_dir)
        loaded = load_session(path)
        assert loaded == sample_session

    def test_filename_contains_workflow_and_task(
        self, sample_session: Session, tmp_sessions_dir: Path
    ) -> None:
        path = save_session(sample_session, base_dir=tmp_sessions_dir)
        assert "ecc" in path.name
        assert "scaffold_v1" in path.name


@pytest.mark.unit
class TestListSessions:
    def test_list_empty_dir(self, tmp_sessions_dir: Path) -> None:
        sessions = list_sessions(base_dir=tmp_sessions_dir)
        assert sessions == []

    def test_list_nonexistent_dir(self, tmp_path: Path) -> None:
        sessions = list_sessions(base_dir=tmp_path / "nope")
        assert sessions == []

    def test_list_returns_saved(
        self, sample_session: Session, tmp_sessions_dir: Path
    ) -> None:
        save_session(sample_session, base_dir=tmp_sessions_dir)
        sessions = list_sessions(base_dir=tmp_sessions_dir)
        assert len(sessions) == 1
        assert sessions[0] == sample_session

    def test_filter_by_workflow(
        self, sample_session: Session, tmp_sessions_dir: Path
    ) -> None:
        save_session(sample_session, base_dir=tmp_sessions_dir)
        assert len(list_sessions(base_dir=tmp_sessions_dir, workflow="ecc")) == 1
        assert len(list_sessions(base_dir=tmp_sessions_dir, workflow="old")) == 0

    def test_filter_by_task(
        self, sample_session: Session, tmp_sessions_dir: Path
    ) -> None:
        save_session(sample_session, base_dir=tmp_sessions_dir)
        assert len(list_sessions(base_dir=tmp_sessions_dir, task_id="scaffold_v1")) == 1
        assert len(list_sessions(base_dir=tmp_sessions_dir, task_id="other")) == 0
