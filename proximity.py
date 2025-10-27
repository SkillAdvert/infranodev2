"""Proximity calculations and distance functions."""

from __future__ import annotations

import math
from typing import Optional, Sequence, Tuple

from config import KM_PER_DEGREE_LAT
from infrastructure import SpatialGrid, _grid_steps_for_radius
from models import LineFeature, PointFeature


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points using Haversine formula.

    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point

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


def exponential_score(distance_km: float, half_distance_km: float) -> float:
    """Calculate exponential decay score based on distance.

    Args:
        distance_km: Distance in kilometers
        half_distance_km: Distance at which score is 50

    Returns:
        Score from 0-100
    """
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
    """Calculate minimum distance from point to line segment.

    Args:
        px, py: Point coordinates
        x1, y1: Line segment start
        x2, y2: Line segment end

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


def _bbox_within_search(
    bbox: Tuple[float, float, float, float],
    lat: float,
    lon: float,
    radius_km: float,
) -> bool:
    """Check if bounding box is within search radius."""
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
    """Find nearest point feature within radius."""
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
    """Find nearest line feature within radius."""
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
    """Calculate minimum distance from point to line feature."""
    best = float("inf")
    for segment in feature.segments:
        distance = point_to_line_segment_distance(lat, lon, *segment)
        if distance < best:
            best = distance
            if best == 0:
                break
    return best if best != float("inf") else 9999.0


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_color_from_score(score_out_of_100: float) -> str:
    """Get hex color based on score (0-100)."""
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
    """Get textual rating description based on score (0-100)."""
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
