"""X (Twitter) posting adapter.

Write-only client using tweepy and the X API v2 free tier.
All credentials are read from environment variables.

Required environment variables:
    X_API_KEY
    X_API_KEY_SECRET
    X_ACCESS_TOKEN
    X_ACCESS_TOKEN_SECRET
"""

from __future__ import annotations

import os

X_MAX_LENGTH = 280


class XClient:
    """Minimal X posting adapter conforming to PostPlatform protocol."""

    name: str = "x"
    max_length: int = X_MAX_LENGTH

    def __init__(self) -> None:
        self._client = None

    def login(self) -> str:
        """Authenticate with X using environment variables.

        Returns the string 'X API' as display name (free tier has no
        user-info read access).
        """
        api_key = os.environ.get("X_API_KEY", "")
        api_key_secret = os.environ.get("X_API_KEY_SECRET", "")
        access_token = os.environ.get("X_ACCESS_TOKEN", "")
        access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET", "")

        missing = []
        if not api_key:
            missing.append("X_API_KEY")
        if not api_key_secret:
            missing.append("X_API_KEY_SECRET")
        if not access_token:
            missing.append("X_ACCESS_TOKEN")
        if not access_token_secret:
            missing.append("X_ACCESS_TOKEN_SECRET")

        if missing:
            raise RuntimeError(
                f"Missing environment variables: {', '.join(missing)}"
            )

        import tweepy

        self._client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_key_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

        return "X API"

    def post(self, text: str) -> str:
        """Post a tweet. Returns the tweet ID as a string."""
        if self._client is None:
            raise RuntimeError("Not logged in. Call login() first.")

        response = self._client.create_tweet(text=text)
        tweet_id = response.data["id"]
        return f"https://x.com/i/status/{tweet_id}"
