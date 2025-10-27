"""Configuration constants and settings for the Infranodal API."""

from __future__ import annotations

import math
import os
from typing import Dict, Literal, Optional, Tuple, cast

# Type definitions
PersonaType = Literal["hyperscaler", "colocation", "edge_computing"]
PowerDeveloperPersona = Literal["greenfield", "repower", "stranded"]

# Constants
KM_PER_DEGREE_LAT = 111.32
INFRASTRUCTURE_CACHE_TTL_SECONDS = int(os.getenv("INFRA_CACHE_TTL", "600"))
GRID_CELL_DEGREES = 0.5

# ============================================================================
# DATA CENTER PERSONA WEIGHTS
# ============================================================================
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

PERSONA_CAPACITY_RANGES = {
    "edge_computing": {"min": 0.4, "max": 5},
    "colocation": {"min": 5, "max": 30},
    "hyperscaler": {"min": 30, "max": 1000},
}

PERSONA_CAPACITY_PARAMS = {
    "edge_computing": {"min_mw": 0.4, "ideal_mw": 2.0, "max_mw": 5.0},
    "colocation": {"min_mw": 5.0, "ideal_mw": 15.0, "max_mw": 30.0},
    "hyperscaler": {"min_mw": 30.0, "ideal_mw": 75.0, "max_mw": 200.0},
    "default": {"min_mw": 5.0, "ideal_mw": 50.0, "max_mw": 100.0},
}

# ============================================================================
# POWER DEVELOPER PROJECT TYPE PERSONAS
# ============================================================================
# Maps greenfield/repower/stranded to component score weights
# Same 7 business criteria as data center personas
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
