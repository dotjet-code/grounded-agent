"""Tests for persona memory module."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persona.memory import Memory


@pytest.fixture()
def mem(tmp_path: Path) -> Memory:
    db = tmp_path / "test.db"
    diary = tmp_path / "diary"
    return Memory(db_path=db, diary_dir=diary)


# ---------------------------------------------------------------------------
# Vocabulary notebook
# ---------------------------------------------------------------------------


class TestVocabulary:
    def test_add_returns_id(self, mem: Memory) -> None:
        row_id = mem.add_vocabulary("草", context="funny reaction")
        assert isinstance(row_id, int)
        assert row_id >= 1

    def test_add_increments_count(self, mem: Memory) -> None:
        assert mem.vocabulary_count() == 0
        mem.add_vocabulary("草")
        mem.add_vocabulary("それな")
        assert mem.vocabulary_count() == 2

    def test_list_returns_newest_first(self, mem: Memory) -> None:
        mem.add_vocabulary("first")
        mem.add_vocabulary("second")
        items = mem.list_vocabulary()
        assert items[0]["expression"] == "second"
        assert items[1]["expression"] == "first"

    def test_list_respects_limit(self, mem: Memory) -> None:
        for i in range(10):
            mem.add_vocabulary(f"word_{i}")
        items = mem.list_vocabulary(limit=3)
        assert len(items) == 3

    def test_fields_stored(self, mem: Memory) -> None:
        mem.add_vocabulary(
            expression="エモい",
            context="used to describe nostalgic feelings",
            structure_note="adjective form of English 'emo'",
            source="timeline observation",
        )
        item = mem.list_vocabulary(limit=1)[0]
        assert item["expression"] == "エモい"
        assert item["context"] == "used to describe nostalgic feelings"
        assert item["structure_note"] == "adjective form of English 'emo'"
        assert item["source"] == "timeline observation"
        assert "date_found" in item

    def test_empty_list(self, mem: Memory) -> None:
        assert mem.list_vocabulary() == []


# ---------------------------------------------------------------------------
# Curiosity list
# ---------------------------------------------------------------------------


class TestCuriosity:
    def test_add_returns_id(self, mem: Memory) -> None:
        row_id = mem.add_curiosity("people put phones away at ticket gates")
        assert isinstance(row_id, int)

    def test_default_status_is_unnamed(self, mem: Memory) -> None:
        mem.add_curiosity("phone pocket sync")
        item = mem.list_curiosity()[0]
        assert item["status"] == "unnamed"
        assert item["times_seen"] == 1

    def test_bump_increments_times_seen(self, mem: Memory) -> None:
        cid = mem.add_curiosity("sunday night sadness")
        mem.bump_curiosity(cid)
        mem.bump_curiosity(cid)
        item = mem.list_curiosity()[0]
        assert item["times_seen"] == 3

    def test_update_status(self, mem: Memory) -> None:
        cid = mem.add_curiosity("monday damage")
        mem.update_curiosity_status(cid, "attempted")
        item = mem.list_curiosity()[0]
        assert item["status"] == "attempted"

    def test_filter_by_status(self, mem: Memory) -> None:
        mem.add_curiosity("thing A")
        cid_b = mem.add_curiosity("thing B")
        mem.update_curiosity_status(cid_b, "named")

        unnamed = mem.list_curiosity(status="unnamed")
        named = mem.list_curiosity(status="named")
        assert len(unnamed) == 1
        assert len(named) == 1
        assert unnamed[0]["phenomenon"] == "thing A"
        assert named[0]["phenomenon"] == "thing B"

    def test_count(self, mem: Memory) -> None:
        assert mem.curiosity_count() == 0
        mem.add_curiosity("x")
        mem.add_curiosity("y")
        assert mem.curiosity_count() == 2

    def test_empty_list(self, mem: Memory) -> None:
        assert mem.list_curiosity() == []


# ---------------------------------------------------------------------------
# Diary
# ---------------------------------------------------------------------------


class TestDiary:
    def test_write_creates_file(self, mem: Memory) -> None:
        path = mem.write_diary("2026-03-16", "Today I watched the timeline.")
        assert path.exists()
        assert path.name == "2026-03-16.md"

    def test_read_returns_content(self, mem: Memory) -> None:
        mem.write_diary("2026-03-16", "First entry.")
        content = mem.read_diary("2026-03-16")
        assert content == "First entry."

    def test_read_missing_returns_none(self, mem: Memory) -> None:
        assert mem.read_diary("1999-01-01") is None

    def test_overwrite_existing(self, mem: Memory) -> None:
        mem.write_diary("2026-03-16", "Draft.")
        mem.write_diary("2026-03-16", "Final version.")
        assert mem.read_diary("2026-03-16") == "Final version."

    def test_list_dates_sorted(self, mem: Memory) -> None:
        mem.write_diary("2026-03-18", "c")
        mem.write_diary("2026-03-16", "a")
        mem.write_diary("2026-03-17", "b")
        dates = mem.list_diary_dates()
        assert dates == ["2026-03-16", "2026-03-17", "2026-03-18"]

    def test_list_empty(self, mem: Memory) -> None:
        assert mem.list_diary_dates() == []


# ---------------------------------------------------------------------------
# Phase detection
# ---------------------------------------------------------------------------


class TestPhaseCounts:
    def test_all_zero_initially(self, mem: Memory) -> None:
        counts = mem.phase_counts()
        assert counts == {"vocabulary": 0, "curiosity": 0, "diary": 0}

    def test_reflects_additions(self, mem: Memory) -> None:
        mem.add_vocabulary("word1")
        mem.add_vocabulary("word2")
        mem.add_curiosity("thing")
        mem.write_diary("2026-03-16", "entry")

        counts = mem.phase_counts()
        assert counts["vocabulary"] == 2
        assert counts["curiosity"] == 1
        assert counts["diary"] == 1
