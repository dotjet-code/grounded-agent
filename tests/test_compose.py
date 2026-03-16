"""Tests for post composer.

All tests use a fake LLM — no API calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persona.compose import PostComposer
from src.persona.memory import Memory
from src.persona.state import PersonaState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def memory(tmp_path: Path) -> Memory:
    return Memory(db_path=tmp_path / "test.db", diary_dir=tmp_path / "diary")


@pytest.fixture()
def state(memory: Memory) -> PersonaState:
    return PersonaState(memory)


def _make_llm(response: str):
    def fake_llm(system: str, user: str) -> str:
        return response
    return fake_llm


def _make_recording_llm(response: str):
    calls: list[tuple[str, str]] = []

    def fake_llm(system: str, user: str) -> str:
        calls.append((system, user))
        return response

    return fake_llm, calls


# ---------------------------------------------------------------------------
# Compose
# ---------------------------------------------------------------------------


class TestCompose:
    def test_returns_string(self, state: PersonaState) -> None:
        composer = PostComposer(state, _make_llm("きょう空を見た。"))
        result = composer.compose()
        assert isinstance(result, str)

    def test_returns_llm_response(self, state: PersonaState) -> None:
        composer = PostComposer(state, _make_llm("電車の中で全員下を向いていた。"))
        result = composer.compose()
        assert result == "電車の中で全員下を向いていた。"

    def test_strips_whitespace(self, state: PersonaState) -> None:
        composer = PostComposer(state, _make_llm("  投稿文  \n"))
        result = composer.compose()
        assert result == "投稿文"

    def test_system_prompt_contains_memory(
        self, memory: Memory, state: PersonaState
    ) -> None:
        memory.add_vocabulary("草", context="funny")
        memory.add_curiosity("改札の前でスマホをしまう現象")

        fake_llm, calls = _make_recording_llm("投稿")
        composer = PostComposer(state, fake_llm)
        composer.compose()

        system, _ = calls[0]
        assert "草" in system
        assert "改札" in system

    def test_system_prompt_in_japanese(self, state: PersonaState) -> None:
        fake_llm, calls = _make_recording_llm("投稿")
        composer = PostComposer(state, fake_llm)
        composer.compose()

        system, _ = calls[0]
        assert "日本語" in system

    def test_phase_0_instruction(self, state: PersonaState) -> None:
        fake_llm, calls = _make_recording_llm("投稿")
        composer = PostComposer(state, fake_llm)
        composer.compose()

        system, _ = calls[0]
        assert "Phase 0" in system

    def test_user_prompt_asks_for_single_post(self, state: PersonaState) -> None:
        fake_llm, calls = _make_recording_llm("投稿")
        composer = PostComposer(state, fake_llm)
        composer.compose()

        _, user = calls[0]
        assert "1つだけ" in user

    def test_includes_no_hashtag_rule(self, state: PersonaState) -> None:
        fake_llm, calls = _make_recording_llm("投稿")
        composer = PostComposer(state, fake_llm)
        composer.compose()

        system, _ = calls[0]
        assert "ハッシュタグ" in system

    def test_includes_length_limit(self, state: PersonaState) -> None:
        fake_llm, calls = _make_recording_llm("投稿")
        composer = PostComposer(state, fake_llm)
        composer.compose()

        system, _ = calls[0]
        assert "280" in system
