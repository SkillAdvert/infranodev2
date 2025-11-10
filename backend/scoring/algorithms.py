"""
Shared scoring algorithms for infrastructure project evaluation.

This module contains the core scoring components used by both:
- Data Center (DC) developer workflows
- Power developer workflows

Extracted from main.py and dc_workflow.py to eliminate code duplication
and provide a single source of truth for scoring algorithms.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

# Type alias for persona types (used in DC workflow)
PersonaType = Literal["hyperscaler", "colocation", "edge_computing"]

# ============================================================================
# CONSTANTS
# ============================================================================

KM_PER_DEGREE_LAT = 111.32

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

INFRASTRUCTURE_SEARCH_RADIUS_KM = {
    "substation": 100.0,
    "transmission": 100.0,
    "fiber": 100.0,
    "ixp": 100.0,
    "water": 100.0,
}

# TNUoS Zones - Hardcoded from main.py
# TODO: Consider moving to a separate configuration file or database
TNUOS_ZONES_HARDCODED = {
    "GZ1": {
        "name": "North Scotland",
        "tariff": 15.32,
        "bounds": {"min_lat": 57.5, "max_lat": 61.0, "min_lng": -6.0, "max_lng": -1.5},
    },
    "GZ2": {
        "name": "South Scotland",
        "tariff": 14.87,
        "bounds": {"min_lat": 55.5, "max_lat": 57.5, "min_lng": -5.5, "max_lng": -2.0},
    },
    "GZ3": {
        "name": "North East England",
        "tariff": 12.63,
        "bounds": {"min_lat": 54.0, "max_lat": 55.5, "min_lng": -2.5, "max_lng": -0.5},
    },
    "GZ4": {
        "name": "North West England",
        "tariff": 8.42,
        "bounds": {"min_lat": 53.0, "max_lat": 55.0, "min_lng": -3.5, "max_lng": -2.0},
    },
    "GZ5": {
        "name": "Yorkshire",
        "tariff": 5.67,
        "bounds": {"min_lat": 53.0, "max_lat": 54.5, "min_lng": -2.0, "max_lng": -0.5},
    },
    "GZ6": {
        "name": "North Wales & Mersey",
        "tariff": 4.23,
        "bounds": {"min_lat": 52.5, "max_lat": 53.5, "min_lng": -4.5, "max_lng": -2.5},
    },
    "GZ7": {
        "name": "South Wales",
        "tariff": 2.11,
        "bounds": {"min_lat": 51.0, "max_lat": 52.5, "min_lng": -5.5, "max_lng": -3.0},
    },
    "GZ8": {
        "name": "Midlands",
        "tariff": 0.45,
        "bounds": {"min_lat": 52.0, "max_lat": 53.5, "min_lng": -2.5, "max_lng": -0.5},
    },
    "GZ9": {
        "name": "Eastern England",
        "tariff": -1.89,
        "bounds": {"min_lat": 52.0, "max_lat": 53.0, "min_lng": -0.5, "max_lng": 1.5},
    },
    "GZ10": {
        "name": "South West England",
        "tariff": 1.23,
        "bounds": {"min_lat": 50.0, "max_lat": 52.0, "min_lng": -5.5, "max_lng": -2.0},
    },
    "GZ11": {
        "name": "Southern England",
        "tariff": -2.56,
        "bounds": {"min_lat": 50.5, "max_lat": 52.0, "min_lng": -2.0, "max_lng": 0.5},
    },
    "GZ12": {
        "name": "South East England",
        "tariff": -2.94,
        "bounds": {"min_lat": 50.5, "max_lat": 52.0, "min_lng": -1.0, "max_lng": 1.5},
    },
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def _coerce_float(value: Any) -> Optional[float]:
    """Convert value to float, returning None if conversion fails."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_color_from_score(score_out_of_100: float) -> str:
    """Map a 0-100 score to a color hex code for visualization."""
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
    """Map a 0-100 score to a human-readable description."""
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


# ============================================================================
# COMPONENT SCORING FUNCTIONS
# ============================================================================


def calculate_capacity_component_score(
    capacity_mw: float,
    persona: Optional[str] = None,
    user_ideal_mw: Optional[float] = None,
) -> float:
    """
    Calculate capacity fit score using Gaussian distribution.

    Scores are highest when project capacity matches the persona's ideal MW.
    """
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
    """
    Score project based on development stage.

    From demand perspective: Earlier stages (planning) score higher.
    From supply perspective: Later stages (operational) score higher.
    """
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
        pass  # Future: invert scoring for supply perspective

    return float(base_score)


def calculate_technology_score(tech_type: str) -> float:
    """Score technology type based on compatibility with data center / grid needs."""
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
    """Calculate grid infrastructure proximity score based on substation and transmission lines."""
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
    """Calculate digital infrastructure proximity score based on fiber and IXP."""
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
    """Calculate water resources proximity score for cooling requirements."""
    distances = proximity_scores.get("nearest_distances", {})
    water_distance = distances.get("water_km")
    water_raw = 0.0
    if water_distance is not None:
        water_raw = math.exp(-water_distance / INFRASTRUCTURE_HALF_DISTANCE_KM["water"])
    score = 100.0 * water_raw
    return max(0.0, min(100.0, float(score)))


def calculate_lcoe_score(development_status_short: str) -> float:
    """Estimate LCOE (Levelized Cost of Energy) based on development stage."""
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
    """
    Estimate TNUoS (Transmission Network Use of System) score based on latitude.

    Northern locations have higher tariffs (lower scores).
    Southern locations have lower/negative tariffs (higher scores).
    """
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
    """Estimate annual capacity factor percentage for a given technology and location."""

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
    """
    Calculate connection speed score based on development stage and infrastructure proximity.

    Combines:
    - Development stage (50% weight)
    - Substation proximity (30% weight)
    - Transmission line proximity (20% weight)
    """
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
    """
    Calculate resilience score based on backup infrastructure availability.

    Considers:
    - Proximity to substations
    - Proximity to transmission lines
    - Technology type (batteries and hybrids add resilience)
    """
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
    """
    Calculate price sensitivity score considering LCOE and TNUoS costs.

    Estimates total cost per MWh including:
    - Base LCOE adjusted for capacity factor
    - TNUoS transmission charges

    Compares against user's max price if provided.
    """
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
    """
    Build component scores that are shared across personas.

    Does not include capacity score, which is persona-specific.
    """
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
    """
    Build complete component scores including persona-specific capacity score.

    Can accept pre-calculated shared scores for performance optimization.
    """
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


def filter_projects_by_persona_capacity(
    projects: List[Dict[str, Any]],
    persona: PersonaType,
    persona_capacity_ranges: Dict[str, Dict[str, float]],
) -> List[Dict[str, Any]]:
    """Filter projects to only those matching persona capacity requirements."""
    capacity_range = persona_capacity_ranges[persona]
    filtered = []
    for project in projects:
        capacity_mw = project.get("capacity_mw", 0)
        if capacity_range["min"] <= capacity_mw <= capacity_range["max"]:
            filtered.append(project)
    return filtered


# ============================================================================
# TNUOS FUNCTIONS
# ============================================================================


def find_tnuos_zone(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """Find TNUoS zone for given coordinates using hard-coded bounding boxes."""

    for zone_id, zone_data in TNUOS_ZONES_HARDCODED.items():
        bounds = zone_data["bounds"]

        if (
            bounds["min_lat"] <= latitude <= bounds["max_lat"]
            and bounds["min_lng"] <= longitude <= bounds["max_lng"]
        ):
            return {
                "zone_id": zone_id,
                "zone_name": zone_data["name"],
                "generation_tariff_pounds_per_kw": zone_data["tariff"],
            }

    return None


def calculate_tnuos_score_from_tariff(tariff: float) -> float:
    """Convert TNUoS tariff (£/kW) to 0-100 investment score."""

    min_tariff = -3.0
    max_tariff = 16.0

    if tariff <= min_tariff:
        return 100.0
    if tariff >= max_tariff:
        return 0.0

    normalized = (tariff - min_tariff) / (max_tariff - min_tariff)
    return 100.0 * (1.0 - normalized)


async def enrich_and_rescore_with_tnuos(
    features: List[Dict[str, Any]],
    persona: Optional[PersonaType] = None,
    persona_weights: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[Dict[str, Any]]:
    """
    Enrich projects with TNUoS data and adjust scores.

    Args:
        features: List of GeoJSON features with project data
        persona: Optional persona type for weight lookup
        persona_weights: Dict mapping persona names to weight dicts (injected dependency)

    Returns:
        Features sorted by updated investment rating
    """
    if not features:
        return features

    # If persona_weights not provided, will fail gracefully
    if persona_weights is None:
        print("⚠️ Warning: persona_weights not provided to enrich_and_rescore_with_tnuos")
        return features

    features_sorted = sorted(
        features,
        key=lambda feature: feature.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    print("📊 Enriching projects with TNUoS zones...")

    enriched_count = 0

    for feature in features_sorted:
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
                persona_weights.get(persona or "hyperscaler", persona_weights["hyperscaler"])
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

    print(f"✓ Enriched {enriched_count}/{len(features_sorted)} projects")

    resorted_features = sorted(
        features_sorted,
        key=lambda feature: feature.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    return resorted_features


# ============================================================================
# PROXIMITY CALCULATION FUNCTIONS
# ============================================================================


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in km."""
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def exponential_score(distance_km: float, half_distance_km: float) -> float:
    """Convert distance to score using exponential decay."""
    if distance_km >= 200:
        return 0.0
    k = 0.693147 / half_distance_km
    score = 100 * (math.e ** (-k * distance_km))
    return max(0.0, min(100.0, score))


def point_to_line_segment_distance(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    """Calculate minimum distance from point to line segment in km."""
    a = px - x1
    b = py - y1
    c = x2 - x1
    d = y2 - y1
    dot = a * c + b * d
    len_sq = c * c + d * d
    if len_sq == 0:
        return haversine(px, py, x1, y1)
    param = dot / len_sq
    if param < 0:
        closest_x, closest_y = x1, y1
    elif param > 1:
        closest_x, closest_y = x2, y2
    else:
        closest_x = x1 + param * c
        closest_y = y1 + param * d
    return haversine(px, py, closest_x, closest_y)


def _grid_steps_for_radius(grid: Any, radius_km: float) -> int:
    """Calculate number of grid steps needed to cover search radius."""
    cell_width_km = max(1.0, grid.approximate_cell_width_km())
    return max(1, int(math.ceil(radius_km / cell_width_km)) + 1)


def _bbox_within_search(
    bbox: Tuple[float, float, float, float],
    lat: float,
    lon: float,
    radius_km: float,
) -> bool:
    """Check if bounding box is within search radius."""
    min_lat, min_lon, max_lat, max_lon = bbox
    lat_margin = radius_km / KM_PER_DEGREE_LAT
    lon_margin = radius_km / (KM_PER_DEGREE_LAT * max(math.cos(math.radians(lat)), 0.2))
    return not (
        lat < min_lat - lat_margin
        or lat > max_lat + lat_margin
        or lon < min_lon - lon_margin
        or lon > max_lon + lon_margin
    )


def _nearest_point(
    grid: Any,
    features: Sequence[Any],
    lat: float,
    lon: float,
    radius_km: float,
) -> Optional[Tuple[float, Any]]:
    """Find nearest point feature within radius."""
    best: Optional[Tuple[float, Any]] = None
    steps = _grid_steps_for_radius(grid, radius_km)
    for step in range(1, steps + 2):
        for feature in grid.query(lat, lon, step):
            # Check if it's a point feature (has lat/lon attributes)
            if not hasattr(feature, 'lat') or not hasattr(feature, 'lon'):
                continue
            distance = haversine(lat, lon, feature.lat, feature.lon)
            if distance > radius_km:
                continue
            if not best or distance < best[0]:
                best = (distance, feature)
        if best:
            break

    if not best and features:
        for feature in features:
            if not hasattr(feature, 'lat') or not hasattr(feature, 'lon'):
                continue
            distance = haversine(lat, lon, feature.lat, feature.lon)
            if not best or distance < best[0]:
                best = (distance, feature)
    return best


def _nearest_line(
    grid: Any,
    features: Sequence[Any],
    lat: float,
    lon: float,
    radius_km: float,
) -> Optional[Tuple[float, Any]]:
    """Find nearest line feature within radius."""
    best: Optional[Tuple[float, Any]] = None
    steps = _grid_steps_for_radius(grid, radius_km)
    for step in range(1, steps + 2):
        for feature in grid.query(lat, lon, step):
            # Check if it's a line feature (has bbox and segments attributes)
            if not hasattr(feature, 'bbox') or not hasattr(feature, 'segments'):
                continue
            if not _bbox_within_search(feature.bbox, lat, lon, radius_km):
                continue
            distance = _distance_to_line_feature(feature, lat, lon)
            if distance > radius_km:
                continue
            if not best or distance < best[0]:
                best = (distance, feature)
        if best:
            break

    if not best and features:
        for feature in features:
            if not hasattr(feature, 'bbox') or not hasattr(feature, 'segments'):
                continue
            if not _bbox_within_search(feature.bbox, lat, lon, radius_km):
                continue
            distance = _distance_to_line_feature(feature, lat, lon)
            if not best or distance < best[0]:
                best = (distance, feature)
    return best


def _distance_to_line_feature(feature: Any, lat: float, lon: float) -> float:
    """Calculate minimum distance from point to line feature."""
    best = float("inf")
    for segment in feature.segments:
        distance = point_to_line_segment_distance(lat, lon, *segment)
        if distance < best:
            best = distance
            if best == 0:
                break
    return best if best != float("inf") else 9999.0


async def calculate_proximity_scores_batch(
    projects: List[Dict[str, Any]],
    infrastructure_catalog: Any,
) -> List[Dict[str, float]]:
    """
    Calculate proximity scores for a batch of projects.

    Args:
        projects: List of project dicts with latitude/longitude
        infrastructure_catalog: InfrastructureCatalog instance with spatial indices

    Returns:
        List of proximity score dicts, one per project
    """
    if not projects:
        return []

    results: List[Dict[str, float]] = []

    for project in projects:
        project_lat = _coerce_float(project.get("latitude"))
        project_lon = _coerce_float(project.get("longitude"))
        if project_lat is None or project_lon is None:
            continue

        proximity_scores: Dict[str, float] = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "total_proximity_bonus": 0.0,
            "nearest_distances": {},
        }

        nearest_distances: Dict[str, float] = {}

        substation = _nearest_point(
            infrastructure_catalog.substations_index,
            infrastructure_catalog.substations,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["substation"],
        )
        if substation:
            distance, _ = substation
            proximity_scores["substation_score"] = exponential_score(distance, 30.0)
            nearest_distances["substation_km"] = round(distance, 1)

        transmission = _nearest_line(
            infrastructure_catalog.transmission_index,
            infrastructure_catalog.transmission_lines,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["transmission"],
        )
        if transmission:
            distance, _ = transmission
            proximity_scores["transmission_score"] = exponential_score(distance, 30.0)
            nearest_distances["transmission_km"] = round(distance, 1)

        fiber = _nearest_line(
            infrastructure_catalog.fiber_index,
            infrastructure_catalog.fiber_cables,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["fiber"],
        )
        if fiber:
            distance, _ = fiber
            proximity_scores["fiber_score"] = exponential_score(distance, 15.0)
            nearest_distances["fiber_km"] = round(distance, 1)

        ixp = _nearest_point(
            infrastructure_catalog.ixp_index,
            infrastructure_catalog.internet_exchange_points,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["ixp"],
        )
        if ixp:
            distance, _ = ixp
            proximity_scores["ixp_score"] = exponential_score(distance, 40.0)
            nearest_distances["ixp_km"] = round(distance, 1)

        water_point = _nearest_point(
            infrastructure_catalog.water_point_index,
            infrastructure_catalog.water_points,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["water"],
        )
        water_line = _nearest_line(
            infrastructure_catalog.water_line_index,
            infrastructure_catalog.water_lines,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["water"],
        )
        water_candidates: List[Tuple[float, str]] = []
        if water_point:
            water_candidates.append((water_point[0], "water_point"))
        if water_line:
            water_candidates.append((water_line[0], "water_line"))
        if water_candidates:
            distance, _ = min(water_candidates, key=lambda item: item[0])
            proximity_scores["water_score"] = exponential_score(distance, 25.0)
            nearest_distances["water_km"] = round(distance, 1)

        proximity_scores["nearest_distances"] = nearest_distances
        proximity_scores["total_proximity_bonus"] = (
            proximity_scores["substation_score"]
            + proximity_scores["transmission_score"]
            + proximity_scores["fiber_score"]
            + proximity_scores["ixp_score"]
            + proximity_scores["water_score"]
        )

        results.append(proximity_scores)

    return results


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Types
    "PersonaType",
    # Constants
    "KM_PER_DEGREE_LAT",
    "PERSONA_CAPACITY_PARAMS",
    "INFRASTRUCTURE_HALF_DISTANCE_KM",
    "INFRASTRUCTURE_SEARCH_RADIUS_KM",
    "TNUOS_ZONES_HARDCODED",
    # Utility functions
    "get_color_from_score",
    "get_rating_description",
    # Component scoring functions
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
    "filter_projects_by_persona_capacity",
    # TNUoS functions
    "find_tnuos_zone",
    "calculate_tnuos_score_from_tariff",
    "enrich_and_rescore_with_tnuos",
    # Proximity calculation functions
    "haversine",
    "exponential_score",
    "point_to_line_segment_distance",
    "calculate_proximity_scores_batch",
    # Internal helpers (exposed for testing)
    "_build_shared_persona_component_scores",
    "_coerce_float",
]
