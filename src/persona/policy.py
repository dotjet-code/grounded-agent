"""Posting policy configuration.

Loaded from a JSON file. Controls posting frequency, quiet hours,
and platform/LLM defaults.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_POLICY_PATH = Path("data/posting_policy.json")


@dataclass(frozen=True)
class PostingPolicy:
    """Posting behavior configuration."""

    max_daily: int = 4
    cooldown_minutes: int = 180
    quiet_start_hour: int = 23  # UTC
    quiet_end_hour: int = 7     # UTC
    platform: str = "x"
    llm: str = "claude"

    def is_quiet_hours(self, now: datetime | None = None) -> bool:
        """Check if current time falls within quiet hours.

        Quiet hours wrap around midnight:
          quiet_start=23, quiet_end=7 → quiet from 23:00 to 06:59
        """
        if now is None:
            now = datetime.now(timezone.utc)
        hour = now.hour

        if self.quiet_start_hour == self.quiet_end_hour:
            return False  # no quiet hours

        if self.quiet_start_hour > self.quiet_end_hour:
            # Wraps midnight: e.g. 23-7
            return hour >= self.quiet_start_hour or hour < self.quiet_end_hour
        else:
            # Same day: e.g. 1-5
            return self.quiet_start_hour <= hour < self.quiet_end_hour

    @classmethod
    def from_json(cls, path: str | Path = _DEFAULT_POLICY_PATH) -> PostingPolicy:
        """Load policy from a JSON file. Returns defaults if file not found."""
        p = Path(path)
        if not p.exists():
            return cls()
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(
            max_daily=data.get("max_daily", cls.max_daily),
            cooldown_minutes=data.get("cooldown_minutes", cls.cooldown_minutes),
            quiet_start_hour=data.get("quiet_start_hour", cls.quiet_start_hour),
            quiet_end_hour=data.get("quiet_end_hour", cls.quiet_end_hour),
            platform=data.get("platform", cls.platform),
            llm=data.get("llm", cls.llm),
        )
