import json
from app.engine.character.models import PsychologyProfileModel, OceanModel
from app.engine.character.cues import big_five_to_behavior_cues, neuroticism_score
from app.engine.character.mbti_resources import (
    format_persona_block,
    get_persona_excerpt_for_mood,
    load_foundations,
)


def judge_character_context_json(
    profile: PsychologyProfileModel,
    mbti_type: str,
    cognitive_hint: str = "",
) -> str:
    cues = big_five_to_behavior_cues(profile.ocean)
    persona_excerpt = get_persona_excerpt_for_mood(mbti_type)

    data = {
        "name": profile.role.name,
        "name_reading": profile.role.name_reading,
        "role_summary": profile.role.role_summary,
        "ocean": profile.ocean.model_dump(),
        "neuroticism": neuroticism_score(profile.ocean),
        "ocean_notes": profile.ocean_notes,
        "behavior_hints": profile.behavior_hints,
        "big_five_behavior_cues": " ".join(cues),
        "scenario": profile.scenario,
        "relationship": profile.relationship,
        "goals": {
            "primary": profile.drives.mission.primary,
            "secondary": profile.drives.mission.secondary,
            "horizon": profile.drives.horizon,
        },
        "behavior_logic": {
            "framework": "MBTI",
            "engine": "characterengine",
            "type": mbti_type,
            "cognitive_hint": cognitive_hint,
            "persona_excerpt_for_mood": persona_excerpt,
            "playbook_note": "MBTI为辅助标签；气质冲突时以big_five_behavior_cues与role_summary为准",
        },
        "drives": profile.drives.model_dump(),
    }
    return json.dumps(data, ensure_ascii=False)


def build_psychology_system_message(
    profile: PsychologyProfileModel,
    mbti_type: str,
    cognitive_hint: str = "",
    foundations_max_chars: int = 1200,
) -> str:
    cues = big_five_to_behavior_cues(profile.ocean)
    persona_block = format_persona_block(mbti_type)
    foundations = load_foundations()
    if len(foundations) > foundations_max_chars:
        foundations = foundations[:foundations_max_chars] + "\n…（截断）"

    parts = [
        "### 【心理引擎 · 气质骨架（Big Five）】",
        *[f"- {c}" for c in cues],
        "- 冲突策略声明：OCEAN 五维气质骨架为单一真源（SSOT）；MBTI 为可读标签与表达习惯辅助，若与气质指令、角色摘要或 system 总则冲突，以气质骨架与总则为准。",
        "",
        "### 【心理引擎 · 行为逻辑（MBTI 辅助）】",
        f"- 信息加工与表达可参照 MBTI {mbti_type} 与本节《行为规格》",
        f"- 认知提示：{cognitive_hint}" if cognitive_hint else "",
        "",
        persona_block,
        "",
        "### 【MBTI 通用基础（节选）】",
        foundations,
        "",
        "### 【心理引擎 · 目标与需要】",
        f"- 主目标：{profile.drives.mission.primary}",
        f"- 次目标：{profile.drives.mission.secondary}" if profile.drives.mission.secondary else "- 次目标：（未配置）",
        f"- 目标时间尺度：{profile.drives.horizon}",
    ]
    if profile.drives.mission.narrative:
        parts.append(f"- 叙事补充：{profile.drives.mission.narrative}")
    if profile.drives.needs:
        parts.append(f"- 需要层：{json.dumps(profile.drives.needs, ensure_ascii=False)}")

    parts.extend([
        "",
        "### 【心理引擎 · 动态状态注入】",
        "- 用户消息末尾附有 character_state XML，含本轮心情与目标快照。",
        "- 心情指数 0～100（50 为中性）与 valence/arousal 为结构化锚点。",
        "- 请在本轮回复中让人物的目标与需要自然影响动机与措辞；未配置项勿编造具体事实，可保持留白。",
    ])

    return "\n".join(parts)


def build_character_state_context_xml(
    profile: PsychologyProfileModel,
    mood_pct: int,
    mood_label: str,
    valence: float,
    confidence: float,
    mood_judge_enabled: bool = True,
) -> str:
    if not mood_judge_enabled:
        mood_pct = 50
        mood_label = "中性"

    if valence < -0.5:
        valence_token = "negative"
    elif valence < -0.15:
        valence_token = "slightly_negative"
    elif valence < 0.15:
        valence_token = "neutral"
    elif valence < 0.5:
        valence_token = "slightly_positive"
    else:
        valence_token = "positive"

    intensity = abs(valence) * confidence
    if intensity < 0.15:
        arousal = "low"
    elif intensity < 0.45:
        arousal = "medium"
    else:
        arousal = "high"

    return (
        f"<context>\n"
        f"  <module name=\"character_state\">\n"
        f"    <mood mood_pct=\"{mood_pct}\" valence=\"{valence_token}\" arousal=\"{arousal}\">{mood_label}</mood>\n"
        f"    <goals horizon=\"{profile.drives.horizon}\">\n"
        f"      <primary>{profile.drives.mission.primary}</primary>\n"
        f"      <secondary>{profile.drives.mission.secondary or '（未配置）'}</secondary>\n"
        f"    </goals>\n"
        f"  </module>\n"
        f"</context>"
    )


def append_character_state_to_user_content(
    user_text: str,
    profile: PsychologyProfileModel,
    mood_pct: int = 50,
    mood_label: str = "中性",
    valence: float = 0.0,
    confidence: float = 0.0,
    mood_judge_enabled: bool = True,
) -> str:
    xml = build_character_state_context_xml(
        profile=profile,
        mood_pct=mood_pct,
        mood_label=mood_label,
        valence=valence,
        confidence=confidence,
        mood_judge_enabled=mood_judge_enabled,
    )
    return f"{user_text}\n\n{xml}"
