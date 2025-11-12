"""Shared proximity algorithms and spatial indexing utilities.

This module centralizes reusable geospatial helpers so both the data centre
and power workflows can reason about infrastructure distances without
duplicating algorithms.  It deliberately stays stateless – callers must supply
catalog data and configuration when invoking the helpers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


KM_PER_DEGREE_LAT = 111.32
DEFAULT_GRID_CELL_DEGREES = 0.5


@dataclass
class PointFeature:
    """Simple container for point-based infrastructure features."""

    lat: float
    lon: float
    data: Dict[str, Any]


@dataclass
class LineFeature:
    """Container for line or polyline infrastructure features."""

    coordinates: List[Tuple[float, float]]
    segments: List[Tuple[float, float, float, float]]
    bbox: Tuple[float, float, float, float]
    data: Dict[str, Any]


@dataclass
class InfrastructureCatalog:
    """Spatially indexed infrastructure features reused across workflows."""

    substations: List[PointFeature]
    transmission_lines: List[LineFeature]
    fiber_cables: List[LineFeature]
    internet_exchange_points: List[PointFeature]
    water_points: List[PointFeature]
    water_lines: List[LineFeature]
    substations_index: "SpatialGrid"
    transmission_index: "SpatialGrid"
    fiber_index: "SpatialGrid"
    ixp_index: "SpatialGrid"
    water_point_index: "SpatialGrid"
    water_line_index: "SpatialGrid"
    load_timestamp: float
    counts: Dict[str, int]


class SpatialGrid:
    """Lightweight spatial index for proximity lookups."""

    def __init__(self, cell_size_deg: float = DEFAULT_GRID_CELL_DEGREES) -> None:
        self.cell_size_deg = cell_size_deg
        self._cells: Dict[Tuple[int, int], List[Any]] = {}

    def _index_lat(self, lat: float) -> int:
        return int(math.floor((lat + 90.0) / self.cell_size_deg))

    def _index_lon(self, lon: float) -> int:
        return int(math.floor((lon + 180.0) / self.cell_size_deg))

    def add_point(self, feature: PointFeature) -> None:
        key = (self._index_lat(feature.lat), self._index_lon(feature.lon))
        self._cells.setdefault(key, []).append(feature)

    def add_bbox(self, bbox: Tuple[float, float, float, float], feature: LineFeature) -> None:
        min_lat, min_lon, max_lat, max_lon = bbox
        lat_start = self._index_lat(min_lat)
        lat_end = self._index_lat(max_lat)
        lon_start = self._index_lon(min_lon)
        lon_end = self._index_lon(max_lon)
        for lat_idx in range(lat_start, lat_end + 1):
            for lon_idx in range(lon_start, lon_end + 1):
                self._cells.setdefault((lat_idx, lon_idx), []).append(feature)

    def query(self, lat: float, lon: float, steps: int) -> Iterable[Any]:
        base_lat = self._index_lat(lat)
        base_lon = self._index_lon(lon)
        seen: set[int] = set()
        for lat_offset in range(-steps, steps + 1):
            for lon_offset in range(-steps, steps + 1):
                cell = (base_lat + lat_offset, base_lon + lon_offset)
                for feature in self._cells.get(cell, ()):  # type: ignore[arg-type]
                    feature_id = id(feature)
                    if feature_id not in seen:
                        seen.add(feature_id)
                        yield feature

    def approximate_cell_width_km(self) -> float:
        return self.cell_size_deg * KM_PER_DEGREE_LAT


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in kilometres between two points."""

    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def exponential_score(distance_km: float, half_distance_km: float) -> float:
    """Utility scoring curve that halves every ``half_distance_km`` kilometres."""

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


def _grid_steps_for_radius(grid: SpatialGrid, radius_km: float) -> int:
    cell_width_km = max(1.0, grid.approximate_cell_width_km())
    return max(1, int(math.ceil(radius_km / cell_width_km)) + 1)


def _bbox_within_search(
    bbox: Tuple[float, float, float, float],
    lat: float,
    lon: float,
    radius_km: float,
) -> bool:
    min_lat, min_lon, max_lat, max_lon = bbox
    lat_margin = radius_km / KM_PER_DEGREE_LAT
    lon_margin = radius_km / (KM_PER_DEGREE_LAT * max(math.cos(math.radians(lat)), 0.2))
    return not (
        lat < min_lat - lat_margin
        or lat > max_lat + lat_margin
        or lon < min_lon - lon_margin
        or lon > max_lon + lon_margin
    )


def nearest_point(
    grid: SpatialGrid,
    features: Sequence[PointFeature],
    lat: float,
    lon: float,
    radius_km: float,
) -> Optional[Tuple[float, PointFeature]]:
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


def _distance_to_line_feature(feature: LineFeature, lat: float, lon: float) -> float:
    best = float("inf")
    for segment in feature.segments:
        distance = point_to_line_segment_distance(lat, lon, *segment)
        if distance < best:
            best = distance
            if best == 0:
                break
    return best if best != float("inf") else 9999.0


def nearest_line(
    grid: SpatialGrid,
    features: Sequence[LineFeature],
    lat: float,
    lon: float,
    radius_km: float,
) -> Optional[Tuple[float, LineFeature]]:
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


def calculate_proximity_scores(
    catalog: InfrastructureCatalog,
    lat: float,
    lon: float,
    search_radius_km: Dict[str, float],
    half_distance_km: Dict[str, float],
) -> Dict[str, float]:
    """Return proximity scores and nearest distances for a project location."""

    proximity_scores: Dict[str, float] = {
        "substation_score": 0.0,
        "transmission_score": 0.0,
        "fiber_score": 0.0,
        "ixp_score": 0.0,
        "water_score": 0.0,
        "total_proximity_bonus": 0.0,
    }
    nearest_distances: Dict[str, float] = {}

    substation = nearest_point(
        catalog.substations_index,
        catalog.substations,
        lat,
        lon,
        search_radius_km.get("substation", 0.0),
    )
    if substation:
        distance, _ = substation
        proximity_scores["substation_score"] = exponential_score(
            distance, half_distance_km.get("substation", 30.0)
        )
        nearest_distances["substation_km"] = round(distance, 1)

    transmission = nearest_line(
        catalog.transmission_index,
        catalog.transmission_lines,
        lat,
        lon,
        search_radius_km.get("transmission", 0.0),
    )
    if transmission:
        distance, _ = transmission
        proximity_scores["transmission_score"] = exponential_score(
            distance, half_distance_km.get("transmission", 30.0)
        )
        nearest_distances["transmission_km"] = round(distance, 1)

    fiber = nearest_line(
        catalog.fiber_index,
        catalog.fiber_cables,
        lat,
        lon,
        search_radius_km.get("fiber", 0.0),
    )
    if fiber:
        distance, _ = fiber
        proximity_scores["fiber_score"] = exponential_score(
            distance, half_distance_km.get("fiber", 30.0)
        )
        nearest_distances["fiber_km"] = round(distance, 1)

    ixp = nearest_point(
        catalog.ixp_index,
        catalog.internet_exchange_points,
        lat,
        lon,
        search_radius_km.get("ixp", 0.0),
    )
    if ixp:
        distance, _ = ixp
        proximity_scores["ixp_score"] = exponential_score(
            distance, half_distance_km.get("ixp", 30.0)
        )
        nearest_distances["ixp_km"] = round(distance, 1)

    water_point = nearest_point(
        catalog.water_point_index,
        catalog.water_points,
        lat,
        lon,
        search_radius_km.get("water", 0.0),
    )
    water_line = nearest_line(
        catalog.water_line_index,
        catalog.water_lines,
        lat,
        lon,
        search_radius_km.get("water", 0.0),
    )

    water_candidates: List[Tuple[float, str]] = []
    if water_point:
        water_candidates.append((water_point[0], "water_point"))
    if water_line:
        water_candidates.append((water_line[0], "water_line"))
    if water_candidates:
        distance, _ = min(water_candidates, key=lambda item: item[0])
        proximity_scores["water_score"] = exponential_score(
            distance, half_distance_km.get("water", 25.0)
        )
        nearest_distances["water_km"] = round(distance, 1)

    proximity_scores["nearest_distances"] = nearest_distances  # type: ignore[assignment]
    proximity_scores["total_proximity_bonus"] = (
        proximity_scores["substation_score"]
        + proximity_scores["transmission_score"]
        + proximity_scores["fiber_score"]
        + proximity_scores["ixp_score"]
        + proximity_scores["water_score"]
    )

    return proximity_scores

