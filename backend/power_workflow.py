"""
Power Developer Workflow (Enhanced Architecture)
=================================================

Analyzes TEC (Transmission Entry Capacity) grid connections for power development opportunities.

This module implements:
- Phase 1: Parameter alignment (user_ideal_mw, user_max_price_mwh, custom_weights)
- Phase 2: Capacity filtering (persona-specific ranges + 90% gating)
- Clean architecture with dependency injection and type safety

Author: AI Assistant
Version: 2.3 - Enhanced Architecture
Date: 2025-11-10
"""

from __future__ import annotations

import math
import time
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Sequence, Tuple, cast

# Optional dependencies with fallback shims for testing
try:
    from fastapi import HTTPException
except ModuleNotFoundError:
    class HTTPException(Exception):
        """Minimal HTTPException shim when FastAPI is unavailable."""
        def __init__(self, status_code: int, detail: str | None = None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

try:
    from pydantic import BaseModel
except ModuleNotFoundError:
    class BaseModel:  # type: ignore
        """Minimal BaseModel shim when Pydantic is unavailable."""
        def __init__(self, **data: Any):
            for key, value in data.items():
                setattr(self, key, value)


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

PowerDeveloperPersona = Literal["greenfield", "repower", "stranded"]

# Type aliases for dependency injection
QuerySupabaseFn = Callable[..., Awaitable[Sequence[Dict[str, Any]]]]
TransformProjectFn = Callable[[Dict[str, Any]], Dict[str, Any]]
CalculateProximityFn = Callable[[Sequence[Dict[str, Any]]], Awaitable[Sequence[Dict[str, Any]]]]
BuildComponentScoresFn = Callable[..., Dict[str, float]]
GetScoreColorFn = Callable[[float], str]
GetScoreDescriptionFn = Callable[[float], str]


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class PowerDeveloperFeature(BaseModel):
    """GeoJSON feature for a scored power developer project."""
    type: Literal["Feature"]
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class PowerDeveloperAnalysisResponse(BaseModel):
    """GeoJSON FeatureCollection of scored projects with metadata."""
    type: Literal["FeatureCollection"]
    features: List[PowerDeveloperFeature]
    metadata: Dict[str, Any]


# ============================================================================
# POWER DEVELOPER PERSONAS & WEIGHTS
# ============================================================================

POWER_DEVELOPER_PERSONAS: Dict[str, Dict[str, float]] = {
    "greenfield": {
        "capacity": 0.15,
        "connection_speed": 0.15,
        "resilience": 0.10,
        "land_planning": 0.25,      # Highest priority for greenfield
        "latency": 0.03,
        "cooling": 0.02,
        "price_sensitivity": 0.20,
    },
    "repower": {
        "capacity": 0.15,
        "connection_speed": 0.20,    # Higher priority for repower
        "resilience": 0.12,
        "land_planning": 0.15,
        "latency": 0.05,
        "cooling": 0.03,
        "price_sensitivity": 0.15,
    },
    "stranded": {
        "capacity": 0.05,            # Lower capacity needs
        "connection_speed": 0.25,    # Highest priority for stranded
        "resilience": 0.10,
        "land_planning": 0.05,
        "latency": 0.05,
        "cooling": 0.05,
        "price_sensitivity": 0.25,  # Very cost-sensitive
    },
}

POWER_DEVELOPER_CAPACITY_RANGES = {
    "greenfield": {"min": 10, "max": 250},   # Large greenfield projects
    "repower": {"min": 5, "max": 100},       # Medium repower projects
    "stranded": {"min": 1, "max": 50},       # Small stranded assets
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def resolve_power_developer_persona(
    raw_value: Optional[str],
) -> Tuple[PowerDeveloperPersona, str, str]:
    """Normalize the requested persona and flag how it was resolved.

    Returns a tuple of:
        (effective_persona, requested_value, resolution_status)

    Where resolution_status is one of "defaulted", "invalid", or "valid".
    """
    requested_value = (raw_value or "").strip()
    normalized_value = requested_value.lower()

    if not normalized_value:
        return "greenfield", requested_value, "defaulted"

    if normalized_value not in POWER_DEVELOPER_PERSONAS:
        return "greenfield", requested_value, "invalid"

    return cast(PowerDeveloperPersona, normalized_value), requested_value, "valid"


def normalize_frontend_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """
    Normalize frontend weights (0-100 scale) to backend format (sum=1.0).

    Maps frontend criteria to backend criteria:
    - route_to_market → price_sensitivity
    - project_stage → land_planning
    - connection_headroom → connection_speed
    - demand_scale → capacity
    - grid_infrastructure → resilience
    - digital_infrastructure → latency
    - water_resources → cooling

    Removes 'value_uplift' if present (deprecated).

    Args:
        weights: Frontend weights dict with 0-100 scale values

    Returns:
        Backend weights dict normalized to sum=1.0
    """
    mapping = {
        "route_to_market": "price_sensitivity",
        "project_stage": "land_planning",
        "connection_headroom": "connection_speed",
        "demand_scale": "capacity",
        "grid_infrastructure": "resilience",
        "digital_infrastructure": "latency",
        "water_resources": "cooling",
    }

    backend_weights = {}
    total = 0.0

    for frontend_key, backend_key in mapping.items():
        if frontend_key in weights:
            value = weights[frontend_key]
            backend_weights[backend_key] = value
            total += value

    # Normalize to sum=1.0
    if total > 0:
        for key in backend_weights:
            backend_weights[key] /= total
    else:
        # Fallback to equal weights if all are 0
        for key in backend_weights:
            backend_weights[key] = 1.0 / 7.0

    return backend_weights


def map_demand_scale_to_mw(demand_scale: float) -> float:
    """
    Convert demand_scale (0-100) to MW capacity.

    Frontend scale mapping:
    - 25 or less: Small (<10MW) → 5 MW
    - 50: Medium (10-30MW) → 20 MW
    - 75: Large (30-99MW) → 65 MW
    - 100: Very Large (100MW+) → 150 MW

    Args:
        demand_scale: Value from 0-100

    Returns:
        Capacity in MW
    """
    if demand_scale <= 25:
        return 5.0
    elif demand_scale <= 50:
        return 20.0
    elif demand_scale <= 75:
        return 65.0
    else:
        return 150.0


def filter_projects_by_capacity_range(
    projects: Sequence[Dict[str, Any]],
    persona: PowerDeveloperPersona
) -> List[Dict[str, Any]]:
    """
    Filter projects by persona-specific capacity range.

    Args:
        projects: List of project dictionaries
        persona: Power developer persona type

    Returns:
        Filtered list of projects within capacity range
    """
    capacity_range = POWER_DEVELOPER_CAPACITY_RANGES[persona]
    filtered = []

    for project in projects:
        capacity_mw = project.get("capacity_mw", 0)
        if capacity_range["min"] <= capacity_mw <= capacity_range["max"]:
            filtered.append(project)

    return filtered


def apply_capacity_gating(
    projects: Sequence[Dict[str, Any]],
    user_ideal_mw: float,
    threshold: float = 0.9
) -> List[Dict[str, Any]]:
    """
    Apply 90% capacity gating - filter projects that meet minimum capacity threshold.

    Args:
        projects: List of project dictionaries
        user_ideal_mw: User's ideal capacity requirement
        threshold: Minimum percentage of ideal (default 0.9 = 90%)

    Returns:
        Filtered list of projects meeting capacity threshold
    """
    min_capacity = user_ideal_mw * threshold
    gated = []

    for project in projects:
        capacity_mw = project.get("capacity_mw", 0)
        if capacity_mw >= min_capacity:
            gated.append(project)

    return gated


# ============================================================================
# VALIDATION
# ============================================================================

# Validate that all persona weights sum to 1.0
for persona_name, weights_dict in POWER_DEVELOPER_PERSONAS.items():
    total_weight = sum(weights_dict.values())
    if not math.isclose(total_weight, 1.0, rel_tol=1e-6):
        print(f"⚠️ WARNING: {persona_name} weights sum to {total_weight}, not 1.0")


# ============================================================================
# MAIN WORKFLOW FUNCTION
# ============================================================================

async def run_power_developer_analysis(
    *,
    # Request parameters
    limit: int,
    source_table: str,
    target_persona: str,
    requested_persona: Optional[str],
    persona_resolution: str,
    weights: Dict[str, float],
    user_ideal_mw: Optional[float],
    user_max_price_mwh: Optional[float],
    apply_capacity_filter: bool,
    # Dependency injection
    query_supabase: QuerySupabaseFn,
    transform_tec_to_project_schema: TransformProjectFn,
    calculate_proximity_scores_batch: CalculateProximityFn,
    build_persona_component_scores: BuildComponentScoresFn,
    get_color_from_score: GetScoreColorFn,
    get_rating_description: GetScoreDescriptionFn,
) -> PowerDeveloperAnalysisResponse:
    """
    Execute the power developer analysis workflow with Phase 1 & 2 enhancements.

    This function encapsulates the scoring pipeline:
    1. Fetch projects from tec_connections table
    2. Transform TEC schema to unified project schema
    3. Apply capacity filtering (persona-specific ranges + 90% gating)
    4. Calculate infrastructure proximity scores
    5. Build component scores (7 business criteria)
    6. Apply persona-weighted scoring
    7. Return scored GeoJSON

    Args:
        limit: Maximum projects to process
        source_table: Data source ("tec_connections" or "renewable_projects")
        target_persona: Resolved persona (greenfield/repower/stranded)
        requested_persona: Original user-provided persona
        persona_resolution: How persona was resolved (valid/invalid/defaulted)
        weights: Persona weights (normalized to sum=1.0)
        user_ideal_mw: Target capacity in MW (Phase 1)
        user_max_price_mwh: Max acceptable price (Phase 1)
        apply_capacity_filter: Whether to apply filtering (Phase 2)
        query_supabase: Function to query database
        transform_tec_to_project_schema: Function to transform TEC rows
        calculate_proximity_scores_batch: Function to calculate proximity
        build_persona_component_scores: Function to build component scores
        get_color_from_score: Function to get color code
        get_rating_description: Function to get rating description

    Returns:
        PowerDeveloperAnalysisResponse with scored projects and metadata
    """
    start_time = time.time()

    # ========================================================================
    # STEP 1: Fetch Projects from Database
    # ========================================================================
    print(f"   📊 Fetching {limit} projects from '{source_table}'...")

    try:
        raw_rows = await query_supabase(f"{source_table}?select=*", limit=limit)
    except Exception as exc:
        print(f"   ❌ Database error: {exc}")
        raise HTTPException(500, f"Failed to fetch projects: {exc}")

    if not raw_rows:
        print("   ⚠️ No projects returned from database")
        return PowerDeveloperAnalysisResponse(
            type="FeatureCollection",
            features=[],
            metadata={
                "error": "No projects found",
                "project_type": target_persona,
                "project_type_resolution": persona_resolution,
                "requested_project_type": requested_persona or None,
                "source_table": source_table,
                "total_projects_processed": 0,
                "projects_with_valid_coords": 0,
                "projects_scored": 0,
                "processing_time_seconds": round(time.time() - start_time, 2),
                "algorithm_version": "2.3 - Power Developer Workflow (Enhanced)",
            },
        )

    print(f"   ✅ Loaded {len(raw_rows)} projects")

    # ========================================================================
    # STEP 2: Transform Rows to Project Schema
    # ========================================================================
    print("   🔄 Transforming to project schema...")

    if source_table == "tec_connections":
        projects = [transform_tec_to_project_schema(row) for row in raw_rows]
    else:
        projects = list(raw_rows)

    # ========================================================================
    # STEP 3: Filter for Valid Coordinates
    # ========================================================================
    valid_projects = [
        project
        for project in projects
        if project.get("latitude") is not None and project.get("longitude") is not None
    ]

    print(f"   📍 Valid coordinates: {len(valid_projects)}/{len(projects)}")

    if not valid_projects:
        print("   ⚠️ No projects with valid coordinates")
        return PowerDeveloperAnalysisResponse(
            type="FeatureCollection",
            features=[],
            metadata={
                "warning": "No valid coordinates",
                "project_type": target_persona,
                "project_type_resolution": persona_resolution,
                "requested_project_type": requested_persona or None,
                "source_table": source_table,
                "total_projects_processed": len(raw_rows),
                "projects_with_valid_coords": 0,
                "projects_scored": 0,
                "processing_time_seconds": round(time.time() - start_time, 2),
                "algorithm_version": "2.3 - Power Developer Workflow (Enhanced)",
            },
        )

    # ========================================================================
    # STEP 3A: Apply Capacity Filtering (PHASE 2)
    # ========================================================================
    if apply_capacity_filter and target_persona:
        capacity_range = POWER_DEVELOPER_CAPACITY_RANGES[target_persona]
        original_count = len(valid_projects)
        valid_projects = filter_projects_by_capacity_range(valid_projects, target_persona)
        print(
            f"   🎯 Capacity filter: {len(valid_projects)}/{original_count} projects "
            f"in range {capacity_range['min']}-{capacity_range['max']} MW"
        )

    # ========================================================================
    # STEP 3B: Apply 90% Capacity Gating (PHASE 2)
    # ========================================================================
    if user_ideal_mw:
        original_count = len(valid_projects)
        valid_projects = apply_capacity_gating(valid_projects, user_ideal_mw, threshold=0.9)
        if len(valid_projects) != original_count:
            print(
                f"   ⚡ Capacity gating: {len(valid_projects)}/{original_count} projects "
                f"meet ≥90% of {user_ideal_mw} MW"
            )

    if not valid_projects:
        print("   ⚠️ No projects passed capacity filtering")
        return PowerDeveloperAnalysisResponse(
            type="FeatureCollection",
            features=[],
            metadata={
                "warning": "No projects meet capacity requirements",
                "project_type": target_persona,
                "capacity_filter_applied": apply_capacity_filter,
                "user_ideal_mw": user_ideal_mw,
                "source_table": source_table,
                "total_projects_processed": len(raw_rows),
                "projects_with_valid_coords": len(valid_projects),
                "projects_scored": 0,
                "processing_time_seconds": round(time.time() - start_time, 2),
                "algorithm_version": "2.3 - Power Developer Workflow (Enhanced)",
            },
        )

    # ========================================================================
    # STEP 4: Calculate Infrastructure Proximity Scores
    # ========================================================================
    print("   🔄 Calculating proximity scores...")

    try:
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects)
        print("   ✅ Proximity calculations complete")
    except Exception as exc:
        print(f"   ❌ Proximity calculation error: {exc}")
        raise

    # ========================================================================
    # STEP 5: Score Each Project Using Power Developer Weights
    # ========================================================================
    print(f"   🔄 Scoring {len(valid_projects)} projects as '{target_persona}'...")

    features: List[PowerDeveloperFeature] = []

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

            # STEP 5A: Build component scores (7 business criteria)
            # PHASE 1: Pass user_ideal_mw and user_max_price_mwh
            component_scores = build_persona_component_scores(
                project,
                proximity_scores,
                persona=target_persona,
                perspective="demand",
                user_ideal_mw=user_ideal_mw,
                user_max_price_mwh=user_max_price_mwh,
            )

            # STEP 5B: Apply power developer weights (simple weighted sum)
            weighted_score = sum(
                component_scores.get(criterion, 0) * weights.get(criterion, 0)
                for criterion in component_scores
            )
            weighted_score = max(0.0, min(100.0, weighted_score))

            # STEP 5C: Convert to display format (0-10 scale)
            display_rating = round(weighted_score / 10.0, 1)
            color_code = get_color_from_score(weighted_score)
            rating_description = get_rating_description(weighted_score)

            # STEP 5D: Build properties object
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
                    key: round(component_scores[key] * weights.get(key, 0), 1)
                    for key in component_scores
                },
                "project_type": target_persona,
                "project_type_weights": weights,
                "internal_total_score": round(weighted_score, 1),
                "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
            }

            # STEP 5E: Build GeoJSON feature
            feature = PowerDeveloperFeature(
                type="Feature",
                geometry={
                    "type": "Point",
                    "coordinates": [project["longitude"], project["latitude"]],
                },
                properties=properties,
            )

            features.append(feature)

        except Exception as exc:
            print(f"   ⚠️ Error scoring project {index + 1}: {exc}")
            continue

    # ========================================================================
    # STEP 6: Sort by Investment Rating
    # ========================================================================
    features_sorted = sorted(
        features,
        key=lambda feature: feature.properties.get("investment_rating", 0),
        reverse=True,
    )

    # ========================================================================
    # STEP 7: Log Results and Return
    # ========================================================================
    processing_time = time.time() - start_time
    print(f"   ✅ Scoring complete: {len(features_sorted)} projects in {processing_time:.2f}s")

    if features_sorted:
        top = features_sorted[0].properties
        print(
            "   🏆 Top project: "
            f"{top.get('project_name')} - Rating {top.get('investment_rating')}/10 • "
            f"{top.get('capacity_mw')}MW"
        )

    metadata = {
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
        "algorithm_version": "2.3 - Power Developer Workflow (Enhanced)",
        "user_ideal_mw": user_ideal_mw,
        "user_max_price_mwh": user_max_price_mwh,
        "capacity_filter_applied": apply_capacity_filter,
        "rating_scale": {
            "9.0-10.0": "Excellent",
            "8.0-8.9": "Very Good",
            "7.0-7.9": "Good",
            "6.0-6.9": "Above Average",
            "5.0-5.9": "Average",
        },
    }

    return PowerDeveloperAnalysisResponse(
        type="FeatureCollection",
        features=features_sorted,
        metadata=metadata,
    )


# ============================================================================
# LEGACY WRAPPER (for backward compatibility)
# ============================================================================

async def analyze_for_power_developer(
    # Dependency injection
    query_supabase,
    calculate_proximity_scores_batch,
    build_persona_component_scores,
    # Request parameters
    custom_weights: Optional[Dict[str, float]] = None,
    source_table: str = "tec_connections",
    target_persona: Optional[str] = None,
    user_ideal_mw: Optional[float] = None,
    user_max_price_mwh: Optional[float] = None,
    apply_capacity_filter: bool = True,
    limit: int = 5000,
) -> Dict[str, Any]:
    """
    Legacy wrapper for backward compatibility with main.py.

    Calls run_power_developer_analysis() with all necessary transformations.
    """
    # Resolve persona
    resolved_persona, requested_persona, persona_resolution = resolve_power_developer_persona(
        target_persona
    )

    # Log persona resolution
    if persona_resolution == "defaulted":
        print("🔄 Power Developer Analysis - Project Type requested: <default>")
        print("   ℹ️ No project type supplied, defaulting to 'greenfield'")
    elif persona_resolution == "invalid":
        print(f"🔄 Power Developer Analysis - Project Type requested: {requested_persona}")
        print(f"   ⚠️ Invalid project type '{requested_persona}', using 'greenfield'")
    else:
        print(f"🔄 Power Developer Analysis - Project Type requested: {requested_persona}")
        print(f"   🎯 Using project type '{resolved_persona}'")

    # Process weights (PHASE 1)
    if custom_weights:
        print(f"   🎚️ Custom weights provided: {len(custom_weights)} criteria")
        weights = normalize_frontend_weights(custom_weights)
        print(f"   ✅ Weights normalized: {', '.join([f'{k}={v:.3f}' for k, v in weights.items()])}")

        # Extract demand_scale and convert to user_ideal_mw if not provided
        if not user_ideal_mw and "demand_scale" in custom_weights:
            user_ideal_mw = map_demand_scale_to_mw(custom_weights["demand_scale"])
            print(f"   📏 Extracted user_ideal_mw from demand_scale: {user_ideal_mw} MW")
    else:
        weights = POWER_DEVELOPER_PERSONAS[resolved_persona]
        print(f"   🎯 Using default weights for '{resolved_persona}' persona")

    # Log user inputs
    if user_ideal_mw:
        print(f"   🎯 Target capacity: {user_ideal_mw} MW")
    if user_max_price_mwh:
        print(f"   💰 Max price budget: £{user_max_price_mwh}/MWh")

    # Import helper functions from global scope
    from backend.power_workflow import (
        _extract_coordinates,
        _coerce_float,
    )

    def transform_tec_to_project_schema(tec_row: Dict[str, Any]) -> Dict[str, Any]:
        """Transform TEC row to unified schema."""
        latitude, longitude = _extract_coordinates(tec_row)
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

    def get_color_from_score_impl(internal_score: float) -> str:
        """Simple color coding implementation."""
        if internal_score >= 90:
            return "#00FF00"
        elif internal_score >= 70:
            return "#90EE90"
        elif internal_score >= 50:
            return "#FFFF00"
        elif internal_score >= 30:
            return "#FFA500"
        else:
            return "#FF0000"

    def get_rating_description_impl(internal_score: float) -> str:
        """Simple rating description implementation."""
        if internal_score >= 90:
            return "Excellent"
        elif internal_score >= 80:
            return "Very Good"
        elif internal_score >= 70:
            return "Good"
        elif internal_score >= 60:
            return "Above Average"
        elif internal_score >= 50:
            return "Average"
        elif internal_score >= 40:
            return "Below Average"
        elif internal_score >= 30:
            return "Poor"
        elif internal_score >= 20:
            return "Very Poor"
        else:
            return "Bad"

    # Call the main workflow function
    response = await run_power_developer_analysis(
        limit=limit,
        source_table=source_table,
        target_persona=resolved_persona,
        requested_persona=requested_persona,
        persona_resolution=persona_resolution,
        weights=weights,
        user_ideal_mw=user_ideal_mw,
        user_max_price_mwh=user_max_price_mwh,
        apply_capacity_filter=apply_capacity_filter,
        query_supabase=query_supabase,
        transform_tec_to_project_schema=transform_tec_to_project_schema,
        calculate_proximity_scores_batch=calculate_proximity_scores_batch,
        build_persona_component_scores=build_persona_component_scores,
        get_color_from_score=get_color_from_score_impl,
        get_rating_description=get_rating_description_impl,
    )

    # Convert Pydantic model to dict for backward compatibility
    return {
        "type": response.type,
        "features": [
            {
                "type": f.type,
                "geometry": f.geometry,
                "properties": f.properties,
            }
            for f in response.features
        ],
        "metadata": response.metadata,
    }


# ============================================================================
# HELPER FUNCTIONS (for transform_tec_to_project_schema)
# ============================================================================

def _coerce_float(value: Any) -> Optional[float]:
    """Safely coerce a value to float, returning None if not possible."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return None


def _extract_coordinates(row: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Return latitude/longitude from heterogeneous Supabase payloads."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    latitude_keys = ["latitude", "lat", "Latitude", "Latitude_deg"]
    longitude_keys = ["longitude", "lon", "lng", "Longitude", "Longitude_deg"]

    for key in latitude_keys:
        if key in row:
            latitude = _coerce_float(row.get(key))
            if latitude is not None:
                break

    for key in longitude_keys:
        if key in row:
            longitude = _coerce_float(row.get(key))
            if longitude is not None:
                break

    if (latitude is None or longitude is None) and isinstance(row.get("location"), dict):
        location_data = row.get("location")
        latitude = latitude or _coerce_float(
            location_data.get("lat") or location_data.get("latitude")
        )
        longitude = longitude or _coerce_float(
            location_data.get("lon")
            or location_data.get("lng")
            or location_data.get("longitude")
        )

    if (latitude is None or longitude is None) and isinstance(row.get("coordinates"), (list, tuple)):
        coords = row.get("coordinates")
        if len(coords) >= 2:
            longitude = longitude or _coerce_float(coords[0])
            latitude = latitude or _coerce_float(coords[1])

    return latitude, longitude
