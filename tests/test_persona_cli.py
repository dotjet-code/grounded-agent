"""Tests for persona CLI.

All tests are local — no LLM API, no network.
Uses the stub LLM built into cli.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persona.cli import build_parser, cmd_run, cmd_status, main
from src.persona.memory import Memory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def env(tmp_path: Path) -> dict[str, str]:
    """Return CLI args pointing to temp directories."""
    db = str(tmp_path / "test.db")
    diary = str(tmp_path / "diary")
    return {"db": db, "diary_dir": diary}


@pytest.fixture()
def input_file(tmp_path: Path) -> Path:
    """Create a sample input file."""
    f = tmp_path / "observed.txt"
    f.write_text("Today I saw people rushing.\n---\nSomeone smiled at a stranger.", encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class TestParser:
    def test_run_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run"])
        assert args.command == "run"
        assert args.input is None

    def test_run_with_input(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run", "--input", "file.txt"])
        assert args.input == "file.txt"

    def test_run_with_short_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run", "-i", "file.txt"])
        assert args.input == "file.txt"

    def test_default_llm_is_stub(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run"])
        assert args.llm == "stub"

    def test_llm_claude(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run", "--llm", "claude"])
        assert args.llm == "claude"

    def test_status_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["status"])
        assert args.command == "status"

    def test_custom_db_path(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--db", "/tmp/custom.db", "status"])
        assert args.db == "/tmp/custom.db"

    def test_custom_diary_dir(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--diary-dir", "/tmp/diary", "status"])
        assert args.diary_dir == "/tmp/diary"


# ---------------------------------------------------------------------------
# cmd_run
# ---------------------------------------------------------------------------


class TestCmdRun:
    def test_run_with_file_input(self, env: dict, input_file: Path, capsys) -> None:
        main(["--db", env["db"], "--diary-dir", env["diary_dir"], "run", "-i", str(input_file)])

        captured = capsys.readouterr()
        assert "Observed 2 text(s)" in captured.out
        assert "Diary entry written" in captured.out

    def test_run_creates_diary_file(self, env: dict, input_file: Path) -> None:
        main(["--db", env["db"], "--diary-dir", env["diary_dir"], "run", "-i", str(input_file)])

        diary_dir = Path(env["diary_dir"])
        diary_files = list(diary_dir.glob("*.md"))
        assert len(diary_files) == 1

    def test_run_creates_database(self, env: dict, input_file: Path) -> None:
        main(["--db", env["db"], "--diary-dir", env["diary_dir"], "run", "-i", str(input_file)])

        assert Path(env["db"]).exists()

    def test_run_with_missing_file(self, env: dict, capsys) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--db", env["db"], "--diary-dir", env["diary_dir"], "run", "-i", "nonexistent.txt"])
        assert exc_info.value.code == 1

    def test_run_with_empty_file(self, env: dict, tmp_path: Path, capsys) -> None:
        empty = tmp_path / "empty.txt"
        empty.write_text("", encoding="utf-8")

        main(["--db", env["db"], "--diary-dir", env["diary_dir"], "run", "-i", str(empty)])

        captured = capsys.readouterr()
        assert "No input texts" in captured.out

    def test_run_single_text_no_separator(self, env: dict, tmp_path: Path, capsys) -> None:
        f = tmp_path / "single.txt"
        f.write_text("Just one observation.", encoding="utf-8")

        main(["--db", env["db"], "--diary-dir", env["diary_dir"], "run", "-i", str(f)])

        captured = capsys.readouterr()
        assert "Observed 1 text(s)" in captured.out


# ---------------------------------------------------------------------------
# cmd_status
# ---------------------------------------------------------------------------


class TestCmdStatus:
    def test_status_empty(self, env: dict, capsys) -> None:
        main(["--db", env["db"], "--diary-dir", env["diary_dir"], "status"])

        captured = capsys.readouterr()
        assert "Current phase: 0" in captured.out
        assert "Vocabulary: 0" in captured.out

    def test_status_after_run(self, env: dict, input_file: Path, capsys) -> None:
        # Run first to populate memory
        main(["--db", env["db"], "--diary-dir", env["diary_dir"], "run", "-i", str(input_file)])

        # Then check status
        main(["--db", env["db"], "--diary-dir", env["diary_dir"], "status"])

        captured = capsys.readouterr()
        assert "Current phase: 0" in captured.out
        assert "Diary entries: 1" in captured.out


# ---------------------------------------------------------------------------
# No command
# ---------------------------------------------------------------------------


class TestNoCommand:
    def test_no_command_exits(self, capsys) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 1
