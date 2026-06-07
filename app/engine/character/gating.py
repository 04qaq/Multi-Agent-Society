from dataclasses import dataclass
from app.engine.character.models import OceanModel


@dataclass
class GatingParams:
    beta: float
    relationship_base: float
    threshold_high: float
    threshold_mid: float


MEMORY_STYLE_PRESETS: dict[str, GatingParams] = {
    "sensitive": GatingParams(
        beta=0.6, relationship_base=0.5,
        threshold_high=0.4, threshold_mid=0.2,
    ),
    "balanced": GatingParams(
        beta=0.4, relationship_base=0.5,
        threshold_high=0.6, threshold_mid=0.35,
    ),
    "easy_going": GatingParams(
        beta=0.2, relationship_base=0.5,
        threshold_high=0.75, threshold_mid=0.5,
    ),
}


def compute_gating_params_from_ocean(ocean: OceanModel) -> GatingParams:
    neuroticism = 1.0 - ocean.emotional_stability
    return GatingParams(
        beta=0.3 + neuroticism * 0.4,
        relationship_base=0.3 + ocean.extraversion * 0.2 + ocean.agreeableness * 0.2,
        threshold_high=0.7 - neuroticism * 0.2,
        threshold_mid=0.4 - neuroticism * 0.15,
    )


def compute_gating_params(
    ocean: OceanModel | None = None,
    style: str = "balanced",
    mode: str = "ocean",
    hybrid_weight: float = 0.5,
) -> GatingParams:
    if mode == "ocean" and ocean is not None:
        return compute_gating_params_from_ocean(ocean)
    elif mode == "hybrid" and ocean is not None:
        ocean_params = compute_gating_params_from_ocean(ocean)
        preset = MEMORY_STYLE_PRESETS.get(style, MEMORY_STYLE_PRESETS["balanced"])
        return GatingParams(
            beta=ocean_params.beta * hybrid_weight + preset.beta * (1 - hybrid_weight),
            relationship_base=ocean_params.relationship_base * hybrid_weight + preset.relationship_base * (1 - hybrid_weight),
            threshold_high=ocean_params.threshold_high * hybrid_weight + preset.threshold_high * (1 - hybrid_weight),
            threshold_mid=ocean_params.threshold_mid * hybrid_weight + preset.threshold_mid * (1 - hybrid_weight),
        )
    else:
        return MEMORY_STYLE_PRESETS.get(style, MEMORY_STYLE_PRESETS["balanced"])


def compute_memory_score(
    gating: GatingParams,
    emotional_delta: float = 0.0,
    importance: float = 0.0,
    user_relevance: float = 0.0,
    novelty: float = 0.0,
    relationship_score: float = 0.0,
    conflict_risk: float = 0.0,
    w_emotional: float = 0.28,
    w_importance: float = 0.22,
    w_user_rel: float = 0.14,
    w_novelty: float = 0.18,
    w_relationship: float = 0.12,
    w_conflict: float = 0.18,
) -> float:
    return (
        w_emotional * emotional_delta
        + w_importance * importance
        + w_user_rel * user_relevance
        + w_novelty * novelty
        + w_relationship * relationship_score
        - w_conflict * conflict_risk
    )


def compute_adaptive_weights(ocean: OceanModel) -> dict[str, float]:
    neuroticism = 1.0 - ocean.emotional_stability
    return {
        "w_emotional": 0.28 + neuroticism * 0.2,
        "w_importance": 0.22,
        "w_user_rel": 0.14,
        "w_novelty": 0.18 + ocean.openness * 0.1,
        "w_relationship": 0.12,
        "w_conflict": 0.18 + ocean.agreeableness * 0.1,
    }
