"""Internal state model for the persona system.

Pure read-only layer over Memory. No LLM, no network.
Provides structured access to the persona's current phase,
recent interests, and a summary suitable for system prompt injection.
"""

from __future__ import annotations

from src.persona.memory import Memory

# Phase thresholds from docs/persona/system_prompt_phase0.md
_PHASE_1_VOCAB = 50
_PHASE_1_CURIOSITY = 20


class PersonaState:
    """Read-only view of the persona's internal state."""

    def __init__(self, memory: Memory) -> None:
        self._memory = memory

    def current_phase(self) -> int:
        """Determine current phase from memory volume.

        Phase 0: initial blank state
        Phase 1: vocabulary > 50 AND curiosity > 20

        Phase 2+ requires trial_log and naming_dictionary tables
        which are not yet implemented. Returns 1 as max for now.
        """
        counts = self._memory.phase_counts()
        if (
            counts["vocabulary"] >= _PHASE_1_VOCAB
            and counts["curiosity"] >= _PHASE_1_CURIOSITY
        ):
            return 1
        return 0

    def recent_vocabulary(self, limit: int = 10) -> list[dict]:
        """Return the most recently learned expressions."""
        return self._memory.list_vocabulary(limit=limit)

    def recent_interests(self, limit: int = 10) -> list[dict]:
        """Return the most active curiosity items."""
        return self._memory.list_curiosity(limit=limit)

    def diary_count(self) -> int:
        """Return total number of diary entries."""
        return len(self._memory.list_diary_dates())

    def latest_diary(self) -> tuple[str, str] | None:
        """Return (date, content) of the most recent diary entry, or None."""
        dates = self._memory.list_diary_dates()
        if not dates:
            return None
        date = dates[-1]
        content = self._memory.read_diary(date)
        if content is None:
            return None
        return (date, content)

    def summary(self) -> str:
        """Build a structured text summary for system prompt injection.

        This is the single point where internal state becomes text
        that the LLM can read. PersonaCore should use this instead
        of assembling context manually.
        """
        lines: list[str] = []

        # Phase
        phase = self.current_phase()
        lines.append(f"## Current phase: {phase}")

        # Vocabulary
        vocab = self.recent_vocabulary(limit=10)
        if vocab:
            lines.append("")
            lines.append("## Recently learned expressions")
            for v in vocab:
                context_part = f": {v['context']}" if v["context"] else ""
                lines.append(f"- {v['expression']}{context_part}")

        # Curiosities
        interests = self.recent_interests(limit=10)
        if interests:
            lines.append("")
            lines.append("## Things I'm curious about")
            for c in interests:
                lines.append(
                    f"- {c['phenomenon']} (seen {c['times_seen']}x, {c['status']})"
                )

        # Latest diary
        diary = self.latest_diary()
        if diary:
            date, content = diary
            lines.append("")
            lines.append(f"## My last diary ({date})")
            lines.append(content)

        # Counts
        counts = self._memory.phase_counts()
        lines.append("")
        lines.append("## Memory size")
        lines.append(f"- Vocabulary: {counts['vocabulary']} entries")
        lines.append(f"- Curiosities: {counts['curiosity']} items")
        lines.append(f"- Diary entries: {counts['diary']} days")

        return "\n".join(lines)
