"""Infrastructure spatial data structures."""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from core.config import get_settings

KM_PER_DEGREE_LAT = 111.32
GRID_CELL_DEGREES = 0.5


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


__all__ = [
    "GRID_CELL_DEGREES",
    "InfrastructureCatalog",
    "LineFeature",
    "PointFeature",
    "SpatialGrid",
]
