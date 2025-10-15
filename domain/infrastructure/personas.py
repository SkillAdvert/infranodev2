"""Persona configuration and scoring helpers."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

PersonaType = str

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
    "colocation": {"min": 5, "max": 50},
    "hyperscaler": {"min": 50, "max": 1000},
}

PERSONA_CAPACITY_PARAMS = {
    "edge_computing": {"min_mw": 0.4, "ideal_mw": 2.0, "max_mw": 5.0},
    "colocation": {"min_mw": 5.0, "ideal_mw": 20.0, "max_mw": 50.0},
    "hyperscaler": {"min_mw": 50.0, "ideal_mw": 100.0, "max_mw": 400.0},
    "default": {"min_mw": 50.0, "ideal_mw": 100.0, "max_mw": 400.0},
}


def filter_projects_by_persona_capacity(
    projects: List[Dict[str, float]], persona: PersonaType
) -> List[Dict[str, float]]:
    params = PERSONA_CAPACITY_RANGES.get(persona)
    if not params:
        return projects
    return [
        project
        for project in projects
        if params["min"] <= project.get("capacity_mw", 0) <= params["max"]
    ]


__all__ = [
    "PERSONA_CAPACITY_PARAMS",
    "PERSONA_CAPACITY_RANGES",
    "PERSONA_WEIGHTS",
    "PersonaType",
    "filter_projects_by_persona_capacity",
]
