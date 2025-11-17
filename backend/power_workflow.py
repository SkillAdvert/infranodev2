from __future__ import annotations

import math
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Literal, cast

from fastapi import HTTPException

from backend.scoring import (
    build_persona_component_scores,
    get_color_from_score,
    get_rating_description,
)

PowerDeveloperPersona = Literal["greenfield", "repower", "stranded"]

POWER_DEVELOPER_PERSONAS: Dict[str, Dict[str, float]] = {
    "greenfield": {
        "capacity": 0.15,
        "connection_speed": 0.40,
        "resilience": 0.05,
        "land_planning": 0.10,
        "latency": 0.05,
        "cooling": 0.05,
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


for persona_name, weights_dict in POWER_DEVELOPER_PERSONAS.items():
    total_weight = sum(weights_dict.values())
    if not math.isclose(total_weight, 1.0, rel_tol=1e-6):
        print(f"⚠️ WARNING: {persona_name} weights sum to {total_weight}, not 1.0")


QuerySupabaseFn = Callable[..., Awaitable[Any]]
ProximityBatchFn = Callable[[List[Dict[str, Any]]], Awaitable[List[Dict[str, float]]]]


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


def extract_coordinates(row: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Return latitude/longitude from heterogeneous Supabase payloads."""

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    latitude_keys = ["latitude", "lat", "Latitude", "Latitude_deg"]
    longitude_keys = ["longitude", "lon", "lng", "Longitude", "Longitude_deg"]

    for key in latitude_keys:
        if key in row:
            latitude = row.get(key)
            if latitude is not None:
                try:
                    latitude = float(latitude)
                except (TypeError, ValueError):
                    latitude = None
            if latitude is not None:
                break

    for key in longitude_keys:
        if key in row:
            longitude = row.get(key)
            if longitude is not None:
                try:
                    longitude = float(longitude)
                except (TypeError, ValueError):
                    longitude = None
            if longitude is not None:
                break

    if (latitude is None or longitude is None) and isinstance(row.get("location"), dict):
        location_data = row.get("location") or {}
        if latitude is None:
            lat_value = location_data.get("lat") or location_data.get("latitude")
            if lat_value is not None:
                try:
                    latitude = float(lat_value)
                except (TypeError, ValueError):
                    latitude = None
        if longitude is None:
            lon_value = (
                location_data.get("lon")
                or location_data.get("lng")
                or location_data.get("longitude")
            )
            if lon_value is not None:
                try:
                    longitude = float(lon_value)
                except (TypeError, ValueError):
                    longitude = None

    if (latitude is None or longitude is None) and isinstance(row.get("coordinates"), (list, tuple)):
        coords = row.get("coordinates")
        if len(coords) >= 2:
            if longitude is None:
                try:
                    longitude = float(coords[0])
                except (TypeError, ValueError):
                    longitude = None
            if latitude is None:
                try:
                    latitude = float(coords[1])
                except (TypeError, ValueError):
                    latitude = None

    return latitude, longitude


def transform_tec_to_project_schema(tec_row: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a TEC connections database row to unified project schema."""

    latitude, longitude = extract_coordinates(tec_row)

    def _coerce_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return {
        "id": tec_row.get("id"),
        "ref_id": str(tec_row.get("id", "")),
        "site_name": tec_row.get("project_name") or "Untitled Project",
        "project_name": tec_row.get("project_name"),
        "capacity_mw": _coerce_float(tec_row.get("capacity_mw")) or 0.0,
        "technology_type": tec_row.get("technology_type") or "Unknown",
        "development_status_short": tec_row.get("development_status") or "Scoping",
        "development_status": tec_row.get("development_status"),
        "constraint_status": tec_row.get("constraint_status"),
        "connection_site": tec_row.get("connection_site"),
        "substation_name": tec_row.get("substation_name"),
        "voltage_kv": _coerce_float(tec_row.get("voltage")),
        "latitude": latitude,
        "longitude": longitude,
        "county": None,
        "country": "UK",
        "operator": tec_row.get("operator") or tec_row.get("customer_name"),
        "_source_table": "tec_connections",
    }


async def run_power_developer_analysis(
    *,
    criteria: Dict[str, Any],
    site_location: Optional[Dict[str, float]],
    target_persona: Optional[str],
    limit: int,
    source_table: str,
    query_supabase: QuerySupabaseFn,
    calculate_proximity_scores_batch: ProximityBatchFn,
) -> Dict[str, Any]:
    """Execute the power developer workflow using supplied dependencies."""

    parsed_custom_weights = None
    if criteria and isinstance(criteria, dict):
        # Map frontend field names to backend field names
        field_mapping = {
            'connection_headroom': 'connection_speed',
            'route_to_market': 'price_sensitivity',
            'project_stage': 'land_planning',
            'demand_scale': 'capacity',
            'grid_infrastructure': 'resilience',
            'digital_infrastructure': 'latency',
            'water_resources': 'cooling',
        }
        parsed_custom_weights = {
            field_mapping.get(k, k): v 
            for k, v in criteria.items() 
            if isinstance(v, (int, float))
        }
        # Normalize to sum=1.0
        total = sum(parsed_custom_weights.values())
        if total:
            parsed_custom_weights = {k: v/total for k, v in parsed_custom_weights.items()}

    start_time = time.time()
    (
        target_persona,
        requested_persona,
        persona_resolution,
    ) = resolve_power_developer_persona(target_persona)

    if persona_resolution == "defaulted":
        print("🔄 Power Developer Analysis - Project Type requested: <default>")
        print("   ℹ️ No project type supplied, defaulting to 'greenfield'")
    elif persona_resolution == "invalid":
        print(
            "🔄 Power Developer Analysis - Project Type requested: "
            f"{requested_persona}"
        )
        print(
            f"   ⚠️ Invalid project type '{requested_persona}', using 'greenfield'"
        )
    else:
        print(
            "🔄 Power Developer Analysis - Project Type requested: "
            f"{requested_persona}"
        )
        print(f"   🎯 Using project type '{target_persona}'")

    weights = parsed_custom_weights if parsed_custom_weights else POWER_DEVELOPER_PERSONAS[target_persona]

    print(f"   📊 Fetching {limit} projects from '{source_table}'...")

    try:
        raw_rows = await query_supabase(f"{source_table}?select=*", limit=limit)
        if not raw_rows:
            print("   ⚠️ No projects returned from database")
            return {
                "type": "FeatureCollection",
                "features": [],
                "metadata": {
                    "error": "No projects found",
                    "project_type": target_persona,
                    "project_type_resolution": persona_resolution,
                    "requested_project_type": requested_persona or None,
                },
            }
        print(f"   ✅ Loaded {len(raw_rows)} projects")
    except Exception as exc:
        print(f"   ❌ Database error: {exc}")
        raise HTTPException(500, f"Failed to fetch projects: {str(exc)}")

    print("   🔄 Transforming to project schema...")

    if source_table == "tec_connections":
        projects = [transform_tec_to_project_schema(row) for row in raw_rows]
    else:
        projects = raw_rows

    valid_projects = [
        p for p in projects if p.get("latitude") is not None and p.get("longitude") is not None
    ]

    print(f"   📍 Valid coordinates: {len(valid_projects)}/{len(projects)}")

    if not valid_projects:
        print("   ⚠️ No projects with valid coordinates")
        return {
            "type": "FeatureCollection",
            "features": [],
            "metadata": {
                "warning": "No valid coordinates",
                "project_type": target_persona,
                "project_type_resolution": persona_resolution,
                "requested_project_type": requested_persona or None,
            },
        }

    print("   🔄 Calculating proximity scores...")

    try:
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects)
        print("   ✅ Proximity calculations complete")
    except Exception as exc:
        print(f"   ❌ Proximity calculation error: {exc}")
        raise

    print(f"   🔄 Scoring {len(valid_projects)} projects as '{target_persona}'...")

    features: List[Dict[str, Any]] = []

    for index, project in enumerate(valid_projects):
        try:
            proximity_scores = (
                all_proximity_scores[index]
                if index < len(all_proximity_scores)
                else {
                    "substation_score": 0.0,
                    "transmission_score": 0.0,
                    "fiber_score": 0.0,
                    "ixp_score": 0.0,
                    "water_score": 0.0,
                    "nearest_distances": {},
                }
            )

            component_scores = build_persona_component_scores(
                project,
                proximity_scores,
                persona=target_persona,
                perspective="demand",
            )

            weighted_score = sum(
                component_scores.get(criterion, 0) * weights.get(criterion, 0)
                for criterion in component_scores
            )

            weighted_score = max(0.0, min(100.0, weighted_score))

            display_rating = round(weighted_score / 10.0, 1)
            color_code = get_color_from_score(weighted_score)
            rating_description = get_rating_description(weighted_score)

            properties = {
                "id": project.get("ref_id"),
                "project_name": project.get("site_name"),
                "site_name": project.get("site_name"),
                "capacity_mw": project.get("capacity_mw"),
                "technology_type": project.get("technology_type"),
                "operator": project.get("operator"),
                "development_status": project.get("development_status_short"),
                "connection_site": project.get("connection_site"),
                "substation_name": project.get("substation_name"),
                "voltage_kv": project.get("voltage_kv"),
                "investment_rating": display_rating,
                "rating_description": rating_description,
                "color_code": color_code,
                "component_scores": {k: round(v, 1) for k, v in component_scores.items()},
                "weighted_contributions": {
                    k: round(component_scores[k] * weights.get(k, 0), 1) for k in component_scores
                },
                "project_type_weights": weights,
                "internal_total_score": round(weighted_score, 1),
                "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
            }

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [project["longitude"], project["latitude"]],
                },
                "properties": properties,
            }

            features.append(feature)

        except Exception as exc:
            print(f"   ⚠️ Error scoring project {index + 1}: {exc}")
            continue

    features_sorted = sorted(
        features,
        key=lambda f: f.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    processing_time = time.time() - start_time

    print(f"   ✅ Scoring complete: {len(features_sorted)} projects in {processing_time:.2f}s")

    if features_sorted:
        top = features_sorted[0]["properties"]
        print(
            f"   🏆 Top project: {top.get('project_name')} - "
            f"Rating {top.get('investment_rating')}/10 • {top.get('capacity_mw')}MW"
        )

    return {
        "type": "FeatureCollection",
        "features": features_sorted,
        "metadata": {
            "scoring_system": "Power Developer - Project Type Analysis",
            "project_type": target_persona,
            "project_type_weights": weights,
            "requested_project_type": requested_persona or None,
            "project_type_resolution": persona_resolution,
            "source_table": source_table,
            "total_projects_processed": len(raw_rows),
            "projects_with_valid_coords": len(valid_projects),
            "projects_scored": len(features_sorted),
            "processing_time_seconds": round(processing_time, 2),
            "algorithm_version": "2.2 - Power Developer Workflow",
            "rating_scale": {
                "9.0-10.0": "Excellent",
                "8.0-8.9": "Very Good",
                "7.0-7.9": "Good",
                "6.0-6.9": "Above Average",
                "5.0-5.9": "Average",
            },
        },
    }


__all__ = [
    "PowerDeveloperPersona",
    "POWER_DEVELOPER_PERSONAS",
    "POWER_DEVELOPER_CAPACITY_RANGES",
    "resolve_power_developer_persona",
    "extract_coordinates",
    "transform_tec_to_project_schema",
    "run_power_developer_analysis",
]
