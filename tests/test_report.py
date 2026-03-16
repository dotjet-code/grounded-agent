"""Tests for report generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.models import Session
from src.report.generator import generate_report, save_report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_session(**overrides: object) -> Session:
    """Create a Session with sensible defaults, overridable per field."""
    defaults = dict(
        session_id="aaa111bbb222",
        workflow="ecc",
        task_id="scaffold_v1",
        machine="mac_mini",
        started_at="2026-03-16T10:00:00+00:00",
        ended_at="2026-03-16T10:15:30+00:00",
        duration_seconds=930.0,
        outcome="success",
        error_count=1,
        human_interventions=2,
        files_created=8,
        tests_passed=5,
        tests_failed=0,
        notes="",
    )
    defaults.update(overrides)
    return Session(**defaults)


def _write_session(directory: Path, session: Session) -> Path:
    """Write a session JSON file and return the path."""
    filename = f"{session.workflow}_{session.task_id}_{session.session_id}.json"
    path = directory / filename
    path.write_text(session.to_json(), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateReportEmpty:
    """Empty directory should produce a valid report with no rows."""

    def test_returns_string(self, tmp_path: Path) -> None:
        result = generate_report(str(tmp_path))
        assert isinstance(result, str)

    def test_contains_title(self, tmp_path: Path) -> None:
        result = generate_report(str(tmp_path))
        assert "# Benchmark Report" in result

    def test_contains_zero_sessions_total(self, tmp_path: Path) -> None:
        result = generate_report(str(tmp_path))
        assert "0" in result  # total sessions = 0


class TestGenerateReportOneSession:
    """Single session file should appear in the table."""

    @pytest.fixture()
    def report(self, tmp_path: Path) -> str:
        session = _make_session()
        _write_session(tmp_path, session)
        return generate_report(str(tmp_path))

    def test_contains_table_headers(self, report: str) -> None:
        for header in (
            "workflow",
            "task_id",
            "duration_seconds",
            "outcome",
            "error_count",
            "human_interventions",
            "tests_passed",
            "tests_failed",
        ):
            assert header in report

    def test_contains_session_data(self, report: str) -> None:
        assert "ecc" in report
        assert "scaffold_v1" in report
        assert "930.0" in report
        assert "success" in report

    def test_totals_one_session(self, report: str) -> None:
        assert "Total sessions: 1" in report

    def test_average_duration(self, report: str) -> None:
        assert "930.0" in report


class TestGenerateReportMultiple:
    """Multiple session files should all appear with correct totals."""

    @pytest.fixture()
    def report(self, tmp_path: Path) -> str:
        s1 = _make_session(
            session_id="aaa111bbb222",
            duration_seconds=100.0,
            error_count=2,
            human_interventions=1,
        )
        s2 = _make_session(
            session_id="ccc333ddd444",
            duration_seconds=200.0,
            error_count=3,
            human_interventions=4,
            outcome="partial",
        )
        _write_session(tmp_path, s1)
        _write_session(tmp_path, s2)
        return generate_report(str(tmp_path))

    def test_total_sessions(self, report: str) -> None:
        assert "Total sessions: 2" in report

    def test_average_duration(self, report: str) -> None:
        # (100 + 200) / 2 = 150.0
        assert "150.0" in report

    def test_total_errors(self, report: str) -> None:
        # 2 + 3 = 5
        assert "Total errors: 5" in report

    def test_total_human_interventions(self, report: str) -> None:
        # 1 + 4 = 5
        assert "Total human interventions: 5" in report


class TestGenerateReportIgnoresNonJson:
    """Non-JSON files in the directory should be silently skipped."""

    def test_ignores_txt_file(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("not json")
        session = _make_session()
        _write_session(tmp_path, session)
        result = generate_report(str(tmp_path))
        assert "Total sessions: 1" in result


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------


class TestSaveReport:
    """save_report should write a timestamped Markdown file with metadata."""

    @pytest.fixture()
    def saved(self, tmp_path: Path) -> Path:
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        reports_dir = tmp_path / "reports"
        _write_session(sessions_dir, _make_session())
        return save_report(str(sessions_dir), str(reports_dir))

    def test_file_exists(self, saved: Path) -> None:
        assert saved.exists()

    def test_filename_format(self, saved: Path) -> None:
        assert saved.name.startswith("report_")
        assert saved.suffix == ".md"

    def test_contains_metadata_header(self, saved: Path) -> None:
        content = saved.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert "generated_at:" in content
        assert "sessions_count: 1" in content

    def test_contains_session_ids(self, saved: Path) -> None:
        content = saved.read_text(encoding="utf-8")
        assert "session_ids:" in content
        assert "aaa111bbb222" in content

    def test_contains_task_ids(self, saved: Path) -> None:
        content = saved.read_text(encoding="utf-8")
        assert "task_ids:" in content
        assert "scaffold_v1" in content

    def test_contains_workflows(self, saved: Path) -> None:
        content = saved.read_text(encoding="utf-8")
        assert "workflows:" in content
        assert "ecc" in content

    def test_contains_report_body(self, saved: Path) -> None:
        content = saved.read_text(encoding="utf-8")
        assert "# Benchmark Report" in content
        assert "Total sessions: 1" in content

    def test_creates_reports_dir(self, tmp_path: Path) -> None:
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        reports_dir = tmp_path / "new_reports"
        _write_session(sessions_dir, _make_session())
        path = save_report(str(sessions_dir), str(reports_dir))
        assert path.exists()
        assert reports_dir.exists()

    def test_empty_sessions(self, tmp_path: Path) -> None:
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        reports_dir = tmp_path / "reports"
        path = save_report(str(sessions_dir), str(reports_dir))
        content = path.read_text(encoding="utf-8")
        assert "sessions_count: 0" in content
        assert "# Benchmark Report" in content
