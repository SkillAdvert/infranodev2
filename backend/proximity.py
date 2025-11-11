"""
Proximity and spatial analysis module for infrastructure calculations.

This module provides spatial grid indexing, distance calculations, and proximity
scoring algorithms with no dependencies on other backend modules.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Constants
KM_PER_DEGREE_LAT = 111.32
GRID_CELL_DEGREES = 0.5

INFRASTRUCTURE_SEARCH_RADIUS_KM = {
    "substation": 100.0,
    "transmission": 100.0,
    "fiber": 100.0,
    "ixp": 100.0,
    "water": 100.0,
}


# Data structures
@dataclass
class PointFeature:
    """Represents a point infrastructure feature."""
    lat: float
    lon: float
    data: Dict[str, Any]


@dataclass
class LineFeature:
    """Represents a line infrastructure feature (transmission lines, fiber cables, etc.)."""
    coordinates: List[Tuple[float, float]]
    segments: List[Tuple[float, float, float, float]]
    bbox: Tuple[float, float, float, float]
    data: Dict[str, Any]


class SpatialGrid:
    """
    Spatial grid index for efficient proximity queries.

    Divides geographic space into cells to enable fast nearest-neighbor searches.
    """

    def __init__(self, cell_size_deg: float = GRID_CELL_DEGREES) -> None:
        self.cell_size_deg = cell_size_deg
        self._cells: Dict[Tuple[int, int], List[Any]] = defaultdict(list)

    def _index_lat(self, lat: float) -> int:
        return int(math.floor((lat + 90.0) / self.cell_size_deg))

    def _index_lon(self, lon: float) -> int:
        return int(math.floor((lon + 180.0) / self.cell_size_deg))

    def add_point(self, feature: PointFeature) -> None:
        """Add a point feature to the spatial index."""
        key = (self._index_lat(feature.lat), self._index_lon(feature.lon))
        self._cells[key].append(feature)

    def add_bbox(self, bbox: Tuple[float, float, float, float], feature: LineFeature) -> None:
        """Add a line feature to the spatial index using its bounding box."""
        min_lat, min_lon, max_lat, max_lon = bbox
        lat_start = self._index_lat(min_lat)
        lat_end = self._index_lat(max_lat)
        lon_start = self._index_lon(min_lon)
        lon_end = self._index_lon(max_lon)
        for lat_idx in range(lat_start, lat_end + 1):
            for lon_idx in range(lon_start, lon_end + 1):
                self._cells[(lat_idx, lon_idx)].append(feature)

    def query(self, lat: float, lon: float, steps: int) -> Iterable[Any]:
        """
        Query the spatial index for features near a given location.

        Args:
            lat: Latitude of query point
            lon: Longitude of query point
            steps: Number of grid cells to search in each direction

        Yields:
            Features within the search radius
        """
        base_lat = self._index_lat(lat)
        base_lon = self._index_lon(lon)
        seen: set[int] = set()
        for lat_offset in range(-steps, steps + 1):
            for lon_offset in range(-steps, lon_offset + 1):
                cell = (base_lat + lat_offset, base_lon + lon_offset)
                for feature in self._cells.get(cell, ()):  # type: ignore[arg-type]
                    feature_id = id(feature)
                    if feature_id not in seen:
                        seen.add(feature_id)
                        yield feature

    def approximate_cell_width_km(self) -> float:
        """Calculate approximate cell width in kilometers."""
        return self.cell_size_deg * KM_PER_DEGREE_LAT


# Distance calculation functions
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.

    Args:
        lat1: Latitude of first point (degrees)
        lon1: Longitude of first point (degrees)
        lat2: Latitude of second point (degrees)
        lon2: Longitude of second point (degrees)

    Returns:
        Distance in kilometers
    """
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def point_to_line_segment_distance(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    """
    Calculate the shortest distance from a point to a line segment.

    Args:
        px, py: Point coordinates (lat, lon)
        x1, y1: Line segment start (lat, lon)
        x2, y2: Line segment end (lat, lon)

    Returns:
        Distance in kilometers
    """
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


# Helper functions for spatial queries
def _grid_steps_for_radius(grid: SpatialGrid, radius_km: float) -> int:
    """Calculate number of grid cells to search for a given radius."""
    cell_width_km = max(1.0, grid.approximate_cell_width_km())
    return max(1, int(math.ceil(radius_km / cell_width_km)) + 1)


def _bbox_within_search(
    bbox: Tuple[float, float, float, float],
    lat: float,
    lon: float,
    radius_km: float,
) -> bool:
    """Check if a bounding box could contain points within the search radius."""
    min_lat, min_lon, max_lat, max_lon = bbox
    lat_margin = radius_km / KM_PER_DEGREE_LAT
    lon_margin = radius_km / (KM_PER_DEGREE_LAT * max(math.cos(math.radians(lat)), 0.2))
    return not (
        lat < min_lat - lat_margin
        or lat > max_lat + lat_margin
        or lon < min_lon - lon_margin
        or lon > max_lon + lon_margin
    )


def _distance_to_line_feature(feature: LineFeature, lat: float, lon: float) -> float:
    """Calculate minimum distance from a point to any segment in a line feature."""
    best = float("inf")
    for segment in feature.segments:
        distance = point_to_line_segment_distance(lat, lon, *segment)
        if distance < best:
            best = distance
            if best == 0:
                break
    return best if best != float("inf") else 9999.0


# Nearest neighbor search functions
def nearest_point(
    grid: SpatialGrid,
    features: Sequence[PointFeature],
    lat: float,
    lon: float,
    radius_km: float,
) -> Optional[Tuple[float, PointFeature]]:
    """
    Find the nearest point feature within a given radius.

    Args:
        grid: Spatial index
        features: List of all point features
        lat: Query latitude
        lon: Query longitude
        radius_km: Maximum search radius

    Returns:
        Tuple of (distance_km, feature) or None if no features found
    """
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


def nearest_line(
    grid: SpatialGrid,
    features: Sequence[LineFeature],
    lat: float,
    lon: float,
    radius_km: float,
) -> Optional[Tuple[float, LineFeature]]:
    """
    Find the nearest line feature within a given radius.

    Args:
        grid: Spatial index
        features: List of all line features
        lat: Query latitude
        lon: Query longitude
        radius_km: Maximum search radius

    Returns:
        Tuple of (distance_km, feature) or None if no features found
    """
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


# Proximity scoring function
def calculate_proximity_scores_for_catalog(
    project_lat: float,
    project_lon: float,
    substations: Sequence[PointFeature],
    substations_index: SpatialGrid,
    transmission_lines: Sequence[LineFeature],
    transmission_index: SpatialGrid,
    fiber_cables: Sequence[LineFeature],
    fiber_index: SpatialGrid,
    ixps: Sequence[PointFeature],
    ixp_index: SpatialGrid,
    water_points: Sequence[PointFeature],
    water_point_index: SpatialGrid,
    water_lines: Sequence[LineFeature],
    water_line_index: SpatialGrid,
) -> Dict[str, Any]:
    """
    Calculate proximity scores to all infrastructure types for a single location.

    Args:
        project_lat: Project latitude
        project_lon: Project longitude
        substations: List of substation point features
        substations_index: Spatial index for substations
        transmission_lines: List of transmission line features
        transmission_index: Spatial index for transmission lines
        fiber_cables: List of fiber cable features
        fiber_index: Spatial index for fiber cables
        ixps: List of internet exchange point features
        ixp_index: Spatial index for IXPs
        water_points: List of water point features
        water_point_index: Spatial index for water points
        water_lines: List of water line features
        water_line_index: Spatial index for water lines

    Returns:
        Dictionary with proximity scores and nearest distances
    """
    proximity_scores: Dict[str, Any] = {
        "substation_score": 0.0,
        "transmission_score": 0.0,
        "fiber_score": 0.0,
        "ixp_score": 0.0,
        "water_score": 0.0,
        "total_proximity_bonus": 0.0,
        "nearest_distances": {},
    }

    nearest_distances: Dict[str, float] = {}

    # Exponential scoring function (inline for this module)
    def exponential_score(distance_km: float, half_distance_km: float) -> float:
        if distance_km >= 200:
            return 0.0
        k = 0.693147 / half_distance_km
        score = 100 * (math.e ** (-k * distance_km))
        return max(0.0, min(100.0, score))

    # Find nearest substation
    substation = nearest_point(
        substations_index,
        substations,
        project_lat,
        project_lon,
        INFRASTRUCTURE_SEARCH_RADIUS_KM["substation"],
    )
    if substation:
        distance, _ = substation
        proximity_scores["substation_score"] = exponential_score(distance, 30.0)
        nearest_distances["substation_km"] = round(distance, 1)

    # Find nearest transmission line
    transmission = nearest_line(
        transmission_index,
        transmission_lines,
        project_lat,
        project_lon,
        INFRASTRUCTURE_SEARCH_RADIUS_KM["transmission"],
    )
    if transmission:
        distance, _ = transmission
        proximity_scores["transmission_score"] = exponential_score(distance, 30.0)
        nearest_distances["transmission_km"] = round(distance, 1)

    # Find nearest fiber cable
    fiber = nearest_line(
        fiber_index,
        fiber_cables,
        project_lat,
        project_lon,
        INFRASTRUCTURE_SEARCH_RADIUS_KM["fiber"],
    )
    if fiber:
        distance, _ = fiber
        proximity_scores["fiber_score"] = exponential_score(distance, 15.0)
        nearest_distances["fiber_km"] = round(distance, 1)

    # Find nearest IXP
    ixp = nearest_point(
        ixp_index,
        ixps,
        project_lat,
        project_lon,
        INFRASTRUCTURE_SEARCH_RADIUS_KM["ixp"],
    )
    if ixp:
        distance, _ = ixp
        proximity_scores["ixp_score"] = exponential_score(distance, 40.0)
        nearest_distances["ixp_km"] = round(distance, 1)

    # Find nearest water resource (point or line)
    water_point = nearest_point(
        water_point_index,
        water_points,
        project_lat,
        project_lon,
        INFRASTRUCTURE_SEARCH_RADIUS_KM["water"],
    )
    water_line = nearest_line(
        water_line_index,
        water_lines,
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

    return proximity_scores


__all__ = [
    "PointFeature",
    "LineFeature",
    "SpatialGrid",
    "haversine",
    "point_to_line_segment_distance",
    "nearest_point",
    "nearest_line",
    "calculate_proximity_scores_for_catalog",
    "INFRASTRUCTURE_SEARCH_RADIUS_KM",
    "KM_PER_DEGREE_LAT",
    "GRID_CELL_DEGREES",
]
