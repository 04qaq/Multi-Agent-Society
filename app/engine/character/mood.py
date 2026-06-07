import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MoodResult:
    valence: float
    confidence: float
    label: str
    mood_pct: int


MOOD_JUDGE_SYSTEM_PROMPT = """\
你是「心情分析」模块，只做结构化输出。

根据 CHARACTER_JSON（五维人格、MBTI行为逻辑提示、drives）与 DIALOGUE（对话历史），
推断角色在读完最后一轮用户话之后当下的主观情绪倾向。

规则：
1. valence: [-1, 1]，正=愉快/温暖/期待，负=冷淡/失落/烦躁
2. 结合 ocean、neuroticism、big_five_behavior_cues、goals、persona_excerpt_for_mood
   - 情绪稳定性高 → valence 不轻易极端
   - 神经质高 → 情绪波动可更明显
   - 气质与 MBTI 冲突时以 big_five_behavior_cues 与 role_summary 为准
3. confidence: [0, 1]，信息不足时降低
4. label: 不超过6个汉字的简短心情标签

输出格式：{"valence": <float>, "confidence": <float>, "label": "<string>"}
"""


def _valence_to_mood_pct(valence: float, confidence: float) -> int:
    v_eff = valence * confidence
    return int((v_eff + 1.0) * 50)


class LlmMoodStrategy:
    def __init__(self, llm):
        self._llm = llm

    async def compute(
        self,
        history: list[dict],
        user_text: str,
        character_context_json: str,
        timeout_s: float = 15.0,
    ) -> MoodResult:
        dialogue_lines = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            dialogue_lines.append(f"{role}: {content}")
        dialogue_lines.append(f"user: {user_text}")

        messages = [
            {"role": "system", "content": MOOD_JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"## CHARACTER_JSON\n{character_context_json}\n\n"
                f"## DIALOGUE\n" + "\n".join(dialogue_lines[-20:])
            )},
        ]

        try:
            response = await self._llm.chat_structured(
                messages=messages,
                response_model=None,
                temperature=0.3,
                max_tokens=200,
            )
            data = json.loads(response)
            valence = float(data.get("valence", 0.0))
            confidence = float(data.get("confidence", 0.0))
            label = str(data.get("label", "（未知）"))
        except Exception as e:
            logger.warning(f"Mood judgment failed: {e}, fallback to neutral")
            valence = 0.0
            confidence = 0.0
            label = "（评判失败，已中性处理）"

        mood_pct = _valence_to_mood_pct(valence, confidence)
        return MoodResult(valence=valence, confidence=confidence, label=label, mood_pct=mood_pct)


class StaticMoodStrategy:
    async def compute(
        self,
        history: list[dict],
        user_text: str,
        character_context_json: str,
        timeout_s: float = 15.0,
    ) -> MoodResult:
        return MoodResult(valence=0.0, confidence=0.0, label="中性", mood_pct=50)
