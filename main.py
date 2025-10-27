"""
Infranodal API v2.1 - Main Application Entry Point
Contains route handlers only - business logic is in separate modules.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Import configuration
from config import (
    PERSONA_CAPACITY_RANGES,
    PERSONA_WEIGHTS,
    POWER_DEVELOPER_PERSONAS,
    PersonaType,
    PowerDeveloperPersona,
    resolve_power_developer_persona,
)

# Import models
from models import (
    FinancialModelRequest,
    FinancialModelResponse,
    ModelResults,
    RevenueBreakdown,
    TecConnectionFeature,
    TecConnectionsResponse,
    UserSite,
)

# Import database functions
from database import query_supabase

# Import infrastructure functions
from infrastructure import _coerce_float

# Import proximity functions
from proximity import get_color_from_score, get_rating_description

# Import TNUoS functions
from tnuos import enrich_and_rescore_top_25_with_tnuos

# Import scoring functions
from scoring import (
    build_persona_component_scores,
    calculate_best_customer_match,
    calculate_custom_weighted_score,
    calculate_enhanced_investment_rating,
    calculate_persona_topsis_score,
    calculate_persona_weighted_score,
    calculate_proximity_scores_batch,
    calculate_rating_distribution,
    filter_projects_by_persona_capacity,
)

# Import financial functions
from financial import (
    create_btm_market_prices,
    create_technology_params,
    create_utility_market_prices,
    extract_revenue_breakdown,
    map_technology_type,
)

# Import transformer functions
from transformers import (
    _extract_coordinates,
    transform_tec_row_to_feature,
    transform_tec_to_project_schema,
)

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

print("Booting model...")
_boot_start_time = time.time()

print("Initializing environment configuration...")
_env_start_time = time.time()
load_dotenv()
print(f"[✓] Environment variables loaded in {time.time() - _env_start_time:.2f}s")

# Try to import renewable financial model components
try:
    print("Loading renewable financial model components...")
    from backend.renewable_model import (
        FinancialAssumptions,
        MarketPrices,
        MarketRegion,
        ProjectType,
        RenewableFinancialModel,
        TechnologyParams,
        TechnologyType,
    )

    FINANCIAL_MODEL_AVAILABLE = True
    print("[✓] Renewable financial model components loaded successfully")
except ImportError as exc:
    print(f"Error initializing renewable financial model components: {exc}")
    FINANCIAL_MODEL_AVAILABLE = False

# ============================================================================
# FASTAPI INITIALIZATION
# ============================================================================

print("Initializing FastAPI renderer...")
_api_start_time = time.time()
app = FastAPI(title="Infranodal API", version="2.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
print(f"[✓] FastAPI renderer initialized in {time.time() - _api_start_time:.2f}s")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

print(f"✅ SUPABASE_URL: {SUPABASE_URL}")
print(f"✅ SUPABASE_KEY exists: {bool(SUPABASE_KEY)}")

# ============================================================================
# ROUTE HANDLERS
# ============================================================================


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint - API health check."""
    return {"message": "Infranodal API v2.1 with Persona-Based Scoring", "status": "active"}


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint with database connectivity test."""
    try:
        print("🔄 Testing database connection...")
        data = await query_supabase("renewable_projects?select=count")
        count = len(data)
        print(f"✅ Database connected: {count} records")
        return {"status": "healthy", "database": "connected", "projects": count}
    except Exception as exc:
        print(f"❌ Database error: {exc}")
        return {"status": "degraded", "database": "disconnected", "error": str(exc)}


@app.get("/api/projects")
async def get_projects(
    limit: int = Query(5000),
    technology: Optional[str] = None,
    country: Optional[str] = None,
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring"),
) -> List[Dict[str, Any]]:
    """Get renewable projects with optional filtering and persona-based scoring."""
    # Build query
    query_parts = ["renewable_projects?select=*"]
    filters = []
    if technology:
        filters.append(f"technology_type.ilike.%{technology}%")
    if country:
        filters.append(f"country.ilike.%{country}%")
    if filters:
        query_parts.extend(filters)
    endpoint = "&".join(query_parts)
    projects = await query_supabase(endpoint, limit=limit)

    # Score each project
    for project in projects:
        dummy_proximity = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "nearest_distances": {},
        }
        if persona:
            rating_result = calculate_persona_weighted_score(project, dummy_proximity, persona)
        else:
            rating_result = calculate_enhanced_investment_rating(project, dummy_proximity)
        project.update(
            {
                "investment_rating": rating_result["investment_rating"],
                "rating_description": rating_result["rating_description"],
                "color_code": rating_result["color_code"],
                "component_scores": rating_result.get("component_scores"),
                "weighted_contributions": rating_result.get("weighted_contributions"),
                "persona": rating_result.get("persona"),
                "base_score": rating_result.get("base_investment_score", rating_result["investment_rating"]),
                "infrastructure_bonus": rating_result.get("infrastructure_bonus", 0.0),
            }
        )
    return projects


@app.get("/api/projects/geojson")
async def get_geojson(
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring"),
) -> Dict[str, Any]:
    """Get renewable projects as GeoJSON FeatureCollection."""
    projects = await query_supabase("renewable_projects?select=*", limit=500)
    features: List[Dict[str, Any]] = []

    for project in projects:
        if not project.get("longitude") or not project.get("latitude"):
            continue
        dummy_proximity = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "nearest_distances": {},
        }
        if persona:
            rating_result = calculate_persona_weighted_score(project, dummy_proximity, persona)
        else:
            rating_result = calculate_enhanced_investment_rating(project, dummy_proximity)

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [project["longitude"], project["latitude"]],
                },
                "properties": {
                    "ref_id": project["ref_id"],
                    "site_name": project["site_name"],
                    "technology_type": project["technology_type"],
                    "operator": project.get("operator"),
                    "capacity_mw": project.get("capacity_mw"),
                    "county": project.get("county"),
                    "country": project.get("country"),
                    "investment_rating": rating_result["investment_rating"],
                    "rating_description": rating_result["rating_description"],
                    "color_code": rating_result["color_code"],
                    "component_scores": rating_result.get("component_scores"),
                    "weighted_contributions": rating_result.get("weighted_contributions"),
                    "persona": rating_result.get("persona"),
                    "base_score": rating_result.get("base_investment_score", rating_result["investment_rating"]),
                    "infrastructure_bonus": rating_result.get("infrastructure_bonus", 0.0),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


@app.post("/api/user-sites/score")
async def score_user_sites(
    sites: List[UserSite],
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring"),
) -> Dict[str, Any]:
    """Score user-submitted sites with persona-based or renewable energy scoring."""
    if not sites:
        raise HTTPException(400, "No sites provided")

    # Validate sites
    for index, site in enumerate(sites):
        if not (49.8 <= site.latitude <= 60.9) or not (-10.8 <= site.longitude <= 2.0):
            raise HTTPException(400, f"Site {index + 1}: Coordinates outside UK bounds")
        if not (5 <= site.capacity_mw <= 500):
            raise HTTPException(400, f"Site {index + 1}: Capacity must be between 5-500 MW")
        if not (2025 <= site.commissioning_year <= 2035):
            raise HTTPException(400, f"Site {index + 1}: Commissioning year must be between 2025-2035")

    scoring_mode = "persona-based" if persona else "renewable energy"
    print(f"🔄 Scoring {len(sites)} user-submitted sites with {scoring_mode.upper()} system...")
    start_time = time.time()

    # Convert sites to dict format
    sites_for_calc: List[Dict[str, Any]] = []
    for site in sites:
        sites_for_calc.append(
            {
                "site_name": site.site_name,
                "technology_type": site.technology_type,
                "capacity_mw": site.capacity_mw,
                "latitude": site.latitude,
                "longitude": site.longitude,
                "commissioning_year": site.commissioning_year,
                "is_btm": site.is_btm,
                "development_status_short": site.development_status_short or "planning",
                "capacity_factor": site.capacity_factor,
            }
        )

    # Calculate proximity scores
    proximity_scores = await calculate_proximity_scores_batch(sites_for_calc)

    # Score each site
    scored_sites: List[Dict[str, Any]] = []
    for index, site_data in enumerate(sites_for_calc):
        prox_scores = (
            proximity_scores[index]
            if index < len(proximity_scores)
            else {
                "substation_score": 0.0,
                "transmission_score": 0.0,
                "fiber_score": 0.0,
                "ixp_score": 0.0,
                "water_score": 0.0,
                "total_proximity_bonus": 0.0,
                "nearest_distances": {},
            }
        )
        if persona:
            rating_result = calculate_persona_weighted_score(site_data, prox_scores, persona)
        else:
            rating_result = calculate_enhanced_investment_rating(site_data, prox_scores)

        scored_sites.append(
            {
                "site_name": site_data["site_name"],
                "technology_type": site_data["technology_type"],
                "capacity_mw": site_data["capacity_mw"],
                "commissioning_year": site_data["commissioning_year"],
                "is_btm": site_data["is_btm"],
                "coordinates": [site_data["longitude"], site_data["latitude"]],
                "investment_rating": rating_result["investment_rating"],
                "rating_description": rating_result["rating_description"],
                "color_code": rating_result["color_code"],
                "component_scores": rating_result.get("component_scores"),
                "weighted_contributions": rating_result.get("weighted_contributions"),
                "persona": rating_result.get("persona"),
                "base_score": rating_result.get("base_investment_score", rating_result["investment_rating"]),
                "infrastructure_bonus": rating_result.get("infrastructure_bonus", 0.0),
                "nearest_infrastructure": rating_result["nearest_infrastructure"],
                "methodology": f"{scoring_mode} scoring system",
            }
        )

    processing_time = time.time() - start_time
    print(f"✅ User sites scored with {scoring_mode.upper()} SYSTEM in {processing_time:.2f}s")

    return {
        "sites": scored_sites,
        "metadata": {
            "scoring_system": f"{scoring_mode} - 1.0-10.0 Investment Rating Scale",
            "persona": persona,
            "processing_time_seconds": round(processing_time, 2),
            "algorithm_version": "2.1 - Persona-Based Infrastructure Proximity Enhanced",
            "rating_scale": {
                "9.0-10.0": "Excellent - Premium investment opportunity",
                "8.0-8.9": "Very Good - Strong investment potential",
                "7.0-7.9": "Good - Solid investment opportunity",
                "6.0-6.9": "Above Average - Moderate investment potential",
                "5.0-5.9": "Average - Standard investment opportunity",
                "4.0-4.9": "Below Average - Limited investment appeal",
                "3.0-3.9": "Poor - Significant investment challenges",
                "2.0-2.9": "Very Poor - High risk investment",
                "1.0-1.9": "Bad - Unfavorable investment conditions",
            },
        },
    }


@app.get("/api/projects/enhanced")
async def get_enhanced_geojson(
    limit: int = Query(5000, description="Number of projects to process"),
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring"),
    apply_capacity_filter: bool = Query(True, description="Filter projects by persona capacity requirements"),
    custom_weights: Optional[str] = Query(None, description="JSON string of custom weights (overrides persona)"),
    scoring_method: str = Query(
        "weighted_sum",
        description="Scoring method to apply (weighted_sum or topsis)",
    ),
    dc_demand_mw: Optional[float] = Query(None, description="DC facility demand in MW for capacity gating"),
    source_table: str = Query(
        "renewable_projects",
        description="Source table - will be demand_sites for power devs in future",
    ),
    user_max_price_mwh: Optional[float] = Query(
        None,
        description="User's maximum acceptable power price (£/MWh) for price_sensitivity scoring",
    ),
) -> Dict[str, Any]:
    """
    Enhanced GeoJSON endpoint with persona-based scoring, TOPSIS support, and TNUoS enrichment.
    """
    start_time = time.time()
    parsed_custom_weights = None
    if custom_weights:
        try:
            parsed_custom_weights = json.loads(custom_weights)
            total = sum(parsed_custom_weights.values())
            if total and abs(total - 1.0) > 0.01:
                parsed_custom_weights = {key: value / total for key, value in parsed_custom_weights.items()}
        except (json.JSONDecodeError, AttributeError):
            parsed_custom_weights = None

    active_scoring_method = scoring_method.lower()
    use_topsis = active_scoring_method == "topsis"
    scoring_mode = "custom weights" if parsed_custom_weights else ("persona-based" if persona else "renewable energy")
    print(
        "🚀 ENHANCED ENDPOINT WITH "
        f"{scoring_mode.upper()} SCORING [{active_scoring_method.upper()}] - Processing {limit} projects..."
    )

    # Fetch projects
    try:
        projects = await query_supabase(f"{source_table}?select=*", limit=limit)
        print(f"✅ Loaded {len(projects)} projects from {source_table}")
        if persona and apply_capacity_filter:
            original_count = len(projects)
            projects = filter_projects_by_persona_capacity(projects, persona)
            print(f"🎯 Filtered to {len(projects)} projects for {persona} (was {original_count})")
        if persona:
            dc_thresholds = {"hyperscaler": 30.0, "colocation": 5.0, "edge_computing": 1.0}
            min_capacity = dc_thresholds.get(persona, 1.0)
            capacity_gated: List[Dict[str, Any]] = []
            for project in projects:
                project_capacity = project.get("capacity_mw", 0) or 0
                if project_capacity >= min_capacity * 0.9:
                    capacity_gated.append(project)
            if len(capacity_gated) != len(projects):
                print(
                    f"⚡ Capacity gating: {len(capacity_gated)}/{len(projects)} projects meet minimum capacity for {persona}"
                )
            projects = capacity_gated
    except Exception as exc:
        print(f"❌ Database error: {exc}")
        return {"error": "Database connection failed", "type": "FeatureCollection", "features": []}

    valid_projects = [project for project in projects if project.get("longitude") and project.get("latitude")]
    print(f"📍 {len(valid_projects)} projects have valid coordinates")
    if not valid_projects:
        return {"type": "FeatureCollection", "features": [], "metadata": {"error": "No projects with valid coordinates"}}

    # Calculate proximity scores
    try:
        print("🔄 Starting batch proximity calculation...")
        batch_start = time.time()
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects)
        batch_time = time.time() - batch_start
        print(f"✅ Batch proximity calculation completed in {batch_time:.2f}s")
    except Exception as exc:
        print(f"❌ Error in batch proximity calculation: {exc}")
        all_proximity_scores = [
            {
                "substation_score": 0.0,
                "transmission_score": 0.0,
                "fiber_score": 0.0,
                "ixp_score": 0.0,
                "water_score": 0.0,
                "total_proximity_bonus": 0.0,
                "nearest_distances": {},
            }
            for _ in valid_projects
        ]

    def get_proximity_scores_for_index(idx: int) -> Dict[str, float]:
        if idx < len(all_proximity_scores):
            return all_proximity_scores[idx]
        return {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "total_proximity_bonus": 0.0,
            "nearest_distances": {},
        }

    # TOPSIS-specific variables
    topsis_component_scores: List[Dict[str, float]] = []
    topsis_results: List[Dict[str, Any]] = []
    topsis_ideal_solution: Dict[str, float] = {}
    topsis_anti_ideal_solution: Dict[str, float] = {}
    weights_for_topsis: Dict[str, float] = {}
    topsis_persona_label: Optional[str] = persona
    persona_for_components: Optional[str] = persona if persona else None

    if use_topsis:
        # Determine weights for TOPSIS
        if parsed_custom_weights:
            weights_for_topsis = parsed_custom_weights
            persona_for_components = "custom"
            topsis_persona_label = persona or "custom"
        elif persona:
            weights_for_topsis = PERSONA_WEIGHTS[persona]
            persona_for_components = persona
            topsis_persona_label = persona
        else:
            topsis_persona_label = "hyperscaler"
            weights_for_topsis = PERSONA_WEIGHTS[topsis_persona_label]
            persona_for_components = topsis_persona_label
            print(
                "⚠️ TOPSIS requested without persona/custom weights; defaulting to hyperscaler persona weights"
            )

        # Collect component scores for all projects
        for index, project in enumerate(valid_projects):
            proximity_scores = get_proximity_scores_for_index(index)
            component_scores = build_persona_component_scores(
                project,
                proximity_scores,
                persona_for_components,
                user_max_price_mwh=user_max_price_mwh,
            )
            topsis_component_scores.append(component_scores)

        # Calculate TOPSIS scores
        topsis_output = calculate_persona_topsis_score(topsis_component_scores, weights_for_topsis)
        topsis_results = topsis_output.get("scores", []) if topsis_output else []
        topsis_ideal_solution = topsis_output.get("ideal_solution", {}) if topsis_output else {}
        topsis_anti_ideal_solution = topsis_output.get("anti_ideal_solution", {}) if topsis_output else {}

    features: List[Dict[str, Any]] = []
    for index, project in enumerate(valid_projects):
        try:
            proximity_scores = get_proximity_scores_for_index(index)

            if use_topsis:
                # TOPSIS scoring path
                component_scores = (
                    topsis_component_scores[index]
                    if index < len(topsis_component_scores)
                    else build_persona_component_scores(
                        project,
                        proximity_scores,
                        persona_for_components,
                        user_max_price_mwh=user_max_price_mwh,
                    )
                )
                topsis_info = topsis_results[index] if index < len(topsis_results) else None

                if not topsis_info:
                    # Fallback to weighted sum if TOPSIS fails
                    if parsed_custom_weights:
                        rating_result = calculate_custom_weighted_score(
                            project, proximity_scores, parsed_custom_weights
                        )
                    elif persona:
                        rating_result = calculate_persona_weighted_score(
                            project, proximity_scores, persona, "demand", user_max_price_mwh
                        )
                    else:
                        rating_result = calculate_enhanced_investment_rating(project, proximity_scores)
                else:
                    # Use TOPSIS results
                    closeness = topsis_info.get("closeness_coefficient", 0.0)
                    internal_total_score = 10.0 + closeness * 90.0
                    display_rating = round(internal_total_score / 10.0, 1)
                    color = get_color_from_score(internal_total_score)
                    description = get_rating_description(internal_total_score)

                    component_scores_rounded = {
                        key: round(value, 1) for key, value in component_scores.items()
                    }
                    weighted_contributions = {
                        key: round(component_scores.get(key, 0.0) * weights_for_topsis.get(key, 0.0), 1)
                        for key in component_scores
                    }

                    rating_result = {
                        "investment_rating": display_rating,
                        "rating_description": description,
                        "color_code": color,
                        "component_scores": component_scores_rounded,
                        "weighted_contributions": weighted_contributions,
                        "persona": topsis_persona_label,
                        "persona_weights": weights_for_topsis,
                        "internal_total_score": round(internal_total_score, 1),
                        "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
                        "topsis_metrics": {
                            "distance_to_ideal": topsis_info.get("distance_to_ideal"),
                            "distance_to_anti_ideal": topsis_info.get("distance_to_anti_ideal"),
                            "closeness_coefficient": closeness,
                            "weighted_normalized_scores": topsis_info.get("weighted_normalized_scores"),
                            "normalized_scores": topsis_info.get("normalized_scores"),
                        },
                        "scoring_methodology": "Persona TOPSIS scoring (closeness scaled to 1-10)",
                    }
            else:
                # Traditional weighted sum scoring
                if parsed_custom_weights:
                    rating_result = calculate_custom_weighted_score(
                        project, proximity_scores, parsed_custom_weights
                    )
                elif persona:
                    rating_result = calculate_persona_weighted_score(
                        project,
                        proximity_scores,
                        persona,
                        "demand",
                        user_max_price_mwh,
                    )
                else:
                    rating_result = calculate_enhanced_investment_rating(project, proximity_scores)

            # Build feature properties
            properties: Dict[str, Any] = {
                "ref_id": project.get("ref_id") or project.get("id"),
                "site_name": project.get("site_name") or project.get("project_name"),
                "technology_type": project.get("technology_type"),
                "operator": project.get("operator"),
                "capacity_mw": project.get("capacity_mw"),
                "development_status_short": project.get("development_status_short"),
                "county": project.get("county"),
                "country": project.get("country"),
                "investment_rating": rating_result["investment_rating"],
                "rating_description": rating_result["rating_description"],
                "color_code": rating_result["color_code"],
                "component_scores": rating_result.get("component_scores"),
                "weighted_contributions": rating_result.get("weighted_contributions"),
                "nearest_infrastructure": rating_result["nearest_infrastructure"],
                "persona": rating_result.get("persona"),
                "persona_weights": rating_result.get("persona_weights"),
                "base_score": rating_result.get("base_investment_score", rating_result["investment_rating"]),
                "infrastructure_bonus": rating_result.get("infrastructure_bonus", 0.0),
                "internal_total_score": rating_result.get("internal_total_score"),
            }

            # Add TOPSIS-specific metrics if using TOPSIS
            if use_topsis and "topsis_metrics" in rating_result:
                properties["topsis_metrics"] = rating_result["topsis_metrics"]
                properties["scoring_methodology"] = rating_result.get("scoring_methodology")

            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [project["longitude"], project["latitude"]],
                    },
                    "properties": properties,
                }
            )
        except Exception as exc:
            print(f"❌ Error processing project {index + 1}: {exc}")
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [project["longitude"], project["latitude"]],
                    },
                    "properties": {
                        "ref_id": project.get("ref_id") or project.get("id"),
                        "site_name": project.get("site_name") or project.get("project_name"),
                        "operator": project.get("operator"),
                        "technology_type": project.get("technology_type"),
                        "capacity_mw": project.get("capacity_mw"),
                        "county": project.get("county"),
                        "country": project.get("country"),
                        "investment_rating": 5.0,
                        "rating_description": "Average",
                        "color_code": "#FFFF00",
                        "nearest_infrastructure": {},
                    },
                }
            )

    # Enrich top 25 with TNUoS data
    try:
        features = await enrich_and_rescore_top_25_with_tnuos(features, persona)
    except Exception as exc:
        print(f"⚠️ TNUoS enrichment skipped: {exc}")

    # Sort by rating
    def _coerce_rating(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    top_projects = [
        feature
        for feature in features
        if isinstance(feature, dict)
        and isinstance(feature.get("properties"), dict)
        and feature["properties"].get("investment_rating") is not None
    ]
    top_projects.sort(
        key=lambda feature: _coerce_rating(feature["properties"].get("investment_rating"))
        or -math.inf,
        reverse=True,
    )

    if top_projects:
        print("🏆 Top 5 projects by investment rating:")
        for index, feature in enumerate(top_projects[:5], start=1):
            properties = feature.get("properties", {})
            rating_value = _coerce_rating(properties.get("investment_rating"))
            rating_display = f"{rating_value:.2f}" if rating_value is not None else "n/a"
            capacity_value = properties.get("capacity_mw")
            if isinstance(capacity_value, (int, float)):
                capacity_display = f"{capacity_value:.1f}MW"
            elif capacity_value:
                capacity_display = str(capacity_value)
            else:
                capacity_display = "n/a"
            status_display = properties.get("development_status_short") or properties.get("rating_description") or "Unknown status"
            tech_display = properties.get("technology_type") or "Unknown tech"
            name_display = properties.get("site_name") or properties.get("ref_id") or "Unknown site"
            print(
                f"  {index}. {name_display} ({tech_display}) — rating {rating_display} • {capacity_display} • {status_display}"
            )

    processing_time = time.time() - start_time
    if persona:
        print(
            f"🎯 PERSONA-BASED SCORING ({persona.upper()}) COMPLETE: {len(features)} features in {processing_time:.2f}s"
        )
    else:
        print(f"🎯 RENEWABLE ENERGY SCORING COMPLETE: {len(features)} features in {processing_time:.2f}s")

    # Build metadata
    metadata: Dict[str, Any] = {
        "scoring_system": f"{scoring_mode} - 1.0-10.0 display scale",
        "scoring_method": active_scoring_method,
        "persona": persona,
        "processing_time_seconds": round(processing_time, 2),
        "projects_processed": len(features),
        "algorithm_version": "2.1 - Persona-Based Infrastructure Scoring",
        "performance_optimization": "Cached infrastructure + batch proximity scoring",
        "rating_distribution": calculate_rating_distribution(features),
        "rating_scale_guide": {
            "excellent": "9.0-10.0",
            "very_good": "8.0-8.9",
            "good": "7.0-7.9",
            "above_average": "6.0-6.9",
            "average": "5.0-5.9",
            "below_average": "4.0-4.9",
        },
    }

    # Add TOPSIS-specific metadata if using TOPSIS
    if use_topsis:
        metadata.update(
            {
                "topsis_ideal_solution": {
                    key: round(value, 6) for key, value in topsis_ideal_solution.items()
                },
                "topsis_anti_ideal_solution": {
                    key: round(value, 6) for key, value in topsis_anti_ideal_solution.items()
                },
                "topsis_persona_reference": topsis_persona_label,
            }
        )

    return {"type": "FeatureCollection", "features": features, "metadata": metadata}


@app.get("/api/infrastructure/transmission")
async def get_transmission_lines() -> Dict[str, Any]:
    """Get transmission lines as GeoJSON."""
    lines = await query_supabase("transmission_lines?select=*")
    features: List[Dict[str, Any]] = []
    for line in lines or []:
        if not line.get("path_coordinates"):
            continue
        try:
            coordinates = json.loads(line["path_coordinates"])
        except (TypeError, json.JSONDecodeError):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coordinates},
                "properties": {
                    "name": line.get("line_name"),
                    "voltage_kv": line.get("voltage_kv"),
                    "operator": line.get("operator"),
                    "type": "transmission_line",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/substations")
async def get_substations() -> Dict[str, Any]:
    """Get substations as GeoJSON."""
    stations = await query_supabase("substations?select=*")
    features: List[Dict[str, Any]] = []
    for station in stations or []:
        lat = _coerce_float(
            station.get("latitude")
            or station.get("lat")
            or station.get("Lat")
        )
        lon = _coerce_float(
            station.get("longitude")
            or station.get("lon")
            or station.get("Long")
        )
        if lat is None or lon is None:
            continue
        name = (
            station.get("substation_name")
            or station.get("name")
            or station.get("SUBST_NAME")
        )
        operator = station.get("operator") or station.get("COMPANY")
        voltage = _coerce_float(
            station.get("primary_voltage_kv")
            or station.get("voltage_kv")
            or station.get("VOLTAGE_HIGH")
        )
        capacity_mva = _coerce_float(station.get("capacity_mva"))
        constraint_status = station.get("constraint_status") or station.get(
            "CONSTRAINT STATUS"
        )

        properties: Dict[str, Any] = {
            "name": name,
            "substation_name": name,
            "operator": operator,
            "primary_voltage_kv": voltage,
            "voltage_kv": voltage,
            "capacity_mva": capacity_mva,
            "type": "substation",
        }
        if constraint_status is not None:
            properties["constraint_status"] = constraint_status
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": properties,
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/gsp")
async def get_gsp_boundaries() -> Dict[str, Any]:
    """Get GSP boundaries as GeoJSON."""
    boundaries = await query_supabase("electrical_grid?type=eq.gsp_boundary&select=*")
    features: List[Dict[str, Any]] = []
    for boundary in boundaries or []:
        geometry = boundary.get("geometry")
        if not geometry:
            continue
        if isinstance(geometry, str):
            try:
                geometry = json.loads(geometry)
            except json.JSONDecodeError:
                continue
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "name": boundary.get("name"),
                    "operator": boundary.get("operator", "NESO"),
                    "type": "gsp_boundary",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/fiber")
async def get_fiber_cables() -> Dict[str, Any]:
    """Get fiber cables as GeoJSON."""
    cables = await query_supabase("fiber_cables?select=*")
    features: List[Dict[str, Any]] = []
    for cable in cables or []:
        if not cable.get("route_coordinates"):
            continue
        try:
            coordinates = json.loads(cable["route_coordinates"])
        except (TypeError, json.JSONDecodeError):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coordinates},
                "properties": {
                    "name": cable.get("cable_name"),
                    "operator": cable.get("operator"),
                    "cable_type": cable.get("cable_type"),
                    "type": "fiber_cable",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/tnuos")
async def get_tnuos_zones() -> Dict[str, Any]:
    """Get TNUoS zones as GeoJSON."""
    zones = await query_supabase("tnuos_zones?tariff_year=eq.2024-25&select=*")
    features: List[Dict[str, Any]] = []
    for zone in zones or []:
        geometry = zone.get("geometry")
        if not geometry:
            continue
        if isinstance(geometry, str):
            try:
                geometry = json.loads(geometry)
            except json.JSONDecodeError:
                continue
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "zone_id": zone.get("zone_id"),
                    "zone_name": zone.get("zone_name"),
                    "tariff_pounds_per_kw": zone.get("generation_tariff_pounds_per_kw"),
                    "tariff_year": zone.get("tariff_year"),
                    "effective_from": zone.get("effective_from"),
                    "type": "tnuos_zone",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/ixp")
async def get_internet_exchanges() -> Dict[str, Any]:
    """Get internet exchange points as GeoJSON."""
    ixps = await query_supabase("internet_exchange_points?select=*")
    features: List[Dict[str, Any]] = []
    for ixp in ixps or []:
        if not ixp.get("longitude") or not ixp.get("latitude"):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [ixp["longitude"], ixp["latitude"]]},
                "properties": {
                    "name": ixp.get("ixp_name"),
                    "operator": ixp.get("operator"),
                    "city": ixp.get("city"),
                    "networks": ixp.get("connected_networks"),
                    "capacity_gbps": ixp.get("capacity_gbps"),
                    "type": "ixp",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/water")
async def get_water_resources() -> Dict[str, Any]:
    """Get water resources as GeoJSON."""
    water_sources = await query_supabase("water_resources?select=*")
    features: List[Dict[str, Any]] = []
    for water in water_sources or []:
        if not water.get("coordinates"):
            continue
        try:
            coordinates = json.loads(water["coordinates"])
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(coordinates, (list, tuple)) and len(coordinates) == 2 and all(
            isinstance(coord, (int, float)) for coord in coordinates
        ):
            geometry = {"type": "Point", "coordinates": coordinates}
        else:
            geometry = {"type": "LineString", "coordinates": coordinates}
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "name": water.get("resource_name"),
                    "resource_type": water.get("resource_type"),
                    "water_quality": water.get("water_quality"),
                    "flow_rate": water.get("flow_rate_liters_sec"),
                    "capacity": water.get("capacity_million_liters"),
                    "type": "water_resource",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/dno-areas")
async def get_dno_license_areas() -> Dict[str, Any]:
    """Return DNO license areas as GeoJSON FeatureCollection."""
    try:
        print("🔄 Fetching DNO license areas from database...")

        areas = await query_supabase("dno_license_areas?select=*")

        features: List[Dict[str, Any]] = []

        for area in areas or []:
            geometry = area.get("geometry")

            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "id": area.get("id"),
                        "name": area.get("dno_name"),
                        "dno_name": area.get("dno_name"),
                        "license_area": area.get("license_area"),
                        "company": area.get("company"),
                        "region": area.get("region"),
                        "type": "dno_area",
                    },
                }
            )

        print(f"✅ Returning {len(features)} DNO license areas")

        return {"type": "FeatureCollection", "features": features}

    except Exception as exc:
        print(f"❌ DNO areas endpoint error: {exc}")
        raise HTTPException(500, f"Failed to fetch DNO license areas: {exc}")


@app.get("/api/projects/compare-scoring")
async def compare_scoring_systems(
    limit: int = Query(10, description="Projects to compare"),
    persona: PersonaType = Query("hyperscaler", description="Persona for comparison"),
) -> Dict[str, Any]:
    """Compare renewable energy scoring vs persona-based scoring."""
    projects = await query_supabase("renewable_projects?select=*", limit=limit)
    comparison: List[Dict[str, Any]] = []
    for project in projects:
        if not project.get("longitude") or not project.get("latitude"):
            continue
        dummy_proximity = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "nearest_distances": {},
        }
        renewable_rating = calculate_enhanced_investment_rating(project, dummy_proximity)
        persona_rating = calculate_persona_weighted_score(project, dummy_proximity, persona)
        comparison.append(
            {
                "site_name": project.get("site_name"),
                "capacity_mw": project.get("capacity_mw"),
                "technology_type": project.get("technology_type"),
                "renewable_energy_system": {
                    "investment_rating": renewable_rating["investment_rating"],
                    "rating_description": renewable_rating["rating_description"],
                    "color": renewable_rating["color_code"],
                },
                "persona_system": {
                    "persona": persona,
                    "investment_rating": persona_rating["investment_rating"],
                    "rating_description": persona_rating["rating_description"],
                    "color": persona_rating["color_code"],
                    "component_scores": persona_rating["component_scores"],
                    "weighted_contributions": persona_rating["weighted_contributions"],
                },
            }
        )
    return {
        "comparison": comparison,
        "summary": {
            "renewable_system": "Traditional renewable energy scoring (capacity, stage, tech)",
            "persona_system": f"{persona} data center scoring with custom weightings",
            "persona_weights": PERSONA_WEIGHTS[persona],
            "migration_benefits": [
                "Scoring tailored to specific data center requirements",
                "Transparent component breakdown showing why sites score differently",
                "Infrastructure priorities matching real deployment needs",
                "Better investment decision making for specific use cases",
            ],
        },
    }


@app.post("/api/projects/power-developer-analysis")
async def analyze_for_power_developer(
    criteria: Dict[str, Any] = Body(default_factory=dict),
    site_location: Optional[Dict[str, float]] = None,
    target_persona: Optional[str] = Query(
        None, description="greenfield, repower, or stranded"
    ),
    limit: int = Query(5000),
    source_table: str = Query(
        "tec_connections", description="Source table: tec_connections or renewable_projects"
    ),
) -> Dict[str, Any]:
    """
    Power developer workflow - analyzes TEC grid connections for development opportunity.
    """
    start_time = time.time()

    # Validate input
    target_persona, requested_persona, persona_resolution = resolve_power_developer_persona(
        target_persona
    )

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

    weights = POWER_DEVELOPER_PERSONAS[target_persona]

    # Fetch projects from database
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

    # Transform rows to project schema
    print("   🔄 Transforming to project schema...")

    if source_table == "tec_connections":
        projects = [transform_tec_to_project_schema(row) for row in raw_rows]
    else:
        projects = raw_rows

    # Filter for valid coordinates
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

    # Calculate infrastructure proximity scores
    print("   🔄 Calculating proximity scores...")

    try:
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects)
        print(f"   ✅ Proximity calculations complete")
    except Exception as exc:
        print(f"   ❌ Proximity calculation error: {exc}")
        raise

    # Score each project using power developer weights
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

            # Build component scores
            component_scores = build_persona_component_scores(
                project,
                proximity_scores,
                persona=target_persona,
                perspective="demand",
            )

            # Apply power developer weights
            weighted_score = sum(
                component_scores.get(criterion, 0) * weights.get(criterion, 0)
                for criterion in component_scores
            )

            weighted_score = max(0.0, min(100.0, weighted_score))

            # Convert to display format
            display_rating = round(weighted_score / 10.0, 1)
            color_code = get_color_from_score(weighted_score)
            rating_description = get_rating_description(weighted_score)

            # Build properties object
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
                "project_type": target_persona,
                "project_type_weights": weights,
                "internal_total_score": round(weighted_score, 1),
                "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
            }

            # Build GeoJSON feature
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

    # Sort by investment rating
    features_sorted = sorted(
        features,
        key=lambda f: f.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    # Log results and return
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


@app.get("/api/projects/customer-match")
async def get_customer_match_projects(
    target_customer: PersonaType = Query("hyperscaler", description="Target customer persona"),
    limit: int = Query(5000, description="Number of projects to analyze"),
) -> Dict[str, Any]:
    """Analyze projects for best customer match."""
    projects = await query_supabase("renewable_projects?select=*", limit=limit)
    filtered_projects = filter_projects_by_persona_capacity(projects, target_customer)

    customer_analysis: List[Dict[str, Any]] = []
    for project in filtered_projects:
        if not project.get("longitude") or not project.get("latitude"):
            continue
        dummy_proximity = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "nearest_distances": {},
        }
        customer_match = calculate_best_customer_match(project, dummy_proximity)
        target_scoring = calculate_persona_weighted_score(project, dummy_proximity, target_customer)
        customer_analysis.append(
            {
                "project_id": project.get("ref_id"),
                "site_name": project.get("site_name"),
                "technology_type": project.get("technology_type"),
                "capacity_mw": project.get("capacity_mw"),
                "county": project.get("county"),
                "coordinates": [project.get("longitude"), project.get("latitude")],
                "target_customer": target_customer,
                "target_customer_score": target_scoring["investment_rating"],
                "target_customer_rating": target_scoring["rating_description"],
                "best_customer_match": customer_match["best_customer_match"],
                "customer_match_scores": customer_match["customer_match_scores"],
                "suitable_customers": customer_match["suitable_customers"],
                "component_scores": target_scoring["component_scores"],
                "weighted_contributions": target_scoring["weighted_contributions"],
            }
        )

    return {
        "target_customer": target_customer,
        "projects_analyzed": len(customer_analysis),
        "capacity_range": PERSONA_CAPACITY_RANGES[target_customer],
        "projects": customer_analysis,
        "metadata": {
            "algorithm_version": "2.3 - Bidirectional Customer Matching",
            "total_projects_before_filtering": len(projects),
            "projects_after_capacity_filtering": len(filtered_projects),
        },
    }


@app.post("/api/financial-model", response_model=FinancialModelResponse)
async def calculate_financial_model(request: FinancialModelRequest) -> FinancialModelResponse:
    """Calculate financial model for utility-scale and behind-the-meter scenarios."""
    if not FINANCIAL_MODEL_AVAILABLE:
        raise HTTPException(500, "Financial model not available - renewable_model.py not found")
    try:
        print(f"🔄 Processing financial model request: {request.technology}, {request.capacity_mw}MW")
        tech_params = create_technology_params(request)
        financial_assumptions = FinancialAssumptions(
            discount_rate=request.discount_rate,
            inflation_rate=request.inflation_rate,
            tax_rate=request.tax_rate,
        )
        tech_type = map_technology_type(request.technology)
        utility_prices = create_utility_market_prices(request)
        utility_model = RenewableFinancialModel(
            project_name="Utility Scale Analysis",
            technology_type=tech_type,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=utility_prices,
            financial_assumptions=financial_assumptions,
        )
        btm_prices = create_btm_market_prices(request)
        btm_model = RenewableFinancialModel(
            project_name="Behind-the-Meter Analysis",
            technology_type=tech_type,
            project_type=ProjectType.BEHIND_THE_METER,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=btm_prices,
            financial_assumptions=financial_assumptions,
        )
        print("🔄 Running utility-scale analysis...")
        utility_results = utility_model.run_analysis()
        print("🔄 Running behind-the-meter analysis...")
        btm_results = btm_model.run_analysis()
        utility_cashflows = utility_model.cashflow_df["net_cashflow"].tolist()
        btm_cashflows = btm_model.cashflow_df["net_cashflow"].tolist()
        utility_breakdown = extract_revenue_breakdown(utility_model.cashflow_df)
        btm_breakdown = extract_revenue_breakdown(btm_model.cashflow_df)
        irr_uplift = (
            (btm_results["irr"] - utility_results["irr"]) if (btm_results["irr"] and utility_results["irr"]) else 0
        )
        npv_delta = btm_results["npv"] - utility_results["npv"]
        print(
            f"✅ Financial analysis complete: Utility IRR={utility_results['irr']:.3f}, "
            f"BTM IRR={btm_results['irr']:.3f}"
        )
        response = FinancialModelResponse(
            standard=ModelResults(
                irr=utility_results["irr"],
                npv=utility_results["npv"],
                cashflows=utility_cashflows,
                breakdown=utility_breakdown,
                lcoe=utility_results["lcoe"],
                payback_simple=utility_results["payback_simple"],
                payback_discounted=utility_results["payback_discounted"],
            ),
            autoproducer=ModelResults(
                irr=btm_results["irr"],
                npv=btm_results["npv"],
                cashflows=btm_cashflows,
                breakdown=btm_breakdown,
                lcoe=btm_results["lcoe"],
                payback_simple=btm_results["payback_simple"],
                payback_discounted=btm_results["payback_discounted"],
            ),
            metrics={
                "total_capex": utility_results["capex_total"],
                "capex_per_mw": utility_results["capex_per_mw"],
                "irr_uplift": irr_uplift,
                "npv_delta": npv_delta,
                "annual_generation": request.capacity_mw * 8760 * request.capacity_factor,
            },
            success=True,
            message="Financial analysis completed successfully",
        )
        utility_irr = utility_results.get("irr")
        btm_irr = btm_results.get("irr")
        print(
            "calculating financial_model, result is "
            f"utility IRR={utility_irr if utility_irr is not None else 'n/a'}, "
            f"BTM IRR={btm_irr if btm_irr is not None else 'n/a'}"
        )
        return response
    except Exception as exc:
        import traceback
        error_msg = f"Financial model calculation failed: {exc}"
        print(f"❌ {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": error_msg, "error_type": type(exc).__name__},
        )


@app.get("/api/tec/connections", response_model=TecConnectionsResponse)
async def get_tec_connections(
    limit: int = Query(1000, ge=1, le=5000),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    plant_type: Optional[str] = Query(None),
):
    """Return TEC connections as a GeoJSON FeatureCollection."""
    try:
        query = "tec_connections?select=*"
        filters: List[str] = []

        if search:
            filters.append(f"project_name.ilike.%{search}%")
        if status:
            filters.append(f"development_status.ilike.%{status}%")
        if plant_type:
            filters.append(f"technology_type.ilike.%{plant_type}%")

        if filters:
            query = f"{query}&{'&'.join(filters)}"

        print(f"🔄 TEC query: limit={limit}, filters={len(filters)}")
        rows = await query_supabase(query, limit=limit)

        if rows is None:
            rows = []
        elif not isinstance(rows, list):
            rows = [rows]

        features: List[TecConnectionFeature] = []
        skipped_rows = 0

        for row in rows:
            feature = transform_tec_row_to_feature(row)
            if feature is None:
                skipped_rows += 1
                continue
            features.append(feature)

        if skipped_rows:
            print(f"⚠️ Skipped {skipped_rows} rows (missing coords)")

        print(f"✅ Returning {len(features)} TEC features")
        return TecConnectionsResponse(
            type="FeatureCollection",
            features=features,
            count=len(features),
        )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ TEC endpoint error: {exc}")
        raise HTTPException(500, f"Failed to fetch TEC connections: {exc}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main_new:app", host="127.0.0.1", port=8000, reload=True)
