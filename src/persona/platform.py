"""Platform adapter protocol for posting.

Each platform adapter implements login() and post().
The CLI resolves the adapter by name via resolve_platform().
"""

from __future__ import annotations

from typing import Protocol


class PostPlatform(Protocol):
    """Interface that all posting adapters must satisfy."""

    name: str
    max_length: int

    def login(self) -> str:
        """Authenticate using environment variables. Returns display name."""
        ...

    def post(self, text: str) -> str:
        """Post text to the platform. Returns a URI or ID string."""
        ...


def resolve_platform(name: str) -> PostPlatform:
    """Resolve a platform adapter by name.

    Raises ValueError for unknown platform names.
    """
    if name == "x":
        from src.persona.x_client import XClient
        return XClient()
    if name == "bluesky":
        from src.persona.bluesky import BlueskyAdapter
        return BlueskyAdapter()
    raise ValueError(f"Unknown platform: {name!r}. Choose 'x' or 'bluesky'.")
