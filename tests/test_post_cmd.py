"""Tests for the post CLI command.

All tests use stub LLM and mocked Bluesky — no real API calls.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.persona.cli import build_parser, main
from src.persona.outbox import Outbox


def _mock_profile(name: str = "Test") -> SimpleNamespace:
    return SimpleNamespace(display_name=name)


def _mock_send_post(uri: str = "at://did:plc:abc/post/1") -> SimpleNamespace:
    return SimpleNamespace(uri=uri)


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

    def test_post_default_no_dry_run(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["post"])
        assert args.dry_run is False

    def test_post_llm_choice(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["post", "--llm", "claude"])
        assert args.llm == "claude"

    def test_post_custom_outbox_db(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["post", "--outbox-db", "/tmp/ob.db"])
        assert args.outbox_db == "/tmp/ob.db"

    def test_post_custom_stop_file(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["post", "--stop-file", "/tmp/STOP"])
        assert args.stop_file == "/tmp/STOP"


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


class TestPostDryRun:
    def test_composes_and_saves_to_outbox(self, env: dict, capsys) -> None:
        main(_post_args(env, dry_run=True))

        captured = capsys.readouterr()
        assert "Composed:" in captured.out
        assert "Dry run" in captured.out
        assert "outbox #" in captured.out

    def test_outbox_entry_is_ready(self, env: dict) -> None:
        main(_post_args(env, dry_run=True))

        outbox = Outbox(db_path=env["outbox_db"])
        entries = outbox.list_recent(limit=1)
        assert len(entries) == 1
        assert entries[0]["status"] == "ready"
        outbox.close()

    @patch("src.persona.bluesky.Client")
    def test_does_not_call_bluesky(self, MockClient, env: dict) -> None:
        main(_post_args(env, dry_run=True))
        MockClient.return_value.login.assert_not_called()


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
# Real post (mocked Bluesky)
# ---------------------------------------------------------------------------


class TestPostReal:
    @patch("src.persona.bluesky.Client")
    def test_posts_to_bluesky(
        self, MockClient, env: dict, monkeypatch, capsys
    ) -> None:
        monkeypatch.setenv("BLUESKY_HANDLE", "test.bsky.social")
        monkeypatch.setenv("BLUESKY_APP_PASSWORD", "app-pass-123")

        mock_atproto = MockClient.return_value
        mock_atproto.login.return_value = _mock_profile()
        mock_atproto.send_post.return_value = _mock_send_post("at://did:plc:abc/post/1")

        main(_post_args(env))

        captured = capsys.readouterr()
        assert "Posted:" in captured.out
        assert "at://did:plc:abc/post/1" in captured.out

    @patch("src.persona.bluesky.Client")
    def test_outbox_marked_posted(
        self, MockClient, env: dict, monkeypatch
    ) -> None:
        monkeypatch.setenv("BLUESKY_HANDLE", "test.bsky.social")
        monkeypatch.setenv("BLUESKY_APP_PASSWORD", "app-pass-123")

        mock_atproto = MockClient.return_value
        mock_atproto.login.return_value = _mock_profile()
        mock_atproto.send_post.return_value = _mock_send_post("at://uri")

        main(_post_args(env))

        outbox = Outbox(db_path=env["outbox_db"])
        entries = outbox.list_recent(limit=1)
        assert entries[0]["status"] == "posted"
        assert entries[0]["posted_uri"] == "at://uri"
        outbox.close()

    def test_fails_without_bluesky_creds(self, env: dict, monkeypatch, capsys) -> None:
        monkeypatch.delenv("BLUESKY_HANDLE", raising=False)
        monkeypatch.delenv("BLUESKY_APP_PASSWORD", raising=False)

        main(_post_args(env))

        captured = capsys.readouterr()
        assert "Failed:" in captured.err

    @patch("src.persona.bluesky.Client")
    def test_network_error_marks_failed(
        self, MockClient, env: dict, monkeypatch, capsys
    ) -> None:
        monkeypatch.setenv("BLUESKY_HANDLE", "test.bsky.social")
        monkeypatch.setenv("BLUESKY_APP_PASSWORD", "app-pass-123")

        mock_atproto = MockClient.return_value
        mock_atproto.login.side_effect = ConnectionError("network down")

        main(_post_args(env))

        captured = capsys.readouterr()
        assert "Failed:" in captured.err

        outbox = Outbox(db_path=env["outbox_db"])
        entries = outbox.list_recent(limit=1)
        assert entries[0]["status"] == "failed"
        assert "network down" in entries[0]["error"]
        outbox.close()
