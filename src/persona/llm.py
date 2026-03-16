"""LLM adapters for the persona system.

Each adapter conforms to LlmCall = Callable[[str, str], str].
The first argument is the system prompt, the second is the user message.
"""

from __future__ import annotations

import os

from src.persona.core import LlmCall

# Default model for the persona loop (cheap, fast)
_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_DEFAULT_MAX_TOKENS = 1024


def make_claude_llm(
    model: str = _DEFAULT_MODEL,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> LlmCall:
    """Create a Claude LLM callable via the Anthropic SDK.

    Reads ANTHROPIC_API_KEY from the environment.
    Raises RuntimeError if the key is not set.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Get one at https://console.anthropic.com/"
        )

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    def call(system: str, user: str) -> str:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Extract text from the first content block
        return response.content[0].text

    return call
