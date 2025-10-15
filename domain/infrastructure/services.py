"""Infrastructure catalog loading and spatial utilities."""
from __future__ import annotations

import asyncio
import math
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from core.clients.supabase import SupabaseClient
from core.config import get_settings
from .models import (
    GRID_CELL_DEGREES,
    InfrastructureCatalog,
    LineFeature,
    PointFeature,
    SpatialGrid,
)


def _coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _prepare_line_feature(
    raw_geometry: Any, payload: Dict[str, Any]
) -> Optional[LineFeature]:
    if not raw_geometry:
        return None

    coordinates: List[Tuple[float, float]] = []
    segments: List[Tuple[float, float, float, float]] = []

    for segment in raw_geometry:
        if not isinstance(segment, list):
            continue
        parsed_segment: List[Tuple[float, float]] = []
        for coord in segment:
            if not isinstance(coord, (list, tuple)) or len(coord) != 2:
                continue
            lat, lon = coord
            parsed_segment.append((float(lat), float(lon)))
        if parsed_segment:
            coordinates.extend(parsed_segment)
            for idx in range(len(parsed_segment) - 1):
                lat1, lon1 = parsed_segment[idx]
                lat2, lon2 = parsed_segment[idx + 1]
                segments.append((lat1, lon1, lat2, lon2))

    if not coordinates:
        return None

    lats = [lat for lat, _ in coordinates]
    lons = [lon for _, lon in coordinates]
    bbox = (min(lats), min(lons), max(lats), max(lons))

    return LineFeature(coordinates=coordinates, segments=segments, bbox=bbox, data=payload)


def _prepare_water_feature(raw_geometry: Any, payload: Dict[str, Any]) -> Optional[Any]:
    if isinstance(raw_geometry, dict) and raw_geometry.get("type") == "Point":
        coordinates = raw_geometry.get("coordinates", [])
        if len(coordinates) == 2:
            return PointFeature(lat=float(coordinates[1]), lon=float(coordinates[0]), data=payload)
    elif isinstance(raw_geometry, dict) and raw_geometry.get("type") == "LineString":
        coords = raw_geometry.get("coordinates", [])
        if coords:
            segments = []
            for idx in range(len(coords) - 1):
                (lon1, lat1), (lon2, lat2) = coords[idx], coords[idx + 1]
                segments.append((float(lat1), float(lon1), float(lat2), float(lon2)))
            lats = [float(lat) for _, lat in coords]
            lons = [float(lon) for lon, _ in coords]
            bbox = (min(lats), min(lons), max(lats), max(lons))
            coordinates = [(float(lat), float(lon)) for lon, lat in coords]
            return LineFeature(coordinates=coordinates, segments=segments, bbox=bbox, data=payload)
    return None


def _grid_steps_for_radius(grid: SpatialGrid, radius_km: float) -> int:
    approx_cell_width = grid.approximate_cell_width_km()
    return max(1, math.ceil(radius_km / approx_cell_width))


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def exponential_score(distance_km: float, half_distance_km: float) -> float:
    if distance_km <= 0:
        return 1.0
    return math.exp(-math.log(2) * (distance_km / half_distance_km))


def point_to_line_segment_distance(
    lat: float,
    lon: float,
    segment: Tuple[float, float, float, float],
) -> float:
    lat1, lon1, lat2, lon2 = segment
    a = haversine(lat1, lon1, lat2, lon2)
    if a == 0:
        return haversine(lat, lon, lat1, lon1)

    b = haversine(lat, lon, lat1, lon1)
    c = haversine(lat, lon, lat2, lon2)
    cos_angle = (b**2 + c**2 - a**2) / (2 * b * c)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    angle = math.acos(cos_angle)
    return min(b, c, abs(math.sin(angle) * b))


def _bbox_within_search(
    bbox: Tuple[float, float, float, float],
    lat: float,
    lon: float,
    radius_km: float,
) -> bool:
    min_lat, min_lon, max_lat, max_lon = bbox
    corners = [
        (min_lat, min_lon),
        (min_lat, max_lon),
        (max_lat, min_lon),
        (max_lat, max_lon),
    ]
    return any(haversine(lat, lon, corner_lat, corner_lon) <= radius_km for corner_lat, corner_lon in corners)


def _nearest_point(
    index: SpatialGrid,
    lat: float,
    lon: float,
    radius_km: float,
) -> Tuple[Optional[PointFeature], Optional[float]]:
    steps = _grid_steps_for_radius(index, radius_km)
    nearest_feature: Optional[PointFeature] = None
    nearest_distance: Optional[float] = None
    for feature in index.query(lat, lon, steps):
        if not isinstance(feature, PointFeature):
            continue
        distance = haversine(lat, lon, feature.lat, feature.lon)
        if distance <= radius_km and (nearest_distance is None or distance < nearest_distance):
            nearest_feature = feature
            nearest_distance = distance
    return nearest_feature, nearest_distance


def _nearest_line(
    index: SpatialGrid,
    lat: float,
    lon: float,
    radius_km: float,
) -> Tuple[Optional[LineFeature], Optional[float]]:
    steps = _grid_steps_for_radius(index, radius_km)
    nearest_feature: Optional[LineFeature] = None
    nearest_distance: Optional[float] = None
    for feature in index.query(lat, lon, steps):
        if not isinstance(feature, LineFeature):
            continue
        if not _bbox_within_search(feature.bbox, lat, lon, radius_km):
            continue
        for segment in feature.segments:
            distance = point_to_line_segment_distance(lat, lon, segment)
            if distance <= radius_km and (nearest_distance is None or distance < nearest_distance):
                nearest_feature = feature
                nearest_distance = distance
    return nearest_feature, nearest_distance


def _distance_to_line_feature(feature: LineFeature, lat: float, lon: float) -> float:
    return min(point_to_line_segment_distance(lat, lon, segment) for segment in feature.segments)


class InfrastructureCache:
    def __init__(self) -> None:
        self._catalog: Optional[InfrastructureCatalog] = None
        self._lock = asyncio.Lock()
        self._last_loaded = 0.0
        self._settings = get_settings()
        self._supabase = SupabaseClient()

    async def get_catalog(self) -> InfrastructureCatalog:
        async with self._lock:
            ttl = self._settings.infra_cache_ttl
            if self._catalog and (time.time() - self._last_loaded) < ttl:
                return self._catalog

            start = time.time()
            (
                substations,
                transmission_lines,
                fiber_cables,
                ixps,
                water_resources,
            ) = await asyncio.gather(
                self._supabase.fetch("substations?select=*"),
                self._supabase.fetch("transmission_lines?select=*"),
                self._supabase.fetch("fiber_cables?select=*&limit=200"),
                self._supabase.fetch("internet_exchange_points?select=*"),
                self._supabase.fetch("water_resources?select=*"),
            )

            catalog = self._build_catalog(
                substations or [],
                transmission_lines or [],
                fiber_cables or [],
                ixps or [],
                water_resources or [],
            )
            self._catalog = catalog
            self._last_loaded = time.time()
            elapsed = self._last_loaded - start
            print(
                "✅ Infrastructure catalog refreshed in "
                f"{elapsed:.2f}s (substations={catalog.counts['substations']}, "
                f"transmission={catalog.counts['transmission']}, fiber={catalog.counts['fiber']}, "
                f"ixp={catalog.counts['ixps']}, water={catalog.counts['water']})"
            )
            return catalog

    def _build_catalog(
        self,
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
            lat = _coerce_float(station.get("Lat") or station.get("latitude"))
            lon = _coerce_float(station.get("Long") or station.get("longitude"))
            if lat is None or lon is None:
                continue
            feature = PointFeature(lat=lat, lon=lon, data=station)
            substation_features.append(feature)
            substation_index.add_point(feature)

        for line in transmission_lines:
            feature = _prepare_line_feature(line.get("path_coordinates"), line)
            if feature:
                transmission_features.append(feature)
                transmission_index.add_bbox(feature.bbox, feature)

        for cable in fiber_cables:
            feature = _prepare_line_feature(cable.get("route_coordinates"), cable)
            if feature:
                fiber_features.append(feature)
                fiber_index.add_bbox(feature.bbox, feature)

        for ixp in ixps:
            lat = _coerce_float(ixp.get("latitude"))
            lon = _coerce_float(ixp.get("longitude"))
            if lat is None or lon is None:
                continue
            feature = PointFeature(lat=lat, lon=lon, data=ixp)
            ixp_features.append(feature)
            ixp_index.add_point(feature)

        for water in water_resources:
            prepared = _prepare_water_feature(water.get("coordinates"), water)
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


__all__ = [
    "InfrastructureCache",
    "_distance_to_line_feature",
    "_nearest_line",
    "_nearest_point",
    "exponential_score",
    "haversine",
]
