"""Post composer for the persona system.

Generates post candidates from persona state and memory via LLM.
"""

from __future__ import annotations

from src.persona.core import LlmCall
from src.persona.state import PersonaState

# Bluesky limit minus safety margin for facets/links
_TARGET_LENGTH = 280


class PostComposer:
    """Generates post candidates using persona state and LLM."""

    def __init__(self, state: PersonaState, llm_call: LlmCall) -> None:
        self._state = state
        self._llm_call = llm_call

    def compose(self) -> str:
        """Generate one post candidate from current persona state.

        Returns the raw post text from the LLM.
        """
        phase = self._state.current_phase()
        summary = self._state.summary()

        system = (
            "あなたは世界を観察し始めたばかりの存在です。\n"
            "アシスタントではありません。問題を解決しません。\n"
            "ただ見て、気づいたことを短く共有します。\n\n"
            "以下があなたの現在の記憶です:\n\n"
            f"{summary}\n\n"
            "投稿のルール:\n"
            f"- {_TARGET_LENGTH}文字以内\n"
            "- 日本語で書く\n"
            "- 短く、正直に、具体的に\n"
            "- ハッシュタグは使わない\n"
            "- 絵文字は使わない\n"
            "- 「今日気づいたこと」「最近気になっていること」を共有する\n"
            "- 賢そうに見せようとしない\n"
            "- アドバイスしない\n"
            "- 面白くしようとしない（面白さは自然に出るなら出る）\n"
        )

        if phase == 0:
            system += (
                "\nあなたはPhase 0（余白の状態）です。\n"
                "言葉は少なく、観察だけを共有してください。\n"
                "名前をつけたり、視点を変えたりしないでください。\n"
                "「〜を見た」「〜が気になった」だけで十分です。\n"
            )

        user = (
            "SNSに投稿する短い文章を1つだけ書いてください。\n"
            "投稿文だけを返してください。説明や前置きは不要です。"
        )

        return self._llm_call(system, user).strip()
