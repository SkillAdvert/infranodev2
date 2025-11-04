from __future__ import annotations

import asyncio
import json
import math
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Tuple, Union, cast

import httpx
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

PersonaType = Literal["hyperscaler", "colocation", "edge_computing"]
PowerDeveloperPersona = Literal["greenfield", "repower", "stranded"]

KM_PER_DEGREE_LAT = 111.32
INFRASTRUCTURE_CACHE_TTL_SECONDS = int(os.getenv("INFRA_CACHE_TTL", "600"))
GRID_CELL_DEGREES = 0.5

# Updated persona weights matching 7 business criteria
PERSONA_WEIGHTS: Dict[str, Dict[str, float]] = {
    "hyperscaler": {
        "capacity": 0.244,                   # 24.4% - Large capacity critical
        "connection_speed": 0.167,           # 16.7% - Fast grid access important
        "resilience": 0.133,                 # 13.3% - Backup infrastructure needed
        "land_planning": 0.2,                # 20.0% - Want shovel-ready sites
        "latency": 0.056,                    # 5.6% - Not critical for hyperscale
        "cooling": 0.144,                    # 14.4% - Critical for high-density
        "price_sensitivity": 0.056,          # 5.6% - Less price-sensitive (quality matters)
    },
    "colocation": {
        "capacity": 0.141,                   # 14.1% - Moderate capacity
        "connection_speed": 0.163,           # 16.3% - Reliable connection important
        "resilience": 0.196,                 # 19.6% - Multi-tenant needs redundancy
        "land_planning": 0.163,              # 16.3% - Want ready sites
        "latency": 0.217,                    # 21.7% - Critical for tenant diversity
        "cooling": 0.087,                    # 8.7% - Important but manageable
        "price_sensitivity": 0.033,          # 3.3% - Cost matters but not primary
    },
    "edge_computing": {
        "capacity": 0.097,                   # 9.7% - Small footprint
        "connection_speed": 0.129,           # 12.9% - Decent connection needed
        "resilience": 0.108,                 # 10.8% - Some redundancy
        "land_planning": 0.28,               # 28.0% - MUST be fast to deploy
        "latency": 0.247,                    # 24.7% - CRITICAL for edge workloads
        "cooling": 0.054,                    # 5.4% - Minimal cooling needs
        "price_sensitivity": 0.086,          # 8.6% - Cost-sensitive for distributed
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

PERSONA_CAPACITY_RANGES = {
    "edge_computing": {"min": 0.4, "max": 5},
    "colocation": {"min": 5, "max": 30},
    "hyperscaler": {"min": 30, "max": 250},
}

# ============================================================================
# POWER DEVELOPER PROJECT TYPE PERSONAS
# ============================================================================
# Maps greenfield/repower/stranded to component score weights
# Same 7 business criteria as hyperscaler personas
# Weights sum to 1.0

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


def resolve_power_developer_persona(
    raw_value: Optional[str],
) -> Tuple[PowerDeveloperPersona, str, str]:
    """Normalize the requested persona and flag how it was resolved.

    Returns a tuple of:
        (effective_persona, requested_value, resolution_status)

    Where ``resolution_status`` is one of ``"defaulted"`` (no value supplied),
    ``"invalid"`` (value supplied but not recognized), or ``"valid"``.
    """

    requested_value = (raw_value or "").strip()
    normalized_value = requested_value.lower()

    if not normalized_value:
        return "greenfield", requested_value, "defaulted"

    if normalized_value not in POWER_DEVELOPER_PERSONAS:
        return "greenfield", requested_value, "invalid"

    return cast(PowerDeveloperPersona, normalized_value), requested_value, "valid"

# Validate weights sum to 1.0
for persona_name, weights_dict in POWER_DEVELOPER_PERSONAS.items():
    total_weight = sum(weights_dict.values())
    if not math.isclose(total_weight, 1.0, rel_tol=1e-6):
        print(f"⚠️ WARNING: {persona_name} weights sum to {total_weight}, not 1.0")

PERSONA_CAPACITY_PARAMS = {
    "edge_computing": {"min_mw": 0.3, "ideal_mw": 2.0, "max_mw": 5.0,"tolerance_factor": 0.7},
    "colocation": {"min_mw": 4.0, "ideal_mw": 12.0, "max_mw": 25.0, "tolerance_factor": 0.5},
    "hyperscaler": {"min_mw": 20.0, "ideal_mw": 50.0, "max_mw": 200.0, "tolerance_factor": 0.4},
    "default": {"min_mw": 5.0, "ideal_mw": 50.0, "max_mw": 100.0, "tolerance_factor": 0.5},
}

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


@dataclass
class PointFeature:
    lat: float
    lon: float
    data: Dict[str, Any]


@dataclass
class LineFeature:
    coordinates: List[Tuple[float, float]]
    segments: List[Tuple[float, float, float, float]]
    bbox: Tuple[float, float, float, float]
    data: Dict[str, Any]


@dataclass
class InfrastructureCatalog:
    substations: List[PointFeature]
    transmission_lines: List[LineFeature]
    fiber_cables: List[LineFeature]
    internet_exchange_points: List[PointFeature]
    water_points: List[PointFeature]
    water_lines: List[LineFeature]
    substations_index: "SpatialGrid"
    transmission_index: "SpatialGrid"
    fiber_index: "SpatialGrid"
    ixp_index: "SpatialGrid"
    water_point_index: "SpatialGrid"
    water_line_index: "SpatialGrid"
    load_timestamp: float
    counts: Dict[str, int]


class SpatialGrid:
    def __init__(self, cell_size_deg: float = GRID_CELL_DEGREES) -> None:
        self.cell_size_deg = cell_size_deg
        self._cells: Dict[Tuple[int, int], List[Any]] = defaultdict(list)

    def _index_lat(self, lat: float) -> int:
        return int(math.floor((lat + 90.0) / self.cell_size_deg))

    def _index_lon(self, lon: float) -> int:
        return int(math.floor((lon + 180.0) / self.cell_size_deg))

    def add_point(self, feature: PointFeature) -> None:
        key = (self._index_lat(feature.lat), self._index_lon(feature.lon))
        self._cells[key].append(feature)

    def add_bbox(self, bbox: Tuple[float, float, float, float], feature: LineFeature) -> None:
        min_lat, min_lon, max_lat, max_lon = bbox
        lat_start = self._index_lat(min_lat)
        lat_end = self._index_lat(max_lat)
        lon_start = self._index_lon(min_lon)
        lon_end = self._index_lon(max_lon)
        for lat_idx in range(lat_start, lat_end + 1):
            for lon_idx in range(lon_start, lon_end + 1):
                self._cells[(lat_idx, lon_idx)].append(feature)

    def query(self, lat: float, lon: float, steps: int) -> Iterable[Any]:
        base_lat = self._index_lat(lat)
        base_lon = self._index_lon(lon)
        seen: set[int] = set()
        for lat_offset in range(-steps, steps + 1):
            for lon_offset in range(-steps, steps + 1):
                cell = (base_lat + lat_offset, base_lon + lon_offset)
                for feature in self._cells.get(cell, ()):  # type: ignore[arg-type]
                    feature_id = id(feature)
                    if feature_id not in seen:
                        seen.add(feature_id)
                        yield feature

    def approximate_cell_width_km(self) -> float:
        return self.cell_size_deg * KM_PER_DEGREE_LAT


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


INFRASTRUCTURE_HALF_DISTANCE_KM = {
    "substation": 50.0,
    "transmission": 50.0,
    "fiber": 25.0,
    "ixp": 25.0,
    "water": 25.0,
}


def _grid_steps_for_radius(grid: SpatialGrid, radius_km: float) -> int:
    cell_width_km = max(1.0, grid.approximate_cell_width_km())
    return max(1, int(math.ceil(radius_km / cell_width_km)) + 1)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def exponential_score(distance_km: float, half_distance_km: float) -> float:
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


def _bbox_within_search(
    bbox: Tuple[float, float, float, float],
    lat: float,
    lon: float,
    radius_km: float,
) -> bool:
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
    grid: SpatialGrid,
    features: Sequence[PointFeature],
    lat: float,
    lon: float,
    radius_km: float,
) -> Optional[Tuple[float, PointFeature]]:
    best: Optional[Tuple[float, PointFeature]] = None
    steps = _grid_steps_for_radius(grid, radius_km)
    for step in range(1, steps + 2):
        for feature in grid.query(lat, lon, step):
            if not isinstance(feature, PointFeature):
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
            distance = haversine(lat, lon, feature.lat, feature.lon)
            if not best or distance < best[0]:
                best = (distance, feature)
    return best


def _nearest_line(
    grid: SpatialGrid,
    features: Sequence[LineFeature],
    lat: float,
    lon: float,
    radius_km: float,
) -> Optional[Tuple[float, LineFeature]]:
    best: Optional[Tuple[float, LineFeature]] = None
    steps = _grid_steps_for_radius(grid, radius_km)
    for step in range(1, steps + 2):
        for feature in grid.query(lat, lon, step):
            if not isinstance(feature, LineFeature):
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
            if not _bbox_within_search(feature.bbox, lat, lon, radius_km):
                continue
            distance = _distance_to_line_feature(feature, lat, lon)
            if not best or distance < best[0]:
                best = (distance, feature)
    return best


def _distance_to_line_feature(feature: LineFeature, lat: float, lon: float) -> float:
    best = float("inf")
    for segment in feature.segments:
        distance = point_to_line_segment_distance(lat, lon, *segment)
        if distance < best:
            best = distance
            if best == 0:
                break
    return best if best != float("inf") else 9999.0

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
    
    # Use user's ideal if provided, otherwise fall back to persona default
    ideal = user_ideal_mw if user_ideal_mw is not None else params.get("ideal_mw", 75.0)
    
    # Calculate tolerance as 50% of ideal capacity
    tolerance_factor = params.get("tolerance_factor", 0.5)
    tolerance = ideal * tolerance_factor
    
    # Gaussian distribution: 100 * exp(-((x - ideal)²) / (2 × tolerance²))
    exponent = -((capacity_mw - ideal) ** 2) / (2 * tolerance ** 2)
    score = 100.0 * math.exp(exponent)
    
    return max(0.0, min(100.0, float(score)))


def calculate_development_stage_score(status: str, perspective: str = "demand") -> float:
    """
    Score based on BTM (Behind-the-Meter) intervention timing and planning viability.

    Scoring philosophy:
    - Peak scores (90-95): Active planning or reactivatable consents (optimal BTM timing)
    - High scores (70-85): Consented or exempt sites (strong BTM potential)
    - Mid scores (40-45): Early concept or awaiting construction (narrowing window)
    - Low scores (0-35): Refused, withdrawn, or under construction (poor BTM fit)

    Args:
        status: Development status from renewable_projects.development_status_short
        perspective: 'demand' (data center) or 'supply' (power developer)

    Returns:
        Float score 0-100 based on BTM intervention suitability
    """
    status_str = str(status).lower().strip()

    # BTM-optimized scoring spectrum (Set 2)
    # Maps to renewable_projects.development_status_short column
    STATUS_SCORES = {
        "decommissioned": 0,                    # Asset dismantled — no potential
        "abandoned": 5,                         # Project halted; non-recoverable
        "appeal withdrawn": 10,                 # Appeal dropped — closed path
        "appeal refused": 15,                   # Appeal denied — minimal viability
        "under construction": 20,               # Build started; BTM window closed
        "appeal lodged": 25,                    # Legal uncertainty; long timelines
        "application refused": 30,              # Denied; redesign needed
        "application withdrawn": 35,            # Paused; may re-enter
        "awaiting construction": 40,            # Consented; BTM opportunity narrowing
        "no application made": 45,              # Concept only; untested
        "secretary of state granted": 80,       # Nationally endorsed; fixed design limits BTM
        "planning expired": 70,                 # Previously consented; reactivatable — HIGH BTM
        "no application required": 100,          # Permitted development — VERY STRONG BTM
        "application submitted": 100,            # Live planning — OPTIMAL BTM timing
        "revised": 90,                          # Resubmitted — TOP-TIER BTM suitability

        # Legacy aliases for backward compatibility
        "consented": 70,                        # Map to "awaiting construction" equivalent
        "granted": 70,                          # Same as consented
        "in planning": 55,                      # Map to "no application made" equivalent
        "operational": 10,                       # Same as decommissioned (no BTM value)
    }

    # Try exact match first
    if status_str in STATUS_SCORES:
        base_score = STATUS_SCORES[status_str]
    else:
        # Fallback: partial string matching for database variants
        # Example: "Planning Consent Granted" → matches "granted" → 40
        base_score = 45.0  # Default to "concept" level for unknowns

        for key, score in STATUS_SCORES.items():
            if key in status_str:
                base_score = score
                break

    # Perspective adjustment (optional)
    if perspective == "supply":
        # Power developers may value operational/construction sites differently
        # Could add logic here if needed, but generally BTM scoring is demand-focused
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
            # Fall back to estimation if value cannot be converted
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
    """
    Score based on grid connection speed potential.

    Factors:
    - Development stage (proxy for grid agreement status)
    - Proximity to substation (faster connection)
    - Grid infrastructure quality

    PLACEHOLDER: In production, would use:
    - Actual grid queue position data
    - Substation headroom/capacity data
    - DNO constraint data
    - Curtailment risk scores

    Returns: 0-100 score (higher = faster connection expected)
    """
    # Get development stage (indicates grid agreement likelihood)
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

    # Proximity to substation (closer = faster/cheaper connection)
    distances = proximity_scores.get("nearest_distances", {})
    substation_km = distances.get("substation_km", 999)

    substation_score = 100.0 * math.exp(-substation_km / 30.0)

    transmission_km = distances.get("transmission_km", 999)
    transmission_score = 100.0 * math.exp(-transmission_km / 50.0)

    # Combine: 50% stage, 30% substation proximity, 20% transmission proximity
    final_score = (stage_score * 0.50) + (substation_score * 0.30) + (transmission_score * 0.20)

    return max(0.0, min(100.0, final_score))


def calculate_resilience_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float]
) -> float:
    """
    Score based on infrastructure resilience/redundancy.

    Factors:
    - Number of nearby backup infrastructure options
    - Technology type (battery storage = onsite firming)
    - Multiple substation options within range

    PLACEHOLDER: In production, would use:
    - Actual N/N+1/2N redundancy analysis
    - Onsite BESS capacity data
    - Gas backup availability
    - Multiple grid connection options
    - Dual fiber route availability

    Returns: 0-100 score (higher = more resilient)
    """
    distances = proximity_scores.get("nearest_distances", {})

    # Count "good" backup options (within reasonable distance)
    backup_count = 0

    # Primary substation (<15km = excellent)
    substation_km = distances.get("substation_km", 999)
    if substation_km < 15:
        backup_count += 4  # Close enough for multiple connection options
    elif substation_km < 30:
        backup_count += 3

    # Transmission line access (<40km)
    transmission_km = distances.get("transmission_km", 999)
    if transmission_km < 30:
        backup_count += 2

    # Technology bonus: Battery storage = onsite firming
    tech_type = str(project.get("technology_type", "")).lower()
    if "battery" in tech_type or "bess" in tech_type:
        backup_count += 1  # Significant resilience boost
    elif "hybrid" in tech_type:
        backup_count += 3  # Some onsite storage

    # Convert count to score (0-10 options mapped to 0-100)
    # Max realistic = 10 options (2+1+2+1+1+2+1 with battery)
    resilience_score = (backup_count / 10.0) * 100.0

    return max(0.0, min(100.0, resilience_score))


def calculate_price_sensitivity_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    user_max_price_mwh: Optional[float] = None
) -> float:
    """
    Score based on total power cost vs. user's budget.

    Calculation:
    - Estimated LCOE (levelized cost of energy)
    - TNUoS transmission charges
    - Total = LCOE + TNUoS impact
    - Compare to user's acceptable price range

    PLACEHOLDER: In production, would use:
    - Actual PPA prices available at site
    - Real-time merchant price forecasts
    - Grid connection cost estimates
    - Curtailment risk financial impact

    Args:
        user_max_price_mwh: User's maximum acceptable price (£/MWh)
                           If None, score all sites relatively

    Returns: 0-100 score (higher = better value for money)
    """
    # Get estimated LCOE for this site
    tech_type = str(project.get("technology_type", "")).lower()
    lat = project.get("latitude", 0)
    lng = project.get("longitude", 0)

    # Estimate LCOE based on technology and location
    # These are rough UK averages for reference
    base_lcoe = 60.0  # £/MWh default
    reference_cf = 0.30

    if "solar" in tech_type:
        base_lcoe = 52.0  # Solar LCOE in UK
        reference_cf = 0.12
    elif "wind" in tech_type:
        if "offshore" in tech_type:
            base_lcoe = 80.0  # Offshore wind
            reference_cf = 0.40
        else:
            base_lcoe = 60.0  # Onshore wind
            reference_cf = 0.30
    elif "battery" in tech_type or "bess" in tech_type:
        base_lcoe = 65.0  # Battery arbitrage
        reference_cf = 0.20
    elif "hydro" in tech_type:
        base_lcoe = 70.0  # Hydro (excellent)
        reference_cf = 0.35
    elif "biomass" in tech_type:
        base_lcoe = 85.0  # Biomass (expensive)
        reference_cf = 0.70
    elif "gas" in tech_type or "ccgt" in tech_type:
        base_lcoe = 70.0  # Gas (fuel dependent)
        reference_cf = 0.55
    elif "hybrid" in tech_type:
        reference_cf = 0.25

    user_cf = project.get("capacity_factor")
    capacity_factor_pct = estimate_capacity_factor(tech_type, lat, user_cf)
    capacity_factor = capacity_factor_pct / 100.0

    adjusted_lcoe = base_lcoe
    if capacity_factor > 0:
        adjusted_lcoe = base_lcoe * (reference_cf / capacity_factor)

    # Get TNUoS estimate (£/kW/year converted to £/MWh impact)
    # TNUoS score is 0-100, need to convert to actual cost
    tnuos_percentile = calculate_tnuos_score(lat, lng)

    # Map TNUoS percentile to actual cost impact
    # UK range: -£3 to +£16/kW/year
    # For 1MW load at 40% capacity factor: impact ~£5-8/MWh
    tnuos_min = -3.0  # £/kW (credits in Scotland)
    tnuos_max = 16.0  # £/kW (charges in South)

    # Convert percentile (0-100) to actual tariff
    tnuos_tariff = tnuos_min + ((100 - tnuos_percentile) / 100.0) * (tnuos_max - tnuos_min)

    # Convert £/kW/year to £/MWh impact (assuming 40% capacity factor)
    # Annual hours = 8760, capacity factor hours = 3504
    annual_hours = 8760
    capacity_hours = annual_hours * capacity_factor
    tnuos_mwh_impact = (
        (abs(tnuos_tariff) * 1000) / capacity_hours if capacity_hours > 0 else 0.0
    )

    # Total estimated cost
    if tnuos_tariff < 0:
        # Negative tariff = credit, reduces cost
        total_cost_mwh = adjusted_lcoe - tnuos_mwh_impact
    else:
        # Positive tariff = charge, increases cost
        total_cost_mwh = adjusted_lcoe + tnuos_mwh_impact

    # Score based on user's budget
    if user_max_price_mwh:
        # User specified a max price
        if total_cost_mwh <= user_max_price_mwh:
            # Within budget - score based on how much cheaper
            savings_pct = (user_max_price_mwh - total_cost_mwh) / user_max_price_mwh
            score = 50 + (savings_pct * 50)  # 50-100 range
        else:
            # Over budget - penalize proportionally
            overage_pct = (total_cost_mwh - user_max_price_mwh) / user_max_price_mwh
            score = 50 * math.exp(-overage_pct * 2)  # Exponential decay
    else:
        # No user budget specified - score relatively
        # Lower cost = higher score
        # Assume range: £40-100/MWh
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
    """Compute persona-agnostic component scores that rely on proximity metrics."""

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
    Compute 7 component scores matching business criteria.

    Args:
        project: Project data from database
        proximity_scores: Infrastructure proximity calculations
        persona: Persona type (for capacity scoring)
        perspective: 'demand' (data center) or 'supply' (power developer)
        user_max_price_mwh: User's max acceptable price for price_sensitivity
        shared_component_scores: Optional cache of persona-agnostic scores

    Returns:
        Dictionary with 7 component scores (0-100 each)
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
        user_ideal_mw, # pass through users ideal capacity
    )

    return base_scores


def _normalize_component_scores(component_scores: Dict[str, float]) -> Dict[str, float]:
    """Normalize component scores to the unit interval."""

    normalized: Dict[str, float] = {}
    for key, value in component_scores.items():
        normalized[key] = max(0.0, min(1.0, value / 100.0))
    return normalized


def _get_persona_tuning(persona: PersonaType) -> Dict[str, float]:
    return PERSONA_SCORING_TUNING.get(persona, PERSONA_SCORING_TUNING["default"])


def _compute_posterior_persona_weights(
    persona: PersonaType,
    base_weights: Dict[str, float],
    normalized_scores: Dict[str, float],
) -> Tuple[Dict[str, float], float]:
    r"""Apply a Dirichlet-style Bayesian update to persona weights.

    The posterior weight for each component :math:`k` follows the simple
    proportionality

    .. math::

        w'_k \propto (w_k)^{\alpha} \cdot (s_k)^{\beta}

    where ``w_k`` is the baseline weight, ``s_k`` is the normalized score, and the
    persona-specific tuning parameters :math:`\alpha, \beta` control how much the
    evidence ``s_k`` can reinforce or diminish the baseline view.
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
    """Measure alignment with persona-specific ideal component targets."""

    targets = PERSONA_TARGET_COMPONENTS.get(persona, PERSONA_TARGET_COMPONENTS["default"])
    alignment = 0.0
    for key, weight in posterior_weights.items():
        target = targets.get(key, 0.75)
        alignment += weight * (1.0 - abs(normalized_scores.get(key, 0.0) - target))
    return max(0.0, min(1.0, alignment))


def _logistic_transform(value: float, midpoint: float, steepness: float) -> float:
    """Stable logistic transform to map [0,1] input to [0,1]."""

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
    """Calculate the persona score with explicit fusion equations.

    Pipeline overview (all values are clamped to ``[0, 1]`` where needed):

    1. Component normalization: ``s_k = component_score_k / 100``.
    2. Posterior weights: ``w'_k = (w_k^α * s_k^β) / Σ_j (w_j^α * s_j^β)``.
    3. Blended evidence strength: ``E = Σ_k (w'_k * s_k)``.
    4. Fusion score: ``F = a * Σ_k (w'_k * s_k) + b * Π_k s_k^{w'_k} + c * alignment``
       where ``alignment = Σ_k w'_k * (1 - |s_k - target_k|)``.
    5. Calibrated rating: ``score = σ(F; m - δ, γ)`` with logistic curve
       ``σ(x; m, γ) = 1 / (1 + exp(-γ * (x - m)))`` and midpoint shift
       ``δ = (E - m) * shift``.

    Args:
        user_max_price_mwh: User's maximum acceptable price (£/MWh)
    """
    baseline_weights = PERSONA_WEIGHTS[persona]

    # Get 7 component scores
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
    """Apply TOPSIS using persona weights, supporting positive and negative impacts."""

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


async def calculate_proximity_scores_batch(projects: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    if not projects:
        return []

    catalog = await INFRASTRUCTURE_CACHE.get_catalog()
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
            catalog.substations_index,
            catalog.substations,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["substation"],
        )
        if substation:
            distance, _ = substation
            proximity_scores["substation_score"] = exponential_score(distance, 30.0)
            nearest_distances["substation_km"] = round(distance, 1)

        transmission = _nearest_line(
            catalog.transmission_index,
            catalog.transmission_lines,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["transmission"],
        )
        if transmission:
            distance, _ = transmission
            proximity_scores["transmission_score"] = exponential_score(distance, 30.0)
            nearest_distances["transmission_km"] = round(distance, 1)

        fiber = _nearest_line(
            catalog.fiber_index,
            catalog.fiber_cables,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["fiber"],
        )
        if fiber:
            distance, _ = fiber
            proximity_scores["fiber_score"] = exponential_score(distance, 15.0)
            nearest_distances["fiber_km"] = round(distance, 1)

        ixp = _nearest_point(
            catalog.ixp_index,
            catalog.internet_exchange_points,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["ixp"],
        )
        if ixp:
            distance, _ = ixp
            proximity_scores["ixp_score"] = exponential_score(distance, 40.0)
            nearest_distances["ixp_km"] = round(distance, 1)

        water_point = _nearest_point(
            catalog.water_point_index,
            catalog.water_points,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["water"],
        )
        water_line = _nearest_line(
            catalog.water_line_index,
            catalog.water_lines,
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
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects)
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
        lat, lon = _extract_coordinates(row)

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)















