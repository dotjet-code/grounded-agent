"""Tests for persona core module.

All tests use a fake LLM callable — no real API calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persona.core import PersonaCore
from src.persona.memory import Memory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def memory(tmp_path: Path) -> Memory:
    return Memory(db_path=tmp_path / "test.db", diary_dir=tmp_path / "diary")


def _make_llm(response: str):
    """Create a fake LLM callable that always returns the given response."""
    def fake_llm(system: str, user: str) -> str:
        return response
    return fake_llm


def _make_recording_llm(response: str):
    """Create a fake LLM that records calls and returns a fixed response."""
    calls: list[tuple[str, str]] = []

    def fake_llm(system: str, user: str) -> str:
        calls.append((system, user))
        return response

    return fake_llm, calls


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


class TestContext:
    def test_empty_memory(self, memory: Memory) -> None:
        core = PersonaCore(memory, _make_llm(""))
        ctx = core.context()
        assert "no memories yet" in ctx.lower() or "Memory size" in ctx

    def test_includes_vocabulary(self, memory: Memory) -> None:
        memory.add_vocabulary("草", context="funny reaction")
        core = PersonaCore(memory, _make_llm(""))
        ctx = core.context()
        assert "草" in ctx
        assert "funny reaction" in ctx

    def test_includes_curiosity(self, memory: Memory) -> None:
        memory.add_curiosity("everyone puts phones away at ticket gates")
        core = PersonaCore(memory, _make_llm(""))
        ctx = core.context()
        assert "ticket gates" in ctx

    def test_includes_latest_diary(self, memory: Memory) -> None:
        memory.write_diary("2026-03-16", "Today I watched.")
        core = PersonaCore(memory, _make_llm(""))
        ctx = core.context()
        assert "Today I watched" in ctx
        assert "2026-03-16" in ctx

    def test_includes_counts(self, memory: Memory) -> None:
        memory.add_vocabulary("word1")
        memory.add_vocabulary("word2")
        memory.add_curiosity("thing")
        core = PersonaCore(memory, _make_llm(""))
        ctx = core.context()
        assert "Vocabulary: 2" in ctx
        assert "Curiosities: 1" in ctx


# ---------------------------------------------------------------------------
# Observe
# ---------------------------------------------------------------------------


class TestObserve:
    def test_empty_input(self, memory: Memory) -> None:
        core = PersonaCore(memory, _make_llm(""))
        result = core.observe([])
        assert result["vocabulary_added"] == 0
        assert result["curiosity_added"] == 0

    def test_parses_vocab_lines(self, memory: Memory) -> None:
        response = (
            "VOCAB: エモい | adjective form of emo, used for nostalgia\n"
            "VOCAB: それな | strong agreement, very casual\n"
            "Nothing else caught my attention."
        )
        core = PersonaCore(memory, _make_llm(response))
        result = core.observe(["some timeline text"])

        assert result["vocabulary_added"] == 2
        assert memory.vocabulary_count() == 2

        items = memory.list_vocabulary()
        expressions = [v["expression"] for v in items]
        assert "エモい" in expressions
        assert "それな" in expressions

    def test_parses_curiosity_lines(self, memory: Memory) -> None:
        response = (
            "CURIOSITY: people sigh at the same time on trains | happens around 8am\n"
            "CURIOSITY: vending machines say thank you | why is the machine polite?"
        )
        core = PersonaCore(memory, _make_llm(response))
        result = core.observe(["observed text"])

        assert result["curiosity_added"] == 2
        assert memory.curiosity_count() == 2

    def test_mixed_vocab_and_curiosity(self, memory: Memory) -> None:
        response = (
            "VOCAB: 推し疲れ | tired of supporting your favorite\n"
            "CURIOSITY: Sunday night timeline gets darker | emotional pattern?"
        )
        core = PersonaCore(memory, _make_llm(response))
        result = core.observe(["text"])

        assert result["vocabulary_added"] == 1
        assert result["curiosity_added"] == 1

    def test_no_matches_in_response(self, memory: Memory) -> None:
        response = "Nothing particularly caught my attention today."
        core = PersonaCore(memory, _make_llm(response))
        result = core.observe(["some text"])

        assert result["vocabulary_added"] == 0
        assert result["curiosity_added"] == 0
        assert memory.vocabulary_count() == 0

    def test_raw_response_preserved(self, memory: Memory) -> None:
        response = "VOCAB: test | reason\nSome other text."
        core = PersonaCore(memory, _make_llm(response))
        result = core.observe(["input"])

        assert result["raw_response"] == response

    def test_skips_empty_expressions(self, memory: Memory) -> None:
        response = "VOCAB:  | empty expression\nVOCAB: real | valid"
        core = PersonaCore(memory, _make_llm(response))
        result = core.observe(["input"])

        assert result["vocabulary_added"] == 1
        assert memory.vocabulary_count() == 1

    def test_observed_texts_passed_to_llm(self, memory: Memory) -> None:
        fake_llm, calls = _make_recording_llm("nothing here")
        core = PersonaCore(memory, fake_llm)
        core.observe(["post one", "post two"])

        assert len(calls) == 1
        system, user = calls[0]
        assert "post one" in user
        assert "post two" in user

    def test_context_included_in_system_prompt(self, memory: Memory) -> None:
        memory.add_vocabulary("既存の言葉", context="already known")
        fake_llm, calls = _make_recording_llm("nothing")
        core = PersonaCore(memory, fake_llm)
        core.observe(["new text"])

        system, _ = calls[0]
        assert "既存の言葉" in system


# ---------------------------------------------------------------------------
# Reflect
# ---------------------------------------------------------------------------


class TestReflect:
    def test_writes_diary(self, memory: Memory) -> None:
        diary_text = "Today I noticed many things."
        core = PersonaCore(memory, _make_llm(diary_text))
        result = core.reflect(date="2026-03-16")

        assert result == diary_text
        assert memory.read_diary("2026-03-16") == diary_text

    def test_returns_diary_text(self, memory: Memory) -> None:
        core = PersonaCore(memory, _make_llm("My diary entry."))
        text = core.reflect(date="2026-03-16")
        assert text == "My diary entry."

    def test_default_date_is_today(self, memory: Memory) -> None:
        core = PersonaCore(memory, _make_llm("entry"))
        core.reflect()  # no date arg

        dates = memory.list_diary_dates()
        assert len(dates) == 1
        # Should be a valid YYYY-MM-DD format
        assert len(dates[0]) == 10

    def test_context_included_in_prompt(self, memory: Memory) -> None:
        memory.add_curiosity("interesting thing")
        fake_llm, calls = _make_recording_llm("diary text")
        core = PersonaCore(memory, fake_llm)
        core.reflect(date="2026-03-16")

        system, _ = calls[0]
        assert "interesting thing" in system

    def test_date_included_in_user_prompt(self, memory: Memory) -> None:
        fake_llm, calls = _make_recording_llm("diary text")
        core = PersonaCore(memory, fake_llm)
        core.reflect(date="2026-03-16")

        _, user = calls[0]
        assert "2026-03-16" in user

    def test_reflect_after_observe(self, memory: Memory) -> None:
        """Observe first, then reflect — diary should reference accumulated memory."""
        observe_response = "VOCAB: なるほど | understanding acknowledgment"
        diary_response = "Today I learned the word なるほど."

        call_count = [0]

        def sequenced_llm(system: str, user: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                return observe_response
            return diary_response

        core = PersonaCore(memory, sequenced_llm)
        core.observe(["some conversation"])
        text = core.reflect(date="2026-03-16")

        assert text == diary_response
        assert memory.vocabulary_count() == 1
        assert memory.read_diary("2026-03-16") == diary_response
