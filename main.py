from __future__ import annotations

import asyncio
import base64
import json
import math
import os
import time
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union, cast

import httpx
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.power_workflow import (
    POWER_DEVELOPER_CAPACITY_RANGES,
    POWER_DEVELOPER_PERSONAS,
    PowerDeveloperPersona,
    extract_coordinates,
    resolve_power_developer_persona,
    run_power_developer_analysis,
    transform_tec_to_project_schema,
)
from backend.scoring import (
    INFRASTRUCTURE_HALF_DISTANCE_KM,
    PERSONA_CAPACITY_RANGES,
    PERSONA_WEIGHTS,
    PersonaType,
    build_persona_component_scores,
    calculate_best_customer_match,
    calculate_capacity_component_score,
    calculate_custom_weighted_score,
    calculate_development_stage_score,
    calculate_digital_infrastructure_score,
    calculate_grid_infrastructure_score,
    calculate_lcoe_score,
    calculate_persona_topsis_score,
    calculate_persona_weighted_score,
    calculate_tnuos_score,
    calculate_technology_score,
    calculate_water_resources_score,
    filter_projects_by_persona_capacity,
    get_color_from_score,
    get_rating_description,
)
from backend.proximity import (
    InfrastructureCatalog,
    LineFeature,
    PointFeature,
    SpatialGrid,
    calculate_proximity_scores,
)
from backend.portfolio import (
    RiskProfile,
    calculate_multi_project_portfolio_score,
    calculate_optimal_allocation,
    analyze_portfolio_correlations,
    calculate_risk_adjusted_returns,
    calculate_efficient_frontier,
    estimate_project_returns,
    build_correlation_matrix,
)

print("Booting model...")
_boot_start_time = time.time()

print("Initializing environment configuration...")
_env_start_time = time.time()
load_dotenv()
print(f"[\u2713] Environment variables loaded in {time.time() - _env_start_time:.2f}s")

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

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

print(f"✅ SUPABASE_URL: {SUPABASE_URL}")
print(f"✅ SUPABASE_KEY exists: {bool(SUPABASE_KEY)}")

INFRASTRUCTURE_CACHE_TTL_SECONDS = int(os.getenv("INFRA_CACHE_TTL", "600"))

# ============================================================================
# HARD-CODED TNUoS ZONES (No DB calls needed)
# ============================================================================

TNUOS_ZONES_HARDCODED = {
    "GZ1": {
        "name": "North Scotland",
        "tariff": 15.32,
        "bounds": {"min_lat": 57.5, "max_lat": 61.0, "min_lng": -6.0, "max_lng": -1.5},
    },
    "GZ2": {
        "name": "South Scotland",
        "tariff": 14.87,
        "bounds": {"min_lat": 55.0, "max_lat": 57.5, "min_lng": -4.0, "max_lng": -1.5},
    },
    "GZ3": {
        "name": "Borders",
        "tariff": 13.45,
        "bounds": {"min_lat": 54.5, "max_lat": 56.0, "min_lng": -4.0, "max_lng": -1.5},
    },
    "GZ4": {
        "name": "Central Scotland",
        "tariff": 12.98,
        "bounds": {"min_lat": 55.5, "max_lat": 56.5, "min_lng": -5.0, "max_lng": -3.0},
    },
    "GZ5": {
        "name": "Argyll",
        "tariff": 11.67,
        "bounds": {"min_lat": 55.0, "max_lat": 57.0, "min_lng": -6.0, "max_lng": -4.0},
    },
    "GZ6": {
        "name": "Dumfries",
        "tariff": 10.34,
        "bounds": {"min_lat": 54.5, "max_lat": 55.5, "min_lng": -4.5, "max_lng": -2.5},
    },
    "GZ7": {
        "name": "Ayr",
        "tariff": 9.87,
        "bounds": {"min_lat": 54.8, "max_lat": 55.5, "min_lng": -5.0, "max_lng": -3.5},
    },
    "GZ8": {
        "name": "Central Belt",
        "tariff": 8.92,
        "bounds": {"min_lat": 55.2, "max_lat": 56.0, "min_lng": -4.5, "max_lng": -3.0},
    },
    "GZ9": {
        "name": "Lothian",
        "tariff": 7.56,
        "bounds": {"min_lat": 55.5, "max_lat": 56.2, "min_lng": -3.5, "max_lng": -2.0},
    },
    "GZ10": {
        "name": "Southern Scotland",
        "tariff": 6.23,
        "bounds": {"min_lat": 54.8, "max_lat": 55.5, "min_lng": -3.5, "max_lng": -1.5},
    },
    "GZ11": {
        "name": "North East England",
        "tariff": 5.67,
        "bounds": {"min_lat": 54.0, "max_lat": 55.5, "min_lng": -3.0, "max_lng": -0.5},
    },
    "GZ12": {
        "name": "Yorkshire",
        "tariff": 4.89,
        "bounds": {"min_lat": 53.0, "max_lat": 54.5, "min_lng": -3.0, "max_lng": -0.5},
    },
    "GZ13": {
        "name": "Humber",
        "tariff": 4.12,
        "bounds": {"min_lat": 52.5, "max_lat": 53.5, "min_lng": -2.0, "max_lng": 0.5},
    },
    "GZ14": {
        "name": "North West England",
        "tariff": 3.78,
        "bounds": {"min_lat": 52.5, "max_lat": 54.5, "min_lng": -3.5, "max_lng": -1.5},
    },
    "GZ15": {
        "name": "East Midlands",
        "tariff": 2.95,
        "bounds": {"min_lat": 51.5, "max_lat": 53.0, "min_lng": -2.5, "max_lng": 0.0},
    },
    "GZ16": {
        "name": "West Midlands",
        "tariff": 2.34,
        "bounds": {"min_lat": 51.5, "max_lat": 52.7, "min_lng": -3.0, "max_lng": -1.5},
    },
    "GZ17": {
        "name": "East England",
        "tariff": 1.87,
        "bounds": {"min_lat": 51.5, "max_lat": 52.5, "min_lng": -0.5, "max_lng": 1.5},
    },
    "GZ18": {
        "name": "South Wales",
        "tariff": 1.45,
        "bounds": {"min_lat": 51.2, "max_lat": 52.0, "min_lng": -3.5, "max_lng": -2.0},
    },
    "GZ19": {
        "name": "North Wales",
        "tariff": 0.98,
        "bounds": {"min_lat": 52.3, "max_lat": 53.5, "min_lng": -3.8, "max_lng": -2.8},
    },
    "GZ20": {
        "name": "Pembroke",
        "tariff": 0.67,
        "bounds": {"min_lat": 51.6, "max_lat": 52.1, "min_lng": -5.5, "max_lng": -4.8},
    },
    "GZ21": {
        "name": "South West England",
        "tariff": -0.12,
        "bounds": {"min_lat": 50.5, "max_lat": 51.5, "min_lng": -4.5, "max_lng": -2.0},
    },
    "GZ22": {
        "name": "Cornwall",
        "tariff": -0.45,
        "bounds": {"min_lat": 49.9, "max_lat": 50.7, "min_lng": -5.5, "max_lng": -4.5},
    },
    "GZ23": {
        "name": "London",
        "tariff": -0.78,
        "bounds": {"min_lat": 51.2, "max_lat": 51.8, "min_lng": -0.5, "max_lng": 0.5},
    },
    "GZ24": {
        "name": "South East England",
        "tariff": -1.23,
        "bounds": {"min_lat": 50.5, "max_lat": 51.5, "min_lng": -2.0, "max_lng": 1.5},
    },
    "GZ25": {
        "name": "Kent",
        "tariff": -1.56,
        "bounds": {"min_lat": 50.8, "max_lat": 51.5, "min_lng": 0.2, "max_lng": 1.8},
    },
    "GZ26": {
        "name": "Southern England",
        "tariff": -1.89,
        "bounds": {"min_lat": 50.5, "max_lat": 51.2, "min_lng": -2.5, "max_lng": 0.0},
    },
    "GZ27": {
        "name": "Solent",
        "tariff": -2.34,
        "bounds": {"min_lat": 50.6, "max_lat": 51.0, "min_lng": -2.0, "max_lng": -1.0},
    },
}

LCOE_CONFIG = {
    "baseline_pounds_per_mwh": 60.0,
    "gamma_slope": 0.04,
    "min_lcoe": 45.0,
    "max_lcoe": 100.0,
    "zone_specific_rates": {},
}


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
) -> List[Dict[str, Any]]:
    """Enrich projects with TNUoS data and adjust scores."""

    if not features:
        return features

    features_sorted = sorted(
        features,
        key=lambda feature: feature.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    print("📊 Enriching projects with TNUoS zones...")

    enriched_count = 100

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

    print(f"✓ Enriched {enriched_count}/{len(features_sorted)} projects")

    resorted_features = sorted(
        features_sorted,
        key=lambda feature: feature.get("properties", {}).get("investment_rating", 0),
        reverse=True,
    )

    return resorted_features


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


async def query_supabase(endpoint: str, *, limit: Optional[int] = None, page_size: int = 1000) -> Any:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(500, "Supabase credentials not configured")

    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

    if limit is not None and limit <= 0:
        return []

    def append_limit(query: str, limit_value: int) -> str:
        separator = "&" if "?" in query else "?"
        return f"{query}{separator}limit={limit_value}"

    async with httpx.AsyncClient(timeout=30.0) as client:  # Increased timeout
        # For small requests, single query
        if limit is None or limit <= page_size:
            endpoint_with_limit = (
                append_limit(endpoint, limit) if limit is not None else endpoint
            )
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/{endpoint_with_limit}", headers=headers
            )
            if response.status_code == 200:
                return response.json()
            error_message = f"Database error: {response.status_code}"
            print(f"Error querying Supabase for {endpoint_with_limit}: {error_message}")
            raise HTTPException(500, error_message)

        # For large requests, use offset-limit pagination (not Range headers)
        assert limit is not None
        aggregated_results: List[Any] = []
        offset = 0

        while len(aggregated_results) < limit:
            chunk_size = min(page_size, limit - len(aggregated_results))

            # Use offset/limit query params instead of Range header
            endpoint_with_pagination = f"{endpoint}&offset={offset}&limit={chunk_size}"

            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/{endpoint_with_pagination}",
                headers=headers,
            )

            if response.status_code != 200:
                error_message = f"Database error: {response.status_code}"
                print(f"Error paginating Supabase at offset {offset}: {error_message}")
                raise HTTPException(500, error_message)

            chunk = response.json()

            if not isinstance(chunk, list):
                return chunk

            if not chunk:
                print(f"   Empty response at offset {offset} - end of data")
                break

            aggregated_results.extend(chunk)
            print(
                f"   Fetched {len(chunk)} rows at offset {offset} (total: {len(aggregated_results)}/{limit})"
            )

            # If we got fewer rows than requested, we've reached the end
            if len(chunk) < chunk_size:
                print(f"   Reached end of data at offset {offset}")
                break

            offset += chunk_size

        print(f"   ✓ Retrieved {len(aggregated_results)} total records")
        return aggregated_results


def extract_user_from_jwt(authorization_header: Optional[str]) -> Tuple[Optional[str], str]:
    default_email = "anonymous"
    if not authorization_header or not isinstance(authorization_header, str):
        return None, default_email

    try:
        scheme, token = authorization_header.split(" ", 1)
        if scheme.lower() != "bearer":
            return None, default_email
    except ValueError:
        return None, default_email

    parts = token.split(".")
    if len(parts) < 2:
        return None, default_email

    payload_segment = parts[1]
    padding = "=" * (-len(payload_segment) % 4)

    try:
        decoded_bytes = base64.urlsafe_b64decode(payload_segment + padding)
        payload = json.loads(decoded_bytes.decode("utf-8"))
    except Exception:
        return None, default_email

    user_id = payload.get("sub")
    user_email = payload.get("email") or default_email
    return user_id, user_email


async def save_workflow_analysis(
    *,
    user_id: Optional[str],
    user_email: str,
    persona: str,
    workflow_type: str,
    request_path: Optional[str],
    criteria_weights: Dict[str, Any],
    scoring_method: str,
    dc_demand_mw: Optional[float],
    user_ideal_mw: Optional[float],
    top_5_projects: Sequence[Dict[str, Any]],
) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Skipping workflow analysis save: Supabase not configured")
        return

    payload = {
        "user_id": user_id,
        "user_email": user_email or "anonymous",
        "persona": persona,
        "workflow_type": workflow_type,
        "request_path": request_path,
        "criteria_weights": criteria_weights or {},
        "scoring_method": scoring_method,
        "dc_demand_mw": dc_demand_mw,
        "user_ideal_mw": user_ideal_mw,
        "top_5_projects": list(top_5_projects)[:10],
    }

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/workflow_analyses",
                headers=headers,
                json=payload,
            )

        if response.status_code not in {200, 201}:
            print(
                "⚠️ Workflow analysis save failed "
                f"({response.status_code}): {response.text}"
            )
    except Exception as exc:
        print(f"⚠️ Workflow analysis save error: {exc}")


class InfrastructureCache:
    def __init__(self) -> None:
        self._catalog: Optional[InfrastructureCatalog] = None
        self._lock = asyncio.Lock()
        self._last_loaded = 0.0

    async def get_catalog(self) -> InfrastructureCatalog:
        async with self._lock:
            if self._catalog and (time.time() - self._last_loaded) < INFRASTRUCTURE_CACHE_TTL_SECONDS:
                return self._catalog

            start = time.time()
            print("Loading infrastructure datasets from Supabase...")
            dataset_start = time.time()
            try:
                (
                    substations,
                    transmission_lines,
                    fiber_cables,
                    ixps,
                    water_resources,
                ) = await asyncio.gather(
                    query_supabase("substations?select=*"),
                    query_supabase("transmission_lines?select=*"),
                    query_supabase("fiber_cables?select=*", limit=200),
                    query_supabase("internet_exchange_points?select=*"),
                    query_supabase("water_resources?select=*"),
                )
            except Exception as exc:
                print(f"Error initializing infrastructure datasets: {exc}")
                raise
            print(
                f"[\u2713] Infrastructure datasets loaded in {time.time() - dataset_start:.2f}s"
            )

            print("Building infrastructure spatial indices...")
            build_start = time.time()
            catalog = self._build_catalog(
                substations or [],
                transmission_lines or [],
                fiber_cables or [],
                ixps or [],
                water_resources or [],
            )
            print(
                f"[\u2713] Infrastructure spatial indices built in {time.time() - build_start:.2f}s"
            )

            elapsed = time.time() - start
            print(
                "✅ Infrastructure catalog refreshed in "
                f"{elapsed:.2f}s (substations={catalog.counts['substations']}, "
                f"transmission={catalog.counts['transmission']}, fiber={catalog.counts['fiber']}, "
                f"ixp={catalog.counts['ixps']}, water={catalog.counts['water']})"
            )

            self._catalog = catalog
            self._last_loaded = time.time()
            return catalog

    def _build_catalog(
        self,
        substations: Sequence[Dict[str, Any]],
        transmission_lines: Sequence[Dict[str, Any]],
        fiber_cables: Sequence[Dict[str, Any]],
        ixps: Sequence[Dict[str, Any]],
        water_resources: Sequence[Dict[str, Any]],
    ) -> InfrastructureCatalog:
        substation_features: List[PointFeature] = []
        transmission_features: List[LineFeature] = []
        fiber_features: List[LineFeature] = []
        ixp_features: List[PointFeature] = []
        water_point_features: List[PointFeature] = []
        water_line_features: List[LineFeature] = []

        substation_index = SpatialGrid()
        transmission_index = SpatialGrid()
        fiber_index = SpatialGrid()
        ixp_index = SpatialGrid()
        water_point_index = SpatialGrid()
        water_line_index = SpatialGrid()

        for station in substations:
            lat = _coerce_float(station.get("Lat") or station.get("latitude"))
            lon = _coerce_float(station.get("Long") or station.get("longitude"))
            if lat is None or lon is None:
                continue
            feature = PointFeature(lat=lat, lon=lon, data=station)
            substation_features.append(feature)
            substation_index.add_point(feature)

        for line in transmission_lines:
            feature = _prepare_line_feature(line.get("path_coordinates"), line)
            if feature:
                transmission_features.append(feature)
                transmission_index.add_bbox(feature.bbox, feature)

        for cable in fiber_cables:
            feature = _prepare_line_feature(cable.get("route_coordinates"), cable)
            if feature:
                fiber_features.append(feature)
                fiber_index.add_bbox(feature.bbox, feature)

        for ixp in ixps:
            lat = _coerce_float(ixp.get("latitude"))
            lon = _coerce_float(ixp.get("longitude"))
            if lat is None or lon is None:
                continue
            feature = PointFeature(lat=lat, lon=lon, data=ixp)
            ixp_features.append(feature)
            ixp_index.add_point(feature)

        for water in water_resources:
            prepared = _prepare_water_feature(water.get("coordinates"), water)
            if isinstance(prepared, PointFeature):
                water_point_features.append(prepared)
                water_point_index.add_point(prepared)
            elif isinstance(prepared, LineFeature):
                water_line_features.append(prepared)
                water_line_index.add_bbox(prepared.bbox, prepared)

        return InfrastructureCatalog(
            substations=substation_features,
            transmission_lines=transmission_features,
            fiber_cables=fiber_features,
            internet_exchange_points=ixp_features,
            water_points=water_point_features,
            water_lines=water_line_features,
            substations_index=substation_index,
            transmission_index=transmission_index,
            fiber_index=fiber_index,
            ixp_index=ixp_index,
            water_point_index=water_point_index,
            water_line_index=water_line_index,
            load_timestamp=time.time(),
            counts={
                "substations": len(substation_features),
                "transmission": len(transmission_features),
                "fiber": len(fiber_features),
                "ixps": len(ixp_features),
                "water": len(water_point_features) + len(water_line_features),
            },
        )


print("Initializing infrastructure cache subsystem...")
INFRASTRUCTURE_CACHE = InfrastructureCache()
print("[\u2713] Infrastructure cache subsystem ready")

print(f"Model boot completed successfully in {time.time() - _boot_start_time:.2f}s.")



def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _prepare_line_feature(raw_geometry: Any, payload: Dict[str, Any]) -> Optional[LineFeature]:
    if not raw_geometry:
        return None
    if isinstance(raw_geometry, str):
        try:
            raw_geometry = json.loads(raw_geometry)
        except json.JSONDecodeError:
            return None

    if not isinstance(raw_geometry, list) or len(raw_geometry) < 2:
        return None

    coordinates: List[Tuple[float, float]] = []
    for entry in raw_geometry:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        lon = _coerce_float(entry[0])
        lat = _coerce_float(entry[1])
        if lat is None or lon is None:
            continue
        coordinates.append((lat, lon))

    if len(coordinates) < 2:
        return None

    min_lat = min(lat for lat, _ in coordinates)
    max_lat = max(lat for lat, _ in coordinates)
    min_lon = min(lon for _, lon in coordinates)
    max_lon = max(lon for _, lon in coordinates)

    segments = [
        (coordinates[i][0], coordinates[i][1], coordinates[i + 1][0], coordinates[i + 1][1])
        for i in range(len(coordinates) - 1)
    ]

    return LineFeature(
        coordinates=coordinates,
        segments=segments,
        bbox=(min_lat, min_lon, max_lat, max_lon),
        data=payload,
    )


def _prepare_water_feature(raw_geometry: Any, payload: Dict[str, Any]) -> Optional[Any]:
    if not raw_geometry:
        return None
    if isinstance(raw_geometry, str):
        try:
            raw_geometry = json.loads(raw_geometry)
        except json.JSONDecodeError:
            return None

    if isinstance(raw_geometry, (list, tuple)) and len(raw_geometry) == 2 and all(
        isinstance(coord, (int, float)) for coord in raw_geometry
    ):
        lon, lat = raw_geometry
        lat_f = _coerce_float(lat)
        lon_f = _coerce_float(lon)
        if lat_f is None or lon_f is None:
            return None
        return PointFeature(lat=lat_f, lon=lon_f, data=payload)

    if isinstance(raw_geometry, list):
        feature = _prepare_line_feature(raw_geometry, payload)
        if feature:
            return feature

    return None


INFRASTRUCTURE_SEARCH_RADIUS_KM = {
    "substation": 100.0,
    "transmission": 100.0,
    "fiber": 100.0,
    "ixp": 100.0,
    "water": 100.0,
}


RENEWABLE_BASE_COMPONENT_WEIGHTS: Dict[str, float] = {
    "capacity": 0.25,
    "development_stage": 0.28,
    "technology": 0.17,
    "lcoe_resource_quality": 0.15,
    "tnuos_transmission_costs": 0.15,
}

RENEWABLE_INFRASTRUCTURE_COMPONENT_WEIGHTS: Dict[str, float] = {
    "grid_infrastructure": 0.45,
    "digital_infrastructure": 0.35,
    "water_resources": 0.20,
}

RENEWABLE_BASE_MAX_SCORE = 85.0
RENEWABLE_INFRASTRUCTURE_SCALING = 0.30
RENEWABLE_INFRASTRUCTURE_MAX_BONUS = 25.0


def calculate_base_investment_score_renewable(
    project: Dict[str, Any]
) -> Tuple[float, Dict[str, float], Dict[str, float]]:
    """Combine project fundamentals into a 0-100 base investment score."""

    capacity_score = calculate_capacity_component_score(project.get("capacity_mw", 0) or 0.0)
    development_status = (
        project.get("development_status_short")
        or project.get("development_status")
        or ""
    )
    stage_score = calculate_development_stage_score(development_status)
    technology_score = calculate_technology_score(project.get("technology_type", ""))
    lcoe_score = calculate_lcoe_score(development_status)

    latitude = _coerce_float(project.get("latitude"))
    longitude = _coerce_float(project.get("longitude"))
    if latitude is None or longitude is None:
        tnuos_score = 50.0
    else:
        tnuos_score = calculate_tnuos_score(latitude, longitude)

    components = {
        "capacity": float(capacity_score),
        "development_stage": float(stage_score),
        "technology": float(technology_score),
        "lcoe_resource_quality": float(lcoe_score),
        "tnuos_transmission_costs": float(tnuos_score),
    }

    weighted_components = {
        key: components[key] * weight
        for key, weight in RENEWABLE_BASE_COMPONENT_WEIGHTS.items()
    }

    weighted_total = sum(weighted_components.values())
    base_score = max(0.0, min(RENEWABLE_BASE_MAX_SCORE, weighted_total))

    contribution_scale = 0.0
    if weighted_total > 0:
        contribution_scale = base_score / weighted_total

    contributions = {
        key: weighted_components[key] * contribution_scale
        for key in weighted_components
    }

    return base_score, components, contributions


def calculate_infrastructure_bonus_renewable(
    proximity_scores: Dict[str, float]
) -> Tuple[float, Dict[str, float], Dict[str, float]]:
    """Translate proximity-derived scores into an infrastructure bonus."""

    grid_score = calculate_grid_infrastructure_score(proximity_scores)
    digital_score = calculate_digital_infrastructure_score(proximity_scores)
    water_score = calculate_water_resources_score(proximity_scores)

    components = {
        "grid_infrastructure": float(grid_score),
        "digital_infrastructure": float(digital_score),
        "water_resources": float(water_score),
    }

    weighted_components = {
        key: components[key] * weight
        for key, weight in RENEWABLE_INFRASTRUCTURE_COMPONENT_WEIGHTS.items()
    }

    raw_bonus = sum(weighted_components.values()) * RENEWABLE_INFRASTRUCTURE_SCALING
    infrastructure_bonus = max(
        0.0, min(RENEWABLE_INFRASTRUCTURE_MAX_BONUS, raw_bonus)
    )

    raw_contributions = {
        key: weighted_components[key] * RENEWABLE_INFRASTRUCTURE_SCALING
        for key in weighted_components
    }
    raw_total = sum(raw_contributions.values())
    contribution_scale = 0.0
    if raw_total > 0:
        contribution_scale = infrastructure_bonus / raw_total

    contributions = {
        key: raw_contributions[key] * contribution_scale for key in raw_contributions
    }

    return infrastructure_bonus, components, contributions


def calculate_enhanced_investment_rating(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    persona: Optional[PersonaType] = None,
) -> Dict[str, Any]:
    if persona is not None:
        return calculate_persona_weighted_score(project, proximity_scores, persona)

    base_score, base_components, base_contributions = calculate_base_investment_score_renewable(project)
    (
        infrastructure_bonus,
        infrastructure_components,
        infrastructure_contributions,
    ) = calculate_infrastructure_bonus_renewable(proximity_scores)
    total_internal_score = min(100.0, base_score + infrastructure_bonus)
    display_rating = total_internal_score / 10.0
    color = get_color_from_score(total_internal_score)
    description = get_rating_description(total_internal_score)

    combined_components = {
        **{key: round(value, 1) for key, value in base_components.items()},
        **{key: round(value, 1) for key, value in infrastructure_components.items()},
    }

    combined_contributions = {
        **{key: round(value, 1) for key, value in base_contributions.items()},
        **{key: round(value, 1) for key, value in infrastructure_contributions.items()},
    }

    return {
        "base_investment_score": round(base_score / 10.0, 1),
        "infrastructure_bonus": round(infrastructure_bonus / 10.0, 1),
        "investment_rating": round(display_rating, 1),
        "rating_description": description,
        "color_code": color,
        "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
        "internal_total_score": round(total_internal_score, 1),
        "component_scores": combined_components,
        "weighted_contributions": combined_contributions,
        "scoring_methodology": "Traditional renewable energy scoring (10-100 internal, 1.0-10.0 display)",
    }


async def calculate_proximity_scores_batch(projects: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    if not projects:
        return []

    catalog = await INFRASTRUCTURE_CACHE.get_catalog()
    results: List[Dict[str, float]] = []

    for project in projects:
        project_lat = _coerce_float(project.get("latitude"))
        project_lon = _coerce_float(project.get("longitude"))
        if project_lat is None or project_lon is None:
            results.append(
                {
                    "substation_score": 0.0,
                    "transmission_score": 0.0,
                    "fiber_score": 0.0,
                    "ixp_score": 0.0,
                    "water_score": 0.0,
                    "total_proximity_bonus": 0.0,
                    "nearest_distances": {},
                }
            )
            continue

        proximity_scores = calculate_proximity_scores(
            catalog,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM,
            INFRASTRUCTURE_HALF_DISTANCE_KM,
        )
        results.append(proximity_scores)

    return results

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

    proximity_scores = await calculate_proximity_scores_batch(sites_for_calc)

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
            rating_result = calculate_persona_weighted_score(site_data, prox_scores, persona, "demand", None, None)
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
    request: Request,
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
    user_ideal_mw: Optional[float] = Query(  # NEW PARAMETER
        None,
        description="User's preferred capacity in MW (overrides persona default, sets Gaussian peak)",
    ),
) -> Dict[str, Any]:
    user_id, user_email = extract_user_from_jwt(request.headers.get("authorization"))
    start_time = time.time()
    parsed_custom_weights = None
    if custom_weights:
        print(f"[CriteriaModal] Raw custom weights payload: {custom_weights}")
        try:
            parsed_custom_weights = json.loads(custom_weights)
            if not isinstance(parsed_custom_weights, dict):
                print(
                    "[CriteriaModal] ⚠️ Expected a JSON object with 7 criteria weights but received",
                    type(parsed_custom_weights).__name__,
                )
                parsed_custom_weights = None
            else:
                total = sum(value for value in parsed_custom_weights.values() if isinstance(value, (int, float)))
                if total and abs(total - 1.0) > 0.01:
                    parsed_custom_weights = {
                        key: value / total if isinstance(value, (int, float)) else value
                        for key, value in parsed_custom_weights.items()
                    }

                ordered_keys = [
                    "capacity",
                    "connection_speed",
                    "resilience",
                    "land_planning",
                    "latency",
                    "cooling",
                    "price_sensitivity",
                ]
                formatted_weights = []
                for key in ordered_keys:
                    value = parsed_custom_weights.get(key)
                    if isinstance(value, (int, float)):
                        formatted_weights.append(f"{key}={value:.3f}")
                    else:
                        formatted_weights.append(f"{key}=None")
                print(
                    "[CriteriaModal] Normalized criteria weights received -> "
                    + ", ".join(formatted_weights)
                )
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            print(f"[CriteriaModal] ❌ Failed to parse custom weights: {exc}")
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
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects)
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
                user_ideal_mw=user_ideal_mw,  
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
                        user_ideal_mw=user_ideal_mw,
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
                            project, proximity_scores, persona, "demand", user_max_price_mwh, user_ideal_mw
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
                        user_ideal_mw,
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

    # Save workflow analysis (fire-and-forget)
    if persona or parsed_custom_weights:
        weights_to_save = parsed_custom_weights or PERSONA_WEIGHTS.get(persona, {})
        asyncio.create_task(
            save_workflow_analysis(
                user_id=user_id,
                user_email=user_email,
                persona=persona or "custom",
                workflow_type=persona or "custom_weights",
                request_path=request.url.path,
                criteria_weights=weights_to_save,
                scoring_method=active_scoring_method,
                dc_demand_mw=dc_demand_mw,
                user_ideal_mw=user_ideal_mw,
                top_5_projects=top_projects[:10],
            )
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


@app.post("/api/projects/power-developer-analysis")
async def analyze_for_power_developer(
    request: Request,
    payload: Dict[str, Any] = Body(default_factory=dict),
    target_persona: Optional[str] = Query(
        None, description="greenfield, repower, or stranded"
    ),
    limit: int = Query(5000),
    source_table: str = Query(
        "tec_connections", description="Source table: tec_connections or renewable_projects"
    ),
) -> Dict[str, Any]:
    user_id, user_email = extract_user_from_jwt(request.headers.get("authorization"))
    raw_criteria = payload.get("criteria") if isinstance(payload, dict) else None
    ideal_value = payload.get("ideal_mw") if isinstance(payload, dict) else None

    if isinstance(raw_criteria, dict):
        criteria = {k: v for k, v in raw_criteria.items() if k != "ideal_mw"}
        if ideal_value is None:
            ideal_value = raw_criteria.get("ideal_mw")
    elif isinstance(payload, dict):
        criteria = {k: v for k, v in payload.items() if k not in {"ideal_mw", "site_location"}}
    else:
        criteria = {}

    site_location = payload.get("site_location") if isinstance(payload, dict) else None

    user_ideal_mw: Optional[float] = None
    try:
        if ideal_value is not None:
            parsed_ideal = float(ideal_value)
            user_ideal_mw = parsed_ideal if parsed_ideal > 0 else None
    except (TypeError, ValueError):
        user_ideal_mw = None

    # Save workflow analysis (fire-and-forget)
    result = await run_power_developer_analysis(
        criteria=criteria,
        site_location=site_location if isinstance(site_location, dict) else None,
        target_persona=target_persona,
        limit=limit,
        source_table=source_table,
        query_supabase=query_supabase,
        calculate_proximity_scores_batch=calculate_proximity_scores_batch,
        user_ideal_mw=user_ideal_mw,
    )

    try:
        asyncio.create_task(
            save_workflow_analysis(
                user_id=user_id,
                user_email=user_email,
                persona=target_persona or "greenfield",
                workflow_type=target_persona or "greenfield",
                request_path=request.url.path,
                criteria_weights=criteria if isinstance(criteria, dict) else {},
                scoring_method="power_developer",
                dc_demand_mw=None,
                user_ideal_mw=user_ideal_mw,
                top_5_projects=[
                    {
                        "type": "Feature",
                        "geometry": feature.get("geometry"),
                        "properties": feature.get("properties"),
                    }
                    for feature in result.get("features", [])[:5]
                ],
            )
        )
    except Exception as exc:
        print(f"⚠️ Workflow save task failed: {exc}")

    return result


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
        target_scoring = calculate_persona_weighted_score(project, dummy_proximity, target_customer, "demand", None, None)
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
        lat, lon = extract_coordinates(row)

        if lat is None or lon is None:
            print(f"⚠️ Skip TEC '{row.get('project_name')}' - no coords")
            return None

        capacity_mw = _coerce_float(row.get("capacity_mw"))
        voltage = _coerce_float(row.get("voltage"))
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


# ============================================================================
# PORTFOLIO OPTIMIZATION ENDPOINTS
# ============================================================================


class PortfolioAnalysisRequest(BaseModel):
    """Request model for portfolio analysis."""
    project_ids: Optional[List[str]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    weights: Optional[Dict[str, float]] = None


class PortfolioOptimizationRequest(BaseModel):
    """Request model for portfolio optimization."""
    project_ids: Optional[List[str]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    total_investment_mw: Optional[float] = None
    risk_profile: str = "moderate"
    max_single_project_pct: float = 40.0
    min_projects: int = 3


class EfficientFrontierRequest(BaseModel):
    """Request model for efficient frontier calculation."""
    project_ids: Optional[List[str]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    num_points: int = 20
    max_weight: float = 0.4


async def _get_projects_for_portfolio(
    project_ids: Optional[List[str]] = None,
    projects: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Helper to get projects either from IDs or direct data."""
    if projects:
        return projects

    if project_ids:
        # Fetch projects from database
        id_list = ",".join(f'"{pid}"' for pid in project_ids)
        query = f"renewable_projects?ref_id=in.({id_list})"
        rows = await query_supabase(query, limit=len(project_ids))
        if rows:
            return rows if isinstance(rows, list) else [rows]

    # Default: fetch top projects
    query = "renewable_projects?select=*&capacity_mw=gte.5&limit=50"
    rows = await query_supabase(query, limit=50)
    return rows if rows and isinstance(rows, list) else []


@app.post("/api/portfolio/analyze")
async def analyze_portfolio(request: PortfolioAnalysisRequest):
    """
    Analyze a portfolio of renewable energy projects.

    Returns comprehensive portfolio metrics including:
    - Portfolio score (composite of multiple factors)
    - Risk-adjusted returns (Sharpe, Sortino, Treynor)
    - Diversification metrics
    - Geographic and technology breakdown
    - Optimal allocations
    """
    try:
        projects = await _get_projects_for_portfolio(
            request.project_ids, request.projects
        )

        if not projects:
            raise HTTPException(400, "No projects found for portfolio analysis")

        result = calculate_multi_project_portfolio_score(
            projects,
            weights=request.weights,
        )

        return {
            "success": True,
            "portfolio_analysis": result,
            "project_count": len(projects),
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ Portfolio analysis error: {exc}")
        raise HTTPException(500, f"Portfolio analysis failed: {exc}")


@app.post("/api/portfolio/optimize")
async def optimize_portfolio(request: PortfolioOptimizationRequest):
    """
    Calculate optimal capacity allocation using Markowitz mean-variance optimization.

    Supports different risk profiles:
    - conservative: Lower volatility, moderate returns
    - moderate: Balanced risk/return
    - aggressive: Higher potential returns, higher volatility
    """
    try:
        projects = await _get_projects_for_portfolio(
            request.project_ids, request.projects
        )

        if not projects:
            raise HTTPException(400, "No projects found for optimization")

        # Map risk profile string to enum
        risk_map = {
            "conservative": RiskProfile.CONSERVATIVE,
            "moderate": RiskProfile.MODERATE,
            "aggressive": RiskProfile.AGGRESSIVE,
        }
        risk_profile = risk_map.get(
            request.risk_profile.lower(), RiskProfile.MODERATE
        )

        result = calculate_optimal_allocation(
            projects,
            total_investment_mw=request.total_investment_mw,
            risk_profile=risk_profile,
            max_single_project_pct=request.max_single_project_pct,
            min_projects=request.min_projects,
        )

        return {
            "success": True,
            "optimization_result": result,
            "project_count": len(projects),
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ Portfolio optimization error: {exc}")
        raise HTTPException(500, f"Portfolio optimization failed: {exc}")


@app.post("/api/portfolio/correlations")
async def get_portfolio_correlations(request: PortfolioAnalysisRequest):
    """
    Analyze correlations between projects in the portfolio.

    Returns:
    - Pairwise correlations (technology and geographic components)
    - Best diversifying pairs (lowest correlation)
    - Highest correlated pairs (potential concentration risk)
    """
    try:
        projects = await _get_projects_for_portfolio(
            request.project_ids, request.projects
        )

        if len(projects) < 2:
            raise HTTPException(
                400, "Need at least 2 projects for correlation analysis"
            )

        result = analyze_portfolio_correlations(projects)

        return {
            "success": True,
            "correlation_analysis": result,
            "project_count": len(projects),
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ Correlation analysis error: {exc}")
        raise HTTPException(500, f"Correlation analysis failed: {exc}")


@app.post("/api/portfolio/risk-adjusted-returns")
async def get_risk_adjusted_returns(
    request: PortfolioAnalysisRequest,
    benchmark_return: float = Query(8.0, description="Benchmark annual return %"),
    benchmark_volatility: float = Query(15.0, description="Benchmark volatility %"),
    risk_free_rate: float = Query(4.0, description="Risk-free rate %"),
):
    """
    Calculate risk-adjusted return metrics for the portfolio.

    Returns:
    - Sharpe ratio (excess return per unit of total risk)
    - Sortino ratio (excess return per unit of downside risk)
    - Treynor ratio (excess return per unit of systematic risk)
    - Information ratio (active return vs tracking error)
    - Value at Risk (VaR) and Conditional VaR
    """
    try:
        projects = await _get_projects_for_portfolio(
            request.project_ids, request.projects
        )

        if not projects:
            raise HTTPException(400, "No projects found for analysis")

        result = calculate_risk_adjusted_returns(
            projects,
            weights=request.weights,
            benchmark_return=benchmark_return,
            benchmark_volatility=benchmark_volatility,
            risk_free_rate=risk_free_rate,
        )

        return {
            "success": True,
            "risk_adjusted_analysis": result,
            "project_count": len(projects),
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ Risk-adjusted returns error: {exc}")
        raise HTTPException(500, f"Risk-adjusted returns calculation failed: {exc}")


@app.post("/api/portfolio/efficient-frontier")
async def get_efficient_frontier(request: EfficientFrontierRequest):
    """
    Calculate the efficient frontier for the portfolio.

    Returns a series of optimal portfolios ranging from minimum variance
    to maximum return, allowing visualization of the risk-return trade-off.
    """
    try:
        projects = await _get_projects_for_portfolio(
            request.project_ids, request.projects
        )

        if not projects:
            raise HTTPException(400, "No projects found for frontier calculation")

        # Convert projects to returns
        project_returns = [estimate_project_returns(p) for p in projects]
        corr_matrix = build_correlation_matrix(project_returns)

        frontier = calculate_efficient_frontier(
            project_returns,
            corr_matrix,
            num_points=request.num_points,
            max_weight=request.max_weight,
        )

        # Convert to JSON-serializable format
        frontier_points = []
        for point in frontier:
            frontier_points.append({
                "expected_return": round(point.expected_return, 2),
                "volatility": round(point.volatility, 2),
                "sharpe_ratio": round(point.sharpe_ratio, 3),
                "weights": {k: round(v, 4) for k, v in point.weights.items()},
                "allocation_count": len([w for w in point.weights.values() if w > 0.01]),
            })

        return {
            "success": True,
            "efficient_frontier": frontier_points,
            "project_count": len(projects),
            "frontier_points": len(frontier_points),
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ Efficient frontier error: {exc}")
        raise HTTPException(500, f"Efficient frontier calculation failed: {exc}")


@app.get("/api/portfolio/geographic-diversification")
async def get_geographic_diversification(
    project_ids: Optional[str] = Query(None, description="Comma-separated project IDs"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Analyze geographic diversification of projects.

    Returns regional breakdown and diversification scores for the UK regions.
    """
    try:
        if project_ids:
            ids = [pid.strip() for pid in project_ids.split(",")]
            projects = await _get_projects_for_portfolio(project_ids=ids)
        else:
            query = "renewable_projects?select=*&capacity_mw=gte.5"
            rows = await query_supabase(query, limit=limit)
            projects = rows if rows and isinstance(rows, list) else []

        if not projects:
            raise HTTPException(400, "No projects found")

        result = calculate_multi_project_portfolio_score(projects)

        return {
            "success": True,
            "geographic_score": result["metrics"]["geographic_score"],
            "regional_breakdown": result["metrics"]["regional_breakdown"],
            "technology_score": result["metrics"]["technology_mix_score"],
            "technology_breakdown": result["metrics"]["technology_breakdown"],
            "project_count": len(projects),
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"❌ Geographic diversification error: {exc}")
        raise HTTPException(500, f"Geographic diversification analysis failed: {exc}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)















