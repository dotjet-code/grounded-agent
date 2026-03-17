"""Tests for X (Twitter) posting adapter.

All tests mock tweepy — no real API calls.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.persona.x_client import XClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _set_x_env(monkeypatch) -> None:
    monkeypatch.setenv("X_API_KEY", "test-key")
    monkeypatch.setenv("X_API_KEY_SECRET", "test-secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "test-token-secret")


def _mock_tweet_response(tweet_id: str = "1234567890") -> SimpleNamespace:
    return SimpleNamespace(data={"id": tweet_id})


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocol:
    def test_has_name(self) -> None:
        client = XClient()
        assert client.name == "x"

    def test_has_max_length(self) -> None:
        client = XClient()
        assert client.max_length == 280


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    def test_raises_without_env(self, monkeypatch) -> None:
        monkeypatch.delenv("X_API_KEY", raising=False)
        monkeypatch.delenv("X_API_KEY_SECRET", raising=False)
        monkeypatch.delenv("X_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("X_ACCESS_TOKEN_SECRET", raising=False)

        client = XClient()
        with pytest.raises(RuntimeError, match="Missing environment variables"):
            client.login()

    def test_raises_with_partial_env(self, monkeypatch) -> None:
        monkeypatch.setenv("X_API_KEY", "key")
        monkeypatch.delenv("X_API_KEY_SECRET", raising=False)
        monkeypatch.delenv("X_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("X_ACCESS_TOKEN_SECRET", raising=False)

        client = XClient()
        with pytest.raises(RuntimeError, match="X_API_KEY_SECRET"):
            client.login()

    @patch("tweepy.Client")
    def test_login_returns_name(self, MockClient, monkeypatch) -> None:
        _set_x_env(monkeypatch)
        client = XClient()
        name = client.login()
        assert name == "X API"

    @patch("tweepy.Client")
    def test_login_creates_client(self, MockClient, monkeypatch) -> None:
        _set_x_env(monkeypatch)
        client = XClient()
        client.login()
        MockClient.assert_called_once_with(
            consumer_key="test-key",
            consumer_secret="test-secret",
            access_token="test-token",
            access_token_secret="test-token-secret",
        )


# ---------------------------------------------------------------------------
# Post
# ---------------------------------------------------------------------------


class TestPost:
    def test_raises_without_login(self) -> None:
        client = XClient()
        with pytest.raises(RuntimeError, match="Not logged in"):
            client.post("hello")

    @patch("tweepy.Client")
    def test_post_returns_url(self, MockClient, monkeypatch) -> None:
        _set_x_env(monkeypatch)
        MockClient.return_value.create_tweet.return_value = (
            _mock_tweet_response("9876543210")
        )

        client = XClient()
        client.login()
        url = client.post("test tweet")

        assert "9876543210" in url
        assert "x.com" in url

    @patch("tweepy.Client")
    def test_post_passes_text(self, MockClient, monkeypatch) -> None:
        _set_x_env(monkeypatch)
        MockClient.return_value.create_tweet.return_value = (
            _mock_tweet_response()
        )

        client = XClient()
        client.login()
        client.post("きょうの発見。")

        MockClient.return_value.create_tweet.assert_called_once_with(
            text="きょうの発見。"
        )
