from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from backend.dc_workflow import (
    PersonaType,
    calculate_persona_weighted_score,
    get_color_from_score,
    get_rating_description,
)

KM_PER_DEGREE_LAT = 111.32
GRID_CELL_DEGREES = 0.5

INFRASTRUCTURE_SEARCH_RADIUS_KM: Dict[str, float] = {
    "substation": 100.0,
    "transmission": 100.0,
    "fiber": 100.0,
    "ixp": 100.0,
    "water": 100.0,
}


@dataclass
class PointFeature:
    lat: float
    lon: float
    data: Dict[str, Any]


@dataclass
class LineFeature:
    coordinates: List[Tuple[float, float]]
    segments: List[Tuple[float, float, float, float]]
    bbox: Tuple[float, float, float, float]
    data: Dict[str, Any]


@dataclass
class InfrastructureCatalog:
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
    def __init__(self, cell_size_deg: float = GRID_CELL_DEGREES) -> None:
        self.cell_size_deg = cell_size_deg
        self._cells: Dict[Tuple[int, int], List[Any]] = defaultdict(list)

    def _index_lat(self, lat: float) -> int:
        return int(math.floor((lat + 90.0) / self.cell_size_deg))

    def _index_lon(self, lon: float) -> int:
        return int(math.floor((lon + 180.0) / self.cell_size_deg))

    def add_point(self, feature: PointFeature) -> None:
        key = (self._index_lat(feature.lat), self._index_lon(feature.lon))
        self._cells[key].append(feature)

    def add_bbox(self, bbox: Tuple[float, float, float, float], feature: LineFeature) -> None:
        min_lat, min_lon, max_lat, max_lon = bbox
        lat_start = self._index_lat(min_lat)
        lat_end = self._index_lat(max_lat)
        lon_start = self._index_lon(min_lon)
        lon_end = self._index_lon(max_lon)
        for lat_idx in range(lat_start, lat_end + 1):
            for lon_idx in range(lon_start, lon_end + 1):
                self._cells[(lat_idx, lon_idx)].append(feature)

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


def coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def prepare_line_feature(raw_geometry: Any, payload: Dict[str, Any]) -> Optional[LineFeature]:
    if not raw_geometry:
        return None
    if isinstance(raw_geometry, str):
        try:
            raw_geometry = json.loads(raw_geometry)
        except json.JSONDecodeError:
            return None

    if not isinstance(raw_geometry, list) or len(raw_geometry) < 2:
        return None

    coordinates: List[Tuple[float, float]] = []
    for entry in raw_geometry:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        lon = coerce_float(entry[0])
        lat = coerce_float(entry[1])
        if lat is None or lon is None:
            continue
        coordinates.append((lat, lon))

    if len(coordinates) < 2:
        return None

    min_lat = min(lat for lat, _ in coordinates)
    max_lat = max(lat for lat, _ in coordinates)
    min_lon = min(lon for _, lon in coordinates)
    max_lon = max(lon for _, lon in coordinates)

    segments = [
        (coordinates[i][0], coordinates[i][1], coordinates[i + 1][0], coordinates[i + 1][1])
        for i in range(len(coordinates) - 1)
    ]

    return LineFeature(
        coordinates=coordinates,
        segments=segments,
        bbox=(min_lat, min_lon, max_lat, max_lon),
        data=payload,
    )


def prepare_water_feature(raw_geometry: Any, payload: Dict[str, Any]) -> Optional[Any]:
    if not raw_geometry:
        return None
    if isinstance(raw_geometry, str):
        try:
            raw_geometry = json.loads(raw_geometry)
        except json.JSONDecodeError:
            return None

    if isinstance(raw_geometry, (list, tuple)) and len(raw_geometry) == 2 and all(
        isinstance(coord, (int, float)) for coord in raw_geometry
    ):
        lon, lat = raw_geometry
        lat_f = coerce_float(lat)
        lon_f = coerce_float(lon)
        if lat_f is None or lon_f is None:
            return None
        return PointFeature(lat=lat_f, lon=lon_f, data=payload)

    if isinstance(raw_geometry, list):
        feature = prepare_line_feature(raw_geometry, payload)
        if feature:
            return feature

    return None


def build_infrastructure_catalog(
    substations: Sequence[Dict[str, Any]],
    transmission_lines: Sequence[Dict[str, Any]],
    fiber_cables: Sequence[Dict[str, Any]],
    ixps: Sequence[Dict[str, Any]],
    water_resources: Sequence[Dict[str, Any]],
) -> InfrastructureCatalog:
    substation_features: List[PointFeature] = []
    transmission_features: List[LineFeature] = []
    fiber_features: List[LineFeature] = []
    ixp_features: List[PointFeature] = []
    water_point_features: List[PointFeature] = []
    water_line_features: List[LineFeature] = []

    substation_index = SpatialGrid()
    transmission_index = SpatialGrid()
    fiber_index = SpatialGrid()
    ixp_index = SpatialGrid()
    water_point_index = SpatialGrid()
    water_line_index = SpatialGrid()

    for station in substations:
        lat = coerce_float(station.get("Lat") or station.get("latitude"))
        lon = coerce_float(station.get("Long") or station.get("longitude"))
        if lat is None or lon is None:
            continue
        feature = PointFeature(lat=lat, lon=lon, data=station)
        substation_features.append(feature)
        substation_index.add_point(feature)

    for line in transmission_lines:
        feature = prepare_line_feature(line.get("path_coordinates"), line)
        if feature:
            transmission_features.append(feature)
            transmission_index.add_bbox(feature.bbox, feature)

    for cable in fiber_cables:
        feature = prepare_line_feature(cable.get("route_coordinates"), cable)
        if feature:
            fiber_features.append(feature)
            fiber_index.add_bbox(feature.bbox, feature)

    for ixp in ixps:
        lat = coerce_float(ixp.get("latitude"))
        lon = coerce_float(ixp.get("longitude"))
        if lat is None or lon is None:
            continue
        feature = PointFeature(lat=lat, lon=lon, data=ixp)
        ixp_features.append(feature)
        ixp_index.add_point(feature)

    for water in water_resources:
        prepared = prepare_water_feature(water.get("coordinates"), water)
        if isinstance(prepared, PointFeature):
            water_point_features.append(prepared)
            water_point_index.add_point(prepared)
        elif isinstance(prepared, LineFeature):
            water_line_features.append(prepared)
            water_line_index.add_bbox(prepared.bbox, prepared)

    return InfrastructureCatalog(
        substations=substation_features,
        transmission_lines=transmission_features,
        fiber_cables=fiber_features,
        internet_exchange_points=ixp_features,
        water_points=water_point_features,
        water_lines=water_line_features,
        substations_index=substation_index,
        transmission_index=transmission_index,
        fiber_index=fiber_index,
        ixp_index=ixp_index,
        water_point_index=water_point_index,
        water_line_index=water_line_index,
        load_timestamp=time.time(),
        counts={
            "substations": len(substation_features),
            "transmission": len(transmission_features),
            "fiber": len(fiber_features),
            "ixps": len(ixp_features),
            "water": len(water_point_features) + len(water_line_features),
        },
    )


def grid_steps_for_radius(grid: SpatialGrid, radius_km: float) -> int:
    cell_width_km = max(1.0, grid.approximate_cell_width_km())
    return max(1, int(math.ceil(radius_km / cell_width_km)) + 1)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def exponential_score(distance_km: float, half_distance_km: float) -> float:
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
    param = -1.0
    if len_sq != 0:
        param = dot / len_sq

    if param < 0:
        xx, yy = x1, y1
    elif param > 1:
        xx, yy = x2, y2
    else:
        xx = x1 + param * c
        yy = y1 + param * d

    dx = px - xx
    dy = py - yy
    return math.sqrt(dx * dx + dy * dy)


def bbox_within_search(
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
    steps = grid_steps_for_radius(grid, radius_km)
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
    best: Optional[Tuple[float, LineFeature]] = None
    steps = grid_steps_for_radius(grid, radius_km)
    for step in range(1, steps + 2):
        for feature in grid.query(lat, lon, step):
            if not isinstance(feature, LineFeature):
                continue
            if not bbox_within_search(feature.bbox, lat, lon, radius_km):
                continue
            distance = distance_to_line_feature(feature, lat, lon)
            if distance > radius_km:
                continue
            if not best or distance < best[0]:
                best = (distance, feature)
        if best:
            break

    if not best and features:
        for feature in features:
            if not bbox_within_search(feature.bbox, lat, lon, radius_km):
                continue
            distance = distance_to_line_feature(feature, lat, lon)
            if not best or distance < best[0]:
                best = (distance, feature)
    return best


def distance_to_line_feature(feature: LineFeature, lat: float, lon: float) -> float:
    best = float("inf")
    for segment in feature.segments:
        distance = point_to_line_segment_distance(lat, lon, *segment)
        if distance < best:
            best = distance
            if best == 0:
                break
    return best if best != float("inf") else 9999.0


def calculate_proximity_scores_for_catalog(
    projects: Sequence[Dict[str, Any]],
    catalog: InfrastructureCatalog,
    *,
    search_radii_km: Optional[Mapping[str, float]] = None,
) -> List[Dict[str, float]]:
    if not projects:
        return []

    radii = dict(INFRASTRUCTURE_SEARCH_RADIUS_KM)
    if search_radii_km:
        radii.update(search_radii_km)

    results: List[Dict[str, float]] = []
    for project in projects:
        project_lat = coerce_float(project.get("latitude"))
        project_lon = coerce_float(project.get("longitude"))
        if project_lat is None or project_lon is None:
            continue

        proximity_scores: Dict[str, float] = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
        }
        nearest_distances: Dict[str, float] = {}

        substation = nearest_point(
            catalog.substations_index,
            catalog.substations,
            project_lat,
            project_lon,
            radii["substation"],
        )
        if substation:
            distance, _ = substation
            proximity_scores["substation_score"] = exponential_score(distance, 30.0)
            nearest_distances["substation_km"] = round(distance, 1)

        transmission = nearest_line(
            catalog.transmission_index,
            catalog.transmission_lines,
            project_lat,
            project_lon,
            radii["transmission"],
        )
        if transmission:
            distance, _ = transmission
            proximity_scores["transmission_score"] = exponential_score(distance, 30.0)
            nearest_distances["transmission_km"] = round(distance, 1)

        fiber = nearest_line(
            catalog.fiber_index,
            catalog.fiber_cables,
            project_lat,
            project_lon,
            radii["fiber"],
        )
        if fiber:
            distance, _ = fiber
            proximity_scores["fiber_score"] = exponential_score(distance, 15.0)
            nearest_distances["fiber_km"] = round(distance, 1)

        ixp = nearest_point(
            catalog.ixp_index,
            catalog.internet_exchange_points,
            project_lat,
            project_lon,
            radii["ixp"],
        )
        if ixp:
            distance, _ = ixp
            proximity_scores["ixp_score"] = exponential_score(distance, 40.0)
            nearest_distances["ixp_km"] = round(distance, 1)

        water_point = nearest_point(
            catalog.water_point_index,
            catalog.water_points,
            project_lat,
            project_lon,
            radii["water"],
        )
        water_line = nearest_line(
            catalog.water_line_index,
            catalog.water_lines,
            project_lat,
            project_lon,
            radii["water"],
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

        results.append(proximity_scores)

    return results


def calculate_enhanced_investment_rating(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    persona: Optional[PersonaType] = None,
) -> Dict[str, Any]:
    if persona is not None:
        return calculate_persona_weighted_score(project, proximity_scores, persona)

    base_score = calculate_base_investment_score_renewable(project)
    infrastructure_bonus = calculate_infrastructure_bonus_renewable(proximity_scores)
    total_internal_score = min(100.0, base_score + infrastructure_bonus)
    display_rating = total_internal_score / 10.0
    color = get_color_from_score(total_internal_score)
    description = get_rating_description(total_internal_score)

    return {
        "base_investment_score": round(base_score / 10.0, 1),
        "infrastructure_bonus": round(infrastructure_bonus / 10.0, 1),
        "investment_rating": round(display_rating, 1),
        "rating_description": description,
        "color_code": color,
        "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
        "internal_total_score": round(total_internal_score, 1),
        "scoring_methodology": "Traditional renewable energy scoring (10-100 internal, 1.0-10.0 display)",
    }


def calculate_base_investment_score_renewable(project: Dict[str, Any]) -> float:
    capacity_score = min(40.0, (float(project.get("capacity_mw", 0.0)) or 0.0) * 2.0)
    status_score_lookup = {
        "Scoping": 20.0,
        "In Planning": 30.0,
        "Awaiting Construction": 40.0,
        "Under Construction": 50.0,
        "Operational": 60.0,
    }
    status_score = status_score_lookup.get(project.get("development_status"), 25.0)
    grid_connection_score = 15.0 if project.get("grid_connection") else 5.0
    technology_score_lookup = {
        "Solar": 15.0,
        "Wind": 20.0,
        "Hydro": 18.0,
        "Battery": 12.0,
    }
    technology_score = technology_score_lookup.get(project.get("technology_type"), 10.0)

    return capacity_score + status_score + grid_connection_score + technology_score


def calculate_infrastructure_bonus_renewable(proximity_scores: Dict[str, float]) -> float:
    return (
        proximity_scores.get("substation_score", 0.0)
        + proximity_scores.get("transmission_score", 0.0)
        + proximity_scores.get("fiber_score", 0.0)
        + proximity_scores.get("ixp_score", 0.0)
        + proximity_scores.get("water_score", 0.0)
    )


def calculate_rating_distribution(features: List[Dict[str, Any]]) -> Dict[str, int]:
    distribution = {
        "excellent": 0,
        "very_good": 0,
        "good": 0,
        "above_average": 0,
        "average": 0,
        "below_average": 0,
        "poor": 0,
        "very_poor": 0,
        "bad": 0,
    }
    for feature in features:
        rating = feature.get("properties", {}).get("investment_rating", 0)
        if rating >= 9.0:
            distribution["excellent"] += 1
        elif rating >= 8.0:
            distribution["very_good"] += 1
        elif rating >= 7.0:
            distribution["good"] += 1
        elif rating >= 6.0:
            distribution["above_average"] += 1
        elif rating >= 5.0:
            distribution["average"] += 1
        elif rating >= 4.0:
            distribution["below_average"] += 1
        elif rating >= 3.0:
            distribution["poor"] += 1
        elif rating >= 2.0:
            distribution["very_poor"] += 1
        else:
            distribution["bad"] += 1
    return distribution


__all__ = [
    "GRID_CELL_DEGREES",
    "INFRASTRUCTURE_SEARCH_RADIUS_KM",
    "InfrastructureCatalog",
    "LineFeature",
    "PointFeature",
    "SpatialGrid",
    "calculate_enhanced_investment_rating",
    "calculate_proximity_scores_for_catalog",
    "calculate_rating_distribution",
    "coerce_float",
    "prepare_line_feature",
    "prepare_water_feature",
    "build_infrastructure_catalog",
    "grid_steps_for_radius",
    "haversine",
    "exponential_score",
    "point_to_line_segment_distance",
    "bbox_within_search",
    "nearest_point",
    "nearest_line",
    "distance_to_line_feature",
    "calculate_base_investment_score_renewable",
    "calculate_infrastructure_bonus_renewable",
]
