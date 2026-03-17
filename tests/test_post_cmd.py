"""Tests for the post CLI command.

All tests use stub LLM and mocked platforms — no real API calls.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.persona.cli import build_parser, main
from src.persona.outbox import Outbox


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_profile(name: str = "Test") -> SimpleNamespace:
    return SimpleNamespace(display_name=name)


def _mock_send_post(uri: str = "at://did:plc:abc/post/1") -> SimpleNamespace:
    return SimpleNamespace(uri=uri)


def _mock_tweet_response(tweet_id: str = "1234567890") -> SimpleNamespace:
    return SimpleNamespace(data={"id": tweet_id})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def env(tmp_path: Path) -> dict[str, str]:
    """Return CLI args pointing to temp directories."""
    return {
        "db": str(tmp_path / "memory.db"),
        "diary_dir": str(tmp_path / "diary"),
        "outbox_db": str(tmp_path / "outbox.db"),
        "stop_file": str(tmp_path / "STOP"),
    }


def _base_args(env: dict) -> list[str]:
    return [
        "--db", env["db"],
        "--diary-dir", env["diary_dir"],
    ]


def _post_args(env: dict, **overrides) -> list[str]:
    args = _base_args(env) + [
        "post",
        "--outbox-db", env["outbox_db"],
        "--stop-file", env["stop_file"],
    ]
    if overrides.get("dry_run", False):
        args.append("--dry-run")
    if "llm" in overrides:
        args.extend(["--llm", overrides["llm"]])
    if "platform" in overrides:
        args.extend(["--platform", overrides["platform"]])
    return args


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class TestPostParser:
    def test_post_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["post"])
        assert args.command == "post"

    def test_post_dry_run(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["post", "--dry-run"])
        assert args.dry_run is True

    def test_default_platform_is_x(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["post"])
        assert args.platform == "x"

    def test_platform_bluesky(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["post", "--platform", "bluesky"])
        assert args.platform == "bluesky"

    def test_platform_x(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["post", "--platform", "x"])
        assert args.platform == "x"


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


class TestPostDryRun:
    def test_composes_and_saves_to_outbox(self, env: dict, capsys) -> None:
        main(_post_args(env, dry_run=True))

        captured = capsys.readouterr()
        assert "Composed" in captured.out
        assert "Dry run" in captured.out
        assert "outbox #" in captured.out

    def test_outbox_entry_is_ready(self, env: dict) -> None:
        main(_post_args(env, dry_run=True))

        outbox = Outbox(db_path=env["outbox_db"])
        entries = outbox.list_recent(limit=1)
        assert len(entries) == 1
        assert entries[0]["status"] == "ready"
        outbox.close()


# ---------------------------------------------------------------------------
# Safety blocking
# ---------------------------------------------------------------------------


class TestPostSafetyBlock:
    def test_emergency_stop_blocks(self, env: dict, capsys) -> None:
        Path(env["stop_file"]).write_text("stop", encoding="utf-8")

        main(_post_args(env, dry_run=True))

        captured = capsys.readouterr()
        assert "Blocked:" in captured.out
        assert "emergency stop" in captured.out

    def test_blocked_entry_in_outbox(self, env: dict) -> None:
        Path(env["stop_file"]).write_text("stop", encoding="utf-8")

        main(_post_args(env, dry_run=True))

        outbox = Outbox(db_path=env["outbox_db"])
        entries = outbox.list_recent(limit=1)
        assert entries[0]["status"] == "blocked"
        outbox.close()


# ---------------------------------------------------------------------------
# Real post: X (mocked tweepy)
# ---------------------------------------------------------------------------


class TestPostX:
    @patch("tweepy.Client")
    def test_posts_to_x(self, MockClient, env: dict, monkeypatch, capsys) -> None:
        monkeypatch.setenv("X_API_KEY", "k")
        monkeypatch.setenv("X_API_KEY_SECRET", "ks")
        monkeypatch.setenv("X_ACCESS_TOKEN", "t")
        monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "ts")

        MockClient.return_value.create_tweet.return_value = (
            _mock_tweet_response("111222333")
        )

        main(_post_args(env, platform="x"))

        captured = capsys.readouterr()
        assert "Posted:" in captured.out
        assert "111222333" in captured.out

    @patch("tweepy.Client")
    def test_outbox_marked_posted(self, MockClient, env: dict, monkeypatch) -> None:
        monkeypatch.setenv("X_API_KEY", "k")
        monkeypatch.setenv("X_API_KEY_SECRET", "ks")
        monkeypatch.setenv("X_ACCESS_TOKEN", "t")
        monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "ts")

        MockClient.return_value.create_tweet.return_value = (
            _mock_tweet_response("999")
        )

        main(_post_args(env, platform="x"))

        outbox = Outbox(db_path=env["outbox_db"])
        entries = outbox.list_recent(limit=1)
        assert entries[0]["status"] == "posted"
        assert "999" in entries[0]["posted_uri"]
        outbox.close()

    def test_fails_without_x_creds(self, env: dict, monkeypatch, capsys) -> None:
        monkeypatch.delenv("X_API_KEY", raising=False)
        monkeypatch.delenv("X_API_KEY_SECRET", raising=False)
        monkeypatch.delenv("X_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("X_ACCESS_TOKEN_SECRET", raising=False)

        main(_post_args(env, platform="x"))

        captured = capsys.readouterr()
        assert "Failed:" in captured.err

    @patch("tweepy.Client")
    def test_network_error_marks_failed(
        self, MockClient, env: dict, monkeypatch, capsys
    ) -> None:
        monkeypatch.setenv("X_API_KEY", "k")
        monkeypatch.setenv("X_API_KEY_SECRET", "ks")
        monkeypatch.setenv("X_ACCESS_TOKEN", "t")
        monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "ts")

        MockClient.return_value.create_tweet.side_effect = (
            ConnectionError("network down")
        )

        main(_post_args(env, platform="x"))

        captured = capsys.readouterr()
        assert "Failed:" in captured.err

        outbox = Outbox(db_path=env["outbox_db"])
        entries = outbox.list_recent(limit=1)
        assert entries[0]["status"] == "failed"
        assert "network down" in entries[0]["error"]
        outbox.close()


# ---------------------------------------------------------------------------
# Real post: Bluesky (mocked atproto)
# ---------------------------------------------------------------------------


class TestPostBluesky:
    @patch("src.persona.bluesky.Client")
    def test_posts_to_bluesky(
        self, MockClient, env: dict, monkeypatch, capsys
    ) -> None:
        monkeypatch.setenv("BLUESKY_HANDLE", "test.bsky.social")
        monkeypatch.setenv("BLUESKY_APP_PASSWORD", "app-pass-123")

        mock_atproto = MockClient.return_value
        mock_atproto.login.return_value = _mock_profile()
        mock_atproto.send_post.return_value = _mock_send_post("at://did:plc:abc/post/1")

        main(_post_args(env, platform="bluesky"))

        captured = capsys.readouterr()
        assert "Posted:" in captured.out
        assert "at://did:plc:abc/post/1" in captured.out


# ---------------------------------------------------------------------------
# No command
# ---------------------------------------------------------------------------


class TestNoCommand:
    def test_no_command_exits(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 1
