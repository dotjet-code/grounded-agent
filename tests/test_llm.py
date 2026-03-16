"""Tests for LLM adapter module.

All tests mock the Anthropic SDK — no real API calls.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.persona.llm import make_claude_llm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_message(text: str = "test response") -> SimpleNamespace:
    """Create a mock Anthropic Message response."""
    return SimpleNamespace(content=[SimpleNamespace(text=text)])


# ---------------------------------------------------------------------------
# API key validation
# ---------------------------------------------------------------------------


class TestApiKey:
    def test_raises_without_api_key(self, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            make_claude_llm()

    @patch("anthropic.Anthropic")
    def test_accepts_api_key_from_env(self, MockAnthropic, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _mock_message()

        llm = make_claude_llm()
        result = llm("system", "user")

        assert result == "test response"
        MockAnthropic.assert_called_once_with(api_key="sk-test-key")


# ---------------------------------------------------------------------------
# LLM call behavior
# ---------------------------------------------------------------------------


class TestClaudeLlm:
    @patch("anthropic.Anthropic")
    def test_returns_text(self, MockAnthropic, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _mock_message("hello world")

        llm = make_claude_llm()
        result = llm("sys prompt", "user msg")

        assert result == "hello world"

    @patch("anthropic.Anthropic")
    def test_passes_system_and_user(self, MockAnthropic, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _mock_message()

        llm = make_claude_llm()
        llm("my system prompt", "my user message")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "my system prompt"
        assert call_kwargs["messages"] == [{"role": "user", "content": "my user message"}]

    @patch("anthropic.Anthropic")
    def test_uses_default_model(self, MockAnthropic, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _mock_message()

        llm = make_claude_llm()
        llm("sys", "usr")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "haiku" in call_kwargs["model"]

    @patch("anthropic.Anthropic")
    def test_custom_model(self, MockAnthropic, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _mock_message()

        llm = make_claude_llm(model="claude-sonnet-4-6-20260316")
        llm("sys", "usr")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-6-20260316"

    @patch("anthropic.Anthropic")
    def test_custom_max_tokens(self, MockAnthropic, monkeypatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _mock_message()

        llm = make_claude_llm(max_tokens=512)
        llm("sys", "usr")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 512

    @patch("anthropic.Anthropic")
    def test_conforms_to_llm_call_type(self, MockAnthropic, monkeypatch) -> None:
        """make_claude_llm should return a callable matching LlmCall signature."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _mock_message("ok")

        llm = make_claude_llm()

        # Should be callable with (str, str) -> str
        result = llm("system", "user")
        assert isinstance(result, str)
