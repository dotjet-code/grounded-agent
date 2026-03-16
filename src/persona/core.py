"""Persona core: the 'brain' that observes and reflects.

Connects memory storage with an LLM (abstracted as a callable)
to process observations and generate diary entries.

No direct dependency on any specific LLM SDK or SNS client.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable

from src.persona.memory import Memory

# Regex to strip common LLM formatting prefixes:
#   "- VOCAB:", "* VOCAB:", "1. VOCAB:", "**VOCAB:**", "  VOCAB:" etc.
_PREFIX_NOISE = re.compile(r"^[\s\-\*\d\.]+")
_BOLD_MARKERS = re.compile(r"\*\*")

# Type alias for the LLM call function.
# Takes a system prompt and a user message, returns the response text.
LlmCall = Callable[[str, str], str]


class PersonaCore:
    """The persona's brain: observe the world, reflect on it."""

    def __init__(self, memory: Memory, llm_call: LlmCall) -> None:
        self._memory = memory
        self._llm_call = llm_call

    # ------------------------------------------------------------------
    # Context: build the internal state text for LLM prompts
    # ------------------------------------------------------------------

    def context(self) -> str:
        """Build a text summary of current memory state for LLM context."""
        parts: list[str] = []

        # Recent vocabulary
        vocab = self._memory.list_vocabulary(limit=10)
        if vocab:
            vocab_lines = [f"- {v['expression']}: {v['context']}" for v in vocab]
            parts.append("## Recently learned expressions\n" + "\n".join(vocab_lines))

        # Active curiosities
        curiosities = self._memory.list_curiosity(limit=10)
        if curiosities:
            cur_lines = [
                f"- {c['phenomenon']} (seen {c['times_seen']}x, {c['status']})"
                for c in curiosities
            ]
            parts.append("## Things I'm curious about\n" + "\n".join(cur_lines))

        # Latest diary entry
        dates = self._memory.list_diary_dates()
        if dates:
            latest = self._memory.read_diary(dates[-1])
            if latest:
                parts.append(f"## My last diary ({dates[-1]})\n{latest}")

        # Memory counts
        counts = self._memory.phase_counts()
        parts.append(
            f"## Memory size\n"
            f"- Vocabulary: {counts['vocabulary']} entries\n"
            f"- Curiosities: {counts['curiosity']} items\n"
            f"- Diary entries: {counts['diary']} days"
        )

        if not parts:
            return "I have no memories yet. This is my first time observing."

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Observe: process external texts and update memory
    # ------------------------------------------------------------------

    def observe(self, texts: list[str]) -> dict[str, Any]:
        """Process observed texts and extract vocabulary/curiosities.

        Args:
            texts: Raw text inputs (e.g. SNS posts, manual input).

        Returns:
            Dict with keys: 'raw_response', 'vocabulary_added', 'curiosity_added'
        """
        if not texts:
            return {"raw_response": "", "vocabulary_added": 0, "curiosity_added": 0}

        observed_text = "\n---\n".join(texts)

        system = (
            "You are observing the world for the first time.\n"
            "You are not an assistant. You do not solve problems.\n"
            "You are simply watching and noting what catches your attention.\n\n"
            "Current memory state:\n" + self.context()
        )

        user = (
            "Here are some texts I observed today:\n\n"
            f"{observed_text}\n\n"
            "Based on what you see:\n"
            "1. List any expressions or words that caught your attention "
            "(format: VOCAB: <expression> | <why it caught your attention>)\n"
            "2. List any phenomena or patterns you noticed "
            "(format: CURIOSITY: <phenomenon> | <note>)\n"
            "3. If nothing catches your attention, just say so honestly.\n\n"
            "Be selective. Only note things that genuinely interest you."
        )

        response = self._llm_call(system, user)

        vocab_count = 0
        curiosity_count = 0

        for raw_line in response.splitlines():
            # Strip markdown/list formatting: "- ", "* ", "1. ", "**", etc.
            line = _BOLD_MARKERS.sub("", raw_line)
            line = _PREFIX_NOISE.sub("", line).strip()

            if line.upper().startswith("VOCAB:"):
                parts = line[6:].split("|", 1)
                expression = parts[0].strip()
                context = parts[1].strip() if len(parts) > 1 else ""
                if expression:
                    self._memory.add_vocabulary(expression, context=context)
                    vocab_count += 1
            elif line.upper().startswith("CURIOSITY:"):
                parts = line[10:].split("|", 1)
                phenomenon = parts[0].strip()
                notes = parts[1].strip() if len(parts) > 1 else ""
                if phenomenon:
                    self._memory.add_curiosity(phenomenon, notes=notes)
                    curiosity_count += 1

        return {
            "raw_response": response,
            "vocabulary_added": vocab_count,
            "curiosity_added": curiosity_count,
        }

    # ------------------------------------------------------------------
    # Reflect: generate a diary entry
    # ------------------------------------------------------------------

    def reflect(self, date: str | None = None) -> str:
        """Generate and save a diary entry for the given date.

        Args:
            date: Date string (YYYY-MM-DD). Defaults to today (UTC).

        Returns:
            The diary text that was written.
        """
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        system = (
            "You are writing your daily diary.\n"
            "You are not an assistant. You are a new presence learning to see the world.\n"
            "Write in first person. Be short, honest, and specific.\n"
            "Do not be clever or funny. Just note what you noticed and what you're "
            "still thinking about.\n\n"
            "Current memory state:\n" + self.context()
        )

        user = (
            f"Write your diary entry for {date}.\n"
            "Include:\n"
            "- What you noticed today\n"
            "- What you're still curious about\n"
            "- Anything that confused you\n"
            "- Anything that surprised you\n"
            "Keep it short. A few lines is enough."
        )

        diary_text = self._llm_call(system, user)
        self._memory.write_diary(date, diary_text)
        return diary_text
