"""Tests for posting policy configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.persona.policy import PostingPolicy


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_default_values(self) -> None:
        p = PostingPolicy()
        assert p.max_daily == 4
        assert p.cooldown_minutes == 180
        assert p.quiet_start_hour == 23
        assert p.quiet_end_hour == 7
        assert p.platform == "x"
        assert p.llm == "claude"

    def test_frozen(self) -> None:
        p = PostingPolicy()
        with pytest.raises(AttributeError):
            p.max_daily = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# JSON loading
# ---------------------------------------------------------------------------


class TestFromJson:
    def test_loads_from_file(self, tmp_path: Path) -> None:
        f = tmp_path / "policy.json"
        f.write_text('{"max_daily": 2, "cooldown_minutes": 60}')

        p = PostingPolicy.from_json(f)
        assert p.max_daily == 2
        assert p.cooldown_minutes == 60

    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        p = PostingPolicy.from_json(tmp_path / "nonexistent.json")
        assert p.max_daily == 4
        assert p.platform == "x"

    def test_partial_json_fills_defaults(self, tmp_path: Path) -> None:
        f = tmp_path / "policy.json"
        f.write_text('{"max_daily": 10}')

        p = PostingPolicy.from_json(f)
        assert p.max_daily == 10
        assert p.cooldown_minutes == 180  # default
        assert p.platform == "x"          # default

    def test_all_fields(self, tmp_path: Path) -> None:
        f = tmp_path / "policy.json"
        f.write_text(
            '{"max_daily": 3, "cooldown_minutes": 120, '
            '"quiet_start_hour": 22, "quiet_end_hour": 8, '
            '"platform": "bluesky", "llm": "stub"}'
        )

        p = PostingPolicy.from_json(f)
        assert p.max_daily == 3
        assert p.quiet_start_hour == 22
        assert p.quiet_end_hour == 8
        assert p.platform == "bluesky"
        assert p.llm == "stub"


# ---------------------------------------------------------------------------
# Quiet hours
# ---------------------------------------------------------------------------


class TestQuietHours:
    def test_midnight_wrap_quiet_at_23(self) -> None:
        p = PostingPolicy(quiet_start_hour=23, quiet_end_hour=7)
        at_23 = datetime(2026, 3, 17, 23, 30, tzinfo=timezone.utc)
        assert p.is_quiet_hours(at_23) is True

    def test_midnight_wrap_quiet_at_3(self) -> None:
        p = PostingPolicy(quiet_start_hour=23, quiet_end_hour=7)
        at_3 = datetime(2026, 3, 17, 3, 0, tzinfo=timezone.utc)
        assert p.is_quiet_hours(at_3) is True

    def test_midnight_wrap_active_at_12(self) -> None:
        p = PostingPolicy(quiet_start_hour=23, quiet_end_hour=7)
        at_12 = datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc)
        assert p.is_quiet_hours(at_12) is False

    def test_midnight_wrap_active_at_7(self) -> None:
        p = PostingPolicy(quiet_start_hour=23, quiet_end_hour=7)
        at_7 = datetime(2026, 3, 17, 7, 0, tzinfo=timezone.utc)
        assert p.is_quiet_hours(at_7) is False

    def test_same_day_quiet(self) -> None:
        p = PostingPolicy(quiet_start_hour=1, quiet_end_hour=5)
        at_3 = datetime(2026, 3, 17, 3, 0, tzinfo=timezone.utc)
        assert p.is_quiet_hours(at_3) is True

    def test_same_day_active(self) -> None:
        p = PostingPolicy(quiet_start_hour=1, quiet_end_hour=5)
        at_12 = datetime(2026, 3, 17, 12, 0, tzinfo=timezone.utc)
        assert p.is_quiet_hours(at_12) is False

    def test_no_quiet_hours_when_equal(self) -> None:
        p = PostingPolicy(quiet_start_hour=0, quiet_end_hour=0)
        at_any = datetime(2026, 3, 17, 15, 0, tzinfo=timezone.utc)
        assert p.is_quiet_hours(at_any) is False

    def test_boundary_start_is_quiet(self) -> None:
        p = PostingPolicy(quiet_start_hour=23, quiet_end_hour=7)
        at_23_exact = datetime(2026, 3, 17, 23, 0, tzinfo=timezone.utc)
        assert p.is_quiet_hours(at_23_exact) is True

    def test_boundary_end_is_active(self) -> None:
        p = PostingPolicy(quiet_start_hour=23, quiet_end_hour=7)
        at_7_exact = datetime(2026, 3, 17, 7, 0, tzinfo=timezone.utc)
        assert p.is_quiet_hours(at_7_exact) is False
