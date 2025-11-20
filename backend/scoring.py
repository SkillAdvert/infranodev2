"""Scoring algorithms for infrastructure projects.

CAVEAT: Contains DC-flavoured constants (e.g. ``PERSONA_WEIGHTS``). This is
acceptable because the functions operate on supplied parameters and the power
workflow can extend the persona dictionaries with its own entries. Keeping
these reusable routines in one place avoids algorithm duplication while
preserving workflow-specific orchestration elsewhere.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Literal, cast


PersonaType = Literal["hyperscaler", "colocation", "edge_computing"]

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

PERSONA_CAPACITY_PARAMS: Dict[str, Dict[str, float]] = {
    "edge_computing": {
        "min_mw": 0.3,
        "ideal_mw": 2.0,
        "max_mw": 5.0,
        "tolerance_factor": 0.7,
    },
    "colocation": {
        "min_mw": 4.0,
        "ideal_mw": 12.0,
        "max_mw": 25.0,
        "tolerance_factor": 0.5,
    },
    "hyperscaler": {
        "min_mw": 20.0,
        "ideal_mw": 50.0,
        "max_mw": 200.0,
        "tolerance_factor": 0.4,
    },
    "default": {
        "min_mw": 5.0,
        "ideal_mw": 50.0,
        "max_mw": 100.0,
        "tolerance_factor": 0.5,
    },
}

INFRASTRUCTURE_HALF_DISTANCE_KM: Dict[str, float] = {
    "substation": 35.0,
    "transmission": 50.0,
    "fiber": 40.0,
    "ixp": 70.0,
    "water": 15.0,
}


def get_color_from_score(score_out_of_100: float) -> str:
    display_score = score_out_of_100 / 10.0
    if display_score >= 9.0:
        return "#00DD00"
    if display_score >= 8.0:
        return "#33FF33"
    if display_score >= 7.0:
        return "#7FFF00"
    if display_score >= 6.0:
        return "#CCFF00"
    if display_score >= 5.0:
        return "#FFFF00"
    if display_score >= 4.0:
        return "#FFCC00"
    if display_score >= 3.0:
        return "#FF9900"
    if display_score >= 2.0:
        return "#FF6600"
    if display_score >= 1.0:
        return "#FF3300"
    return "#CC0000"


def get_rating_description(score_out_of_100: float) -> str:
    display_score = score_out_of_100 / 10.0
    if display_score >= 9.0:
        return "Excellent"
    if display_score >= 8.0:
        return "Very Good"
    if display_score >= 7.0:
        return "Good"
    if display_score >= 6.0:
        return "Above Average"
    if display_score >= 5.0:
        return "Average"
    if display_score >= 4.0:
        return "Below Average"
    if display_score >= 3.0:
        return "Poor"
    if display_score >= 2.0:
        return "Very Poor"
    if display_score >= 1.0:
        return "Bad"
    return "Very Bad"


def calculate_capacity_component_score(
    capacity_mw: float,
    persona: Optional[str] = None,
    user_ideal_mw: Optional[float] = None,
) -> float:
    persona_key = (persona or "default").lower()
    if persona_key == "custom":
        persona_key = "default"

    params = PERSONA_CAPACITY_PARAMS.get(persona_key, PERSONA_CAPACITY_PARAMS["default"])

    ideal = user_ideal_mw if user_ideal_mw is not None else params.get("ideal_mw", 75.0)

    tolerance_factor = params.get("tolerance_factor", 0.5)
    tolerance = ideal * tolerance_factor

    exponent = -((capacity_mw - ideal) ** 2) / (2 * tolerance ** 2)
    score = 100.0 * math.exp(exponent)

    return max(0.0, min(100.0, float(score)))


def calculate_development_stage_score(status: str, perspective: str = "demand") -> float:
    status_str = str(status).lower().strip()

    status_scores = {
        "decommissioned": 0,
        "abandoned": 5,
        "appeal withdrawn": 10,
        "appeal refused": 15,
        "under construction": 20,
        "appeal lodged": 25,
        "application refused": 30,
        "application withdrawn": 35,
        "awaiting construction": 40,
        "no application made": 45,
        "secretary of state granted": 80,
        "planning expired": 70,
        "no application required": 100,
        "application submitted": 100,
        "revised": 90,
        "consented": 70,
        "granted": 70,
        "in planning": 55,
        "operational": 10,
    }

    if status_str in status_scores:
        base_score = status_scores[status_str]
    else:
        base_score = 45.0
        for key, score in status_scores.items():
            if key in status_str:
                base_score = score
                break

    if perspective == "supply":
        pass

    return float(base_score)


def calculate_technology_score(tech_type: str) -> float:
    tech = str(tech_type).lower()
    if "solar" in tech:
        return 80.0
    if "battery" in tech:
        return 80.0
    if "wind" in tech:
        return 60.0
    if "hybrid" in tech:
        return 100.0
    if "ccgt" in tech:
        return 100.0
    return 80.0


def calculate_grid_infrastructure_score(proximity_scores: Dict[str, float]) -> float:
    distances = proximity_scores.get("nearest_distances", {})
    substation_distance = distances.get("substation_km")
    transmission_distance = distances.get("transmission_km")

    substation_raw = 0.0
    if substation_distance is not None:
        substation_raw = math.exp(-substation_distance / INFRASTRUCTURE_HALF_DISTANCE_KM["substation"])
    transmission_raw = 0.0
    if transmission_distance is not None:
        transmission_raw = math.exp(
            -transmission_distance / INFRASTRUCTURE_HALF_DISTANCE_KM["transmission"]
        )

    score = 50.0 * (substation_raw + transmission_raw)
    return max(0.0, min(100.0, float(score)))


def calculate_digital_infrastructure_score(proximity_scores: Dict[str, float]) -> float:
    distances = proximity_scores.get("nearest_distances", {})
    fiber_distance = distances.get("fiber_km")
    ixp_distance = distances.get("ixp_km")

    fiber_raw = 0.0
    if fiber_distance is not None:
        fiber_raw = math.exp(-fiber_distance / INFRASTRUCTURE_HALF_DISTANCE_KM["fiber"])
    ixp_raw = 0.0
    if ixp_distance is not None:
        ixp_raw = math.exp(-ixp_distance / INFRASTRUCTURE_HALF_DISTANCE_KM["ixp"])

    score = 50.0 * (fiber_raw + ixp_raw)
    return max(0.0, min(100.0, float(score)))


def calculate_water_resources_score(proximity_scores: Dict[str, float]) -> float:
    distances = proximity_scores.get("nearest_distances", {})
    water_distance = distances.get("water_km")
    water_raw = 0.0
    if water_distance is not None:
        water_raw = math.exp(-water_distance / INFRASTRUCTURE_HALF_DISTANCE_KM["water"])
    score = 100.0 * water_raw
    return max(0.0, min(100.0, float(score)))


def calculate_lcoe_score(development_status_short: str) -> float:
    status_map = {
        "operational": 10.0,
        "under construction": 50.0,
        "consented": 85.0,
        "in planning": 70.0,
        "site identified": 50.0,
        "concept": 30.0,
        "unknown": 50.0,
    }
    normalized = (development_status_short or "unknown").strip().lower()
    score = status_map.get(normalized, status_map["unknown"])
    return max(0.0, min(100.0, float(score)))


def calculate_tnuos_score(project_lat: float, project_lng: float) -> float:
    lat_normalized = (project_lat - 49.5) / (60.0 - 49.5)
    estimated_tariff = -2.0 + (17.0 * lat_normalized)
    min_tariff = -3.0
    max_tariff = 16.0
    if estimated_tariff <= min_tariff:
        percentile_score = 100.0
    elif estimated_tariff >= max_tariff:
        percentile_score = 0.0
    else:
        normalized_position = (estimated_tariff - min_tariff) / (max_tariff - min_tariff)
        percentile_score = 100.0 * (1.0 - normalized_position)
    return min(100.0, max(0.0, percentile_score))


def estimate_capacity_factor(
    tech_type: str, latitude: float, user_provided: Optional[float] = None
) -> float:
    def clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    if user_provided is not None:
        try:
            return clamp(float(user_provided), 5.0, 95.0)
        except (TypeError, ValueError):
            pass

    tech = str(tech_type).lower()
    lat = float(latitude or 0.0)

    if "solar" in tech:
        base_cf = 12.0 - ((lat - 50.0) / 8.0) * 2.0
        return clamp(base_cf, 9.0, 13.0)
    if "wind" in tech:
        if "offshore" in tech:
            return 45.0
        base_cf = 28.0 + ((lat - 50.0) / 8.0) * 7.0
        return clamp(base_cf, 25.0, 38.0)
    if "battery" in tech or "bess" in tech:
        return 20.0
    if "hydro" in tech:
        return 50.0
    if "gas" in tech or "ccgt" in tech:
        return 70.0
    if "biomass" in tech:
        return 70.0
    if "hybrid" in tech:
        return 50
    return 30.0


def calculate_connection_speed_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
) -> float:
    dev_status_raw = project.get("development_status_short", "")
    dev_status = str(dev_status_raw).lower()

    base_stage_score = calculate_development_stage_score(dev_status)
    stage_min, stage_max = 20.0, 95.0
    if stage_max > stage_min:
        normalized = (base_stage_score - stage_min) / (stage_max - stage_min)
        normalized = max(0.0, min(1.0, normalized))
        stage_score = 15.0 + (normalized * (100.0 - 15.0))
    else:
        stage_score = base_stage_score
    stage_score = max(15.0, min(100.0, stage_score))

    distances = proximity_scores.get("nearest_distances", {})
    substation_km = distances.get("substation_km", 999)
    substation_score = 100.0 * math.exp(-substation_km / 30.0)

    transmission_km = distances.get("transmission_km", 999)
    transmission_score = 100.0 * math.exp(-transmission_km / 50.0)

    final_score = (stage_score * 0.50) + (substation_score * 0.30) + (transmission_score * 0.20)

    return max(0.0, min(100.0, final_score))


def calculate_resilience_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
) -> float:
    distances = proximity_scores.get("nearest_distances", {})

    backup_count = 0

    substation_km = distances.get("substation_km", 999)
    if substation_km < 15:
        backup_count += 4
    elif substation_km < 30:
        backup_count += 3

    transmission_km = distances.get("transmission_km", 999)
    if transmission_km < 30:
        backup_count += 2

    tech_type = str(project.get("technology_type", "")).lower()
    if "battery" in tech_type or "bess" in tech_type:
        backup_count += 1
    elif "hybrid" in tech_type:
        backup_count += 3

    resilience_score = (backup_count / 10.0) * 100.0

    return max(0.0, min(100.0, resilience_score))


def calculate_price_sensitivity_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    user_max_price_mwh: Optional[float] = None,
) -> float:
    tech_type = str(project.get("technology_type", "")).lower()
    lat = project.get("latitude", 0)
    lng = project.get("longitude", 0)

    user_cf = project.get("capacity_factor")
    capacity_factor_pct = estimate_capacity_factor(tech_type, lat, user_cf)
    capacity_factor = capacity_factor_pct / 100.0

    base_lcoe = 60.0
    reference_cf = 0.30

    if "solar" in tech_type:
        base_lcoe = 52.0
        reference_cf = 0.12
    elif "wind" in tech_type:
        if "offshore" in tech_type:
            base_lcoe = 80.0
            reference_cf = 0.40
        else:
            base_lcoe = 60.0
            reference_cf = 0.30
    elif "battery" in tech_type or "bess" in tech_type:
        base_lcoe = 65.0
        reference_cf = 0.20
    elif "hydro" in tech_type:
        base_lcoe = 70.0
        reference_cf = 0.35
    elif "biomass" in tech_type:
        base_lcoe = 85.0
        reference_cf = 0.70
    elif "gas" in tech_type or "ccgt" in tech_type:
        base_lcoe = 70.0
        reference_cf = 0.55
    elif "hybrid" in tech_type:
        reference_cf = 0.25

    adjusted_lcoe = base_lcoe
    if capacity_factor > 0:
        adjusted_lcoe = base_lcoe * (reference_cf / capacity_factor)

    tnuos_percentile = calculate_tnuos_score(lat, lng)

    tnuos_min = -3.0
    tnuos_max = 16.0

    tnuos_tariff = tnuos_min + ((100 - tnuos_percentile) / 100.0) * (tnuos_max - tnuos_min)

    annual_hours = 8760
    capacity_hours = annual_hours * capacity_factor
    tnuos_mwh_impact = (
        (abs(tnuos_tariff) * 1000) / capacity_hours if capacity_hours > 0 else 0.0
    )

    if tnuos_tariff < 0:
        total_cost_mwh = adjusted_lcoe - tnuos_mwh_impact
    else:
        total_cost_mwh = adjusted_lcoe + tnuos_mwh_impact

    if user_max_price_mwh:
        try:
            threshold = float(user_max_price_mwh)
        except (TypeError, ValueError):
            threshold = None
    else:
        threshold = None

    if threshold is not None:
        if total_cost_mwh <= threshold:
            return 100.0
        overage_pct = (total_cost_mwh - threshold) / threshold if threshold else 0.0
        if overage_pct <= 0:
            score = 100.0
        elif overage_pct <= 0.1:
            score = 90 - (overage_pct * 100)
        elif overage_pct <= 0.25:
            score = 70 - (overage_pct * 80)
        else:
            score = 50 * math.exp(-overage_pct * 2)
    else:
        min_expected = 40.0
        max_expected = 100.0

        normalized = (total_cost_mwh - min_expected) / (max_expected - min_expected)
        score = 100 * (1 - min(1.0, max(0.0, normalized)))

    return max(0.0, min(100.0, score))


def _build_shared_persona_component_scores(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    perspective: str = "demand",
    user_max_price_mwh: Optional[float] = None,
) -> Dict[str, float]:
    connection_speed_score = calculate_connection_speed_score(project, proximity_scores)
    resilience_score = calculate_resilience_score(project, proximity_scores)
    land_planning_score = calculate_development_stage_score(
        project.get("development_status_short", ""),
        perspective,
    )
    latency_score = calculate_digital_infrastructure_score(proximity_scores)
    cooling_score = calculate_water_resources_score(proximity_scores)
    price_sensitivity_score = calculate_price_sensitivity_score(
        project,
        proximity_scores,
        user_max_price_mwh,
    )

    return {
        "connection_speed": connection_speed_score,
        "resilience": resilience_score,
        "land_planning": land_planning_score,
        "latency": latency_score,
        "cooling": cooling_score,
        "price_sensitivity": price_sensitivity_score,
    }


def build_persona_component_scores(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    persona: Optional[str] = None,
    perspective: str = "demand",
    user_max_price_mwh: Optional[float] = None,
    user_ideal_mw: Optional[float] = None,
    shared_component_scores: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    base_scores = (
        dict(shared_component_scores)
        if shared_component_scores is not None
        else _build_shared_persona_component_scores(
            project, proximity_scores, perspective, user_max_price_mwh
        )
    )

    base_scores["capacity"] = calculate_capacity_component_score(
        project.get("capacity_mw", 0) or 0,
        persona,
        user_ideal_mw,
    )

    return base_scores


def _normalize_component_scores(component_scores: Dict[str, float]) -> Dict[str, float]:
    normalized: Dict[str, float] = {}
    for key, value in component_scores.items():
        normalized[key] = max(0.0, min(1.0, value / 100.0))
    return normalized


def _get_persona_tuning(persona: PersonaType) -> Dict[str, float]:
    return PERSONA_SCORING_TUNING.get(persona, PERSONA_SCORING_TUNING["default"])


def _resolve_persona_key_for_tuning(persona_label: Optional[str]) -> PersonaType:
    persona_key = (persona_label or "default").lower()
    if persona_key not in PERSONA_SCORING_TUNING:
        persona_key = "default"
    return cast(PersonaType, persona_key)


def _compute_posterior_persona_weights(
    persona: PersonaType,
    base_weights: Dict[str, float],
    normalized_scores: Dict[str, float],
) -> Tuple[Dict[str, float], float]:
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
    targets = PERSONA_TARGET_COMPONENTS.get(persona, PERSONA_TARGET_COMPONENTS["default"])
    alignment = 0.0
    for key, weight in posterior_weights.items():
        target = targets.get(key, 0.75)
        alignment += weight * (1.0 - abs(normalized_scores.get(key, 0.0) - target))
    return max(0.0, min(1.0, alignment))


def _logistic_transform(value: float, midpoint: float, steepness: float) -> float:
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

    persona_for_tuning = _resolve_persona_key_for_tuning(persona)
    return _calculate_weighted_score_with_weights(
        component_scores,
        baseline_weights,
        persona,
        proximity_scores,
        persona_for_tuning,
    )


def calculate_weighted_score_from_components(
    component_scores: Dict[str, float],
    baseline_weights: Dict[str, float],
    persona_label: Optional[str] = None,
    proximity_scores: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Apply persona-style weighting to precomputed component scores.

    This mirrors :func:`calculate_persona_weighted_score` but accepts explicit
    weights, making it suitable for workflows (like power developer) that
    define their own weight schemas while reusing the data center scoring
    pipeline.
    """

    persona_for_tuning = _resolve_persona_key_for_tuning(persona_label)
    return _calculate_weighted_score_with_weights(
        component_scores,
        baseline_weights,
        persona_label or persona_for_tuning,
        proximity_scores or {},
        persona_for_tuning,
    )


def _calculate_weighted_score_with_weights(
    component_scores: Dict[str, float],
    baseline_weights: Dict[str, float],
    persona_label: str,
    proximity_scores: Dict[str, float],
    persona_for_tuning: PersonaType,
) -> Dict[str, Any]:
    normalized_scores = _normalize_component_scores(component_scores)
    posterior_weights, evidence_strength = _compute_posterior_persona_weights(
        persona_for_tuning, baseline_weights, normalized_scores
    )
    target_alignment = _calculate_target_alignment(
        persona_for_tuning, normalized_scores, posterior_weights
    )

    tuning = _get_persona_tuning(persona_for_tuning)
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
        "persona": persona_label,
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


def filter_projects_by_persona_capacity(
    projects: List[Dict[str, Any]],
    persona: PersonaType,
) -> List[Dict[str, Any]]:
    capacity_range = PERSONA_CAPACITY_RANGES[persona]
    filtered = []
    for project in projects:
        capacity_mw = project.get("capacity_mw", 0)
        if capacity_range["min"] <= capacity_mw <= capacity_range["max"]:
            filtered.append(project)
    return filtered


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
    "calculate_weighted_score_from_components",
    "calculate_persona_topsis_score",
    "calculate_custom_weighted_score",
    "calculate_best_customer_match",
    "filter_projects_by_persona_capacity",
]

