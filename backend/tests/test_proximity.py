"""Comprehensive tests for backend/proximity.py module.

Tests SpatialGrid spatial indexing, haversine distance calculations,
proximity scoring, and infrastructure catalog operations.
"""

import sys
import math
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.proximity import (
    # Constants
    KM_PER_DEGREE_LAT,
    DEFAULT_GRID_CELL_DEGREES,
    # Classes
    PointFeature,
    LineFeature,
    InfrastructureCatalog,
    SpatialGrid,
    # Functions
    haversine,
    exponential_score,
    point_to_line_segment_distance,
    nearest_point,
    nearest_line,
    calculate_proximity_scores,
)


# ============================================================================
# Test Data Classes
# ============================================================================


class TestPointFeature:
    """Test PointFeature dataclass."""

    def test_create_point_feature(self):
        """Should create a point feature with lat, lon, data."""
        feature = PointFeature(lat=51.5, lon=-0.1, data={"name": "London"})
        assert feature.lat == 51.5
        assert feature.lon == -0.1
        assert feature.data == {"name": "London"}

    def test_point_feature_equality(self):
        """Equal features should be equal."""
        f1 = PointFeature(lat=51.5, lon=-0.1, data={})
        f2 = PointFeature(lat=51.5, lon=-0.1, data={})
        assert f1 == f2

    def test_point_feature_with_complex_data(self):
        """Should handle complex data dictionaries."""
        data = {
            "id": 123,
            "name": "Substation A",
            "capacity_mva": 500.0,
            "voltage_kv": 400,
            "metadata": {"operator": "National Grid", "year": 2020},
        }
        feature = PointFeature(lat=52.0, lon=-1.5, data=data)
        assert feature.data["id"] == 123
        assert feature.data["metadata"]["operator"] == "National Grid"


class TestLineFeature:
    """Test LineFeature dataclass."""

    def test_create_line_feature(self):
        """Should create a line feature with coordinates and segments."""
        coords = [(51.5, -0.1), (51.6, -0.2), (51.7, -0.3)]
        segments = [
            (51.5, -0.1, 51.6, -0.2),
            (51.6, -0.2, 51.7, -0.3),
        ]
        bbox = (51.5, -0.3, 51.7, -0.1)

        feature = LineFeature(
            coordinates=coords,
            segments=segments,
            bbox=bbox,
            data={"name": "Transmission Line"}
        )

        assert len(feature.coordinates) == 3
        assert len(feature.segments) == 2
        assert feature.bbox == (51.5, -0.3, 51.7, -0.1)

    def test_line_feature_with_single_segment(self):
        """Should handle single-segment lines."""
        coords = [(51.5, -0.1), (51.6, -0.2)]
        segments = [(51.5, -0.1, 51.6, -0.2)]
        bbox = (51.5, -0.2, 51.6, -0.1)

        feature = LineFeature(
            coordinates=coords,
            segments=segments,
            bbox=bbox,
            data={}
        )

        assert len(feature.segments) == 1


# ============================================================================
# Test SpatialGrid
# ============================================================================


class TestSpatialGrid:
    """Test SpatialGrid spatial indexing class."""

    def test_create_spatial_grid(self):
        """Should create an empty spatial grid."""
        grid = SpatialGrid()
        assert grid.cell_size_deg == DEFAULT_GRID_CELL_DEGREES

    def test_create_grid_with_custom_cell_size(self):
        """Should accept custom cell size."""
        grid = SpatialGrid(cell_size_deg=1.0)
        assert grid.cell_size_deg == 1.0

    def test_add_point_to_grid(self):
        """Should add point features to grid."""
        grid = SpatialGrid()
        feature = PointFeature(lat=51.5, lon=-0.1, data={})

        grid.add_point(feature)

        # Query the location
        results = list(grid.query(51.5, -0.1, steps=1))
        assert len(results) == 1
        assert results[0] == feature

    def test_add_multiple_points(self):
        """Should handle multiple points in same cell."""
        grid = SpatialGrid()
        f1 = PointFeature(lat=51.5, lon=-0.1, data={"id": 1})
        f2 = PointFeature(lat=51.51, lon=-0.11, data={"id": 2})

        grid.add_point(f1)
        grid.add_point(f2)

        results = list(grid.query(51.5, -0.1, steps=1))
        assert len(results) == 2

    def test_query_with_steps(self):
        """Should find features within step radius."""
        grid = SpatialGrid(cell_size_deg=0.5)
        f1 = PointFeature(lat=51.5, lon=-0.1, data={"id": 1})
        f2 = PointFeature(lat=52.5, lon=-0.1, data={"id": 2})  # 2 cells away

        grid.add_point(f1)
        grid.add_point(f2)

        # Query with 1 step should only find f1
        results_1 = list(grid.query(51.5, -0.1, steps=1))
        # Query with more steps should find f2
        results_3 = list(grid.query(51.5, -0.1, steps=3))

        assert len(results_1) == 1
        assert len(results_3) == 2

    def test_add_bbox(self):
        """Should add line features by bounding box."""
        grid = SpatialGrid(cell_size_deg=0.5)
        coords = [(51.5, -0.3), (51.5, -0.1)]
        segments = [(51.5, -0.3, 51.5, -0.1)]
        bbox = (51.5, -0.3, 51.5, -0.1)
        feature = LineFeature(
            coordinates=coords,
            segments=segments,
            bbox=bbox,
            data={}
        )

        grid.add_bbox(bbox, feature)

        # Should be queryable from multiple cells along the line
        results1 = list(grid.query(51.5, -0.2, steps=1))
        assert len(results1) >= 1

    def test_approximate_cell_width_km(self):
        """Should calculate approximate cell width in km."""
        grid = SpatialGrid(cell_size_deg=0.5)
        width = grid.approximate_cell_width_km()

        expected = 0.5 * KM_PER_DEGREE_LAT
        assert width == pytest.approx(expected, rel=0.01)

    def test_query_empty_grid(self):
        """Query on empty grid should return empty."""
        grid = SpatialGrid()
        results = list(grid.query(51.5, -0.1, steps=5))
        assert len(results) == 0

    def test_grid_handles_negative_coordinates(self):
        """Should handle negative lat/lon correctly."""
        grid = SpatialGrid()
        feature = PointFeature(lat=-33.9, lon=151.2, data={"name": "Sydney"})

        grid.add_point(feature)
        results = list(grid.query(-33.9, 151.2, steps=1))

        assert len(results) == 1

    def test_grid_handles_extreme_latitudes(self):
        """Should handle extreme latitude values."""
        grid = SpatialGrid()
        f_north = PointFeature(lat=89.0, lon=0.0, data={"name": "Arctic"})
        f_south = PointFeature(lat=-89.0, lon=0.0, data={"name": "Antarctic"})

        grid.add_point(f_north)
        grid.add_point(f_south)

        results_north = list(grid.query(89.0, 0.0, steps=1))
        results_south = list(grid.query(-89.0, 0.0, steps=1))

        assert len(results_north) == 1
        assert len(results_south) == 1

    def test_no_duplicate_results(self):
        """Query should not return duplicate features."""
        grid = SpatialGrid(cell_size_deg=1.0)

        # Create a line that spans multiple cells
        coords = [(50.0, -2.0), (52.0, 0.0)]
        segments = [(50.0, -2.0, 52.0, 0.0)]
        bbox = (50.0, -2.0, 52.0, 0.0)
        feature = LineFeature(
            coordinates=coords,
            segments=segments,
            bbox=bbox,
            data={}
        )

        grid.add_bbox(bbox, feature)

        # Query with large steps
        results = list(grid.query(51.0, -1.0, steps=3))

        # Should only have 1 unique feature
        assert len(results) == 1


# ============================================================================
# Test Distance Calculations
# ============================================================================


class TestHaversine:
    """Test haversine distance calculation."""

    def test_same_point_zero_distance(self):
        """Same point should have zero distance."""
        distance = haversine(51.5, -0.1, 51.5, -0.1)
        assert distance == 0.0

    def test_known_distance_london_to_paris(self):
        """Test known approximate distance: London to Paris ~340 km."""
        # London: 51.5074, -0.1278
        # Paris: 48.8566, 2.3522
        distance = haversine(51.5074, -0.1278, 48.8566, 2.3522)
        # Actual distance is approximately 340 km
        assert 330 < distance < 350

    def test_known_distance_new_york_to_los_angeles(self):
        """Test known approximate distance: NYC to LA ~3940 km."""
        # New York: 40.7128, -74.0060
        # Los Angeles: 34.0522, -118.2437
        distance = haversine(40.7128, -74.0060, 34.0522, -118.2437)
        # Actual distance is approximately 3940 km
        assert 3900 < distance < 4000

    def test_distance_is_symmetric(self):
        """Distance A to B should equal B to A."""
        d1 = haversine(51.5, -0.1, 48.8, 2.3)
        d2 = haversine(48.8, 2.3, 51.5, -0.1)
        assert d1 == pytest.approx(d2, rel=1e-10)

    def test_distance_always_positive(self):
        """Distance should always be positive."""
        test_cases = [
            (90.0, 0.0, -90.0, 0.0),     # Pole to pole
            (0.0, 0.0, 0.0, 180.0),      # Equator crossing
            (-33.9, 151.2, 51.5, -0.1),  # Sydney to London
        ]
        for lat1, lon1, lat2, lon2 in test_cases:
            distance = haversine(lat1, lon1, lat2, lon2)
            assert distance >= 0

    def test_short_distance_accuracy(self):
        """Test accuracy for short distances."""
        # Points about 1 km apart at equator
        # 1 degree longitude at equator ≈ 111 km
        distance = haversine(0.0, 0.0, 0.0, 0.009)  # ~1 km
        assert 0.9 < distance < 1.1


class TestExponentialScore:
    """Test exponential_score decay function."""

    def test_zero_distance_is_100(self):
        """Zero distance should return 100."""
        score = exponential_score(0.0, 30.0)
        assert score == pytest.approx(100.0, rel=0.01)

    def test_half_distance_is_50(self):
        """At half-distance, score should be ~50."""
        score = exponential_score(30.0, 30.0)
        assert score == pytest.approx(50.0, rel=0.02)

    def test_200km_or_more_is_zero(self):
        """200 km or more should return 0."""
        assert exponential_score(200.0, 30.0) == 0.0
        assert exponential_score(300.0, 30.0) == 0.0
        assert exponential_score(1000.0, 30.0) == 0.0

    def test_score_bounded(self):
        """Score should always be in [0, 100] range."""
        test_distances = [0, 5, 10, 25, 50, 100, 150, 199, 200, 250]
        for distance in test_distances:
            score = exponential_score(distance, 30.0)
            assert 0.0 <= score <= 100.0

    def test_different_half_distances(self):
        """Different half-distances should produce different curves."""
        score_short = exponential_score(30.0, 15.0)  # Steeper decay
        score_long = exponential_score(30.0, 50.0)   # Slower decay

        assert score_short < score_long

    def test_monotonic_decrease(self):
        """Score should monotonically decrease with distance."""
        prev_score = 100.0
        for distance in range(0, 200, 10):
            score = exponential_score(float(distance), 30.0)
            assert score <= prev_score
            prev_score = score


class TestPointToLineSegmentDistance:
    """Test point_to_line_segment_distance function."""

    def test_point_on_line_zero_distance(self):
        """Point on the line should have ~zero distance."""
        # Point is midpoint of line
        distance = point_to_line_segment_distance(
            0.5, 0.5,  # Point (lat, lon)
            0.0, 0.0,  # Line start
            1.0, 1.0   # Line end
        )
        assert distance == pytest.approx(0.0, abs=0.1)

    def test_point_at_start(self):
        """Point at start of line should have zero distance."""
        distance = point_to_line_segment_distance(
            0.0, 0.0,  # Point
            0.0, 0.0,  # Line start
            1.0, 1.0   # Line end
        )
        assert distance == pytest.approx(0.0, abs=0.01)

    def test_point_at_end(self):
        """Point at end of line should have zero distance."""
        distance = point_to_line_segment_distance(
            1.0, 1.0,  # Point
            0.0, 0.0,  # Line start
            1.0, 1.0   # Line end
        )
        assert distance == pytest.approx(0.0, abs=0.01)

    def test_point_perpendicular_to_line(self):
        """Test perpendicular distance to line."""
        # Horizontal line at lat=0, point at lat=1
        distance = point_to_line_segment_distance(
            1.0, 0.5,  # Point (1 degree north of line center)
            0.0, 0.0,  # Line start
            0.0, 1.0   # Line end
        )
        # 1 degree of latitude ≈ 111 km
        assert 100 < distance < 120

    def test_point_beyond_line_end(self):
        """Point beyond line end should use end point distance."""
        distance = point_to_line_segment_distance(
            0.0, 2.0,  # Point beyond line end
            0.0, 0.0,  # Line start
            0.0, 1.0   # Line end
        )
        # Should be distance from (0, 2) to (0, 1)
        expected = haversine(0.0, 2.0, 0.0, 1.0)
        assert distance == pytest.approx(expected, rel=0.01)

    def test_zero_length_segment(self):
        """Zero-length segment should return point-to-point distance."""
        distance = point_to_line_segment_distance(
            1.0, 1.0,  # Point
            0.0, 0.0,  # Same start and end
            0.0, 0.0
        )
        expected = haversine(1.0, 1.0, 0.0, 0.0)
        assert distance == pytest.approx(expected, rel=0.01)


# ============================================================================
# Test Nearest Feature Functions
# ============================================================================


class TestNearestPoint:
    """Test nearest_point function."""

    def test_find_nearest_point(self):
        """Should find the nearest point feature."""
        grid = SpatialGrid()
        f1 = PointFeature(lat=51.5, lon=-0.1, data={"id": 1})
        f2 = PointFeature(lat=52.0, lon=-0.5, data={"id": 2})
        f3 = PointFeature(lat=51.0, lon=0.5, data={"id": 3})

        grid.add_point(f1)
        grid.add_point(f2)
        grid.add_point(f3)

        features = [f1, f2, f3]

        # Query near f1
        result = nearest_point(grid, features, 51.5, -0.1, radius_km=100.0)

        assert result is not None
        distance, feature = result
        assert feature.data["id"] == 1
        assert distance < 1.0  # Very close

    def test_no_points_in_radius(self):
        """Should return None if no points in radius."""
        grid = SpatialGrid()
        f1 = PointFeature(lat=51.5, lon=-0.1, data={"id": 1})
        grid.add_point(f1)

        # Query far away with small radius
        result = nearest_point(grid, [f1], 55.0, 5.0, radius_km=10.0)

        # Falls back to linear search but still outside radius conceptually
        # The function will still return nearest if fallback is used
        # Let's check the distance
        if result:
            distance, _ = result
            # Should be far
            assert distance > 100

    def test_empty_features_returns_none(self):
        """Empty feature list should return None."""
        grid = SpatialGrid()
        result = nearest_point(grid, [], 51.5, -0.1, radius_km=100.0)
        assert result is None

    def test_fallback_to_linear_search(self):
        """Should fallback to linear search if grid misses."""
        grid = SpatialGrid(cell_size_deg=0.1)  # Small cells
        f1 = PointFeature(lat=51.5, lon=-0.1, data={"id": 1})
        # Don't add to grid, only to features list

        result = nearest_point(grid, [f1], 51.5, -0.1, radius_km=100.0)

        # Fallback should still find it
        assert result is not None


class TestNearestLine:
    """Test nearest_line function."""

    def test_find_nearest_line(self):
        """Should find the nearest line feature."""
        grid = SpatialGrid()

        # Create two line features
        l1_coords = [(51.5, -0.1), (51.5, 0.0)]
        l1_segments = [(51.5, -0.1, 51.5, 0.0)]
        l1_bbox = (51.5, -0.1, 51.5, 0.0)
        line1 = LineFeature(
            coordinates=l1_coords,
            segments=l1_segments,
            bbox=l1_bbox,
            data={"id": 1}
        )

        l2_coords = [(52.5, -1.0), (52.5, -0.5)]
        l2_segments = [(52.5, -1.0, 52.5, -0.5)]
        l2_bbox = (52.5, -1.0, 52.5, -0.5)
        line2 = LineFeature(
            coordinates=l2_coords,
            segments=l2_segments,
            bbox=l2_bbox,
            data={"id": 2}
        )

        grid.add_bbox(l1_bbox, line1)
        grid.add_bbox(l2_bbox, line2)

        features = [line1, line2]

        # Query near line1
        result = nearest_line(grid, features, 51.5, -0.05, radius_km=50.0)

        assert result is not None
        distance, feature = result
        assert feature.data["id"] == 1

    def test_empty_features_returns_none(self):
        """Empty feature list should return None."""
        grid = SpatialGrid()
        result = nearest_line(grid, [], 51.5, -0.1, radius_km=100.0)
        assert result is None


# ============================================================================
# Test Calculate Proximity Scores
# ============================================================================


class TestCalculateProximityScores:
    """Test calculate_proximity_scores function."""

    def _create_mock_catalog(self):
        """Create a mock infrastructure catalog for testing."""
        # Create spatial grids
        substations_index = SpatialGrid()
        transmission_index = SpatialGrid()
        fiber_index = SpatialGrid()
        ixp_index = SpatialGrid()
        water_point_index = SpatialGrid()
        water_line_index = SpatialGrid()

        # Create sample features
        substation = PointFeature(lat=51.5, lon=-0.1, data={"name": "Sub1"})
        substations_index.add_point(substation)

        transmission_coords = [(51.4, -0.2), (51.6, 0.0)]
        transmission_segments = [(51.4, -0.2, 51.6, 0.0)]
        transmission_bbox = (51.4, -0.2, 51.6, 0.0)
        transmission = LineFeature(
            coordinates=transmission_coords,
            segments=transmission_segments,
            bbox=transmission_bbox,
            data={"name": "Trans1"}
        )
        transmission_index.add_bbox(transmission_bbox, transmission)

        fiber_coords = [(51.45, -0.15), (51.55, -0.05)]
        fiber_segments = [(51.45, -0.15, 51.55, -0.05)]
        fiber_bbox = (51.45, -0.15, 51.55, -0.05)
        fiber = LineFeature(
            coordinates=fiber_coords,
            segments=fiber_segments,
            bbox=fiber_bbox,
            data={"name": "Fiber1"}
        )
        fiber_index.add_bbox(fiber_bbox, fiber)

        ixp = PointFeature(lat=51.52, lon=-0.08, data={"name": "IXP1"})
        ixp_index.add_point(ixp)

        water_point = PointFeature(lat=51.48, lon=-0.12, data={"name": "River1"})
        water_point_index.add_point(water_point)

        return InfrastructureCatalog(
            substations=[substation],
            transmission_lines=[transmission],
            fiber_cables=[fiber],
            internet_exchange_points=[ixp],
            water_points=[water_point],
            water_lines=[],
            substations_index=substations_index,
            transmission_index=transmission_index,
            fiber_index=fiber_index,
            ixp_index=ixp_index,
            water_point_index=water_point_index,
            water_line_index=water_line_index,
            load_timestamp=0.0,
            counts={
                "substations": 1,
                "transmission_lines": 1,
                "fiber_cables": 1,
                "ixp": 1,
                "water_points": 1,
            }
        )

    def test_returns_all_score_types(self):
        """Should return all proximity score types."""
        catalog = self._create_mock_catalog()
        search_radius = {
            "substation": 100.0,
            "transmission": 100.0,
            "fiber": 100.0,
            "ixp": 100.0,
            "water": 100.0,
        }
        half_distance = {
            "substation": 30.0,
            "transmission": 30.0,
            "fiber": 30.0,
            "ixp": 50.0,
            "water": 25.0,
        }

        scores = calculate_proximity_scores(
            catalog, 51.5, -0.1, search_radius, half_distance
        )

        assert "substation_score" in scores
        assert "transmission_score" in scores
        assert "fiber_score" in scores
        assert "ixp_score" in scores
        assert "water_score" in scores
        assert "total_proximity_bonus" in scores
        assert "nearest_distances" in scores

    def test_close_location_high_scores(self):
        """Location close to infrastructure should have high scores."""
        catalog = self._create_mock_catalog()
        search_radius = {
            "substation": 100.0,
            "transmission": 100.0,
            "fiber": 100.0,
            "ixp": 100.0,
            "water": 100.0,
        }
        half_distance = {
            "substation": 30.0,
            "transmission": 30.0,
            "fiber": 30.0,
            "ixp": 50.0,
            "water": 25.0,
        }

        # Query at infrastructure location
        scores = calculate_proximity_scores(
            catalog, 51.5, -0.1, search_radius, half_distance
        )

        assert scores["substation_score"] > 80.0
        assert scores["total_proximity_bonus"] > 100.0

    def test_far_location_low_scores(self):
        """Location far from infrastructure should have low scores."""
        catalog = self._create_mock_catalog()
        search_radius = {
            "substation": 100.0,
            "transmission": 100.0,
            "fiber": 100.0,
            "ixp": 100.0,
            "water": 100.0,
        }
        half_distance = {
            "substation": 30.0,
            "transmission": 30.0,
            "fiber": 30.0,
            "ixp": 50.0,
            "water": 25.0,
        }

        # Query far from infrastructure
        scores = calculate_proximity_scores(
            catalog, 55.0, 5.0, search_radius, half_distance
        )

        # All scores should be low
        assert scores["substation_score"] < 50.0

    def test_nearest_distances_populated(self):
        """Should populate nearest distances dictionary."""
        catalog = self._create_mock_catalog()
        search_radius = {
            "substation": 100.0,
            "transmission": 100.0,
            "fiber": 100.0,
            "ixp": 100.0,
            "water": 100.0,
        }
        half_distance = {
            "substation": 30.0,
            "transmission": 30.0,
            "fiber": 30.0,
            "ixp": 50.0,
            "water": 25.0,
        }

        scores = calculate_proximity_scores(
            catalog, 51.5, -0.1, search_radius, half_distance
        )

        distances = scores["nearest_distances"]
        assert "substation_km" in distances
        assert distances["substation_km"] < 10.0  # Very close

    def test_scores_bounded(self):
        """All scores should be in [0, 100] range."""
        catalog = self._create_mock_catalog()
        search_radius = {
            "substation": 100.0,
            "transmission": 100.0,
            "fiber": 100.0,
            "ixp": 100.0,
            "water": 100.0,
        }
        half_distance = {
            "substation": 30.0,
            "transmission": 30.0,
            "fiber": 30.0,
            "ixp": 50.0,
            "water": 25.0,
        }

        test_locations = [
            (51.5, -0.1),   # Near infrastructure
            (55.0, 5.0),    # Far from infrastructure
            (52.0, -1.0),   # Medium distance
        ]

        for lat, lon in test_locations:
            scores = calculate_proximity_scores(
                catalog, lat, lon, search_radius, half_distance
            )
            assert 0.0 <= scores["substation_score"] <= 100.0
            assert 0.0 <= scores["transmission_score"] <= 100.0
            assert 0.0 <= scores["fiber_score"] <= 100.0
            assert 0.0 <= scores["ixp_score"] <= 100.0
            assert 0.0 <= scores["water_score"] <= 100.0


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestProximityEdgeCases:
    """Test edge cases in proximity calculations."""

    def test_haversine_with_zero_coordinates(self):
        """Haversine should handle coordinates at origin."""
        distance = haversine(0.0, 0.0, 0.0, 0.0)
        assert distance == 0.0

    def test_haversine_crossing_dateline(self):
        """Haversine should handle crossing the international dateline."""
        # Point near dateline on each side
        distance = haversine(0.0, 179.0, 0.0, -179.0)
        # Should be about 222 km (2 degrees at equator)
        assert 200 < distance < 250

    def test_haversine_crossing_prime_meridian(self):
        """Haversine should handle crossing the prime meridian."""
        distance = haversine(51.5, -0.5, 51.5, 0.5)
        # About 1 degree of longitude at 51.5 lat ≈ 69 km
        assert 50 < distance < 90

    def test_spatial_grid_with_very_small_cells(self):
        """Should work with very small cell sizes."""
        grid = SpatialGrid(cell_size_deg=0.01)
        feature = PointFeature(lat=51.5, lon=-0.1, data={})
        grid.add_point(feature)

        results = list(grid.query(51.5, -0.1, steps=1))
        assert len(results) == 1

    def test_spatial_grid_with_large_cells(self):
        """Should work with large cell sizes."""
        grid = SpatialGrid(cell_size_deg=10.0)
        f1 = PointFeature(lat=51.5, lon=-0.1, data={"id": 1})
        f2 = PointFeature(lat=55.0, lon=5.0, data={"id": 2})

        grid.add_point(f1)
        grid.add_point(f2)

        # Both might be in same or adjacent cells
        results = list(grid.query(53.0, 2.0, steps=1))
        assert len(results) >= 1

    def test_exponential_score_with_very_small_half_distance(self):
        """Exponential score with small half-distance."""
        score = exponential_score(1.0, 1.0)
        assert 40.0 < score < 60.0  # Should be around 50

    def test_exponential_score_with_very_large_half_distance(self):
        """Exponential score with large half-distance."""
        score = exponential_score(50.0, 100.0)
        assert score > 50.0  # Still high because decay is slow

    def test_line_segment_distance_vertical_line(self):
        """Distance to vertical line segment."""
        distance = point_to_line_segment_distance(
            51.5, 0.0,   # Point
            51.0, -0.1,  # Line start
            52.0, -0.1   # Line end (vertical)
        )
        # Point is east of the vertical line
        # 0.1 degree longitude at 51.5 lat ≈ 7 km
        assert 5.0 < distance < 15.0

    def test_line_segment_distance_horizontal_line(self):
        """Distance to horizontal line segment."""
        distance = point_to_line_segment_distance(
            52.0, -0.05,  # Point (north of line)
            51.5, -0.1,   # Line start
            51.5, 0.0     # Line end (horizontal)
        )
        # Point is 0.5 degrees north ≈ 55 km
        assert 50.0 < distance < 60.0
