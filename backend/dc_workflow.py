"""Data centre workflow entry points.

This module keeps the public API for DC-specific consumers while delegating the
underlying scoring logic to :mod:`backend.scoring`.  It allows existing imports
(`backend.dc_workflow`) to keep working while enforcing the new shared
architecture that centralises reusable algorithms.
"""

from __future__ import annotations

from backend.scoring import (
    INFRASTRUCTURE_HALF_DISTANCE_KM,
    PERSONA_CAPACITY_PARAMS,
    PERSONA_CAPACITY_RANGES,
    PERSONA_SCORING_TUNING,
    PERSONA_TARGET_COMPONENTS,
    PERSONA_WEIGHTS,
    PersonaType,
    build_persona_component_scores,
    calculate_best_customer_match,
    calculate_capacity_component_score,
    calculate_connection_speed_score,
    calculate_custom_weighted_score,
    calculate_development_stage_score,
    calculate_digital_infrastructure_score,
    calculate_grid_infrastructure_score,
    calculate_lcoe_score,
    calculate_persona_topsis_score,
    calculate_persona_weighted_score,
    calculate_price_sensitivity_score,
    calculate_resilience_score,
    calculate_tnuos_score,
    calculate_technology_score,
    calculate_water_resources_score,
    estimate_capacity_factor,
    filter_projects_by_persona_capacity,
    get_color_from_score,
    get_rating_description,
)

__all__ = [
    "PersonaType",
    "PERSONA_WEIGHTS",
    "PERSONA_TARGET_COMPONENTS",
    "PERSONA_SCORING_TUNING",
    "PERSONA_CAPACITY_RANGES",
    "PERSONA_CAPACITY_PARAMS",
    "INFRASTRUCTURE_HALF_DISTANCE_KM",
    "get_color_from_score",
    "get_rating_description",
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
    "calculate_persona_weighted_score",
    "calculate_persona_topsis_score",
    "calculate_custom_weighted_score",
    "calculate_best_customer_match",
    "filter_projects_by_persona_capacity",
]

