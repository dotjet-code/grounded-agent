"""Tests for Bluesky client module.

All tests use mocked atproto Client — no network calls.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.persona.bluesky import BlueskyClient, TimelinePost


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_profile(display_name: str = "Test User") -> SimpleNamespace:
    return SimpleNamespace(display_name=display_name)


def _mock_post(
    handle: str = "alice.bsky.social",
    display_name: str = "Alice",
    text: str = "Hello world",
    created_at: str = "2026-03-16T10:00:00Z",
    uri: str = "at://did:plc:abc/app.bsky.feed.post/123",
) -> SimpleNamespace:
    return SimpleNamespace(
        post=SimpleNamespace(
            author=SimpleNamespace(handle=handle, display_name=display_name),
            record=SimpleNamespace(text=text, created_at=created_at),
            uri=uri,
        )
    )


def _mock_timeline_response(posts: list | None = None) -> SimpleNamespace:
    if posts is None:
        posts = [_mock_post()]
    return SimpleNamespace(feed=posts)


def _mock_create_response(uri: str = "at://did:plc:abc/app.bsky.feed.post/456") -> SimpleNamespace:
    return SimpleNamespace(uri=uri)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    @patch("src.persona.bluesky.Client")
    def test_login_returns_display_name(self, MockClient: MagicMock) -> None:
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = _mock_profile("テストユーザー")

        client = BlueskyClient()
        name = client.login("test.bsky.social", "app-password")

        assert name == "テストユーザー"
        assert client.logged_in is True

    @patch("src.persona.bluesky.Client")
    def test_login_fallback_to_handle(self, MockClient: MagicMock) -> None:
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = _mock_profile(display_name=None)

        client = BlueskyClient()
        name = client.login("test.bsky.social", "app-password")

        assert name == "test.bsky.social"

    @patch("src.persona.bluesky.Client")
    def test_not_logged_in_initially(self, MockClient: MagicMock) -> None:
        client = BlueskyClient()
        assert client.logged_in is False


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


class TestFetchTimeline:
    @patch("src.persona.bluesky.Client")
    def test_returns_timeline_posts(self, MockClient: MagicMock) -> None:
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = _mock_profile()
        mock_instance.get_timeline.return_value = _mock_timeline_response([
            _mock_post(handle="alice.bsky.social", text="post one"),
            _mock_post(handle="bob.bsky.social", text="post two"),
        ])

        client = BlueskyClient()
        client.login("me", "pass")
        posts = client.fetch_timeline(limit=10)

        assert len(posts) == 2
        assert isinstance(posts[0], TimelinePost)
        assert posts[0].text == "post one"
        assert posts[1].author_handle == "bob.bsky.social"

    @patch("src.persona.bluesky.Client")
    def test_passes_limit(self, MockClient: MagicMock) -> None:
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = _mock_profile()
        mock_instance.get_timeline.return_value = _mock_timeline_response([])

        client = BlueskyClient()
        client.login("me", "pass")
        client.fetch_timeline(limit=5)

        mock_instance.get_timeline.assert_called_once_with(limit=5)

    @patch("src.persona.bluesky.Client")
    def test_skips_non_text_records(self, MockClient: MagicMock) -> None:
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = _mock_profile()

        non_text_post = SimpleNamespace(
            post=SimpleNamespace(
                author=SimpleNamespace(handle="x", display_name="X"),
                record=SimpleNamespace(),  # no text attribute
                uri="at://...",
            )
        )
        mock_instance.get_timeline.return_value = _mock_timeline_response([
            _mock_post(text="real post"),
            non_text_post,
        ])

        client = BlueskyClient()
        client.login("me", "pass")
        posts = client.fetch_timeline()

        assert len(posts) == 1
        assert posts[0].text == "real post"

    @patch("src.persona.bluesky.Client")
    def test_empty_timeline(self, MockClient: MagicMock) -> None:
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = _mock_profile()
        mock_instance.get_timeline.return_value = _mock_timeline_response([])

        client = BlueskyClient()
        client.login("me", "pass")
        posts = client.fetch_timeline()

        assert posts == []

    def test_raises_if_not_logged_in(self) -> None:
        client = BlueskyClient()
        with pytest.raises(RuntimeError, match="Not logged in"):
            client.fetch_timeline()

    @patch("src.persona.bluesky.Client")
    def test_display_name_fallback(self, MockClient: MagicMock) -> None:
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = _mock_profile()

        post_no_name = SimpleNamespace(
            post=SimpleNamespace(
                author=SimpleNamespace(handle="noname.bsky.social", display_name=None),
                record=SimpleNamespace(text="hello", created_at="2026-01-01T00:00:00Z"),
                uri="at://...",
            )
        )
        mock_instance.get_timeline.return_value = _mock_timeline_response([post_no_name])

        client = BlueskyClient()
        client.login("me", "pass")
        posts = client.fetch_timeline()

        assert posts[0].author_display_name == "noname.bsky.social"


# ---------------------------------------------------------------------------
# Create post
# ---------------------------------------------------------------------------


class TestCreatePost:
    @patch("src.persona.bluesky.Client")
    def test_returns_uri(self, MockClient: MagicMock) -> None:
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = _mock_profile()
        mock_instance.send_post.return_value = _mock_create_response(
            "at://did:plc:abc/app.bsky.feed.post/789"
        )

        client = BlueskyClient()
        client.login("me", "pass")
        uri = client.create_post("きょうの発見。")

        assert uri == "at://did:plc:abc/app.bsky.feed.post/789"

    @patch("src.persona.bluesky.Client")
    def test_sends_japanese_lang(self, MockClient: MagicMock) -> None:
        mock_instance = MockClient.return_value
        mock_instance.login.return_value = _mock_profile()
        mock_instance.send_post.return_value = _mock_create_response()

        client = BlueskyClient()
        client.login("me", "pass")
        client.create_post("テスト")

        mock_instance.send_post.assert_called_once_with(text="テスト", langs=["ja"])

    def test_raises_if_not_logged_in(self) -> None:
        client = BlueskyClient()
        with pytest.raises(RuntimeError, match="Not logged in"):
            client.create_post("hello")
