import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

try:
    from backend.power_workflow import (
        POWER_DEVELOPER_PERSONAS,
        resolve_power_developer_persona,
        run_power_developer_analysis,
    )
    from backend.scoring import (
        build_persona_component_scores,
        calculate_weighted_score_from_components,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    pytest.skip(f"main.py dependencies missing: {exc}", allow_module_level=True)


def test_resolve_persona_defaults_to_greenfield_when_missing():
    persona, requested, status = resolve_power_developer_persona(None)
    assert persona == "greenfield"
    assert requested == ""
    assert status == "defaulted"


def test_resolve_persona_honors_stranded_case_insensitive():
    persona, requested, status = resolve_power_developer_persona("Stranded")
    assert persona == "stranded"
    assert requested == "Stranded"
    assert status == "valid"


def test_resolve_persona_rejects_invalid_value():
    persona, requested, status = resolve_power_developer_persona("unknown")
    assert persona == "greenfield"
    assert requested == "unknown"
    assert status == "invalid"


def test_defined_personas_match_weights():
    for persona_name in ("greenfield", "repower", "stranded"):
        persona, _, status = resolve_power_developer_persona(persona_name)
        assert status == "valid"
        assert persona in POWER_DEVELOPER_PERSONAS


@pytest.mark.asyncio
async def test_capacity_preference_changes_power_dev_scores():
    async def fake_query_supabase(_query: str, limit: int = 1):
        return [
            {
                "ref_id": "proj-1",
                "site_name": "Test Project",
                "capacity_mw": 20,
                "technology_type": "solar",
                "development_status_short": "in planning",
                "latitude": 51.0,
                "longitude": -0.1,
            }
            for _ in range(limit)
        ]

    async def fake_proximity_batch(projects):
        return [
            {
                "substation_score": 0.0,
                "transmission_score": 0.0,
                "fiber_score": 0.0,
                "ixp_score": 0.0,
                "water_score": 0.0,
                "nearest_distances": {},
            }
            for _ in projects
        ]

    result_default = await run_power_developer_analysis(
        criteria={},
        site_location=None,
        target_persona="greenfield",
        limit=1,
        source_table="renewable_projects",
        query_supabase=fake_query_supabase,
        calculate_proximity_scores_batch=fake_proximity_batch,
        user_ideal_mw=None,
    )

    result_custom_capacity = await run_power_developer_analysis(
        criteria={},
        site_location=None,
        target_persona="greenfield",
        limit=1,
        source_table="renewable_projects",
        query_supabase=fake_query_supabase,
        calculate_proximity_scores_batch=fake_proximity_batch,
        user_ideal_mw=5.0,
    )

    base_capacity = result_default["features"][0]["properties"]["component_scores"]["capacity"]
    custom_capacity = result_custom_capacity["features"][0]["properties"]["component_scores"]["capacity"]

    assert base_capacity != custom_capacity


@pytest.mark.asyncio
async def test_power_dev_scoring_uses_persona_pipeline():
    project = {
        "ref_id": "proj-2",
        "site_name": "Pipeline Match",
        "capacity_mw": 40,
        "technology_type": "wind",
        "development_status_short": "in planning",
        "latitude": 51.5,
        "longitude": -0.2,
    }

    proximity_scores = {
        "substation_score": 80.0,
        "transmission_score": 75.0,
        "fiber_score": 70.0,
        "ixp_score": 65.0,
        "water_score": 60.0,
        "nearest_distances": {},
    }

    async def fake_query_supabase(_query: str, limit: int = 1):
        return [project for _ in range(limit)]

    async def fake_proximity_batch(projects):
        return [proximity_scores for _ in projects]

    result = await run_power_developer_analysis(
        criteria={},
        site_location=None,
        target_persona="greenfield",
        limit=1,
        source_table="renewable_projects",
        query_supabase=fake_query_supabase,
        calculate_proximity_scores_batch=fake_proximity_batch,
        user_ideal_mw=None,
    )

    properties = result["features"][0]["properties"]

    fresh_component_scores = build_persona_component_scores(
        project,
        proximity_scores,
        persona="greenfield",
        perspective="demand",
    )

    expected_rating = calculate_weighted_score_from_components(
        fresh_component_scores,
        POWER_DEVELOPER_PERSONAS["greenfield"],
        persona_label="greenfield",
        proximity_scores=proximity_scores,
    )

    assert properties["investment_rating"] == expected_rating["investment_rating"]
    assert properties["rating_description"] == expected_rating["rating_description"]
    assert properties["color_code"] == expected_rating["color_code"]
