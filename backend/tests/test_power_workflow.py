"""Comprehensive tests for backend/power_workflow.py module.

Tests persona resolution, coordinate extraction, TEC transformation,
and the complete power developer analysis workflow.
"""

import sys
import math
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

try:
    from backend.power_workflow import (
        # Constants
        PowerDeveloperPersona,
        POWER_DEVELOPER_PERSONAS,
        POWER_DEVELOPER_CAPACITY_RANGES,
        # Functions
        resolve_power_developer_persona,
        extract_coordinates,
        transform_tec_to_project_schema,
        run_power_developer_analysis,
    )
    from backend.scoring import (
        build_persona_component_scores,
        calculate_weighted_score_from_components,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    pytest.skip(f"module dependencies missing: {exc}", allow_module_level=True)


# ============================================================================
# Test Constants
# ============================================================================


class TestPowerDeveloperConstants:
    """Test power developer persona constants."""

    def test_persona_weights_sum_to_one(self):
        """All persona weight dictionaries should sum to approximately 1.0."""
        for persona, weights in POWER_DEVELOPER_PERSONAS.items():
            total = sum(weights.values())
            assert math.isclose(total, 1.0, rel_tol=1e-6), (
                f"Persona '{persona}' weights sum to {total}, not 1.0"
            )

    def test_persona_weights_all_positive(self):
        """All persona weights should be positive values."""
        for persona, weights in POWER_DEVELOPER_PERSONAS.items():
            for component, weight in weights.items():
                assert weight > 0, f"Weight for {persona}.{component} is not positive"

    def test_all_personas_defined(self):
        """All power developer personas should be defined."""
        expected_personas = ["greenfield", "repower", "stranded"]
        for persona in expected_personas:
            assert persona in POWER_DEVELOPER_PERSONAS

    def test_persona_has_required_components(self):
        """All personas should have the same component keys."""
        expected_components = {
            "capacity",
            "connection_speed",
            "resilience",
            "land_planning",
            "latency",
            "cooling",
            "price_sensitivity",
        }
        for persona, weights in POWER_DEVELOPER_PERSONAS.items():
            assert set(weights.keys()) == expected_components, (
                f"Persona '{persona}' missing components"
            )

    def test_capacity_ranges_valid(self):
        """Capacity ranges should be valid (min <= max)."""
        for persona, ranges in POWER_DEVELOPER_CAPACITY_RANGES.items():
            assert ranges["min"] <= ranges["max"], (
                f"Persona '{persona}' has invalid capacity range"
            )

    def test_capacity_ranges_allow_wide_range(self):
        """Power developer personas should allow wide capacity ranges."""
        for persona, ranges in POWER_DEVELOPER_CAPACITY_RANGES.items():
            # All power developer personas should allow 1 MW to 1000 MW
            assert ranges["min"] == 1
            assert ranges["max"] == 1000


# ============================================================================
# Test Persona Resolution
# ============================================================================


class TestResolvePersona:
    """Test resolve_power_developer_persona function."""

    def test_resolve_persona_defaults_to_greenfield_when_missing(self):
        """None should default to 'greenfield' with 'defaulted' status."""
        persona, requested, status = resolve_power_developer_persona(None)
        assert persona == "greenfield"
        assert requested == ""
        assert status == "defaulted"

    def test_resolve_persona_defaults_to_greenfield_when_empty(self):
        """Empty string should default to 'greenfield' with 'defaulted' status."""
        persona, requested, status = resolve_power_developer_persona("")
        assert persona == "greenfield"
        assert requested == ""
        assert status == "defaulted"

    def test_resolve_persona_defaults_to_greenfield_when_whitespace(self):
        """Whitespace should default to 'greenfield' with 'defaulted' status."""
        persona, requested, status = resolve_power_developer_persona("   ")
        assert persona == "greenfield"
        assert requested == ""
        assert status == "defaulted"

    def test_resolve_persona_honors_greenfield(self):
        """'greenfield' should resolve to 'greenfield' with 'valid' status."""
        persona, requested, status = resolve_power_developer_persona("greenfield")
        assert persona == "greenfield"
        assert requested == "greenfield"
        assert status == "valid"

    def test_resolve_persona_honors_repower(self):
        """'repower' should resolve to 'repower' with 'valid' status."""
        persona, requested, status = resolve_power_developer_persona("repower")
        assert persona == "repower"
        assert requested == "repower"
        assert status == "valid"

    def test_resolve_persona_honors_stranded(self):
        """'stranded' should resolve to 'stranded' with 'valid' status."""
        persona, requested, status = resolve_power_developer_persona("stranded")
        assert persona == "stranded"
        assert requested == "stranded"
        assert status == "valid"

    def test_resolve_persona_honors_stranded_case_insensitive(self):
        """Resolution should be case-insensitive."""
        persona, requested, status = resolve_power_developer_persona("Stranded")
        assert persona == "stranded"
        assert requested == "Stranded"  # Original casing preserved
        assert status == "valid"

    def test_resolve_persona_honors_repower_uppercase(self):
        """Uppercase 'REPOWER' should resolve correctly."""
        persona, requested, status = resolve_power_developer_persona("REPOWER")
        assert persona == "repower"
        assert requested == "REPOWER"
        assert status == "valid"

    def test_resolve_persona_honors_greenfield_mixed_case(self):
        """Mixed case 'GreenField' should resolve correctly."""
        persona, requested, status = resolve_power_developer_persona("GreenField")
        assert persona == "greenfield"
        assert requested == "GreenField"
        assert status == "valid"

    def test_resolve_persona_rejects_invalid_value(self):
        """Unknown persona should fallback to 'greenfield' with 'invalid' status."""
        persona, requested, status = resolve_power_developer_persona("unknown")
        assert persona == "greenfield"
        assert requested == "unknown"
        assert status == "invalid"

    def test_resolve_persona_rejects_typo(self):
        """Typo should be rejected as invalid."""
        persona, requested, status = resolve_power_developer_persona("greenfild")
        assert persona == "greenfield"
        assert requested == "greenfild"
        assert status == "invalid"

    def test_resolve_persona_rejects_dc_personas(self):
        """Data centre personas should be rejected as invalid."""
        for dc_persona in ["hyperscaler", "colocation", "edge_computing"]:
            persona, requested, status = resolve_power_developer_persona(dc_persona)
            assert persona == "greenfield"
            assert status == "invalid"

    def test_defined_personas_match_weights(self):
        """All defined personas should have weights."""
        for persona_name in ("greenfield", "repower", "stranded"):
            persona, _, status = resolve_power_developer_persona(persona_name)
            assert status == "valid"
            assert persona in POWER_DEVELOPER_PERSONAS


# ============================================================================
# Test Coordinate Extraction
# ============================================================================


class TestExtractCoordinates:
    """Test extract_coordinates function."""

    def test_extract_standard_keys(self):
        """Should extract lat/lon from standard keys."""
        row = {"latitude": 51.5, "longitude": -0.1}
        lat, lon = extract_coordinates(row)
        assert lat == 51.5
        assert lon == -0.1

    def test_extract_short_keys(self):
        """Should extract from short keys (lat, lon)."""
        row = {"lat": 52.0, "lon": -1.0}
        lat, lon = extract_coordinates(row)
        assert lat == 52.0
        assert lon == -1.0

    def test_extract_lng_key(self):
        """Should extract from 'lng' key."""
        row = {"lat": 53.0, "lng": -2.0}
        lat, lon = extract_coordinates(row)
        assert lat == 53.0
        assert lon == -2.0

    def test_extract_capitalized_keys(self):
        """Should extract from capitalized keys."""
        row = {"Latitude": 54.0, "Longitude": -3.0}
        lat, lon = extract_coordinates(row)
        assert lat == 54.0
        assert lon == -3.0

    def test_extract_degree_suffix_keys(self):
        """Should extract from keys with _deg suffix."""
        row = {"Latitude_deg": 55.0, "Longitude_deg": -4.0}
        lat, lon = extract_coordinates(row)
        assert lat == 55.0
        assert lon == -4.0

    def test_extract_from_location_dict(self):
        """Should extract from nested location object."""
        row = {"location": {"lat": 56.0, "lon": -5.0}}
        lat, lon = extract_coordinates(row)
        assert lat == 56.0
        assert lon == -5.0

    def test_extract_from_location_dict_lng(self):
        """Should extract from location object with lng key."""
        row = {"location": {"lat": 57.0, "lng": -6.0}}
        lat, lon = extract_coordinates(row)
        assert lat == 57.0
        assert lon == -6.0

    def test_extract_from_location_dict_longitude(self):
        """Should extract from location object with full keys."""
        row = {"location": {"latitude": 58.0, "longitude": -7.0}}
        lat, lon = extract_coordinates(row)
        assert lat == 58.0
        assert lon == -7.0

    def test_extract_from_coordinates_array(self):
        """Should extract from GeoJSON-style coordinates array [lon, lat]."""
        row = {"coordinates": [-8.0, 59.0]}  # [lon, lat]
        lat, lon = extract_coordinates(row)
        assert lat == 59.0
        assert lon == -8.0

    def test_priority_top_level_over_location(self):
        """Top-level keys should take priority over location object."""
        row = {
            "latitude": 51.0,
            "longitude": 0.0,
            "location": {"lat": 99.0, "lon": 99.0}
        }
        lat, lon = extract_coordinates(row)
        assert lat == 51.0
        assert lon == 0.0

    def test_missing_latitude_returns_none(self):
        """Missing latitude should return None."""
        row = {"longitude": -0.1}
        lat, lon = extract_coordinates(row)
        assert lat is None
        assert lon == -0.1

    def test_missing_longitude_returns_none(self):
        """Missing longitude should return None."""
        row = {"latitude": 51.5}
        lat, lon = extract_coordinates(row)
        assert lat == 51.5
        assert lon is None

    def test_empty_row_returns_none(self):
        """Empty row should return None for both."""
        lat, lon = extract_coordinates({})
        assert lat is None
        assert lon is None

    def test_string_coordinates_converted(self):
        """String coordinates should be converted to float."""
        row = {"latitude": "51.5", "longitude": "-0.1"}
        lat, lon = extract_coordinates(row)
        assert lat == 51.5
        assert lon == -0.1

    def test_invalid_string_returns_none(self):
        """Invalid string coordinates should return None."""
        row = {"latitude": "not_a_number", "longitude": "-0.1"}
        lat, lon = extract_coordinates(row)
        assert lat is None
        assert lon == -0.1

    def test_none_values_handled(self):
        """None values should be handled."""
        row = {"latitude": None, "longitude": None}
        lat, lon = extract_coordinates(row)
        assert lat is None
        assert lon is None

    def test_fallback_chain(self):
        """Should follow fallback chain correctly."""
        # Only location object has valid coords
        row = {
            "latitude": None,
            "location": {"lat": 50.0, "lon": 1.0}
        }
        lat, lon = extract_coordinates(row)
        assert lat == 50.0
        assert lon == 1.0


# ============================================================================
# Test TEC Transformation
# ============================================================================


class TestTransformTecToProjectSchema:
    """Test transform_tec_to_project_schema function."""

    def test_basic_transformation(self):
        """Should transform basic TEC row correctly."""
        tec_row = {
            "id": 123,
            "project_name": "Wind Farm Alpha",
            "capacity_mw": 50.0,
            "technology_type": "Wind",
            "development_status": "Under Construction",
            "latitude": 52.5,
            "longitude": -1.5,
            "operator": "Wind Developer Ltd"
        }

        result = transform_tec_to_project_schema(tec_row)

        assert result["id"] == 123
        assert result["ref_id"] == "123"
        assert result["site_name"] == "Wind Farm Alpha"
        assert result["project_name"] == "Wind Farm Alpha"
        assert result["capacity_mw"] == 50.0
        assert result["technology_type"] == "Wind"
        assert result["development_status_short"] == "Under Construction"
        assert result["latitude"] == 52.5
        assert result["longitude"] == -1.5
        assert result["operator"] == "Wind Developer Ltd"
        assert result["_source_table"] == "tec_connections"

    def test_missing_project_name(self):
        """Missing project name should use default."""
        tec_row = {
            "id": 456,
            "latitude": 53.0,
            "longitude": -2.0
        }

        result = transform_tec_to_project_schema(tec_row)

        assert result["site_name"] == "Untitled Project"
        assert result["project_name"] is None

    def test_missing_capacity_defaults_to_zero(self):
        """Missing capacity should default to 0."""
        tec_row = {
            "id": 789,
            "project_name": "Test",
            "latitude": 54.0,
            "longitude": -3.0
        }

        result = transform_tec_to_project_schema(tec_row)

        assert result["capacity_mw"] == 0.0

    def test_invalid_capacity_defaults_to_zero(self):
        """Invalid capacity should default to 0."""
        tec_row = {
            "id": 101,
            "capacity_mw": "invalid",
            "latitude": 55.0,
            "longitude": -4.0
        }

        result = transform_tec_to_project_schema(tec_row)

        assert result["capacity_mw"] == 0.0

    def test_string_capacity_converted(self):
        """String capacity should be converted to float."""
        tec_row = {
            "id": 102,
            "capacity_mw": "75.5",
            "latitude": 56.0,
            "longitude": -5.0
        }

        result = transform_tec_to_project_schema(tec_row)

        assert result["capacity_mw"] == 75.5

    def test_missing_technology_defaults_to_unknown(self):
        """Missing technology should default to 'Unknown'."""
        tec_row = {
            "id": 103,
            "latitude": 57.0,
            "longitude": -6.0
        }

        result = transform_tec_to_project_schema(tec_row)

        assert result["technology_type"] == "Unknown"

    def test_missing_status_defaults_to_scoping(self):
        """Missing status should default to 'Scoping'."""
        tec_row = {
            "id": 104,
            "latitude": 58.0,
            "longitude": -7.0
        }

        result = transform_tec_to_project_schema(tec_row)

        assert result["development_status_short"] == "Scoping"

    def test_connection_fields_preserved(self):
        """TEC-specific connection fields should be preserved."""
        tec_row = {
            "id": 105,
            "connection_site": "Substation X",
            "substation_name": "Grid Point Y",
            "voltage": 400,
            "constraint_status": "Constrained",
            "latitude": 51.0,
            "longitude": 0.0
        }

        result = transform_tec_to_project_schema(tec_row)

        assert result["connection_site"] == "Substation X"
        assert result["substation_name"] == "Grid Point Y"
        assert result["voltage_kv"] == 400.0
        assert result["constraint_status"] == "Constrained"

    def test_country_defaults_to_uk(self):
        """Country should default to 'UK'."""
        tec_row = {"id": 106, "latitude": 52.0, "longitude": -1.0}
        result = transform_tec_to_project_schema(tec_row)
        assert result["country"] == "UK"

    def test_county_is_none(self):
        """County should be None (not in TEC data)."""
        tec_row = {"id": 107, "latitude": 53.0, "longitude": -2.0}
        result = transform_tec_to_project_schema(tec_row)
        assert result["county"] is None

    def test_customer_name_fallback_for_operator(self):
        """Should use customer_name as fallback for operator."""
        tec_row = {
            "id": 108,
            "customer_name": "Energy Corp",
            "latitude": 54.0,
            "longitude": -3.0
        }

        result = transform_tec_to_project_schema(tec_row)

        assert result["operator"] == "Energy Corp"


# ============================================================================
# Test Power Developer Analysis Workflow
# ============================================================================


class TestRunPowerDeveloperAnalysis:
    """Test run_power_developer_analysis async function."""

    @pytest.mark.asyncio
    async def test_basic_analysis_returns_feature_collection(self):
        """Should return GeoJSON FeatureCollection."""
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
            ]

        async def fake_proximity_batch(projects):
            return [
                {
                    "substation_score": 50.0,
                    "transmission_score": 50.0,
                    "fiber_score": 50.0,
                    "ixp_score": 50.0,
                    "water_score": 50.0,
                    "nearest_distances": {},
                }
                for _ in projects
            ]

        result = await run_power_developer_analysis(
            criteria={},
            site_location=None,
            target_persona="greenfield",
            limit=1,
            source_table="renewable_projects",
            query_supabase=fake_query_supabase,
            calculate_proximity_scores_batch=fake_proximity_batch,
        )

        assert result["type"] == "FeatureCollection"
        assert "features" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_returns_scored_features(self):
        """Features should have investment_rating and component_scores."""
        async def fake_query_supabase(_query: str, limit: int = 1):
            return [
                {
                    "ref_id": "proj-1",
                    "site_name": "Scored Project",
                    "capacity_mw": 50,
                    "technology_type": "wind",
                    "development_status_short": "consented",
                    "latitude": 52.0,
                    "longitude": -1.0,
                }
            ]

        async def fake_proximity_batch(projects):
            return [
                {
                    "substation_score": 80.0,
                    "transmission_score": 75.0,
                    "fiber_score": 70.0,
                    "ixp_score": 65.0,
                    "water_score": 60.0,
                    "nearest_distances": {
                        "substation_km": 10.0,
                        "transmission_km": 15.0,
                    },
                }
                for _ in projects
            ]

        result = await run_power_developer_analysis(
            criteria={},
            site_location=None,
            target_persona="greenfield",
            limit=1,
            source_table="renewable_projects",
            query_supabase=fake_query_supabase,
            calculate_proximity_scores_batch=fake_proximity_batch,
        )

        assert len(result["features"]) == 1
        props = result["features"][0]["properties"]

        assert "investment_rating" in props
        assert "rating_description" in props
        assert "color_code" in props
        assert "component_scores" in props
        assert "weighted_contributions" in props

    @pytest.mark.asyncio
    async def test_capacity_preference_changes_power_dev_scores(self):
        """User ideal capacity should affect scoring."""
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
    async def test_power_dev_scoring_uses_persona_pipeline(self):
        """Workflow should use the persona scoring pipeline correctly."""
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

    @pytest.mark.asyncio
    async def test_empty_database_returns_empty_features(self):
        """Empty database should return empty features list."""
        async def fake_query_supabase(_query: str, limit: int = 1):
            return []

        async def fake_proximity_batch(projects):
            return []

        result = await run_power_developer_analysis(
            criteria={},
            site_location=None,
            target_persona="greenfield",
            limit=100,
            source_table="renewable_projects",
            query_supabase=fake_query_supabase,
            calculate_proximity_scores_batch=fake_proximity_batch,
        )

        assert result["features"] == []
        assert "error" in result["metadata"]

    @pytest.mark.asyncio
    async def test_projects_without_coordinates_filtered(self):
        """Projects without valid coordinates should be filtered out."""
        async def fake_query_supabase(_query: str, limit: int = 1):
            return [
                {"ref_id": "1", "site_name": "Valid", "latitude": 51.0, "longitude": -0.1},
                {"ref_id": "2", "site_name": "No Lat"},  # Missing latitude
                {"ref_id": "3", "site_name": "No Lon", "latitude": 52.0},  # Missing longitude
                {"ref_id": "4", "site_name": "Both Valid", "latitude": 53.0, "longitude": -1.0},
            ]

        async def fake_proximity_batch(projects):
            return [
                {
                    "substation_score": 50.0,
                    "transmission_score": 50.0,
                    "fiber_score": 50.0,
                    "ixp_score": 50.0,
                    "water_score": 50.0,
                    "nearest_distances": {},
                }
                for _ in projects
            ]

        result = await run_power_developer_analysis(
            criteria={},
            site_location=None,
            target_persona="greenfield",
            limit=100,
            source_table="renewable_projects",
            query_supabase=fake_query_supabase,
            calculate_proximity_scores_batch=fake_proximity_batch,
        )

        # Only 2 projects should pass coordinate validation
        assert len(result["features"]) == 2
        assert result["metadata"]["total_projects_processed"] == 4
        assert result["metadata"]["projects_with_valid_coords"] == 2

    @pytest.mark.asyncio
    async def test_results_sorted_by_investment_rating(self):
        """Results should be sorted by investment_rating descending."""
        async def fake_query_supabase(_query: str, limit: int = 1):
            return [
                {"ref_id": "low", "capacity_mw": 1, "latitude": 51.0, "longitude": -0.1, "development_status_short": "abandoned"},
                {"ref_id": "high", "capacity_mw": 50, "latitude": 52.0, "longitude": -1.0, "development_status_short": "consented"},
                {"ref_id": "mid", "capacity_mw": 25, "latitude": 53.0, "longitude": -2.0, "development_status_short": "in planning"},
            ]

        async def fake_proximity_batch(projects):
            return [
                {
                    "substation_score": 80.0,
                    "transmission_score": 75.0,
                    "fiber_score": 70.0,
                    "ixp_score": 65.0,
                    "water_score": 60.0,
                    "nearest_distances": {},
                }
                for _ in projects
            ]

        result = await run_power_developer_analysis(
            criteria={},
            site_location=None,
            target_persona="greenfield",
            limit=100,
            source_table="renewable_projects",
            query_supabase=fake_query_supabase,
            calculate_proximity_scores_batch=fake_proximity_batch,
        )

        ratings = [f["properties"]["investment_rating"] for f in result["features"]]
        assert ratings == sorted(ratings, reverse=True)

    @pytest.mark.asyncio
    async def test_persona_recorded_in_metadata(self):
        """Selected persona should be recorded in metadata."""
        async def fake_query_supabase(_query: str, limit: int = 1):
            return [{"ref_id": "1", "latitude": 51.0, "longitude": -0.1}]

        async def fake_proximity_batch(projects):
            return [{"substation_score": 50.0, "nearest_distances": {}}]

        for persona in ["greenfield", "repower", "stranded"]:
            result = await run_power_developer_analysis(
                criteria={},
                site_location=None,
                target_persona=persona,
                limit=1,
                source_table="renewable_projects",
                query_supabase=fake_query_supabase,
                calculate_proximity_scores_batch=fake_proximity_batch,
            )

            assert result["metadata"]["project_type"] == persona
            assert result["metadata"]["project_type_resolution"] == "valid"

    @pytest.mark.asyncio
    async def test_invalid_persona_uses_greenfield(self):
        """Invalid persona should fallback to greenfield."""
        async def fake_query_supabase(_query: str, limit: int = 1):
            return [{"ref_id": "1", "latitude": 51.0, "longitude": -0.1}]

        async def fake_proximity_batch(projects):
            return [{"substation_score": 50.0, "nearest_distances": {}}]

        result = await run_power_developer_analysis(
            criteria={},
            site_location=None,
            target_persona="invalid_persona",
            limit=1,
            source_table="renewable_projects",
            query_supabase=fake_query_supabase,
            calculate_proximity_scores_batch=fake_proximity_batch,
        )

        assert result["metadata"]["project_type"] == "greenfield"
        assert result["metadata"]["project_type_resolution"] == "invalid"
        assert result["metadata"]["requested_project_type"] == "invalid_persona"

    @pytest.mark.asyncio
    async def test_tec_connections_source_transforms_data(self):
        """TEC connections source should transform data."""
        async def fake_query_supabase(_query: str, limit: int = 1):
            # TEC-style data
            return [
                {
                    "id": 999,
                    "project_name": "TEC Wind Farm",
                    "capacity_mw": 100,
                    "technology_type": "Wind",
                    "development_status": "Scoping",
                    "latitude": 54.0,
                    "longitude": -3.0,
                    "customer_name": "Wind Corp"
                }
            ]

        async def fake_proximity_batch(projects):
            return [{"substation_score": 50.0, "nearest_distances": {}}]

        result = await run_power_developer_analysis(
            criteria={},
            site_location=None,
            target_persona="greenfield",
            limit=1,
            source_table="tec_connections",
            query_supabase=fake_query_supabase,
            calculate_proximity_scores_batch=fake_proximity_batch,
        )

        assert len(result["features"]) == 1
        props = result["features"][0]["properties"]
        assert props["site_name"] == "TEC Wind Farm"

    @pytest.mark.asyncio
    async def test_metadata_contains_processing_time(self):
        """Metadata should contain processing time."""
        async def fake_query_supabase(_query: str, limit: int = 1):
            return [{"ref_id": "1", "latitude": 51.0, "longitude": -0.1}]

        async def fake_proximity_batch(projects):
            return [{"substation_score": 50.0, "nearest_distances": {}}]

        result = await run_power_developer_analysis(
            criteria={},
            site_location=None,
            target_persona="greenfield",
            limit=1,
            source_table="renewable_projects",
            query_supabase=fake_query_supabase,
            calculate_proximity_scores_batch=fake_proximity_batch,
        )

        assert "processing_time_seconds" in result["metadata"]
        assert result["metadata"]["processing_time_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_custom_weights_from_criteria(self):
        """Custom weights from criteria should be applied."""
        async def fake_query_supabase(_query: str, limit: int = 1):
            return [
                {
                    "ref_id": "1",
                    "capacity_mw": 50,
                    "latitude": 51.0,
                    "longitude": -0.1,
                    "development_status_short": "consented"
                }
            ]

        async def fake_proximity_batch(projects):
            return [{"substation_score": 80.0, "nearest_distances": {}}]

        # Custom weights emphasizing connection_speed
        criteria = {
            "connection_headroom": 0.8,  # Maps to connection_speed
            "route_to_market": 0.2,       # Maps to price_sensitivity
        }

        result = await run_power_developer_analysis(
            criteria=criteria,
            site_location=None,
            target_persona="greenfield",
            limit=1,
            source_table="renewable_projects",
            query_supabase=fake_query_supabase,
            calculate_proximity_scores_batch=fake_proximity_batch,
        )

        # Weights should be in metadata
        weights = result["metadata"]["project_type_weights"]
        assert "connection_speed" in weights or "connection_headroom" in weights


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling in power workflow."""

    @pytest.mark.asyncio
    async def test_database_error_raises_http_exception(self):
        """Database errors should raise HTTPException."""
        from fastapi import HTTPException

        async def failing_query(_query: str, limit: int = 1):
            raise Exception("Database connection failed")

        async def fake_proximity_batch(projects):
            return []

        with pytest.raises(HTTPException) as exc_info:
            await run_power_developer_analysis(
                criteria={},
                site_location=None,
                target_persona="greenfield",
                limit=1,
                source_table="renewable_projects",
                query_supabase=failing_query,
                calculate_proximity_scores_batch=fake_proximity_batch,
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_proximity_error_propagates(self):
        """Proximity calculation errors should propagate."""
        async def fake_query_supabase(_query: str, limit: int = 1):
            return [{"ref_id": "1", "latitude": 51.0, "longitude": -0.1}]

        async def failing_proximity(projects):
            raise Exception("Proximity calculation failed")

        with pytest.raises(Exception) as exc_info:
            await run_power_developer_analysis(
                criteria={},
                site_location=None,
                target_persona="greenfield",
                limit=1,
                source_table="renewable_projects",
                query_supabase=fake_query_supabase,
                calculate_proximity_scores_batch=failing_proximity,
            )

        assert "Proximity" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_scoring_error_continues_other_projects(self):
        """Scoring errors should skip project but continue others."""
        call_count = [0]

        async def fake_query_supabase(_query: str, limit: int = 1):
            return [
                {"ref_id": "1", "latitude": 51.0, "longitude": -0.1, "capacity_mw": 50},
                {"ref_id": "2", "latitude": 52.0, "longitude": -1.0, "capacity_mw": 50},
            ]

        async def fake_proximity_batch(projects):
            call_count[0] += 1
            # Return valid scores
            return [
                {"substation_score": 50.0, "nearest_distances": {}}
                for _ in projects
            ]

        result = await run_power_developer_analysis(
            criteria={},
            site_location=None,
            target_persona="greenfield",
            limit=10,
            source_table="renewable_projects",
            query_supabase=fake_query_supabase,
            calculate_proximity_scores_batch=fake_proximity_batch,
        )

        # Should have processed projects
        assert len(result["features"]) >= 1
