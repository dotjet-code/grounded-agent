"""Bluesky client for the persona system.

Wraps the atproto SDK to provide a simple interface for:
- Authentication (handle + app password)
- Reading the home timeline
- Creating posts
"""

from __future__ import annotations

from dataclasses import dataclass

from atproto import Client


@dataclass(frozen=True)
class TimelinePost:
    """A single post from the timeline, stripped to what we need."""

    author_handle: str
    author_display_name: str
    text: str
    created_at: str
    uri: str


class BlueskyClient:
    """Thin wrapper around atproto Client for persona use."""

    def __init__(self) -> None:
        self._client = Client()
        self._logged_in = False

    @property
    def logged_in(self) -> bool:
        return self._logged_in

    def login(self, handle: str, password: str) -> str:
        """Authenticate with Bluesky. Returns display name."""
        profile = self._client.login(handle, password)
        self._logged_in = True
        return profile.display_name or handle

    def fetch_timeline(self, limit: int = 30) -> list[TimelinePost]:
        """Fetch recent posts from the home timeline."""
        if not self._logged_in:
            raise RuntimeError("Not logged in. Call login() first.")

        response = self._client.get_timeline(limit=limit)
        posts: list[TimelinePost] = []

        for feed_view in response.feed:
            post = feed_view.post
            record = post.record

            # record can be various types; we only care about text posts
            text = getattr(record, "text", None)
            if text is None:
                continue

            created_at = getattr(record, "created_at", "")

            posts.append(
                TimelinePost(
                    author_handle=post.author.handle,
                    author_display_name=post.author.display_name or post.author.handle,
                    text=text,
                    created_at=created_at,
                    uri=post.uri,
                )
            )

        return posts

    def create_post(self, text: str) -> str:
        """Create a post on Bluesky. Returns the post URI."""
        if not self._logged_in:
            raise RuntimeError("Not logged in. Call login() first.")

        response = self._client.send_post(text=text, langs=["ja"])
        return response.uri


class BlueskyAdapter:
    """PostPlatform-compatible adapter wrapping BlueskyClient.

    Reads credentials from environment variables.
    """

    name: str = "bluesky"
    max_length: int = 300

    def __init__(self) -> None:
        self._client = BlueskyClient()

    def login(self) -> str:
        import os

        handle = os.environ.get("BLUESKY_HANDLE", "")
        password = os.environ.get("BLUESKY_APP_PASSWORD", "")
        if not handle or not password:
            raise RuntimeError(
                "Missing environment variables: BLUESKY_HANDLE, BLUESKY_APP_PASSWORD"
            )
        return self._client.login(handle, password)

    def post(self, text: str) -> str:
        return self._client.create_post(text)
