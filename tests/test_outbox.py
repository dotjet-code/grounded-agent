"""Tests for outbox and safety guard.

All tests are offline — no network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persona.outbox import (
    BLUESKY_MAX_LENGTH,
    Outbox,
    SafetyGuard,
)


@pytest.fixture()
def outbox(tmp_path: Path) -> Outbox:
    return Outbox(db_path=tmp_path / "outbox.db")


@pytest.fixture()
def guard(tmp_path: Path, outbox: Outbox) -> SafetyGuard:
    return SafetyGuard(
        outbox=outbox,
        stop_file=tmp_path / "STOP",
        max_daily=3,
        cooldown_minutes=60,
    )


# ---------------------------------------------------------------------------
# Outbox CRUD
# ---------------------------------------------------------------------------


class TestOutboxCrud:
    def test_save_returns_id(self, outbox: Outbox) -> None:
        row_id = outbox.save("test post")
        assert isinstance(row_id, int)
        assert row_id >= 1

    def test_save_default_status_is_ready(self, outbox: Outbox) -> None:
        row_id = outbox.save("test")
        entry = outbox.get(row_id)
        assert entry is not None
        assert entry["status"] == "ready"

    def test_save_blocked(self, outbox: Outbox) -> None:
        row_id = outbox.save("bad post", status="blocked", block_reason="forbidden")
        entry = outbox.get(row_id)
        assert entry["status"] == "blocked"
        assert entry["block_reason"] == "forbidden"

    def test_mark_posted(self, outbox: Outbox) -> None:
        row_id = outbox.save("post")
        outbox.mark_posted(row_id, "at://did:plc:abc/post/123")
        entry = outbox.get(row_id)
        assert entry["status"] == "posted"
        assert entry["posted_uri"] == "at://did:plc:abc/post/123"

    def test_mark_failed(self, outbox: Outbox) -> None:
        row_id = outbox.save("post")
        outbox.mark_failed(row_id, "network error")
        entry = outbox.get(row_id)
        assert entry["status"] == "failed"
        assert entry["error"] == "network error"

    def test_get_nonexistent(self, outbox: Outbox) -> None:
        assert outbox.get(9999) is None

    def test_list_recent(self, outbox: Outbox) -> None:
        outbox.save("first")
        outbox.save("second")
        entries = outbox.list_recent(limit=10)
        assert len(entries) == 2
        assert entries[0]["text"] == "second"  # newest first

    def test_list_recent_limit(self, outbox: Outbox) -> None:
        for i in range(10):
            outbox.save(f"post {i}")
        entries = outbox.list_recent(limit=3)
        assert len(entries) == 3


# ---------------------------------------------------------------------------
# Outbox counting
# ---------------------------------------------------------------------------


class TestOutboxCounting:
    def test_today_posted_count_empty(self, outbox: Outbox) -> None:
        assert outbox.today_posted_count() == 0

    def test_today_posted_count(self, outbox: Outbox) -> None:
        r1 = outbox.save("a")
        r2 = outbox.save("b")
        outbox.mark_posted(r1, "uri1")
        outbox.mark_posted(r2, "uri2")
        assert outbox.today_posted_count() == 2

    def test_today_count_ignores_non_posted(self, outbox: Outbox) -> None:
        outbox.save("ready post")  # status = ready
        r = outbox.save("posted")
        outbox.mark_posted(r, "uri")
        assert outbox.today_posted_count() == 1

    def test_last_posted_at_empty(self, outbox: Outbox) -> None:
        assert outbox.last_posted_at() is None

    def test_last_posted_at(self, outbox: Outbox) -> None:
        r = outbox.save("post")
        outbox.mark_posted(r, "uri")
        assert outbox.last_posted_at() is not None

    def test_recent_posted_texts(self, outbox: Outbox) -> None:
        r1 = outbox.save("hello")
        r2 = outbox.save("world")
        outbox.mark_posted(r1, "u1")
        outbox.mark_posted(r2, "u2")
        texts = outbox.recent_posted_texts()
        assert "hello" in texts
        assert "world" in texts


# ---------------------------------------------------------------------------
# SafetyGuard: emergency stop
# ---------------------------------------------------------------------------


class TestEmergencyStop:
    def test_passes_without_stop_file(self, guard: SafetyGuard) -> None:
        passed, _ = guard.check("normal post")
        assert passed

    def test_blocks_with_stop_file(self, tmp_path: Path, outbox: Outbox) -> None:
        stop_file = tmp_path / "STOP"
        stop_file.write_text("stop", encoding="utf-8")
        guard = SafetyGuard(outbox=outbox, stop_file=stop_file)
        passed, reason = guard.check("any post")
        assert not passed
        assert "emergency stop" in reason


# ---------------------------------------------------------------------------
# SafetyGuard: length
# ---------------------------------------------------------------------------


class TestLengthCheck:
    def test_passes_short_post(self, guard: SafetyGuard) -> None:
        passed, _ = guard.check("short")
        assert passed

    def test_blocks_too_long(self, guard: SafetyGuard) -> None:
        passed, reason = guard.check("x" * (BLUESKY_MAX_LENGTH + 1))
        assert not passed
        assert "too long" in reason

    def test_passes_exact_limit(self, guard: SafetyGuard) -> None:
        passed, _ = guard.check("x" * BLUESKY_MAX_LENGTH)
        assert passed


# ---------------------------------------------------------------------------
# SafetyGuard: forbidden words
# ---------------------------------------------------------------------------


class TestForbiddenWords:
    def test_passes_clean_text(self, guard: SafetyGuard) -> None:
        passed, _ = guard.check("きょう空を見た")
        assert passed

    def test_blocks_forbidden(self, tmp_path: Path, outbox: Outbox) -> None:
        guard = SafetyGuard(
            outbox=outbox,
            stop_file=tmp_path / "STOP",
            forbidden_words=("NG_WORD",),
        )
        passed, reason = guard.check("this contains NG_WORD in it")
        assert not passed
        assert "forbidden" in reason


# ---------------------------------------------------------------------------
# SafetyGuard: daily cap
# ---------------------------------------------------------------------------


class TestDailyCap:
    def test_passes_under_cap(self, guard: SafetyGuard, outbox: Outbox) -> None:
        r = outbox.save("post")
        outbox.mark_posted(r, "uri")
        # Disable cooldown so we only test daily cap
        guard._cooldown_minutes = 0
        passed, _ = guard.check("new post")
        assert passed

    def test_blocks_at_cap(self, guard: SafetyGuard, outbox: Outbox) -> None:
        for i in range(3):  # max_daily=3
            r = outbox.save(f"post {i}")
            outbox.mark_posted(r, f"uri{i}")
        # Disable cooldown so we only test daily cap
        guard._cooldown_minutes = 0
        passed, reason = guard.check("completely different text")
        assert not passed
        assert "daily cap" in reason


# ---------------------------------------------------------------------------
# SafetyGuard: cooldown
# ---------------------------------------------------------------------------


class TestCooldown:
    def test_passes_no_previous_posts(self, guard: SafetyGuard) -> None:
        passed, _ = guard.check("first post ever")
        assert passed

    def test_blocks_too_soon(self, guard: SafetyGuard, outbox: Outbox) -> None:
        r = outbox.save("recent post")
        outbox.mark_posted(r, "uri")
        # Just posted, cooldown=60min, should block
        passed, reason = guard.check("another post")
        assert not passed
        assert "cooldown" in reason


# ---------------------------------------------------------------------------
# SafetyGuard: duplicate
# ---------------------------------------------------------------------------


class TestDuplicate:
    def test_passes_unique(self, guard: SafetyGuard, outbox: Outbox) -> None:
        r = outbox.save("first unique post")
        outbox.mark_posted(r, "uri")
        # Need to bypass cooldown for this test
        guard._cooldown_minutes = 0
        passed, _ = guard.check("completely different text")
        assert passed

    def test_blocks_exact_duplicate(self, guard: SafetyGuard, outbox: Outbox) -> None:
        r = outbox.save("exact same text")
        outbox.mark_posted(r, "uri")
        guard._cooldown_minutes = 0
        passed, reason = guard.check("exact same text")
        assert not passed
        assert "duplicate" in reason

    def test_blocks_similar(self, guard: SafetyGuard, outbox: Outbox) -> None:
        r = outbox.save("today I noticed something interesting at the station")
        outbox.mark_posted(r, "uri")
        guard._cooldown_minutes = 0
        passed, reason = guard.check("today I noticed something interesting at the statio")
        assert not passed
        assert "duplicate" in reason


# ---------------------------------------------------------------------------
# SafetyGuard: full pipeline
# ---------------------------------------------------------------------------


class TestFullCheck:
    def test_all_pass(self, guard: SafetyGuard) -> None:
        passed, reason = guard.check("きょう夕焼けがきれいだった")
        assert passed
        assert "all checks passed" in reason

    def test_returns_first_failure(self, tmp_path: Path, outbox: Outbox) -> None:
        stop_file = tmp_path / "STOP"
        stop_file.write_text("stop")
        guard = SafetyGuard(outbox=outbox, stop_file=stop_file)
        # Emergency stop should be checked first
        passed, reason = guard.check("x" * 999)
        assert not passed
        assert "emergency stop" in reason  # not "too long"
