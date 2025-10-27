from __future__ import annotations

import json
import math
import os
import time
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

print("Booting model...")
_boot_start_time = time.time()

print("Initializing environment configuration...")
_env_start_time = time.time()
load_dotenv()
print(f"[\u2713] Environment variables loaded in {time.time() - _env_start_time:.2f}s")

from backend.config import (
    PERSONA_CAPACITY_RANGES,
    PERSONA_WEIGHTS,
    POWER_DEVELOPER_CAPACITY_RANGES,
    POWER_DEVELOPER_PERSONAS,
    PersonaType,
)
from backend.infrastructure import (
    InfrastructureCache,
    calculate_proximity_scores_batch,
    coerce_float,
)
from backend.scoring import (
    calculate_best_customer_match,
    build_persona_component_scores,
    calculate_custom_weighted_score,
    calculate_enhanced_investment_rating,
    calculate_persona_topsis_score,
    calculate_persona_weighted_score,
    calculate_rating_distribution,
    enrich_and_rescore_top_25_with_tnuos,
    filter_projects_by_persona_capacity,
    get_color_from_score,
    get_rating_description,
    resolve_power_developer_persona,
)
from backend.supabase import SUPABASE_KEY, SUPABASE_URL, query_supabase
from backend.tnuos import LCOE_CONFIG, TNUOS_ZONES_HARDCODED

try:
    print("Loading renewable financial model components...")
    from backend.renewable_model import (
        FinancialAssumptions,
        MarketPrices,
        ProjectType,
        RenewableFinancialModel,
        TechnologyParams,
        TechnologyType,
        MarketRegion,
    )

    FINANCIAL_MODEL_AVAILABLE = True
    print("[\u2713] Renewable financial model components loaded successfully")
except ImportError as exc:  # pragma: no cover - handled dynamically at runtime
    print(f"Error initializing renewable financial model components: {exc}")
    FINANCIAL_MODEL_AVAILABLE = False

print("Initializing FastAPI renderer...")
_api_start_time = time.time()
app = FastAPI(title="Infranodal API", version="2.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
print(f"[\u2713] FastAPI renderer initialized in {time.time() - _api_start_time:.2f}s")

print(f"✅ SUPABASE_URL: {SUPABASE_URL}")
print(f"✅ SUPABASE_KEY exists: {bool(SUPABASE_KEY)}")

print("Initializing infrastructure cache subsystem...")
INFRASTRUCTURE_CACHE = InfrastructureCache()
print("[✓] Infrastructure cache subsystem ready")
print(f"Model boot completed successfully in {time.time() - _boot_start_time:.2f}s.")


class UserSite(BaseModel):
    site_name: str
    technology_type: str
    capacity_mw: float
    latitude: float
    longitude: float
    commissioning_year: int
    is_btm: bool
    capacity_factor: Optional[float] = None
    development_status_short: Optional[str] = "planning"


class FinancialModelRequest(BaseModel):
    technology: str
    capacity_mw: float
    capacity_factor: float
    project_life: int
    degradation: float
    capex_per_kw: float
    devex_abs: float
    devex_pct: float
    opex_fix_per_mw_year: float
    opex_var_per_mwh: float
    tnd_costs_per_year: float
    ppa_price: float
    ppa_escalation: float
    ppa_duration: int
    merchant_price: float
    capacity_market_per_mw_year: float
    ancillary_per_mw_year: float
    discount_rate: float
    inflation_rate: float
    tax_rate: float = 0.19
    grid_savings_factor: float
    battery_capacity_mwh: Optional[float] = None
    battery_capex_per_mwh: Optional[float] = None
    battery_cycles_per_year: Optional[int] = None


class RevenueBreakdown(BaseModel):
    energyRev: float
    capacityRev: float
    ancillaryRev: float
    gridSavings: float
    opexTotal: float


class ModelResults(BaseModel):
    irr: Optional[float]
    npv: float
    cashflows: List[float]
    breakdown: RevenueBreakdown
    lcoe: float
    payback_simple: Optional[float]
    payback_discounted: Optional[float]


class FinancialModelResponse(BaseModel):
    standard: ModelResults
    autoproducer: ModelResults
    metrics: Dict[str, float]
    success: bool
    message: str





@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Infranodal API v2.1 with Persona-Based Scoring", "status": "active"}


@app.get("/health")
async def health() -> Dict[str, Any]:
    try:
        print("🔄 Testing database connection...")
        data = await query_supabase("renewable_projects?select=count")
        count = len(data)
        print(f"✅ Database connected: {count} records")
        return {"status": "healthy", "database": "connected", "projects": count}
    except Exception as exc:  # pragma: no cover - diagnostic logging
        print(f"❌ Database error: {exc}")
        return {"status": "degraded", "database": "disconnected", "error": str(exc)}


@app.get("/api/projects")
async def get_projects(
    limit: int = Query(5000),
    technology: Optional[str] = None,
    country: Optional[str] = None,
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring"),
) -> List[Dict[str, Any]]:
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
    if not sites:
        raise HTTPException(400, "No sites provided")

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

    proximity_scores = await calculate_proximity_scores_batch(sites_for_calc, INFRASTRUCTURE_CACHE)

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
    scoring_method: Literal["weighted_sum", "topsis"] = Query(
        "weighted_sum",
        description="Scoring method to apply (weighted_sum or topsis)",
    ),
    dc_demand_mw: Optional[float] = Query(None, description="DC facility demand in MW for capacity gating"),
    source_table: str = Query(
        "renewable_projects",
        description="Source table - will be demand_sites for power devs in future",
    ),

    # NEW: User's price budget
    user_max_price_mwh: Optional[float] = Query(
        None,
        description="User's maximum acceptable power price (£/MWh) for price_sensitivity scoring",
    ),
) -> Dict[str, Any]:
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
        # Continuation of get_enhanced_geojson function
    
    valid_projects = [project for project in projects if project.get("longitude") and project.get("latitude")]
    print(f"📍 {len(valid_projects)} projects have valid coordinates")
    if not valid_projects:
        return {"type": "FeatureCollection", "features": [], "metadata": {"error": "No projects with valid coordinates"}}

    try:
        print("🔄 Starting batch proximity calculation...")
        batch_start = time.time()
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects, INFRASTRUCTURE_CACHE)
        batch_time = time.time() - batch_start
        print(f"✅ Batch proximity calculation completed in {batch_time:.2f}s")
    except Exception as exc:  # pragma: no cover - fallback path
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
        except Exception as exc:  # pragma: no cover - per-project failure fallback
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

    try:
        features = await enrich_and_rescore_top_25_with_tnuos(features, persona)
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"⚠️ TNUoS enrichment skipped: {exc}")

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
    stations = await query_supabase("substations?select=*")
    features: List[Dict[str, Any]] = []
    for station in stations or []:
        lat = coerce_float(
            station.get("latitude")
            or station.get("lat")
            or station.get("Lat")
        )
        lon = coerce_float(
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
        voltage = coerce_float(
            station.get("primary_voltage_kv")
            or station.get("voltage_kv")
            or station.get("VOLTAGE_HIGH")
        )
        capacity_mva = coerce_float(station.get("capacity_mva"))
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

    except Exception as exc:  # pragma: no cover - runtime safeguard
        print(f"❌ DNO areas endpoint error: {exc}")
        raise HTTPException(500, f"Failed to fetch DNO license areas: {exc}")


@app.get("/api/projects/compare-scoring")
async def compare_scoring_systems(
    limit: int = Query(10, description="Projects to compare"),
    persona: PersonaType = Query("hyperscaler", description="Persona for comparison"),
) -> Dict[str, Any]:
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


# ============================================================================
# TEC CONNECTIONS TRANSFORMATION
# ============================================================================

def _extract_coordinates(row: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Return latitude/longitude from heterogeneous Supabase payloads."""

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    latitude_keys = [
        "latitude",
        "lat",
        "Latitude",
        "Latitude_deg",
    ]
    longitude_keys = [
        "longitude",
        "lon",
        "lng",
        "Longitude",
        "Longitude_deg",
    ]

    for key in latitude_keys:
        if key in row:
            latitude = coerce_float(row.get(key))
            if latitude is not None:
                break

    for key in longitude_keys:
        if key in row:
            longitude = coerce_float(row.get(key))
            if longitude is not None:
                break

    if (latitude is None or longitude is None) and isinstance(row.get("location"), dict):
        location_data = row.get("location")
        latitude = latitude or coerce_float(
            location_data.get("lat") or location_data.get("latitude")
        )
        longitude = longitude or coerce_float(
            location_data.get("lon")
            or location_data.get("lng")
            or location_data.get("longitude")
        )

    if (latitude is None or longitude is None) and isinstance(row.get("coordinates"), (list, tuple)):
        coords = row.get("coordinates")
        if len(coords) >= 2:
            longitude = longitude or coerce_float(coords[0])
            latitude = latitude or coerce_float(coords[1])

    return latitude, longitude


def transform_tec_to_project_schema(tec_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a TEC connections database row to unified project schema.

    TEC table has different field names than renewable_projects, so we map them:
    - project_name → site_name
    - development_status → development_status_short
    - Coordinates might be NULL (we'll handle that separately)
    """

    latitude, longitude = _extract_coordinates(tec_row)

    return {
        "id": tec_row.get("id"),
        "ref_id": str(tec_row.get("id", "")),
        "site_name": tec_row.get("project_name") or "Untitled Project",
        "project_name": tec_row.get("project_name"),
        "capacity_mw": coerce_float(tec_row.get("capacity_mw")) or 0.0,
        "technology_type": tec_row.get("technology_type") or "Unknown",
        "development_status_short": tec_row.get("development_status") or "Scoping",
        "development_status": tec_row.get("development_status"),
        "constraint_status": tec_row.get("constraint_status"),
        "connection_site": tec_row.get("connection_site"),
        "substation_name": tec_row.get("substation_name"),
        "voltage_kv": coerce_float(tec_row.get("voltage")),
        "latitude": latitude,
        "longitude": longitude,
        "county": None,
        "country": "UK",
        "operator": tec_row.get("operator") or tec_row.get("customer_name"),
        "_source_table": "tec_connections",
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

    Mirrors hyperscaler workflow exactly:
    1. Fetch projects (from tec_connections)
    2. Transform to schema (TEC rows → project objects)
    3. Calculate proximity scores (infrastructure analysis)
    4. Build component scores (7 business criteria)
    5. Apply project type weights (greenfield/repower/stranded)
    6. Return scored GeoJSON

    Args:
        criteria: Not used (legacy parameter, kept for compatibility)
        site_location: Not used (legacy parameter)
        target_persona: Project type - "greenfield", "repower", or "stranded"
        limit: Max projects to return (default 150)
        source_table: Data source - "tec_connections" (new) or "renewable_projects" (fallback)

    Returns:
        GeoJSON FeatureCollection with scored projects
    """

    start_time = time.time()

    # ========================================================================
    # STEP 0: Validate Input
    # ========================================================================
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

    # ========================================================================
    # STEP 1: Fetch Projects from Database
    # ========================================================================
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

    # ========================================================================
    # STEP 2: Transform Rows to Project Schema
    # ========================================================================
    print("   🔄 Transforming to project schema...")

    if source_table == "tec_connections":
        projects = [transform_tec_to_project_schema(row) for row in raw_rows]
    else:
        projects = raw_rows

    # ========================================================================
    # STEP 3: Filter for Valid Coordinates
    # ========================================================================
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

    # ========================================================================
    # STEP 4: Calculate Infrastructure Proximity Scores
    # ========================================================================
    print("   🔄 Calculating proximity scores...")

    try:
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects, INFRASTRUCTURE_CACHE)
        print(f"   ✅ Proximity calculations complete")
    except Exception as exc:
        print(f"   ❌ Proximity calculation error: {exc}")
        raise

    # ========================================================================
    # STEP 5: Score Each Project Using Power Developer Weights
    # ========================================================================
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

            # STEP 5A: Build component scores (7 business criteria)
            component_scores = build_persona_component_scores(
                project,
                proximity_scores,
                persona=target_persona,
                perspective="demand",
            )

            # STEP 5B: Apply power developer weights
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
                    k: round(component_scores[k] * weights.get(k, 0), 1) for k in component_scores
                },
                "project_type": target_persona,
                "project_type_weights": weights,
                "internal_total_score": round(weighted_score, 1),
                "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
            }

            # STEP 5E: Build GeoJSON feature
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

    # ========================================================================
    # STEP 6: Sort by Investment Rating
    # ========================================================================
    features_sorted = sorted(
        features,
        key=lambda f: f.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    # ========================================================================
    # STEP 7: Log Results and Return
    # ========================================================================
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

def map_technology_type(tech_string: str):
    if not FINANCIAL_MODEL_AVAILABLE:
        return "solar_pv"
    mapping = {
        "solar": TechnologyType.SOLAR_PV,
        "solar_pv": TechnologyType.SOLAR_PV,
        "wind": TechnologyType.WIND,
        "battery": TechnologyType.BATTERY,
        "solar_battery": TechnologyType.SOLAR_BATTERY,
        "solar_bess": TechnologyType.SOLAR_BATTERY,
        "wind_battery": TechnologyType.WIND_BATTERY,
    }
    return mapping.get(tech_string.lower(), TechnologyType.SOLAR_PV)


def create_technology_params(request: FinancialModelRequest) -> TechnologyParams:
    return TechnologyParams(
        capacity_mw=request.capacity_mw,
        capex_per_mw=request.capex_per_kw * 1000,
        opex_per_mw_year=request.opex_fix_per_mw_year,
        degradation_rate_annual=request.degradation,
        lifetime_years=request.project_life,
        capacity_factor=request.capacity_factor,
        battery_capacity_mwh=request.battery_capacity_mwh,
        battery_capex_per_mwh=request.battery_capex_per_mwh,
        battery_cycles_per_year=request.battery_cycles_per_year,
    )


def create_utility_market_prices(request: FinancialModelRequest) -> MarketPrices:
    return MarketPrices(
        base_power_price=request.merchant_price,
        power_price_escalation=0.025,
        ppa_price=request.ppa_price,
        ppa_duration_years=request.ppa_duration,
        ppa_escalation=request.ppa_escalation,
        ppa_percentage=0.7,
        capacity_payment=request.capacity_market_per_mw_year / 1000,
        frequency_response_price=(
            request.ancillary_per_mw_year / (8760 * 0.1) if request.ancillary_per_mw_year > 0 else 0
        ),
    )


def create_btm_market_prices(request: FinancialModelRequest) -> MarketPrices:
    annual_generation = request.capacity_mw * 8760 * request.capacity_factor
    grid_savings_per_mwh = (
        (request.grid_savings_factor * request.tnd_costs_per_year) / annual_generation
        if annual_generation > 0
        else 0
    )
    return MarketPrices(
        base_power_price=request.merchant_price,
        power_price_escalation=0.025,
        retail_electricity_price=request.ppa_price,
        retail_price_escalation=request.ppa_escalation,
        grid_charges=grid_savings_per_mwh,
        demand_charges=0,
    )


def extract_revenue_breakdown(cashflow_df) -> RevenueBreakdown:
    if cashflow_df is None or len(cashflow_df) == 0:
        return RevenueBreakdown(energyRev=0, capacityRev=0, ancillaryRev=0, gridSavings=0, opexTotal=0)
    operating_years = cashflow_df[cashflow_df["year"] > 0]
    energy_rev = 0.0
    capacity_rev = 0.0
    ancillary_rev = 0.0
    grid_savings = 0.0
    opex_total = operating_years["opex"].sum() if "opex" in operating_years.columns else 0.0
    for column in operating_years.columns:
        if not column.startswith("revenue_"):
            continue
        values = operating_years[column].sum()
        if "ppa" in column or "merchant" in column or "energy_savings" in column:
            energy_rev += values
        elif "capacity" in column:
            capacity_rev += values
        elif "frequency_response" in column or "ancillary" in column:
            ancillary_rev += values
        elif "grid_charges" in column:
            grid_savings += values
    return RevenueBreakdown(
        energyRev=energy_rev,
        capacityRev=capacity_rev,
        ancillaryRev=ancillary_rev,
        gridSavings=grid_savings,
        opexTotal=opex_total,
    )


@app.post("/api/financial-model", response_model=FinancialModelResponse)
async def calculate_financial_model(request: FinancialModelRequest) -> FinancialModelResponse:
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
    except Exception as exc:  # pragma: no cover - forward error to client
        import traceback
        error_msg = f"Financial model calculation failed: {exc}"
        print(f"❌ {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": error_msg, "error_type": type(exc).__name__},
        )


# ============================================================================
# TEC CONNECTIONS ENDPOINT
# ============================================================================


class TecConnectionProperties(BaseModel):
    id: Union[int, str]
    project_name: str
    operator: Optional[str] = None
    customer_name: Optional[str] = None
    capacity_mw: Optional[float] = None
    mw_delta: Optional[float] = None
    technology_type: Optional[str] = None
    plant_type: Optional[str] = None
    project_status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    connection_site: Optional[str] = None
    substation_name: Optional[str] = None
    voltage: Optional[float] = None
    constraint_status: Optional[str] = None
    created_at: Optional[str] = None
    agreement_type: Optional[str] = None
    effective_from: Optional[str] = None


class TecConnectionGeometry(BaseModel):
    type: str = "Point"
    coordinates: List[float]


class TecConnectionFeature(BaseModel):
    type: str = "Feature"
    geometry: TecConnectionGeometry
    properties: TecConnectionProperties
    id: Optional[str] = None


class TecConnectionsResponse(BaseModel):
    type: str = "FeatureCollection"
    features: List[TecConnectionFeature]
    count: int


def transform_tec_row_to_feature(row: Dict[str, Any]) -> Optional[TecConnectionFeature]:
    """Transform a Supabase TEC row into a GeoJSON feature."""

    try:
        lat, lon = _extract_coordinates(row)

        if lat is None or lon is None:
            print(f"⚠️ Skip TEC '{row.get('project_name')}' - no coords")
            return None

        capacity_mw = coerce_float(row.get("capacity_mw"))
        voltage = coerce_float(row.get("voltage"))
        technology_type = row.get("technology_type")
        operator = row.get("operator") or row.get("customer_name")
        customer_name = row.get("customer_name") or row.get("operator")

        return TecConnectionFeature(
            id=str(row.get("id")),
            geometry=TecConnectionGeometry(coordinates=[lon, lat]),
            properties=TecConnectionProperties(
                id=row.get("id"),
                project_name=row.get("project_name") or "Untitled",
                operator=operator,
                customer_name=customer_name,
                capacity_mw=capacity_mw,
                mw_delta=capacity_mw,
                technology_type=technology_type,
                plant_type=technology_type,
                project_status=row.get("development_status"),
                latitude=lat,
                longitude=lon,
                connection_site=row.get("connection_site"),
                substation_name=row.get("substation_name"),
                voltage=voltage,
                constraint_status=row.get("constraint_status"),
                created_at=row.get("created_at"),
            ),
        )
    except Exception as exc:  # pragma: no cover - diagnostic logging only
        print(f"❌ Transform error row {row.get('id')}: {exc}")
        return None


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)







