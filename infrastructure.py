"""Infrastructure caching and spatial indexing."""

from __future__ import annotations

import asyncio
import json
import math
import time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from config import GRID_CELL_DEGREES, INFRASTRUCTURE_CACHE_TTL_SECONDS, KM_PER_DEGREE_LAT
from database import query_supabase
from models import InfrastructureCatalog, LineFeature, PointFeature


# ============================================================================
# SPATIAL GRID INDEX
# ============================================================================


class SpatialGrid:
    """Spatial grid for efficient proximity queries."""

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


# ============================================================================
# INFRASTRUCTURE CACHE
# ============================================================================


class InfrastructureCache:
    """Cache for infrastructure data with automatic refresh."""

    def __init__(self) -> None:
        self._catalog: Optional[InfrastructureCatalog] = None
        self._lock = asyncio.Lock()
        self._last_loaded = 0.0

    async def get_catalog(self) -> InfrastructureCatalog:
        """Get infrastructure catalog, loading if necessary."""
        async with self._lock:
            if self._catalog and (time.time() - self._last_loaded) < INFRASTRUCTURE_CACHE_TTL_SECONDS:
                return self._catalog

            start = time.time()
            print("Loading infrastructure datasets from Supabase...")
            dataset_start = time.time()
            try:
                (
                    substations,
                    transmission_lines,
                    fiber_cables,
                    ixps,
                    water_resources,
                ) = await asyncio.gather(
                    query_supabase("substations?select=*"),
                    query_supabase("transmission_lines?select=*"),
                    query_supabase("fiber_cables?select=*", limit=200),
                    query_supabase("internet_exchange_points?select=*"),
                    query_supabase("water_resources?select=*"),
                )
            except Exception as exc:
                print(f"Error initializing infrastructure datasets: {exc}")
                raise
            print(
                f"[✓] Infrastructure datasets loaded in {time.time() - dataset_start:.2f}s"
            )

            print("Building infrastructure spatial indices...")
            build_start = time.time()
            catalog = self._build_catalog(
                substations or [],
                transmission_lines or [],
                fiber_cables or [],
                ixps or [],
                water_resources or [],
            )
            print(
                f"[✓] Infrastructure spatial indices built in {time.time() - build_start:.2f}s"
            )

            elapsed = time.time() - start
            print(
                "✅ Infrastructure catalog refreshed in "
                f"{elapsed:.2f}s (substations={catalog.counts['substations']}, "
                f"transmission={catalog.counts['transmission']}, fiber={catalog.counts['fiber']}, "
                f"ixp={catalog.counts['ixps']}, water={catalog.counts['water']})"
            )

            self._catalog = catalog
            self._last_loaded = time.time()
            return catalog

    def _build_catalog(
        self,
        substations: Sequence[Dict[str, Any]],
        transmission_lines: Sequence[Dict[str, Any]],
        fiber_cables: Sequence[Dict[str, Any]],
        ixps: Sequence[Dict[str, Any]],
        water_resources: Sequence[Dict[str, Any]],
    ) -> InfrastructureCatalog:
        """Build infrastructure catalog with spatial indices."""
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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _coerce_float(value: Any) -> Optional[float]:
    """Coerce value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _prepare_line_feature(raw_geometry: Any, payload: Dict[str, Any]) -> Optional[LineFeature]:
    """Prepare a line feature from raw geometry data."""
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
        lon = _coerce_float(entry[0])
        lat = _coerce_float(entry[1])
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


def _prepare_water_feature(raw_geometry: Any, payload: Dict[str, Any]) -> Optional[Any]:
    """Prepare a water feature (point or line) from raw geometry data."""
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
        lat_f = _coerce_float(lat)
        lon_f = _coerce_float(lon)
        if lat_f is None or lon_f is None:
            return None
        return PointFeature(lat=lat_f, lon=lon_f, data=payload)

    if isinstance(raw_geometry, list):
        feature = _prepare_line_feature(raw_geometry, payload)
        if feature:
            return feature

    return None


# ============================================================================
# INFRASTRUCTURE SEARCH CONFIGURATION
# ============================================================================

INFRASTRUCTURE_SEARCH_RADIUS_KM = {
    "substation": 100.0,
    "transmission": 100.0,
    "fiber": 100.0,
    "ixp": 100.0,
    "water": 100.0,
}


INFRASTRUCTURE_HALF_DISTANCE_KM = {
    "substation": 50.0,
    "transmission": 50.0,
    "fiber": 25.0,
    "ixp": 25.0,
    "water": 25.0,
}


def _grid_steps_for_radius(grid: SpatialGrid, radius_km: float) -> int:
    """Calculate grid steps needed for a given search radius."""
    cell_width_km = max(1.0, grid.approximate_cell_width_km())
    return max(1, int(math.ceil(radius_km / cell_width_km)) + 1)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

print("Initializing infrastructure cache subsystem...")
INFRASTRUCTURE_CACHE = InfrastructureCache()
print("[✓] Infrastructure cache subsystem ready")
