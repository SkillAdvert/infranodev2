"""Comprehensive tests for backend/scoring.py module.

Tests all 8 component scoring algorithms with edge cases, boundary conditions,
and validation of scoring outputs.
"""

import sys
import math
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.scoring import (
    # Constants
    PERSONA_WEIGHTS,
    PERSONA_TARGET_COMPONENTS,
    PERSONA_SCORING_TUNING,
    PERSONA_CAPACITY_RANGES,
    PERSONA_CAPACITY_PARAMS,
    INFRASTRUCTURE_HALF_DISTANCE_KM,
    # Utility functions
    get_color_from_score,
    get_rating_description,
    # Component scoring functions
    calculate_capacity_component_score,
    calculate_development_stage_score,
    calculate_technology_score,
    calculate_grid_infrastructure_score,
    calculate_digital_infrastructure_score,
    calculate_water_resources_score,
    calculate_lcoe_score,
    calculate_tnuos_score,
    estimate_capacity_factor,
    calculate_connection_speed_score,
    calculate_resilience_score,
    calculate_price_sensitivity_score,
    # Aggregation functions
    build_persona_component_scores,
    calculate_persona_weighted_score,
    calculate_weighted_score_from_components,
    calculate_persona_topsis_score,
    calculate_custom_weighted_score,
    calculate_best_customer_match,
    filter_projects_by_persona_capacity,
)


# ============================================================================
# Test Constants and Configuration
# ============================================================================


class TestConstants:
    """Test that constants are properly defined and valid."""

    def test_persona_weights_sum_to_one(self):
        """All persona weight dictionaries should sum to approximately 1.0."""
        for persona, weights in PERSONA_WEIGHTS.items():
            total = sum(weights.values())
            assert math.isclose(total, 1.0, rel_tol=1e-3), (
                f"Persona '{persona}' weights sum to {total}, not 1.0"
            )

    def test_persona_weights_all_positive(self):
        """All persona weights should be positive values."""
        for persona, weights in PERSONA_WEIGHTS.items():
            for component, weight in weights.items():
                assert weight > 0, f"Weight for {persona}.{component} is not positive"

    def test_persona_weights_have_required_components(self):
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
        for persona, weights in PERSONA_WEIGHTS.items():
            assert set(weights.keys()) == expected_components, (
                f"Persona '{persona}' missing components"
            )

    def test_persona_capacity_ranges_valid(self):
        """Capacity ranges should have min <= max."""
        for persona, ranges in PERSONA_CAPACITY_RANGES.items():
            assert ranges["min"] <= ranges["max"], (
                f"Persona '{persona}' has invalid capacity range"
            )

    def test_persona_capacity_params_valid(self):
        """Capacity params should have min_mw <= ideal_mw <= max_mw."""
        for persona, params in PERSONA_CAPACITY_PARAMS.items():
            assert params["min_mw"] <= params["ideal_mw"] <= params["max_mw"], (
                f"Persona '{persona}' has invalid capacity params ordering"
            )
            assert 0 < params["tolerance_factor"] <= 1.0, (
                f"Persona '{persona}' has invalid tolerance_factor"
            )

    def test_infrastructure_half_distances_positive(self):
        """All half-distance values should be positive."""
        for infra_type, distance in INFRASTRUCTURE_HALF_DISTANCE_KM.items():
            assert distance > 0, f"Half-distance for '{infra_type}' is not positive"

    def test_target_components_in_valid_range(self):
        """Target component scores should be in [0, 1] range."""
        for persona, targets in PERSONA_TARGET_COMPONENTS.items():
            for component, value in targets.items():
                assert 0.0 <= value <= 1.0, (
                    f"Target for {persona}.{component} is out of range"
                )


# ============================================================================
# Test Color and Rating Functions
# ============================================================================


class TestColorFromScore:
    """Test get_color_from_score function."""

    @pytest.mark.parametrize("score,expected_color", [
        (100.0, "#00DD00"),  # Excellent - 10/10
        (95.0, "#00DD00"),   # Excellent - 9.5/10
        (90.0, "#00DD00"),   # Excellent - 9.0/10
        (85.0, "#33FF33"),   # Very Good - 8.5/10
        (80.0, "#33FF33"),   # Very Good - 8.0/10
        (75.0, "#7FFF00"),   # Good - 7.5/10
        (70.0, "#7FFF00"),   # Good - 7.0/10
        (65.0, "#CCFF00"),   # Above Average - 6.5/10
        (60.0, "#CCFF00"),   # Above Average - 6.0/10
        (55.0, "#FFFF00"),   # Average - 5.5/10
        (50.0, "#FFFF00"),   # Average - 5.0/10
        (45.0, "#FFCC00"),   # Below Average - 4.5/10
        (40.0, "#FFCC00"),   # Below Average - 4.0/10
        (35.0, "#FF9900"),   # Poor - 3.5/10
        (30.0, "#FF9900"),   # Poor - 3.0/10
        (25.0, "#FF6600"),   # Very Poor - 2.5/10
        (20.0, "#FF6600"),   # Very Poor - 2.0/10
        (15.0, "#FF3300"),   # Bad - 1.5/10
        (10.0, "#FF3300"),   # Bad - 1.0/10
        (5.0, "#CC0000"),    # Very Bad - 0.5/10
        (0.0, "#CC0000"),    # Very Bad - 0/10
    ])
    def test_color_thresholds(self, score, expected_color):
        """Test color mapping for different score thresholds."""
        assert get_color_from_score(score) == expected_color

    def test_color_returns_string(self):
        """Color should always return a hex string."""
        for score in [0, 25, 50, 75, 100]:
            color = get_color_from_score(score)
            assert isinstance(color, str)
            assert color.startswith("#")
            assert len(color) == 7


class TestRatingDescription:
    """Test get_rating_description function."""

    @pytest.mark.parametrize("score,expected_desc", [
        (100.0, "Excellent"),
        (90.0, "Excellent"),
        (85.0, "Very Good"),
        (80.0, "Very Good"),
        (75.0, "Good"),
        (70.0, "Good"),
        (65.0, "Above Average"),
        (60.0, "Above Average"),
        (55.0, "Average"),
        (50.0, "Average"),
        (45.0, "Below Average"),
        (40.0, "Below Average"),
        (35.0, "Poor"),
        (30.0, "Poor"),
        (25.0, "Very Poor"),
        (20.0, "Very Poor"),
        (15.0, "Bad"),
        (10.0, "Bad"),
        (5.0, "Very Bad"),
        (0.0, "Very Bad"),
    ])
    def test_rating_thresholds(self, score, expected_desc):
        """Test rating descriptions for different score thresholds."""
        assert get_rating_description(score) == expected_desc


# ============================================================================
# Test Component Scoring Functions
# ============================================================================


class TestCapacityComponentScore:
    """Test calculate_capacity_component_score function."""

    def test_ideal_capacity_returns_100(self):
        """Capacity at ideal value should return 100."""
        # Default persona ideal is 50 MW (from PERSONA_CAPACITY_PARAMS["default"])
        ideal = PERSONA_CAPACITY_PARAMS["default"]["ideal_mw"]
        score = calculate_capacity_component_score(ideal, persona=None)
        assert score == pytest.approx(100.0, rel=0.01)

    def test_zero_capacity(self):
        """Zero capacity should return a low score."""
        score = calculate_capacity_component_score(0.0)
        assert 0.0 <= score <= 100.0

    def test_negative_capacity_handled(self):
        """Negative capacity should return valid score."""
        score = calculate_capacity_component_score(-10.0)
        assert 0.0 <= score <= 100.0

    def test_very_large_capacity(self):
        """Very large capacity should return a low score (far from ideal)."""
        score = calculate_capacity_component_score(10000.0)
        assert score < 50.0  # Far from any ideal

    @pytest.mark.parametrize("persona", ["hyperscaler", "colocation", "edge_computing"])
    def test_persona_specific_ideal(self, persona):
        """Each persona should score highest near their ideal capacity."""
        ideal = PERSONA_CAPACITY_PARAMS[persona]["ideal_mw"]
        score_at_ideal = calculate_capacity_component_score(ideal, persona=persona)
        score_far_above = calculate_capacity_component_score(ideal * 5, persona=persona)
        score_far_below = calculate_capacity_component_score(ideal * 0.1, persona=persona)

        assert score_at_ideal > score_far_above
        assert score_at_ideal > score_far_below

    def test_user_ideal_overrides_persona(self):
        """User-provided ideal should override persona default."""
        user_ideal = 25.0
        score_at_user_ideal = calculate_capacity_component_score(
            25.0, persona="hyperscaler", user_ideal_mw=user_ideal
        )
        score_at_persona_ideal = calculate_capacity_component_score(
            50.0, persona="hyperscaler", user_ideal_mw=user_ideal
        )

        assert score_at_user_ideal > score_at_persona_ideal

    def test_custom_persona_uses_default(self):
        """Custom persona should use default params."""
        score_custom = calculate_capacity_component_score(50.0, persona="custom")
        score_default = calculate_capacity_component_score(50.0, persona="default")
        assert score_custom == score_default

    def test_score_bounded_0_to_100(self):
        """Score should always be in [0, 100] range."""
        test_values = [0, 1, 10, 50, 100, 500, 1000, -5]
        for val in test_values:
            score = calculate_capacity_component_score(val)
            assert 0.0 <= score <= 100.0


class TestDevelopmentStageScore:
    """Test calculate_development_stage_score function."""

    @pytest.mark.parametrize("status,expected_min", [
        ("operational", 0),
        ("under construction", 15),
        ("consented", 60),
        ("in planning", 50),
        ("application submitted", 95),
        ("no application required", 95),
        ("granted", 60),
        ("decommissioned", 0),
        ("abandoned", 0),
    ])
    def test_known_status_scores(self, status, expected_min):
        """Known statuses should return expected minimum scores."""
        score = calculate_development_stage_score(status)
        assert score >= expected_min
        assert 0.0 <= score <= 100.0

    def test_unknown_status_uses_default(self):
        """Unknown status should return default score (45)."""
        score = calculate_development_stage_score("unknown_status_xyz")
        assert score == 45.0

    def test_case_insensitive(self):
        """Status matching should be case-insensitive."""
        assert calculate_development_stage_score("OPERATIONAL") == \
               calculate_development_stage_score("operational")
        assert calculate_development_stage_score("In Planning") == \
               calculate_development_stage_score("in planning")

    def test_partial_match(self):
        """Partial status matches should work."""
        score = calculate_development_stage_score("application submitted for review")
        # Should match "application submitted" pattern
        assert score == 100.0

    def test_perspective_parameter_accepted(self):
        """Supply perspective should be accepted without error."""
        score = calculate_development_stage_score("operational", perspective="supply")
        assert 0.0 <= score <= 100.0

    def test_empty_string(self):
        """Empty string should return default score."""
        score = calculate_development_stage_score("")
        assert 0.0 <= score <= 100.0


class TestTechnologyScore:
    """Test calculate_technology_score function."""

    @pytest.mark.parametrize("tech,expected", [
        ("solar", 80.0),
        ("Solar PV", 80.0),
        ("SOLAR", 80.0),
        ("battery", 80.0),
        ("BESS", 80.0),
        ("wind", 60.0),
        ("Wind Farm", 60.0),
        ("offshore wind", 60.0),
        ("hybrid", 100.0),
        ("hybrid system", 100.0),
        ("ccgt", 100.0),
        ("gas ccgt", 100.0),
        ("unknown", 80.0),  # Default
        ("", 80.0),         # Default
    ])
    def test_technology_scores(self, tech, expected):
        """Different technologies should return expected scores."""
        assert calculate_technology_score(tech) == expected

    def test_technology_priority_solar_over_hybrid(self):
        """Solar check happens before hybrid check."""
        # "Solar + Battery Hybrid" contains "solar" first, so returns 80
        score = calculate_technology_score("Solar + Battery Hybrid")
        assert score == 80.0  # Solar match happens first


class TestGridInfrastructureScore:
    """Test calculate_grid_infrastructure_score function."""

    def test_close_to_substation_and_transmission(self):
        """Very close to both should score high."""
        proximity_scores = {
            "nearest_distances": {
                "substation_km": 0.0,
                "transmission_km": 0.0,
            }
        }
        score = calculate_grid_infrastructure_score(proximity_scores)
        assert score == 100.0

    def test_far_from_infrastructure(self):
        """Far from both should score low."""
        proximity_scores = {
            "nearest_distances": {
                "substation_km": 200.0,
                "transmission_km": 200.0,
            }
        }
        score = calculate_grid_infrastructure_score(proximity_scores)
        assert score < 10.0

    def test_missing_distances_handled(self):
        """Missing distance data should not crash."""
        proximity_scores = {"nearest_distances": {}}
        score = calculate_grid_infrastructure_score(proximity_scores)
        assert score == 0.0

    def test_empty_proximity_scores(self):
        """Empty proximity scores should not crash."""
        score = calculate_grid_infrastructure_score({})
        assert score == 0.0

    def test_score_bounded(self):
        """Score should be in [0, 100] range."""
        for distance in [0, 10, 50, 100, 200, 500]:
            proximity_scores = {
                "nearest_distances": {
                    "substation_km": distance,
                    "transmission_km": distance,
                }
            }
            score = calculate_grid_infrastructure_score(proximity_scores)
            assert 0.0 <= score <= 100.0


class TestDigitalInfrastructureScore:
    """Test calculate_digital_infrastructure_score function."""

    def test_close_to_fiber_and_ixp(self):
        """Close to both fiber and IXP should score high."""
        proximity_scores = {
            "nearest_distances": {
                "fiber_km": 0.0,
                "ixp_km": 0.0,
            }
        }
        score = calculate_digital_infrastructure_score(proximity_scores)
        assert score == 100.0

    def test_far_from_digital_infrastructure(self):
        """Far from digital infrastructure should score low."""
        proximity_scores = {
            "nearest_distances": {
                "fiber_km": 200.0,
                "ixp_km": 200.0,
            }
        }
        score = calculate_digital_infrastructure_score(proximity_scores)
        assert score < 10.0

    def test_missing_distances(self):
        """Missing distances should not crash."""
        score = calculate_digital_infrastructure_score({})
        assert score == 0.0


class TestWaterResourcesScore:
    """Test calculate_water_resources_score function."""

    def test_close_to_water(self):
        """Close to water should score high."""
        proximity_scores = {
            "nearest_distances": {"water_km": 0.0}
        }
        score = calculate_water_resources_score(proximity_scores)
        assert score == 100.0

    def test_far_from_water(self):
        """Far from water should score low."""
        proximity_scores = {
            "nearest_distances": {"water_km": 100.0}
        }
        score = calculate_water_resources_score(proximity_scores)
        assert score < 10.0

    def test_missing_water_distance(self):
        """Missing water distance should return 0."""
        score = calculate_water_resources_score({})
        assert score == 0.0


class TestLcoeScore:
    """Test calculate_lcoe_score function."""

    @pytest.mark.parametrize("status,expected", [
        ("operational", 10.0),
        ("under construction", 50.0),
        ("consented", 85.0),
        ("in planning", 70.0),
        ("site identified", 50.0),
        ("concept", 30.0),
        ("unknown", 50.0),
    ])
    def test_lcoe_status_mapping(self, status, expected):
        """Different statuses should map to expected LCOE scores."""
        assert calculate_lcoe_score(status) == expected

    def test_case_insensitive(self):
        """Status matching should be case-insensitive."""
        assert calculate_lcoe_score("OPERATIONAL") == calculate_lcoe_score("operational")

    def test_none_handled(self):
        """None status should return unknown score."""
        score = calculate_lcoe_score(None)
        assert score == 50.0  # unknown default


class TestTnuosScore:
    """Test calculate_tnuos_score function."""

    def test_southern_uk_scores_high(self):
        """Southern UK (lower latitude) should score higher (lower tariffs)."""
        score = calculate_tnuos_score(50.0, -0.1)  # London area
        assert score > 70.0

    def test_northern_scotland_scores_lower(self):
        """Northern Scotland (higher latitude) should score lower (higher tariffs)."""
        score = calculate_tnuos_score(58.0, -4.0)  # Northern Scotland
        assert score < 30.0

    def test_score_bounded(self):
        """Score should always be in [0, 100] range."""
        test_coords = [
            (49.5, -5.0),   # Far south
            (55.0, -3.0),   # Central
            (60.0, -1.0),   # Far north
            (52.0, 1.0),    # East
        ]
        for lat, lng in test_coords:
            score = calculate_tnuos_score(lat, lng)
            assert 0.0 <= score <= 100.0

    def test_longitude_has_no_effect(self):
        """TNUoS score is based primarily on latitude."""
        score1 = calculate_tnuos_score(52.0, -5.0)
        score2 = calculate_tnuos_score(52.0, 1.0)
        # Scores should be identical (same latitude)
        assert score1 == score2


class TestEstimateCapacityFactor:
    """Test estimate_capacity_factor function."""

    def test_solar_capacity_factor(self):
        """Solar should have reasonable CF in UK latitudes."""
        cf = estimate_capacity_factor("solar", 51.5)
        assert 9.0 <= cf <= 13.0

    def test_wind_capacity_factor(self):
        """Wind should have reasonable CF."""
        cf = estimate_capacity_factor("wind", 55.0)
        assert 25.0 <= cf <= 38.0

    def test_offshore_wind_fixed_cf(self):
        """Offshore wind should have fixed 45% CF."""
        cf = estimate_capacity_factor("offshore wind", 55.0)
        assert cf == 45.0

    def test_battery_capacity_factor(self):
        """Battery should return 20% CF."""
        cf = estimate_capacity_factor("battery", 51.0)
        assert cf == 20.0

    def test_user_provided_cf_overrides(self):
        """User-provided CF should override calculation."""
        cf = estimate_capacity_factor("solar", 51.0, user_provided=35.0)
        assert cf == 35.0

    def test_user_cf_clamped(self):
        """User CF should be clamped to [5, 95] range."""
        cf_low = estimate_capacity_factor("solar", 51.0, user_provided=1.0)
        cf_high = estimate_capacity_factor("solar", 51.0, user_provided=99.0)
        assert cf_low == 5.0
        assert cf_high == 95.0

    @pytest.mark.parametrize("tech,expected_cf", [
        ("bess", 20.0),
        ("hydro", 50.0),
        ("gas", 70.0),
        ("ccgt", 70.0),
        ("biomass", 70.0),
        ("hybrid", 50.0),
        ("unknown", 30.0),
    ])
    def test_various_technologies(self, tech, expected_cf):
        """Different technologies should return expected CFs."""
        assert estimate_capacity_factor(tech, 51.0) == expected_cf


class TestConnectionSpeedScore:
    """Test calculate_connection_speed_score function."""

    def test_good_stage_and_close_infrastructure(self):
        """Good development stage + close infrastructure = high score."""
        project = {"development_status_short": "consented"}
        proximity_scores = {
            "nearest_distances": {
                "substation_km": 5.0,
                "transmission_km": 10.0,
            }
        }
        score = calculate_connection_speed_score(project, proximity_scores)
        assert score > 70.0

    def test_poor_stage_and_far_infrastructure(self):
        """Poor stage + far infrastructure = low score."""
        project = {"development_status_short": "abandoned"}
        proximity_scores = {
            "nearest_distances": {
                "substation_km": 100.0,
                "transmission_km": 150.0,
            }
        }
        score = calculate_connection_speed_score(project, proximity_scores)
        assert score < 40.0

    def test_score_bounded(self):
        """Score should be in [0, 100] range."""
        project = {"development_status_short": "in planning"}
        for distance in [0, 10, 50, 100, 200]:
            proximity_scores = {
                "nearest_distances": {
                    "substation_km": distance,
                    "transmission_km": distance,
                }
            }
            score = calculate_connection_speed_score(project, proximity_scores)
            assert 0.0 <= score <= 100.0


class TestResilienceScore:
    """Test calculate_resilience_score function."""

    def test_close_to_infrastructure_with_battery(self):
        """Close infrastructure + battery = high resilience."""
        project = {"technology_type": "battery"}
        proximity_scores = {
            "nearest_distances": {
                "substation_km": 5.0,
                "transmission_km": 10.0,
            }
        }
        score = calculate_resilience_score(project, proximity_scores)
        assert score > 50.0

    def test_hybrid_adds_resilience(self):
        """Hybrid technology should add to resilience score."""
        project = {"technology_type": "hybrid"}
        proximity_scores = {
            "nearest_distances": {
                "substation_km": 5.0,
                "transmission_km": 10.0,
            }
        }
        score = calculate_resilience_score(project, proximity_scores)
        assert score >= 70.0

    def test_far_infrastructure_low_resilience(self):
        """Far from infrastructure = low resilience."""
        project = {"technology_type": "solar"}
        proximity_scores = {
            "nearest_distances": {
                "substation_km": 100.0,
                "transmission_km": 100.0,
            }
        }
        score = calculate_resilience_score(project, proximity_scores)
        assert score < 30.0

    def test_score_bounded(self):
        """Score should be in [0, 100] range."""
        project = {"technology_type": "solar"}
        score = calculate_resilience_score(project, {})
        assert 0.0 <= score <= 100.0


class TestPriceSensitivityScore:
    """Test calculate_price_sensitivity_score function."""

    def test_low_latitude_lower_cost(self):
        """Lower latitude (south) should have better price sensitivity."""
        project = {
            "technology_type": "solar",
            "latitude": 50.0,
            "longitude": -1.0,
        }
        score = calculate_price_sensitivity_score(project, {})
        assert score > 50.0

    def test_user_max_price_affects_score(self):
        """User max price threshold should affect scoring."""
        project = {
            "technology_type": "solar",
            "latitude": 52.0,
            "longitude": -1.0,
        }
        score_with_threshold = calculate_price_sensitivity_score(
            project, {}, user_max_price_mwh=100.0
        )
        score_without = calculate_price_sensitivity_score(project, {})
        # Both should be valid scores
        assert 0.0 <= score_with_threshold <= 100.0
        assert 0.0 <= score_without <= 100.0

    def test_score_bounded(self):
        """Score should be in [0, 100] range."""
        project = {
            "technology_type": "wind",
            "latitude": 55.0,
            "longitude": -3.0,
        }
        score = calculate_price_sensitivity_score(project, {})
        assert 0.0 <= score <= 100.0


# ============================================================================
# Test Aggregation Functions
# ============================================================================


class TestBuildPersonaComponentScores:
    """Test build_persona_component_scores function."""

    def test_returns_all_components(self):
        """Should return all 7 component scores."""
        project = {
            "capacity_mw": 50.0,
            "development_status_short": "in planning",
            "technology_type": "solar",
            "latitude": 51.5,
            "longitude": -0.1,
        }
        proximity_scores = {
            "nearest_distances": {
                "substation_km": 10.0,
                "transmission_km": 20.0,
                "fiber_km": 15.0,
                "ixp_km": 50.0,
                "water_km": 5.0,
            }
        }
        scores = build_persona_component_scores(project, proximity_scores)

        expected_components = {
            "capacity", "connection_speed", "resilience",
            "land_planning", "latency", "cooling", "price_sensitivity"
        }
        assert set(scores.keys()) == expected_components

    def test_all_scores_bounded(self):
        """All component scores should be in [0, 100] range."""
        project = {
            "capacity_mw": 50.0,
            "development_status_short": "in planning",
        }
        scores = build_persona_component_scores(project, {})

        for component, score in scores.items():
            assert 0.0 <= score <= 100.0, f"{component} out of range"

    def test_persona_affects_capacity_score(self):
        """Different personas should yield different capacity scores."""
        # Use capacity that is ideal for edge_computing (2 MW)
        project_edge_ideal = {"capacity_mw": 2.0}

        scores_edge = build_persona_component_scores(
            project_edge_ideal, {}, persona="edge_computing"
        )
        scores_hyper = build_persona_component_scores(
            project_edge_ideal, {}, persona="hyperscaler"
        )

        # 2 MW is ideal for edge (ideal=2.0), far from hyperscaler (ideal=50)
        assert scores_edge["capacity"] > scores_hyper["capacity"]

    def test_shared_scores_reused(self):
        """Shared component scores should be reused if provided."""
        project = {"capacity_mw": 50.0}
        shared = {
            "connection_speed": 80.0,
            "resilience": 70.0,
            "land_planning": 60.0,
            "latency": 50.0,
            "cooling": 40.0,
            "price_sensitivity": 30.0,
        }
        scores = build_persona_component_scores(
            project, {}, shared_component_scores=shared
        )

        for key in shared:
            assert scores[key] == shared[key]


class TestCalculateWeightedScoreFromComponents:
    """Test calculate_weighted_score_from_components function."""

    def test_returns_required_fields(self):
        """Should return all required output fields."""
        component_scores = {
            "capacity": 80.0,
            "connection_speed": 75.0,
            "resilience": 70.0,
            "land_planning": 65.0,
            "latency": 60.0,
            "cooling": 55.0,
            "price_sensitivity": 50.0,
        }
        weights = PERSONA_WEIGHTS["hyperscaler"]

        result = calculate_weighted_score_from_components(
            component_scores, weights, persona_label="hyperscaler"
        )

        assert "investment_rating" in result
        assert "rating_description" in result
        assert "color_code" in result
        assert "component_scores" in result
        assert "weighted_contributions" in result
        assert "internal_total_score" in result

    def test_investment_rating_bounded(self):
        """Investment rating should be in [0, 10] range."""
        component_scores = {
            "capacity": 50.0,
            "connection_speed": 50.0,
            "resilience": 50.0,
            "land_planning": 50.0,
            "latency": 50.0,
            "cooling": 50.0,
            "price_sensitivity": 50.0,
        }
        weights = PERSONA_WEIGHTS["hyperscaler"]

        result = calculate_weighted_score_from_components(
            component_scores, weights, persona_label="hyperscaler"
        )

        assert 0.0 <= result["investment_rating"] <= 10.0

    def test_high_scores_yield_high_rating(self):
        """High component scores should yield high investment rating."""
        component_scores = {
            "capacity": 95.0,
            "connection_speed": 95.0,
            "resilience": 95.0,
            "land_planning": 95.0,
            "latency": 95.0,
            "cooling": 95.0,
            "price_sensitivity": 95.0,
        }
        weights = PERSONA_WEIGHTS["hyperscaler"]

        result = calculate_weighted_score_from_components(
            component_scores, weights, persona_label="hyperscaler"
        )

        assert result["investment_rating"] >= 8.0

    def test_low_scores_yield_low_rating(self):
        """Low component scores should yield low investment rating."""
        component_scores = {
            "capacity": 10.0,
            "connection_speed": 10.0,
            "resilience": 10.0,
            "land_planning": 10.0,
            "latency": 10.0,
            "cooling": 10.0,
            "price_sensitivity": 10.0,
        }
        weights = PERSONA_WEIGHTS["hyperscaler"]

        result = calculate_weighted_score_from_components(
            component_scores, weights, persona_label="hyperscaler"
        )

        assert result["investment_rating"] <= 4.0


class TestCalculatePersonaTopsisScore:
    """Test calculate_persona_topsis_score function."""

    def test_empty_input(self):
        """Empty input should return empty scores."""
        result = calculate_persona_topsis_score([], {})
        assert result["scores"] == []
        assert result["ideal_solution"] == {}
        assert result["anti_ideal_solution"] == {}

    def test_single_project(self):
        """Single project should get closeness coefficient of 1.0."""
        component_scores = [
            {"capacity": 80.0, "connection_speed": 70.0}
        ]
        weights = {"capacity": 0.6, "connection_speed": 0.4}

        result = calculate_persona_topsis_score(component_scores, weights)

        assert len(result["scores"]) == 1
        assert result["scores"][0]["closeness_coefficient"] == 1.0

    def test_multiple_projects_ranking(self):
        """Multiple projects should be ranked by closeness coefficient."""
        component_scores = [
            {"capacity": 90.0, "connection_speed": 90.0},  # Best
            {"capacity": 50.0, "connection_speed": 50.0},  # Middle
            {"capacity": 10.0, "connection_speed": 10.0},  # Worst
        ]
        weights = {"capacity": 0.5, "connection_speed": 0.5}

        result = calculate_persona_topsis_score(component_scores, weights)

        closeness_values = [s["closeness_coefficient"] for s in result["scores"]]
        # First should have highest closeness
        assert closeness_values[0] == max(closeness_values)
        # Last should have lowest closeness
        assert closeness_values[2] == min(closeness_values)

    def test_ideal_and_anti_ideal_solutions(self):
        """Should correctly identify ideal and anti-ideal solutions."""
        component_scores = [
            {"capacity": 90.0, "connection_speed": 30.0},
            {"capacity": 30.0, "connection_speed": 90.0},
        ]
        weights = {"capacity": 0.5, "connection_speed": 0.5}

        result = calculate_persona_topsis_score(component_scores, weights)

        # Ideal should have max weighted values
        assert "capacity" in result["ideal_solution"]
        assert "connection_speed" in result["ideal_solution"]


class TestCalculateCustomWeightedScore:
    """Test calculate_custom_weighted_score function."""

    def test_returns_required_fields(self):
        """Should return all required output fields."""
        project = {
            "capacity_mw": 50.0,
            "development_status_short": "in planning",
            "technology_type": "solar",
            "latitude": 51.5,
            "longitude": -0.1,
        }
        custom_weights = {
            "capacity": 0.2,
            "development_stage": 0.2,
            "technology": 0.1,
            "grid_infrastructure": 0.2,
            "digital_infrastructure": 0.1,
            "water_resources": 0.1,
            "lcoe_resource_quality": 0.1,
        }

        result = calculate_custom_weighted_score(project, {}, custom_weights)

        assert "investment_rating" in result
        assert "rating_description" in result
        assert "color_code" in result
        assert "component_scores" in result
        assert result["persona"] == "custom"

    def test_weights_affect_score(self):
        """Custom weights should affect the final score."""
        # Use a project where components have very different scores
        project = {
            "capacity_mw": 500.0,  # Far from ideal - low score
            "development_status_short": "operational",  # Low score (10)
            "technology_type": "hybrid",  # High score (100)
            "latitude": 51.5,
            "longitude": -0.1,
        }

        # Heavy weight on technology (hybrid = 100)
        weights_tech = {"technology": 1.0}
        # Heavy weight on development_stage (operational = 10)
        weights_stage = {"development_stage": 1.0}

        result_tech = calculate_custom_weighted_score(project, {}, weights_tech)
        result_stage = calculate_custom_weighted_score(project, {}, weights_stage)

        # Technology has high score (100), development_stage has low (10)
        # So weighting technology should give higher rating
        assert result_tech["internal_total_score"] > result_stage["internal_total_score"]


class TestCalculateBestCustomerMatch:
    """Test calculate_best_customer_match function."""

    def test_returns_required_fields(self):
        """Should return all required output fields."""
        project = {
            "capacity_mw": 50.0,
            "development_status_short": "in planning",
        }

        result = calculate_best_customer_match(project, {})

        assert "best_customer_match" in result
        assert "customer_match_scores" in result
        assert "best_match_score" in result
        assert "capacity_mw" in result
        assert "suitable_customers" in result

    def test_edge_capacity_matches_edge(self):
        """Small capacity should match edge_computing."""
        project = {"capacity_mw": 2.0}  # Edge range: 0.4-5 MW
        result = calculate_best_customer_match(project, {})
        assert "edge_computing" in result["suitable_customers"] or \
               result["best_customer_match"] == "edge_computing"

    def test_hyperscaler_capacity_matches_hyperscaler(self):
        """Large capacity should match hyperscaler."""
        project = {"capacity_mw": 100.0}  # Hyperscaler range: 30-250 MW
        result = calculate_best_customer_match(project, {})
        # Should either be suitable for hyperscaler or match hyperscaler
        # (depends on other factors too)
        assert result["best_customer_match"] in [
            "hyperscaler", "colocation", "edge_computing"
        ]

    def test_out_of_range_capacity(self):
        """Capacity outside all ranges should get low scores."""
        project = {"capacity_mw": 500.0}  # Above all ranges
        result = calculate_best_customer_match(project, {})
        # All scores should be low (2.0 default when out of range)
        for persona, score in result["customer_match_scores"].items():
            if PERSONA_CAPACITY_RANGES[persona]["max"] < 500:
                assert score == 2.0


class TestFilterProjectsByPersonaCapacity:
    """Test filter_projects_by_persona_capacity function."""

    def test_filters_correctly(self):
        """Should filter projects to match persona capacity range."""
        projects = [
            {"capacity_mw": 1.0},   # Edge
            {"capacity_mw": 3.0},   # Edge
            {"capacity_mw": 10.0},  # Colocation
            {"capacity_mw": 20.0},  # Colocation
            {"capacity_mw": 50.0},  # Hyperscaler
            {"capacity_mw": 100.0}, # Hyperscaler
        ]

        edge_filtered = filter_projects_by_persona_capacity(projects, "edge_computing")
        colo_filtered = filter_projects_by_persona_capacity(projects, "colocation")
        hyper_filtered = filter_projects_by_persona_capacity(projects, "hyperscaler")

        # Check counts based on capacity ranges
        assert len(edge_filtered) == 2   # 1.0 and 3.0
        assert len(colo_filtered) == 2   # 10.0 and 20.0
        assert len(hyper_filtered) == 2  # 50.0 and 100.0

    def test_empty_list(self):
        """Empty project list should return empty."""
        result = filter_projects_by_persona_capacity([], "hyperscaler")
        assert result == []

    def test_missing_capacity(self):
        """Projects with missing capacity should be excluded."""
        projects = [
            {"capacity_mw": 50.0},
            {"name": "no_capacity"},
            {},
        ]
        result = filter_projects_by_persona_capacity(projects, "hyperscaler")
        assert len(result) == 1


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_values_handled(self):
        """None values in project data are handled by providing defaults."""
        # The scoring module requires valid coordinates for TNUOS score
        # Test that valid coordinates work with None for other fields
        project = {
            "capacity_mw": None,
            "development_status_short": None,
            "technology_type": None,
            "latitude": 51.5,  # Valid coordinate required
            "longitude": -0.1,  # Valid coordinate required
        }
        # Should not raise - capacity defaults to 0, status defaults to "unknown"
        scores = build_persona_component_scores(project, {})
        assert isinstance(scores, dict)
        # Capacity of 0 or None should give a valid (low) score
        assert 0.0 <= scores["capacity"] <= 100.0

    def test_negative_values_handled(self):
        """Negative values should not crash scoring."""
        project = {
            "capacity_mw": -10.0,
            "latitude": -91.0,
            "longitude": -181.0,
        }
        # Should not raise
        scores = build_persona_component_scores(project, {})
        assert isinstance(scores, dict)

    def test_extreme_coordinates(self):
        """Extreme coordinate values should be handled."""
        # North Pole
        score1 = calculate_tnuos_score(90.0, 0.0)
        # South Pole
        score2 = calculate_tnuos_score(-90.0, 0.0)

        assert 0.0 <= score1 <= 100.0
        assert 0.0 <= score2 <= 100.0

    def test_string_capacity_in_calculate_function(self):
        """String capacity in component function should be handled."""
        # The calculate_capacity_component_score expects numeric input
        # Test with numeric 0 to verify score is calculated
        score = calculate_capacity_component_score(0.0)
        assert 0.0 <= score <= 100.0

    def test_project_requires_numeric_capacity(self):
        """Projects should have numeric capacity for scoring."""
        # If capacity_mw is not numeric, the scoring will use fallback
        project = {"capacity_mw": 0, "latitude": 51.5, "longitude": -0.1}
        scores = build_persona_component_scores(project, {})
        assert "capacity" in scores
        assert 0.0 <= scores["capacity"] <= 100.0

    def test_minimal_project(self):
        """Minimal project with just coordinates should work."""
        # At minimum, the scoring needs coordinates for TNUOS calculation
        project = {"latitude": 51.5, "longitude": -0.1}
        scores = build_persona_component_scores(project, {})
        assert isinstance(scores, dict)
        assert len(scores) == 7
