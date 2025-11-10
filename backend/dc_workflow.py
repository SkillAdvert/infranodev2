from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

# Import shared scoring algorithms
from backend.scoring.algorithms import (
    INFRASTRUCTURE_HALF_DISTANCE_KM,
    PERSONA_CAPACITY_PARAMS,
    PersonaType,
    build_persona_component_scores,
    calculate_capacity_component_score,
    calculate_connection_speed_score,
    calculate_development_stage_score,
    calculate_digital_infrastructure_score,
    calculate_grid_infrastructure_score,
    calculate_lcoe_score,
    calculate_resilience_score,
    calculate_technology_score,
    calculate_tnuos_score,
    calculate_water_resources_score,
    estimate_capacity_factor,
    filter_projects_by_persona_capacity,
    get_color_from_score,
    get_rating_description,
    calculate_price_sensitivity_score,
    _build_shared_persona_component_scores,
)

# DC-Specific persona configurations
PERSONA_WEIGHTS: Dict[str, Dict[str, float]] = {
    "hyperscaler": {
        "capacity": 0.244,
        "connection_speed": 0.167,
        "resilience": 0.133,
        "land_planning": 0.2,
        "latency": 0.056,
        "cooling": 0.144,
        "price_sensitivity": 0.056,
    },
    "colocation": {
        "capacity": 0.141,
        "connection_speed": 0.163,
        "resilience": 0.196,
        "land_planning": 0.163,
        "latency": 0.217,
        "cooling": 0.087,
        "price_sensitivity": 0.033,
    },
    "edge_computing": {
        "capacity": 0.097,
        "connection_speed": 0.129,
        "resilience": 0.108,
        "land_planning": 0.28,
        "latency": 0.247,
        "cooling": 0.054,
        "price_sensitivity": 0.086,
    },
}

PERSONA_TARGET_COMPONENTS: Dict[str, Dict[str, float]] = {
    "hyperscaler": {
        "capacity": 0.92,
        "connection_speed": 0.78,
        "resilience": 0.82,
        "land_planning": 0.8,
        "latency": 0.65,
        "cooling": 0.88,
        "price_sensitivity": 0.55,
    },
    "colocation": {
        "capacity": 0.7,
        "connection_speed": 0.82,
        "resilience": 0.86,
        "land_planning": 0.78,
        "latency": 0.9,
        "cooling": 0.68,
        "price_sensitivity": 0.6,
    },
    "edge_computing": {
        "capacity": 0.55,
        "connection_speed": 0.75,
        "resilience": 0.7,
        "land_planning": 0.9,
        "latency": 0.92,
        "cooling": 0.5,
        "price_sensitivity": 0.68,
    },
    "default": {
        "capacity": 0.75,
        "connection_speed": 0.75,
        "resilience": 0.75,
        "land_planning": 0.75,
        "latency": 0.75,
        "cooling": 0.75,
        "price_sensitivity": 0.75,
    },
}

PERSONA_SCORING_TUNING: Dict[str, Dict[str, float]] = {
    "hyperscaler": {
        "alpha": 1.0,
        "beta": 0.0,
        "evidence_floor": 1e-9,
        "logistic_midpoint": 0.5,
        "logistic_steepness": 4,
        "evidence_shift": 0.2,
        "sum_weight": 1.0,
        "product_weight": 0.0,
        "alignment_weight": 0.0,
    },
    "colocation": {
        "alpha": 1.0,
        "beta": 0.0,
        "evidence_floor": 1e-9,
        "logistic_midpoint": 0.5,
        "logistic_steepness": 4,
        "evidence_shift": 0.2,
        "sum_weight": 1.0,
        "product_weight": 0.0,
        "alignment_weight": 0.0,
    },
    "edge_computing": {
        "alpha": 1.0,
        "beta": 0.0,
        "evidence_floor": 1e-9,
        "logistic_midpoint": 0.5,
        "logistic_steepness": 4,
        "evidence_shift": 0.2,
        "sum_weight": 1.0,
        "product_weight": 0.0,
        "alignment_weight": 0.0,
    },
    "default": {
        "alpha": 1.0,
        "beta": 0.0,
        "evidence_floor": 1e-9,
        "logistic_midpoint": 0.5,
        "logistic_steepness": 4,
        "evidence_shift": 0.2,
        "sum_weight": 1.0,
        "product_weight": 0.0,
        "alignment_weight": 0.0,
    },
}

PERSONA_CAPACITY_RANGES: Dict[str, Dict[str, float]] = {
    "edge_computing": {"min": 0.4, "max": 5},
    "colocation": {"min": 5, "max": 30},
    "hyperscaler": {"min": 30, "max": 250},
}


# ============================================================================
# DC-SPECIFIC SCORING FUNCTIONS
# ============================================================================


def _normalize_component_scores(component_scores: Dict[str, float]) -> Dict[str, float]:
    """Normalize component scores from 0-100 range to 0-1 range."""
    normalized: Dict[str, float] = {}
    for key, value in component_scores.items():
        normalized[key] = max(0.0, min(1.0, value / 100.0))
    return normalized


def _get_persona_tuning(persona: PersonaType) -> Dict[str, float]:
    """Get tuning parameters for a given persona."""
    return PERSONA_SCORING_TUNING.get(persona, PERSONA_SCORING_TUNING["default"])


def _compute_posterior_persona_weights(
    persona: PersonaType,
    base_weights: Dict[str, float],
    normalized_scores: Dict[str, float],
) -> Tuple[Dict[str, float], float]:
    """
    Compute posterior weights using Bayesian-style evidence adjustment.

    Returns:
        Tuple of (posterior_weights, evidence_strength)
    """
    tuning = _get_persona_tuning(persona)
    alpha = tuning["alpha"]
    beta = tuning["beta"]
    evidence_floor = tuning["evidence_floor"]

    posterior: Dict[str, float] = {}
    for key, weight in base_weights.items():
        evidence = max(normalized_scores.get(key, 0.0), evidence_floor)
        posterior[key] = (weight ** alpha) * (evidence ** beta)

    total = sum(posterior.values()) or 1e-9
    for key in posterior:
        posterior[key] /= total

    evidence_strength = sum(
        posterior[key] * normalized_scores.get(key, 0.0) for key in posterior
    )
    return posterior, evidence_strength


def _calculate_target_alignment(
    persona: PersonaType,
    normalized_scores: Dict[str, float],
    posterior_weights: Dict[str, float],
) -> float:
    """Calculate how well scores align with persona targets."""
    targets = PERSONA_TARGET_COMPONENTS.get(persona, PERSONA_TARGET_COMPONENTS["default"])
    alignment = 0.0
    for key, weight in posterior_weights.items():
        target = targets.get(key, 0.75)
        alignment += weight * (1.0 - abs(normalized_scores.get(key, 0.0) - target))
    return max(0.0, min(1.0, alignment))


def _logistic_transform(value: float, midpoint: float, steepness: float) -> float:
    """Apply logistic transformation to smooth score distribution."""
    return 1.0 / (1.0 + math.exp(-steepness * (value - midpoint)))


def calculate_persona_weighted_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    persona: PersonaType = "hyperscaler",
    perspective: str = "demand",
    user_max_price_mwh: Optional[float] = None,
    user_ideal_mw: Optional[float] = None,
    shared_component_scores: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Calculate persona-weighted score using Bayesian evidence fusion.

    This is the main DC workflow scoring function that combines:
    - Component scores (capacity, connection_speed, resilience, etc.)
    - Persona-specific weights
    - Bayesian posterior adjustment
    - Logistic transformation for final score
    """
    baseline_weights = PERSONA_WEIGHTS[persona]

    component_scores = build_persona_component_scores(
        project,
        proximity_scores,
        persona,
        perspective,
        user_max_price_mwh,
        user_ideal_mw,
        shared_component_scores,
    )

    normalized_scores = _normalize_component_scores(component_scores)
    posterior_weights, evidence_strength = _compute_posterior_persona_weights(
        persona, baseline_weights, normalized_scores
    )
    target_alignment = _calculate_target_alignment(
        persona, normalized_scores, posterior_weights
    )

    tuning = _get_persona_tuning(persona)
    weighted_sum = sum(
        normalized_scores[key] * posterior_weights.get(key, 0.0)
        for key in normalized_scores
    )
    weighted_product = math.exp(
        sum(
            posterior_weights.get(key, 0.0)
            * math.log(max(normalized_scores.get(key, 0.0), 1e-9))
            for key in normalized_scores
        )
    )

    fusion_score = (
        tuning["sum_weight"] * weighted_sum
        + tuning["product_weight"] * weighted_product
        + tuning["alignment_weight"] * target_alignment
    )

    evidence_adjustment = (
        evidence_strength - tuning["logistic_midpoint"]
    ) * tuning["evidence_shift"]
    effective_midpoint = tuning["logistic_midpoint"] - evidence_adjustment
    logistic_value = _logistic_transform(
        max(0.0, min(1.0, fusion_score)),
        max(0.05, min(0.95, effective_midpoint)),
        tuning["logistic_steepness"],
    )

    final_internal_score = max(0.0, min(100.0, logistic_value * 100.0))
    display_rating = final_internal_score / 10.0
    color = get_color_from_score(final_internal_score)
    description = get_rating_description(final_internal_score)

    weighted_contributions = {
        key: round(component_scores[key] * posterior_weights.get(key, 0.0), 1)
        for key in component_scores
    }

    return {
        "investment_rating": round(display_rating, 1),
        "rating_description": description,
        "color_code": color,
        "component_scores": {
            key: round(value, 1) for key, value in component_scores.items()
        },
        "weighted_contributions": weighted_contributions,
        "persona": persona,
        "persona_weights": baseline_weights,
        "posterior_persona_weights": {
            key: round(value, 4) for key, value in posterior_weights.items()
        },
        "internal_total_score": round(final_internal_score, 1),
        "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
        "scoring_metadata": {
            "normalized_scores": normalized_scores,
            "weighted_sum": weighted_sum,
            "weighted_product": weighted_product,
            "target_alignment": target_alignment,
            "evidence_strength": evidence_strength,
            "fusion_score": fusion_score,
            "effective_midpoint": effective_midpoint,
        },
    }


def calculate_persona_topsis_score(
    component_scores: Sequence[Dict[str, float]],
    weights: Dict[str, float],
) -> Dict[str, Any]:
    """
    Calculate TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution) scores.

    TOPSIS is a multi-criteria decision analysis method that ranks alternatives based on
    their distance to an ideal solution and anti-ideal solution.
    """
    if not component_scores:
        return {
            "scores": [],
            "ideal_solution": {},
            "anti_ideal_solution": {},
        }

    component_keys = list(component_scores[0].keys())
    denominators: Dict[str, float] = {}
    for key in component_keys:
        sum_squares = sum((scores.get(key, 0.0) or 0.0) ** 2 for scores in component_scores)
        denominators[key] = math.sqrt(sum_squares) or 1e-9

    weighted_vectors: List[Dict[str, Dict[str, float]]] = []
    for scores in component_scores:
        normalized: Dict[str, float] = {}
        weighted: Dict[str, float] = {}
        for key in component_keys:
            raw_value = scores.get(key, 0.0) or 0.0
            denominator = denominators[key]
            normalized_value = raw_value / denominator if denominator else 0.0
            weight = weights.get(key, 0.0)
            weighted_value = normalized_value * weight
            normalized[key] = normalized_value
            weighted[key] = weighted_value
        weighted_vectors.append(
            {
                "normalized_scores": normalized,
                "weighted_normalized_scores": weighted,
            }
        )

    ideal_solution: Dict[str, float] = {}
    anti_ideal_solution: Dict[str, float] = {}
    for key in component_keys:
        values = [vector["weighted_normalized_scores"][key] for vector in weighted_vectors]
        ideal_solution[key] = max(values)
        anti_ideal_solution[key] = min(values)

    results: List[Dict[str, Any]] = []
    for vector in weighted_vectors:
        weighted = vector["weighted_normalized_scores"]
        distance_to_ideal = math.sqrt(
            sum((weighted[key] - ideal_solution[key]) ** 2 for key in component_keys)
        )
        distance_to_anti_ideal = math.sqrt(
            sum((weighted[key] - anti_ideal_solution[key]) ** 2 for key in component_keys)
        )
        closeness = 0.0
        denominator = distance_to_ideal + distance_to_anti_ideal
        if denominator > 0:
            closeness = distance_to_anti_ideal / denominator
        elif distance_to_ideal == 0 and distance_to_anti_ideal == 0:
            closeness = 1.0
        results.append(
            {
                "normalized_scores": vector["normalized_scores"],
                "weighted_normalized_scores": weighted,
                "distance_to_ideal": distance_to_ideal,
                "distance_to_anti_ideal": distance_to_anti_ideal,
                "closeness_coefficient": closeness,
            }
        )

    return {
        "scores": results,
        "ideal_solution": ideal_solution,
        "anti_ideal_solution": anti_ideal_solution,
    }


def calculate_custom_weighted_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    custom_weights: Dict[str, float],
) -> Dict[str, Any]:
    """
    Calculate score using custom user-defined weights.

    This bypasses persona presets and allows full customization of component weights.
    """
    capacity_score = calculate_capacity_component_score(project.get("capacity_mw", 0) or 0)
    stage_score = calculate_development_stage_score(project.get("development_status_short", ""))
    tech_score = calculate_technology_score(project.get("technology_type", ""))
    grid_score = calculate_grid_infrastructure_score(proximity_scores)
    digital_score = calculate_digital_infrastructure_score(proximity_scores)
    water_score = calculate_water_resources_score(proximity_scores)
    lcoe_score = calculate_lcoe_score(project.get("development_status_short", ""))
    tnuos_score = calculate_tnuos_score(project.get("latitude", 0), project.get("longitude", 0))

    weighted_score = (
        capacity_score * custom_weights.get("capacity", 0.0)
        + stage_score * custom_weights.get("development_stage", 0.0)
        + tech_score * custom_weights.get("technology", 0.0)
        + grid_score * custom_weights.get("grid_infrastructure", 0.0)
        + digital_score * custom_weights.get("digital_infrastructure", 0.0)
        + water_score * custom_weights.get("water_resources", 0.0)
        + lcoe_score * custom_weights.get("lcoe_resource_quality", 0.0)
        + tnuos_score * custom_weights.get("tnuos_transmission_costs", 0.0)
    )

    final_internal_score = max(0.0, min(100.0, weighted_score))
    display_rating = final_internal_score / 10.0
    color = get_color_from_score(final_internal_score)
    description = get_rating_description(final_internal_score)

    return {
        "investment_rating": round(display_rating, 1),
        "rating_description": description,
        "color_code": color,
        "component_scores": {
            "capacity": round(capacity_score, 1),
            "development_stage": round(stage_score, 1),
            "technology": round(tech_score, 1),
            "grid_infrastructure": round(grid_score, 1),
            "digital_infrastructure": round(digital_score, 1),
            "water_resources": round(water_score, 1),
            "lcoe_resource_quality": round(lcoe_score, 1),
        },
        "weighted_contributions": {
            "capacity": round(capacity_score * custom_weights.get("capacity", 0.0), 1),
            "development_stage": round(
                stage_score * custom_weights.get("development_stage", 0.0), 1
            ),
            "technology": round(tech_score * custom_weights.get("technology", 0.0), 1),
            "grid_infrastructure": round(
                grid_score * custom_weights.get("grid_infrastructure", 0.0),
                1,
            ),
            "digital_infrastructure": round(
                digital_score * custom_weights.get("digital_infrastructure", 0.0),
                1,
            ),
            "water_resources": round(water_score * custom_weights.get("water_resources", 0.0), 1),
            "lcoe_resource_quality": round(
                lcoe_score * custom_weights.get("lcoe_resource_quality", 0.0),
                1,
            ),
        },
        "persona": "custom",
        "persona_weights": custom_weights,
        "internal_total_score": round(final_internal_score, 1),
        "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
    }


def calculate_best_customer_match(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
) -> Dict[str, Any]:
    """
    Determine which data center persona best matches a project.

    Scores the project against all personas and returns the best match.
    """
    customer_scores: Dict[str, float] = {}
    shared_scores = _build_shared_persona_component_scores(project, proximity_scores)
    for persona in ["hyperscaler", "colocation", "edge_computing"]:
        capacity_mw = project.get("capacity_mw", 0)
        capacity_range = PERSONA_CAPACITY_RANGES[persona]
        if capacity_range["min"] <= capacity_mw <= capacity_range["max"]:
            scoring_result = calculate_persona_weighted_score(
                project,
                proximity_scores,
                persona,
                "demand",
                None,
                None,
                shared_component_scores=shared_scores,
            )
            customer_scores[persona] = scoring_result["investment_rating"]
        else:
            customer_scores[persona] = 2.0

    best_customer = max(customer_scores.keys(), key=lambda key: customer_scores[key])
    best_score = customer_scores[best_customer]

    return {
        "best_customer_match": best_customer,
        "customer_match_scores": customer_scores,
        "best_match_score": round(best_score, 1),
        "capacity_mw": project.get("capacity_mw", 0),
        "suitable_customers": [
            persona for persona, score in customer_scores.items() if score >= 6.0
        ],
    }


__all__ = [
    "PersonaType",
    "PERSONA_WEIGHTS",
    "PERSONA_TARGET_COMPONENTS",
    "PERSONA_SCORING_TUNING",
    "PERSONA_CAPACITY_RANGES",
    "PERSONA_CAPACITY_PARAMS",
    "INFRASTRUCTURE_HALF_DISTANCE_KM",
    "get_color_from_score",
    "get_rating_description",
    "calculate_capacity_component_score",
    "calculate_development_stage_score",
    "calculate_technology_score",
    "calculate_grid_infrastructure_score",
    "calculate_digital_infrastructure_score",
    "calculate_water_resources_score",
    "calculate_lcoe_score",
    "calculate_tnuos_score",
    "estimate_capacity_factor",
    "calculate_connection_speed_score",
    "calculate_resilience_score",
    "calculate_price_sensitivity_score",
    "build_persona_component_scores",
    "calculate_persona_weighted_score",
    "calculate_persona_topsis_score",
    "calculate_custom_weighted_score",
    "calculate_best_customer_match",
    "filter_projects_by_persona_capacity",
]
