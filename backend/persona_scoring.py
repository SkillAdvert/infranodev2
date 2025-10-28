from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Tuple, cast

PersonaType = Literal["hyperscaler", "colocation", "edge_computing"]
PowerDeveloperPersona = Literal["greenfield", "repower", "stranded"]


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


PERSONA_CAPACITY_RANGES = {
    "edge_computing": {"min": 0.4, "max": 5},
    "colocation": {"min": 5, "max": 30},
    "hyperscaler": {"min": 30, "max": 1000},
}


POWER_DEVELOPER_PERSONAS: Dict[str, Dict[str, float]] = {
    "greenfield": {
        "capacity": 0.15,
        "connection_speed": 0.15,
        "resilience": 0.10,
        "land_planning": 0.25,
        "latency": 0.03,
        "cooling": 0.02,
        "price_sensitivity": 0.20,
    },
    "repower": {
        "capacity": 0.15,
        "connection_speed": 0.20,
        "resilience": 0.12,
        "land_planning": 0.15,
        "latency": 0.05,
        "cooling": 0.03,
        "price_sensitivity": 0.15,
    },
    "stranded": {
        "capacity": 0.05,
        "connection_speed": 0.25,
        "resilience": 0.10,
        "land_planning": 0.05,
        "latency": 0.05,
        "cooling": 0.05,
        "price_sensitivity": 0.25,
    },
}


POWER_DEVELOPER_CAPACITY_RANGES = {
    "greenfield": {"min": 1, "max": 1000},
    "repower": {"min": 1, "max": 1000},
    "stranded": {"min": 1, "max": 1000},
}


PERSONA_CAPACITY_PARAMS = {
    "edge_computing": {"min_mw": 0.4, "ideal_mw": 2.0, "max_mw": 5.0},
    "colocation": {"min_mw": 5.0, "ideal_mw": 15.0, "max_mw": 30.0},
    "hyperscaler": {"min_mw": 30.0, "ideal_mw": 75.0, "max_mw": 200.0},
    "default": {"min_mw": 5.0, "ideal_mw": 50.0, "max_mw": 100.0},
}


INFRASTRUCTURE_SEARCH_RADIUS_KM = {
    "substation": 100.0,
    "transmission": 100.0,
    "fiber": 100.0,
    "ixp": 100.0,
    "water": 100.0,
}


INFRASTRUCTURE_HALF_DISTANCE_KM = {
    "substation": 50.0,
    "transmission": 50.0,
    "fiber": 25.0,
    "ixp": 25.0,
    "water": 25.0,
}


def resolve_power_developer_persona(
    raw_value: Optional[str],
) -> Tuple[PowerDeveloperPersona, str, str]:
    """Normalize the requested persona and flag how it was resolved."""

    requested_value = (raw_value or "").strip()
    normalized_value = requested_value.lower()

    if not normalized_value:
        return "greenfield", requested_value, "defaulted"

    if normalized_value not in POWER_DEVELOPER_PERSONAS:
        return "greenfield", requested_value, "invalid"

    return cast(PowerDeveloperPersona, normalized_value), requested_value, "valid"


for persona_name, weights_dict in POWER_DEVELOPER_PERSONAS.items():
    total_weight = sum(weights_dict.values())
    if not math.isclose(total_weight, 1.0, rel_tol=1e-6):
        print(f"⚠️ WARNING: {persona_name} weights sum to {total_weight}, not 1.0")


def calculate_capacity_component_score(
    capacity_mw: float, persona: Optional[str] = None
) -> float:
    persona_key = persona or "default"
    params = PERSONA_CAPACITY_PARAMS.get(persona_key, PERSONA_CAPACITY_PARAMS["default"])

    minimum = params["min_mw"]
    ideal = params["ideal_mw"]
    maximum = params["max_mw"]

    if capacity_mw <= minimum:
        return 0.0
    if capacity_mw >= maximum:
        return 100.0
    if capacity_mw <= ideal:
        normalized = (capacity_mw - minimum) / (ideal - minimum)
        return max(0.0, min(100.0, float(normalized * 100.0)))

    logistic_argument = capacity_mw - ideal
    score = 100.0 / (1.0 + math.exp(-0.05 * logistic_argument))
    return max(0.0, min(100.0, float(score)))


def calculate_development_stage_score(
    status: str, perspective: str = "demand"
) -> float:
    """Score based on BTM (Behind-the-Meter) intervention timing and planning viability."""

    status_str = str(status).lower().strip()

    STATUS_SCORES = {
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

    if status_str in STATUS_SCORES:
        base_score = STATUS_SCORES[status_str]
    else:
        base_score = 45.0
        for key, score in STATUS_SCORES.items():
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
    if "CCGT" in tech:
        return 100.0
    return 80.0


def calculate_grid_infrastructure_score(proximity_scores: Dict[str, float]) -> float:
    distances = proximity_scores.get("nearest_distances", {})
    substation_distance = distances.get("substation_km")
    transmission_distance = distances.get("transmission_km")

    substation_raw = 0.0
    if substation_distance is not None:
        substation_raw = math.exp(
            -substation_distance / INFRASTRUCTURE_HALF_DISTANCE_KM["substation"]
        )
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
    """Estimate a reasonable capacity factor for the given technology."""

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
    tech_type = project.get("technology_type", "")
    lat = float(project.get("latitude") or 0.0)
    lng = float(project.get("longitude") or 0.0)

    base_lcoe = calculate_lcoe_score(project.get("development_status_short", ""))
    capacity_factor_pct = estimate_capacity_factor(tech_type, lat, project.get("capacity_factor"))
    capacity_factor = capacity_factor_pct / 100.0

    adjusted_lcoe = base_lcoe
    if capacity_factor > 0:
        reference_cf = 0.4
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
        if total_cost_mwh <= user_max_price_mwh:
            savings_pct = (user_max_price_mwh - total_cost_mwh) / user_max_price_mwh
            score = 50 + (savings_pct * 50)
        else:
            overage_pct = (total_cost_mwh - user_max_price_mwh) / user_max_price_mwh
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
    )

    return base_scores


def calculate_persona_weighted_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    persona: PersonaType = "hyperscaler",
    perspective: str = "demand",
    user_max_price_mwh: Optional[float] = None,
    shared_component_scores: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    weights = PERSONA_WEIGHTS[persona]

    component_scores = build_persona_component_scores(
        project,
        proximity_scores,
        persona,
        perspective,
        user_max_price_mwh,
        shared_component_scores,
    )

    weighted_score = (
        component_scores["capacity"] * weights["capacity"]
        + component_scores["connection_speed"] * weights["connection_speed"]
        + component_scores["resilience"] * weights["resilience"]
        + component_scores["land_planning"] * weights["land_planning"]
        + component_scores["latency"] * weights["latency"]
        + component_scores["cooling"] * weights["cooling"]
        + component_scores["price_sensitivity"] * weights["price_sensitivity"]
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
            key: round(value, 1) for key, value in component_scores.items()
        },
        "weighted_contributions": {
            key: round(component_scores[key] * weights.get(key, 0.0), 1)
            for key in component_scores
        },
        "persona": persona,
        "persona_weights": weights,
        "internal_total_score": round(final_internal_score, 1),
        "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
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
                stage_score * custom_weights.get("development_stage", 0.0),
                1,
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
            "water_resources": round(
                water_score * custom_weights.get("water_resources", 0.0),
                1,
            ),
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
                persona,  # type: ignore[arg-type]
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
    projects: List[Dict[str, Any]], persona: PersonaType
) -> List[Dict[str, Any]]:
    capacity_range = PERSONA_CAPACITY_RANGES[persona]
    filtered = []
    for project in projects:
        capacity_mw = project.get("capacity_mw", 0)
        if capacity_range["min"] <= capacity_mw <= capacity_range["max"]:
            filtered.append(project)
    return filtered


def get_color_from_score(score_out_of_100: float) -> str:
    if score_out_of_100 >= 80:
        return "#2ECC71"
    if score_out_of_100 >= 60:
        return "#F1C40F"
    if score_out_of_100 >= 40:
        return "#E67E22"
    return "#E74C3C"


def get_rating_description(score_out_of_100: float) -> str:
    if score_out_of_100 >= 90:
        return "Exceptional fit"
    if score_out_of_100 >= 75:
        return "High potential"
    if score_out_of_100 >= 60:
        return "Moderate potential"
    if score_out_of_100 >= 45:
        return "Needs further due diligence"
    return "High risk"

