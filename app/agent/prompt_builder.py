from app.engine.character.models import PsychologyProfileModel
from app.engine.character.mood import MoodResult
from app.engine.character.assemble import (
    build_psychology_system_message,
    append_character_state_to_user_content,
)


class PromptBuilder:
    def __init__(
        self,
        profile: PsychologyProfileModel,
        mbti_type: str,
        cognitive_hint: str = "",
        system_base: str = "",
    ):
        self._profile = profile
        self._mbti_type = mbti_type
        self._cognitive_hint = cognitive_hint
        self._system_base = system_base or f"你是{profile.role.name}。{profile.role.role_summary}"

    def build(
        self,
        history: list[dict],
        user_text: str,
        mood: MoodResult | None = None,
        long_memory_context: str = "",
        shared_world_context: str = "",
        relationship_context: str = "",
        plugin_context: str = "",
    ) -> list[dict]:
        psych_system = build_psychology_system_message(
            profile=self._profile,
            mbti_type=self._mbti_type,
            cognitive_hint=self._cognitive_hint,
        )

        memory_parts = []
        if long_memory_context:
            memory_parts.append(f"### 相关记忆\n{long_memory_context}")
        if shared_world_context:
            memory_parts.append(f"### 世界状态\n{shared_world_context}")
        if relationship_context:
            memory_parts.append(f"### 关系\n{relationship_context}")
        if plugin_context:
            memory_parts.append(f"### 游戏上下文\n{plugin_context}")

        memory_context = "\n\n".join(memory_parts) if memory_parts else "（无额外上下文）"

        if mood is not None:
            augmented_user = append_character_state_to_user_content(
                user_text=user_text,
                profile=self._profile,
                mood_pct=mood.mood_pct,
                mood_label=mood.label,
                valence=mood.valence,
                confidence=mood.confidence,
                mood_judge_enabled=True,
            )
        else:
            augmented_user = append_character_state_to_user_content(
                user_text=user_text,
                profile=self._profile,
                mood_judge_enabled=False,
            )

        messages: list[dict] = [
            {"role": "system", "content": self._system_base},
            {"role": "system", "content": psych_system},
            {"role": "system", "content": f"### 记忆上下文\n{memory_context}"},
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": augmented_user})
        return messages
