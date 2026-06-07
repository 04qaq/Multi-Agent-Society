import yaml
from pathlib import Path
from typing import Optional

_RESOURCES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "resources"

_FOUNDATIONS_CACHE: Optional[str] = None
_PERSONAS_CACHE: Optional[dict] = None


def load_foundations() -> str:
    global _FOUNDATIONS_CACHE
    if _FOUNDATIONS_CACHE is not None:
        return _FOUNDATIONS_CACHE
    path = _RESOURCES_DIR / "foundations.md"
    if path.exists():
        _FOUNDATIONS_CACHE = path.read_text(encoding="utf-8")
    else:
        _FOUNDATIONS_CACHE = ""
    return _FOUNDATIONS_CACHE


def load_personas() -> dict:
    global _PERSONAS_CACHE
    if _PERSONAS_CACHE is not None:
        return _PERSONAS_CACHE
    path = _RESOURCES_DIR / "personas.yaml"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _PERSONAS_CACHE = yaml.safe_load(f) or {}
    else:
        _PERSONAS_CACHE = {}
    return _PERSONAS_CACHE


def get_persona(mbti_type: str) -> Optional[dict]:
    personas = load_personas()
    return personas.get(mbti_type.upper())


def format_persona_block(mbti_type: str, max_chars: int = 2800) -> str:
    persona = get_persona(mbti_type)
    if not persona:
        return f"## MBTI 行为规格 · {mbti_type}\n（未配置）"

    lines = [
        f"## MBTI 行为规格 · {mbti_type}",
    ]
    stack = persona.get("stack", "")
    if stack:
        lines.append(f"**功能栈**：{stack}")

    for key, label in [
        ("cognitive", "认知习惯"),
        ("decision", "决策习惯"),
        ("pressure_mood", "压力与心情联动"),
        ("voice", "外显声线"),
    ]:
        val = persona.get(key, "")
        if val:
            lines.append(f"**{label}**：{val}")

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...（截断）"
    return text


def get_persona_excerpt_for_mood(mbti_type: str, max_chars: int = 420) -> str:
    persona = get_persona(mbti_type)
    if not persona:
        return ""

    stack = persona.get("stack", "")
    pressure = persona.get("pressure_mood", "")
    excerpt = f"{stack} {pressure}".strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars] + "…"
    return excerpt
