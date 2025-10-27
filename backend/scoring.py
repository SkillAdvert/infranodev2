from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, cast

from backend.config import (
    PERSONA_CAPACITY_PARAMS,
    PERSONA_CAPACITY_RANGES,
    PERSONA_WEIGHTS,
    POWER_DEVELOPER_CAPACITY_RANGES,
    POWER_DEVELOPER_PERSONAS,
    PersonaType,
    PowerDeveloperPersona,
)
from backend.tnuos import (
    calculate_tnuos_score,
    calculate_tnuos_score_from_tariff,
    find_tnuos_zone,
)
from backend.infrastructure import INFRASTRUCTURE_HALF_DISTANCE_KM


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


async def enrich_and_rescore_top_25_with_tnuos(
    features: List[Dict[str, Any]],
    persona: Optional[PersonaType] = None,
) -> List[Dict[str, Any]]:
    """Enrich top 25 projects with TNUoS data and adjust scores."""

    if not features:
        return features

    features_sorted = sorted(
        features,
        key=lambda feature: feature.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    top_25 = features_sorted[:25]
    remaining = features_sorted[25:]

    print("📊 Enriching top 25 projects with TNUoS zones...")

    enriched_count = 0

    for feature in top_25:
        properties = feature.setdefault("properties", {})

        try:
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            if len(coordinates) < 2:
                properties["tnuos_enriched"] = False
                continue

            longitude, latitude = coordinates[0], coordinates[1]
            zone = find_tnuos_zone(latitude, longitude)

            if not zone:
                properties["tnuos_enriched"] = False
                continue

            properties["tnuos_zone_id"] = zone["zone_id"]
            properties["tnuos_zone_name"] = zone["zone_name"]
            tariff_value = zone["generation_tariff_pounds_per_kw"]
            properties["tnuos_tariff_pounds_per_kw"] = tariff_value

            tnuos_score = calculate_tnuos_score_from_tariff(tariff_value)
            properties["tnuos_score"] = round(tnuos_score, 1)

            old_rating = float(properties.get("investment_rating", 0.0))
            component_scores = dict(properties.get("component_scores") or {})
            component_scores["tnuos_transmission_costs"] = tnuos_score

            weights = dict(
                PERSONA_WEIGHTS.get(persona or "hyperscaler", PERSONA_WEIGHTS["hyperscaler"])
            )
            if "tnuos_transmission_costs" not in weights:
                fallback_weight = 0.1
                existing_total = sum(weights.values()) or 1.0
                weights = {
                    key: (value / existing_total) * (1.0 - fallback_weight)
                    for key, value in weights.items()
                }
                weights["tnuos_transmission_costs"] = fallback_weight

            total_weight = sum(weights.values()) or 1.0
            if not math.isclose(total_weight, 1.0, rel_tol=1e-6):
                weights = {key: value / total_weight for key, value in weights.items()}

            weighted_score = sum(
                (component_scores.get(key, 0.0) or 0.0) * weight
                for key, weight in weights.items()
            )

            weighted_score = max(0.0, min(100.0, weighted_score))
            new_rating = round(weighted_score / 10.0, 1)

            properties["component_scores"] = {
                key: round(value, 1) for key, value in component_scores.items()
            }

            weighted_contributions = dict(properties.get("weighted_contributions") or {})
            weighted_contributions = {
                key: round((component_scores.get(key, 0.0) or 0.0) * weights.get(key, 0.0), 1)
                for key in component_scores
            }

            properties["weighted_contributions"] = weighted_contributions
            properties["investment_rating"] = new_rating
            properties["internal_total_score"] = round(weighted_score, 1)
            properties["tnuos_enriched"] = True
            properties["rating_change"] = round(new_rating - old_rating, 1)

            if abs(new_rating - old_rating) > 0.2:
                site_name = properties.get("site_name", "Project")
                print(
                    f"  • {site_name}: {old_rating:.1f} → {new_rating:.1f} ({zone['zone_name']})"
                )

            enriched_count += 1
        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"⚠️  Error processing project: {exc}")
            properties["tnuos_enriched"] = False

    print(f"✓ Enriched {enriched_count}/{len(top_25)} projects")

    for feature in remaining:
        feature.setdefault("properties", {})["tnuos_enriched"] = False

    resorted_top_25 = sorted(
        top_25,
        key=lambda feature: feature.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    return resorted_top_25 + remaining


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


def calculate_capacity_component_score(capacity_mw: float, persona: Optional[str] = None) -> float:
    persona_key = (persona or "default").lower()
    if persona_key == "custom":
        persona_key = "default"
    params = PERSONA_CAPACITY_PARAMS.get(persona_key, PERSONA_CAPACITY_PARAMS["default"])
    ideal = params.get("ideal_mw", 75.0)
    logistic_argument = capacity_mw - ideal
    score = 100.0 / (1.0 + math.exp(-0.05 * logistic_argument))
    return max(0.0, min(100.0, float(score)))


def calculate_development_stage_score(status: str, perspective: str = "demand") -> float:
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
        return float(base_score)

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
        substation_raw = math.exp(-substation_distance / INFRASTRUCTURE_HALF_DISTANCE_KM["substation"])
    transmission_raw = 0.0
    if transmission_distance is not None:
        transmission_raw = math.exp(-transmission_distance / INFRASTRUCTURE_HALF_DISTANCE_KM["transmission"])

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
    proximity_scores: Dict[str, float]
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
    proximity_scores: Dict[str, float]
) -> float:
    distances = proximity_scores.get("nearest_distances", {})

    backup_count = 0

    substation_km = distances.get("substation_km", 999)
    if substation_km < 15:
        backup_count += 4
    elif substation_km < 30:
        backup_count += 3
    elif substation_km < 50:
        backup_count += 2
    elif substation_km < 75:
        backup_count += 1

    transmission_km = distances.get("transmission_km", 999)
    if transmission_km < 20:
        backup_count += 3
    elif transmission_km < 40:
        backup_count += 2
    elif transmission_km < 60:
        backup_count += 1

    fiber_km = distances.get("fiber_km", 999)
    if fiber_km < 10:
        backup_count += 2
    elif fiber_km < 25:
        backup_count += 1

    ixp_km = distances.get("ixp_km", 999)
    if ixp_km < 50:
        backup_count += 2
    elif ixp_km < 100:
        backup_count += 1

    tech_type = str(project.get("technology_type", "")).lower()
    if "battery" in tech_type or "storage" in tech_type:
        backup_count += 2
    if "gas" in tech_type or "diesel" in tech_type:
        backup_count += 1

    if backup_count <= 1:
        return 25.0
    if backup_count == 2:
        return 35.0
    if backup_count == 3:
        return 45.0
    if backup_count == 4:
        return 60.0
    if backup_count == 5:
        return 70.0
    if backup_count == 6:
        return 80.0
    if backup_count == 7:
        return 90.0
    return 95.0


def calculate_price_sensitivity_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    user_max_price_mwh: Optional[float] = None,
) -> float:
    tech_type = str(project.get("technology_type", "")).lower()
    lat = float(project.get("latitude", 0.0) or 0.0)
    lng = float(project.get("longitude", 0.0) or 0.0)

    base_lcoe = 70.0
    reference_cf = 0.30

    if "solar" in tech_type:
        base_lcoe = 55.0
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

    user_cf = project.get("capacity_factor")
    capacity_factor_pct = estimate_capacity_factor(tech_type, lat, user_cf)
    capacity_factor = capacity_factor_pct / 100.0

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

    distances_to_ideal = []
    distances_to_anti_ideal = []
    for vector in weighted_vectors:
        weighted_scores = vector["weighted_normalized_scores"]
        distance_to_ideal = math.sqrt(
            sum((weighted_scores[key] - ideal_solution[key]) ** 2 for key in component_keys)
        )
        distance_to_anti_ideal = math.sqrt(
            sum((weighted_scores[key] - anti_ideal_solution[key]) ** 2 for key in component_keys)
        )
        distances_to_ideal.append(distance_to_ideal)
        distances_to_anti_ideal.append(distance_to_anti_ideal)

    scores = []
    for distance_to_ideal, distance_to_anti_ideal in zip(
        distances_to_ideal, distances_to_anti_ideal
    ):
        denominator = distance_to_ideal + distance_to_anti_ideal
        closeness = distance_to_anti_ideal / denominator if denominator else 0.0
        scores.append(closeness)

    return {
        "scores": scores,
        "ideal_solution": ideal_solution,
        "anti_ideal_solution": anti_ideal_solution,
        "vectors": weighted_vectors,
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
            "development_stage": round(stage_score * custom_weights.get("development_stage", 0.0), 1),
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


def calculate_base_investment_score_renewable(project: Dict[str, Any]) -> float:
    capacity = project.get("capacity_mw", 0) or 0
    status = str(project.get("development_status_short", "")).lower()
    tech = str(project.get("technology_type", "")).lower()
    if capacity >= 200:
        capacity_score = 30.0
    elif capacity >= 100:
        capacity_score = 80.0
    elif capacity >= 50:
        capacity_score = 70.0
    elif capacity >= 25:
        capacity_score = 90.0
    elif capacity >= 10:
        capacity_score = 60.0
    elif capacity >= 5:
        capacity_score = 30.0
    else:
        capacity_score = 15.0

    if "operational" in status:
        stage_score = 10.0
    elif "construction" in status:
        stage_score = 60.0
    elif "granted" in status:
        stage_score = 90.0
    elif "submitted" in status:
        stage_score = 80.0
    elif "planning" in status:
        stage_score = 70.0
    elif "pre-planning" in status:
        stage_score = 60.0
    else:
        stage_score = 50.0

    if "solar" in tech:
        tech_score = 80.0
    elif "battery" in tech:
        tech_score = 85.0
    elif "wind" in tech:
        tech_score = 80.0
    elif "hybrid" in tech:
        tech_score = 100.0
    else:
        tech_score = 70.0

    base_score = capacity_score * 0.30 + stage_score * 0.50 + tech_score * 0.20
    return max(0.0, min(100.0, base_score))


def calculate_infrastructure_bonus_renewable(proximity_scores: Dict[str, float]) -> float:
    grid_bonus = 0.0
    substation_score = proximity_scores.get("substation_score", 0.0)
    transmission_score = proximity_scores.get("transmission_score", 0.0)
    if substation_score > 40:
        grid_bonus += 15.0
    elif substation_score > 25:
        grid_bonus += 10.0
    elif substation_score > 10:
        grid_bonus += 5.0
    if transmission_score > 30:
        grid_bonus += 10.0
    elif transmission_score > 15:
        grid_bonus += 5.0
    grid_bonus = min(25.0, grid_bonus)

    digital_bonus = 0.0
    fiber_score = proximity_scores.get("fiber_score", 0.0)
    ixp_score = proximity_scores.get("ixp_score", 0.0)
    if fiber_score > 15:
        digital_bonus += 5.0
    elif fiber_score > 8:
        digital_bonus += 3.0
    if ixp_score > 8:
        digital_bonus += 5.0
    elif ixp_score > 4:
        digital_bonus += 2.0
    digital_bonus = min(10.0, digital_bonus)

    water_bonus = 0.0
    water_score = proximity_scores.get("water_score", 0.0)
    if water_score > 10:
        water_bonus = 5.0
    elif water_score > 5:
        water_bonus = 3.0
    elif water_score > 2:
        water_bonus = 1.0

    return grid_bonus + digital_bonus + water_bonus


def calculate_enhanced_investment_rating(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    persona: Optional[PersonaType] = None,
) -> Dict[str, Any]:
    if persona is not None:
        return calculate_persona_weighted_score(project, proximity_scores, persona)

    base_score = calculate_base_investment_score_renewable(project)
    infrastructure_bonus = calculate_infrastructure_bonus_renewable(proximity_scores)
    total_internal_score = min(100.0, base_score + infrastructure_bonus)
    display_rating = total_internal_score / 10.0
    color = get_color_from_score(total_internal_score)
    description = get_rating_description(total_internal_score)

    return {
        "base_investment_score": round(base_score / 10.0, 1),
        "infrastructure_bonus": round(infrastructure_bonus / 10.0, 1),
        "investment_rating": round(display_rating, 1),
        "rating_description": description,
        "color_code": color,
        "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
        "internal_total_score": round(total_internal_score, 1),
        "scoring_methodology": "Traditional renewable energy scoring (10-100 internal, 1.0-10.0 display)",
    }


def calculate_best_customer_match(project: Dict[str, Any], proximity_scores: Dict[str, float]) -> Dict[str, Any]:
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
        "suitable_customers": [persona for persona, score in customer_scores.items() if score >= 6.0],
    }


def filter_projects_by_persona_capacity(projects: List[Dict[str, Any]], persona: PersonaType) -> List[Dict[str, Any]]:
    capacity_range = PERSONA_CAPACITY_RANGES[persona]
    filtered = []
    for project in projects:
        capacity_mw = project.get("capacity_mw", 0)
        if capacity_range["min"] <= capacity_mw <= capacity_range["max"]:
            filtered.append(project)
    return filtered


def calculate_rating_distribution(features: List[Dict[str, Any]]) -> Dict[str, int]:
    distribution = {
        "excellent": 0,
        "very_good": 0,
        "good": 0,
        "above_average": 0,
        "average": 0,
        "below_average": 0,
        "poor": 0,
        "very_poor": 0,
        "bad": 0,
    }
    for feature in features:
        rating = feature.get("properties", {}).get("investment_rating", 0)
        if rating >= 9.0:
            distribution["excellent"] += 1
        elif rating >= 8.0:
            distribution["very_good"] += 1
        elif rating >= 7.0:
            distribution["good"] += 1
        elif rating >= 6.0:
            distribution["above_average"] += 1
        elif rating >= 5.0:
            distribution["average"] += 1
        elif rating >= 4.0:
            distribution["below_average"] += 1
        elif rating >= 3.0:
            distribution["poor"] += 1
        elif rating >= 2.0:
            distribution["very_poor"] += 1
        else:
            distribution["bad"] += 1
    return distribution


__all__ = [
    "resolve_power_developer_persona",
    "enrich_and_rescore_top_25_with_tnuos",
    "get_color_from_score",
    "get_rating_description",
    "calculate_capacity_component_score",
    "calculate_development_stage_score",
    "calculate_technology_score",
    "calculate_grid_infrastructure_score",
    "calculate_digital_infrastructure_score",
    "calculate_water_resources_score",
    "calculate_lcoe_score",
    "estimate_capacity_factor",
    "calculate_connection_speed_score",
    "calculate_resilience_score",
    "calculate_price_sensitivity_score",
    "build_persona_component_scores",
    "calculate_persona_weighted_score",
    "calculate_persona_topsis_score",
    "calculate_custom_weighted_score",
    "calculate_base_investment_score_renewable",
    "calculate_infrastructure_bonus_renewable",
    "calculate_enhanced_investment_rating",
    "calculate_best_customer_match",
    "filter_projects_by_persona_capacity",
    "calculate_rating_distribution",
]
