from dataclasses import dataclass
from app.engine.character.models import OceanModel
from app.engine.character.mood import MoodResult


@dataclass
class MessageContext:
    agent_id: str
    persona: str
    ocean: OceanModel
    mood: MoodResult
    recent_self_count: int
    total_messages: int
    is_mentioned: bool = False
    time_since_last_reply: float = 60.0


def compute_reply_probability(context: MessageContext) -> float:
    base_prob = 0.5

    extraversion = context.ocean.extraversion
    base_prob += (extraversion - 0.5) * 0.3

    if context.mood.mood_pct > 70:
        base_prob += 0.15
    elif context.mood.mood_pct < 30:
        base_prob -= 0.15

    if context.is_mentioned:
        base_prob += 0.35

    base_prob -= context.recent_self_count * 0.1

    if context.total_messages == 0:
        base_prob += 0.2

    return max(0.05, min(0.95, base_prob))
