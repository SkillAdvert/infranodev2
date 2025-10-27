from __future__ import annotations

import math
import os
from typing import Dict, Literal

PersonaType = Literal["hyperscaler", "colocation", "edge_computing"]
PowerDeveloperPersona = Literal["greenfield", "repower", "stranded"]

KM_PER_DEGREE_LAT = 111.32
GRID_CELL_DEGREES = 0.5
INFRASTRUCTURE_CACHE_TTL_SECONDS = int(os.getenv("INFRA_CACHE_TTL", "600"))

# Updated persona weights matching 7 business criteria
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

for persona_name, weights_dict in POWER_DEVELOPER_PERSONAS.items():
    total_weight = sum(weights_dict.values())
    if not math.isclose(total_weight, 1.0, rel_tol=1e-6):
        print(f"⚠️ WARNING: {persona_name} weights sum to {total_weight}, not 1.0")

__all__ = [
    "PersonaType",
    "PowerDeveloperPersona",
    "KM_PER_DEGREE_LAT",
    "GRID_CELL_DEGREES",
    "INFRASTRUCTURE_CACHE_TTL_SECONDS",
    "PERSONA_WEIGHTS",
    "PERSONA_CAPACITY_RANGES",
    "POWER_DEVELOPER_PERSONAS",
    "POWER_DEVELOPER_CAPACITY_RANGES",
    "PERSONA_CAPACITY_PARAMS",
]
