"""Tests for run-level safety (RunGuard, call budget)."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from src.persona.safety import (
    EXIT_LOCK_HELD,
    BudgetExceeded,
    RunGuard,
    with_call_budget,
)


def _write_lock(state_dir, minutes_ago: int) -> None:
    started = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    (state_dir / "run.lock").write_text(
        json.dumps({"pid": 999, "started_at": started.isoformat()}),
        encoding="utf-8",
    )


class TestCallBudget:
    def test_allows_calls_within_budget(self):
        calls = []
        llm = with_call_budget(lambda s, u: calls.append(u) or "ok", max_calls=2)
        assert llm("sys", "one") == "ok"
        assert llm("sys", "two") == "ok"
        assert calls == ["one", "two"]

    def test_blocks_calls_over_budget(self):
        llm = with_call_budget(lambda s, u: "ok", max_calls=2)
        llm("sys", "one")
        llm("sys", "two")
        with pytest.raises(BudgetExceeded):
            llm("sys", "three")


class TestRunGuard:
    def test_acquires_and_releases_lock(self, tmp_path):
        with RunGuard(tmp_path) as guard:
            assert (tmp_path / "run.lock").exists()
            guard.finish(0, posts_today=1)
        assert not (tmp_path / "run.lock").exists()
        hb = json.loads((tmp_path / "heartbeat.json").read_text())
        assert hb["exit_code"] == 0
        assert hb["posts_today"] == 1

    def test_fresh_lock_blocks_second_run(self, tmp_path):
        _write_lock(tmp_path, minutes_ago=5)
        with pytest.raises(SystemExit) as e:
            RunGuard(tmp_path).__enter__()
        assert e.value.code == EXIT_LOCK_HELD

    def test_stale_lock_is_broken(self, tmp_path):
        _write_lock(tmp_path, minutes_ago=45)
        with RunGuard(tmp_path) as guard:
            assert (tmp_path / "run.lock").exists()
            guard.finish(0)
        assert not (tmp_path / "run.lock").exists()

    def test_crash_still_writes_heartbeat(self, tmp_path):
        with pytest.raises(ValueError):
            with RunGuard(tmp_path):
                raise ValueError("boom")
        hb = json.loads((tmp_path / "heartbeat.json").read_text())
        assert hb["exit_code"] == 1
        assert not (tmp_path / "run.lock").exists()

    def test_system_exit_heartbeat_recorded_by_caller(self, tmp_path):
        # Mirrors the cli.py wiring: caller records the exit code.
        with pytest.raises(SystemExit):
            with RunGuard(tmp_path) as guard:
                try:
                    raise SystemExit(2)
                except SystemExit as e:
                    guard.finish(int(e.code or 0))
                    raise
        hb = json.loads((tmp_path / "heartbeat.json").read_text())
        assert hb["exit_code"] == 2
