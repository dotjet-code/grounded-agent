"""Tests for persona internal state model.

All tests are offline — no LLM, no network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persona.memory import Memory
from src.persona.state import PersonaState


@pytest.fixture()
def memory(tmp_path: Path) -> Memory:
    return Memory(db_path=tmp_path / "test.db", diary_dir=tmp_path / "diary")


@pytest.fixture()
def state(memory: Memory) -> PersonaState:
    return PersonaState(memory)


# ---------------------------------------------------------------------------
# Phase detection
# ---------------------------------------------------------------------------


class TestCurrentPhase:
    def test_phase_0_when_empty(self, state: PersonaState) -> None:
        assert state.current_phase() == 0

    def test_phase_0_below_threshold(self, memory: Memory, state: PersonaState) -> None:
        for i in range(49):
            memory.add_vocabulary(f"word_{i}")
        for i in range(19):
            memory.add_curiosity(f"thing_{i}")
        assert state.current_phase() == 0

    def test_phase_0_vocab_enough_but_curiosity_not(
        self, memory: Memory, state: PersonaState
    ) -> None:
        for i in range(50):
            memory.add_vocabulary(f"word_{i}")
        for i in range(10):
            memory.add_curiosity(f"thing_{i}")
        assert state.current_phase() == 0

    def test_phase_1_when_both_thresholds_met(
        self, memory: Memory, state: PersonaState
    ) -> None:
        for i in range(50):
            memory.add_vocabulary(f"word_{i}")
        for i in range(20):
            memory.add_curiosity(f"thing_{i}")
        assert state.current_phase() == 1

    def test_phase_1_well_above_threshold(
        self, memory: Memory, state: PersonaState
    ) -> None:
        for i in range(200):
            memory.add_vocabulary(f"word_{i}")
        for i in range(100):
            memory.add_curiosity(f"thing_{i}")
        # Phase 2 requires trial_log which doesn't exist yet, so max is 1
        assert state.current_phase() == 1


# ---------------------------------------------------------------------------
# Recent vocabulary
# ---------------------------------------------------------------------------


class TestRecentVocabulary:
    def test_empty(self, state: PersonaState) -> None:
        assert state.recent_vocabulary() == []

    def test_returns_entries(self, memory: Memory, state: PersonaState) -> None:
        memory.add_vocabulary("草", context="funny")
        memory.add_vocabulary("それな", context="agreement")
        result = state.recent_vocabulary()
        assert len(result) == 2

    def test_respects_limit(self, memory: Memory, state: PersonaState) -> None:
        for i in range(20):
            memory.add_vocabulary(f"word_{i}")
        result = state.recent_vocabulary(limit=5)
        assert len(result) == 5


# ---------------------------------------------------------------------------
# Recent interests
# ---------------------------------------------------------------------------


class TestRecentInterests:
    def test_empty(self, state: PersonaState) -> None:
        assert state.recent_interests() == []

    def test_returns_entries(self, memory: Memory, state: PersonaState) -> None:
        memory.add_curiosity("phone pocket sync")
        result = state.recent_interests()
        assert len(result) == 1
        assert result[0]["phenomenon"] == "phone pocket sync"

    def test_respects_limit(self, memory: Memory, state: PersonaState) -> None:
        for i in range(20):
            memory.add_curiosity(f"thing_{i}")
        result = state.recent_interests(limit=3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Diary
# ---------------------------------------------------------------------------


class TestDiaryAccess:
    def test_diary_count_empty(self, state: PersonaState) -> None:
        assert state.diary_count() == 0

    def test_diary_count(self, memory: Memory, state: PersonaState) -> None:
        memory.write_diary("2026-03-16", "day 1")
        memory.write_diary("2026-03-17", "day 2")
        assert state.diary_count() == 2

    def test_latest_diary_none_when_empty(self, state: PersonaState) -> None:
        assert state.latest_diary() is None

    def test_latest_diary_returns_tuple(
        self, memory: Memory, state: PersonaState
    ) -> None:
        memory.write_diary("2026-03-16", "first")
        memory.write_diary("2026-03-17", "second")
        result = state.latest_diary()
        assert result is not None
        date, content = result
        assert date == "2026-03-17"
        assert content == "second"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_empty_memory_has_phase_and_counts(self, state: PersonaState) -> None:
        s = state.summary()
        assert "Current phase: 0" in s
        assert "Vocabulary: 0" in s
        assert "Curiosities: 0" in s
        assert "Diary entries: 0" in s

    def test_includes_vocabulary(self, memory: Memory, state: PersonaState) -> None:
        memory.add_vocabulary("エモい", context="nostalgic feeling")
        s = state.summary()
        assert "エモい" in s
        assert "nostalgic feeling" in s

    def test_includes_curiosity(self, memory: Memory, state: PersonaState) -> None:
        memory.add_curiosity("vending machines say thank you")
        s = state.summary()
        assert "vending machines say thank you" in s

    def test_includes_latest_diary(self, memory: Memory, state: PersonaState) -> None:
        memory.write_diary("2026-03-16", "Today I noticed.")
        s = state.summary()
        assert "2026-03-16" in s
        assert "Today I noticed." in s

    def test_includes_correct_counts(
        self, memory: Memory, state: PersonaState
    ) -> None:
        memory.add_vocabulary("a")
        memory.add_vocabulary("b")
        memory.add_curiosity("x")
        memory.write_diary("2026-03-16", "entry")
        s = state.summary()
        assert "Vocabulary: 2" in s
        assert "Curiosities: 1" in s
        assert "Diary entries: 1" in s

    def test_phase_reflected_in_summary(
        self, memory: Memory, state: PersonaState
    ) -> None:
        for i in range(50):
            memory.add_vocabulary(f"w_{i}")
        for i in range(20):
            memory.add_curiosity(f"c_{i}")
        s = state.summary()
        assert "Current phase: 1" in s

    def test_vocab_without_context(
        self, memory: Memory, state: PersonaState
    ) -> None:
        memory.add_vocabulary("草")
        s = state.summary()
        assert "草" in s
        # Should not have trailing colon or empty context
        assert "草:" not in s

    def test_summary_is_string(self, state: PersonaState) -> None:
        assert isinstance(state.summary(), str)
