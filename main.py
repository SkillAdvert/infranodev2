from __future__ import annotations

import asyncio
import json
import math
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Tuple

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

try:
    from backend.renewable_model import (
        FinancialAssumptions,
        MarketPrices,
        ProjectType,
        RenewableFinancialModel,
        TechnologyParams,
        TechnologyType,
        MarketRegion,
    )

    FINANCIAL_MODEL_AVAILABLE = True
    print("✅ Financial model imported successfully")
except ImportError as exc:  # pragma: no cover - handled dynamically at runtime
    print(f"⚠️ Financial model not available: {exc}")
    FINANCIAL_MODEL_AVAILABLE = False

app = FastAPI(title="Infranodal API", version="2.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

print(f"✅ SUPABASE_URL: {SUPABASE_URL}")
print(f"✅ SUPABASE_KEY exists: {bool(SUPABASE_KEY)}")

PersonaType = Literal["hyperscaler", "colocation", "edge_computing"]

KM_PER_DEGREE_LAT = 111.32
INFRASTRUCTURE_CACHE_TTL_SECONDS = int(os.getenv("INFRA_CACHE_TTL", "600"))
GRID_CELL_DEGREES = 0.5

# Updated persona weights with LCOE
PERSONA_WEIGHTS: Dict[str, Dict[str, float]] = {
    "hyperscaler": {
        "capacity": 0.25,
        "development_stage": 0.20,
        "technology": 0.08,
        "grid_infrastructure": 0.12,
        "digital_infrastructure": 0.05,
        "water_resources": 0.05,
        "tnuos_transmission_costs": 0.12,
        "lcoe_resource_quality": 0.13,
    },
    "colocation": {
        "capacity": 0.13,
        "development_stage": 0.18,
        "technology": 0.08,
        "grid_infrastructure": 0.17,
        "digital_infrastructure": 0.22,
        "water_resources": 0.05,
        "tnuos_transmission_costs": 0.10,
        "lcoe_resource_quality": 0.07,
    },
    "edge_computing": {
        "capacity": 0.09,
        "development_stage": 0.26,
        "technology": 0.14,
        "grid_infrastructure": 0.10,
        "digital_infrastructure": 0.23,
        "water_resources": 0.05,
        "tnuos_transmission_costs": 0.06,
        "lcoe_resource_quality": 0.07,
    },
}

PERSONA_CAPACITY_RANGES = {
    "edge_computing": {"min": 1, "max": 30},
    "colocation": {"min": 5, "max": 50},
    "hyperscaler": {"min": 50, "max": 1000},
}

LCOE_CONFIG = {
    "baseline_pounds_per_mwh": 55.0,
    "gamma_slope": 0.04,
    "min_lcoe": 40.0,
    "max_lcoe": 75.0,
    "zone_specific_rates": {},
}


class UserSite(BaseModel):
    site_name: str
    technology_type: str
    capacity_mw: float
    latitude: float
    longitude: float
    commissioning_year: int
    is_btm: bool


class FinancialModelRequest(BaseModel):
    technology: str
    capacity_mw: float
    capacity_factor: float
    project_life: int
    degradation: float
    capex_per_kw: float
    devex_abs: float
    devex_pct: float
    opex_fix_per_mw_year: float
    opex_var_per_mwh: float
    tnd_costs_per_year: float
    ppa_price: float
    ppa_escalation: float
    ppa_duration: int
    merchant_price: float
    capacity_market_per_mw_year: float
    ancillary_per_mw_year: float
    discount_rate: float
    inflation_rate: float
    tax_rate: float = 0.19
    grid_savings_factor: float
    battery_capacity_mwh: Optional[float] = None
    battery_capex_per_mwh: Optional[float] = None
    battery_cycles_per_year: Optional[int] = None


class RevenueBreakdown(BaseModel):
    energyRev: float
    capacityRev: float
    ancillaryRev: float
    gridSavings: float
    opexTotal: float


class ModelResults(BaseModel):
    irr: Optional[float]
    npv: float
    cashflows: List[float]
    breakdown: RevenueBreakdown
    lcoe: float
    payback_simple: Optional[float]
    payback_discounted: Optional[float]


class FinancialModelResponse(BaseModel):
    standard: ModelResults
    autoproducer: ModelResults
    metrics: Dict[str, float]
    success: bool
    message: str


async def query_supabase(endpoint: str) -> Any:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(500, "Supabase credentials not configured")

    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{SUPABASE_URL}/rest/v1/{endpoint}", headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(500, f"Database error: {response.status_code}")


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


class InfrastructureCache:
    def __init__(self) -> None:
        self._catalog: Optional[InfrastructureCatalog] = None
        self._lock = asyncio.Lock()
        self._last_loaded = 0.0

    async def get_catalog(self) -> InfrastructureCatalog:
        async with self._lock:
            if self._catalog and (time.time() - self._last_loaded) < INFRASTRUCTURE_CACHE_TTL_SECONDS:
                return self._catalog

            start = time.time()
            (
                substations,
                transmission_lines,
                fiber_cables,
                ixps,
                water_resources,
            ) = await asyncio.gather(
                query_supabase("substations?select=*"),
                query_supabase("transmission_lines?select=*"),
                query_supabase("fiber_cables?select=*&limit=200"),
                query_supabase("internet_exchange_points?select=*"),
                query_supabase("water_resources?select=*"),
            )

            catalog = self._build_catalog(
                substations or [],
                transmission_lines or [],
                fiber_cables or [],
                ixps or [],
                water_resources or [],
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


INFRASTRUCTURE_CACHE = InfrastructureCache()



def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _prepare_line_feature(raw_geometry: Any, payload: Dict[str, Any]) -> Optional[LineFeature]:
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


INFRASTRUCTURE_SEARCH_RADIUS_KM = {
    "substation": 120.0,
    "transmission": 150.0,
    "fiber": 120.0,
    "ixp": 150.0,
    "water": 150.0,
}


def _grid_steps_for_radius(grid: SpatialGrid, radius_km: float) -> int:
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
    best = float("inf")
    for segment in feature.segments:
        distance = point_to_line_segment_distance(lat, lon, *segment)
        if distance < best:
            best = distance
            if best == 0:
                break
    return best if best != float("inf") else 9999.0

def get_color_from_score(score_out_of_100: float) -> str:
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


def calculate_capacity_component_score(capacity_mw: float, persona: Optional[str] = None) -> float:
    if not persona or persona == "custom":
        if capacity_mw >= 250:
            return 125.0
        if capacity_mw >= 100:
            return 100.0
        if capacity_mw >= 50:
            return 85.0
        if capacity_mw >= 25:
            return 70.0
        if capacity_mw >= 10:
            return 55.0
        if capacity_mw >= 5:
            return 40.0
        if capacity_mw >= 1:
            return 25.0
        return 10.0

    if persona == "hyperscaler":
        if 50 <= capacity_mw <= 200:
            return 100.0
        if 25 <= capacity_mw < 50:
            return 60.0 + (capacity_mw - 25) * (25.0 / 25)
        if 200 < capacity_mw <= 400:
            excess = (capacity_mw - 200) / 200
            return max(70.0, 85.0 - (excess * 15))
        if capacity_mw > 400:
            return max(40.0, 70.0 - ((capacity_mw - 400) / 100) * 10)
        return max(20.0, capacity_mw * 2)

    if persona == "colocation":
        if 10 <= capacity_mw <= 50:
            return 100.0
        if 5 <= capacity_mw < 10:
            return 70.0 + (capacity_mw - 5) * (15.0 / 5)
        if 50 < capacity_mw <= 100:
            excess = (capacity_mw - 50) / 50
            return max(60.0, 85.0 - (excess * 25))
        if capacity_mw > 100:
            return max(30.0, 60.0 - ((capacity_mw - 100) / 50) * 15)
        return max(30.0, capacity_mw * 6)

    if persona == "edge_computing":
        if 1 <= capacity_mw <= 10:
            return 100.0
        if 0.5 <= capacity_mw < 1:
            return 60.0 + (capacity_mw - 0.5) * (25.0 / 0.5)
        if 10 < capacity_mw <= 25:
            excess = (capacity_mw - 10) / 15
            return max(40.0, 85.0 - (excess * 45))
        if capacity_mw > 25:
            return max(20.0, 40.0 - ((capacity_mw - 25) / 25) * 15)
        return max(10.0, capacity_mw * 20)

    return 50.0


def calculate_development_stage_score(status: str, perspective: str = "demand") -> float:
    status = str(status).lower()
    if perspective == "supply":
        if "fid_ready" in status or "ready" in status:
            return 95.0
        if "consented" in status or "granted" in status:
            return 85.0
        if "submitted" in status:
            return 65.0
        if "planning" in status or "pre-planning" in status:
            return 45.0
        if "operational" in status:
            return 30.0
        return 20.0
    if "operational" in status:
        return 50.0
    if "construction" in status:
        return 70.0
    if "granted" in status:
        return 85.0
    if "submitted" in status:
        return 45.0
    if "planning" in status:
        return 30.0
    return 10.0


def calculate_technology_score(tech_type: str) -> float:
    tech = str(tech_type).lower()
    if "solar" in tech:
        return 70.0
    if "battery" in tech:
        return 80.0
    if "wind" in tech:
        return 90.0
    if "hybrid" in tech:
        return 95.0
    return 60.0


def calculate_grid_infrastructure_score(proximity_scores: Dict[str, float]) -> float:
    substation_score = proximity_scores.get("substation_score", 0.0)
    transmission_score = proximity_scores.get("transmission_score", 0.0)
    grid_score = 10.0
    if substation_score > 30:
        grid_score += 50.0
    elif substation_score > 20:
        grid_score += 30.0
    elif substation_score > 10:
        grid_score += 15.0
    if transmission_score > 30:
        grid_score += 40.0
    elif transmission_score > 15:
        grid_score += 20.0
    return min(100.0, grid_score)


def calculate_digital_infrastructure_score(proximity_scores: Dict[str, float]) -> float:
    fiber_score = proximity_scores.get("fiber_score", 0.0)
    ixp_score = proximity_scores.get("ixp_score", 0.0)
    digital_score = 10.0
    if fiber_score > 15:
        digital_score += 40.0
    elif fiber_score > 8:
        digital_score += 25.0
    elif fiber_score > 3:
        digital_score += 10.0
    if ixp_score > 8:
        digital_score += 35.0
    elif ixp_score > 4:
        digital_score += 20.0
    elif ixp_score > 1:
        digital_score += 10.0
    return min(100.0, digital_score)


def calculate_water_resources_score(proximity_scores: Dict[str, float]) -> float:
    water_score = proximity_scores.get("water_score", 0.0)
    if water_score > 10:
        return 100.0
    if water_score > 5:
        return 80.0
    if water_score > 2:
        return 60.0
    return 40.0


def calculate_lcoe_score(project_lat: float, project_lng: float, technology_type: str) -> float:
    tech_lcoe = {
        "solar": 52.0,
        "wind": 48.0,
        "battery": 60.0,
        "hybrid": 50.0,
        "offshore wind": 45.0,
        "onshore wind": 48.0,
    }
    tech_key = str(technology_type).lower()
    lcoe = tech_lcoe.get(tech_key, LCOE_CONFIG["baseline_pounds_per_mwh"])
    baseline = LCOE_CONFIG["baseline_pounds_per_mwh"]
    gamma = LCOE_CONFIG["gamma_slope"]
    if lcoe <= baseline:
        score = 100.0
    else:
        penalty = lcoe - baseline
        score = 100.0 * (math.e ** (-gamma * penalty))
    return min(100.0, max(10.0, score))


def calculate_tnuos_score(project_lat: float, project_lng: float) -> float:
    lat_normalized = (project_lat - 49.5) / (60.0 - 49.5)
    estimated_tariff = -2.0 + (17.0 * lat_normalized)
    min_tariff = -3.0
    max_tariff = 16.0
    if estimated_tariff <= min_tariff:
        percentile_score = 100.0
    elif estimated_tariff >= max_tariff:
        percentile_score = 0.0
    else:
        normalized_position = (estimated_tariff - min_tariff) / (max_tariff - min_tariff)
        percentile_score = 100.0 * (1.0 - normalized_position)
    return min(100.0, max(0.0, percentile_score))
    
def build_persona_component_scores(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    persona: Optional[str] = None,
    perspective: str = "demand",
) -> Dict[str, float]:
    """Compute raw component scores used for persona-based evaluation."""

    capacity_score = calculate_capacity_component_score(
        project.get("capacity_mw", 0) or 0,
        persona,
    )
    stage_score = calculate_development_stage_score(
        project.get("development_status_short", ""),
        perspective,
    )
    tech_score = calculate_technology_score(project.get("technology_type", ""))
    grid_score = calculate_grid_infrastructure_score(proximity_scores)
    digital_score = calculate_digital_infrastructure_score(proximity_scores)
    water_score = calculate_water_resources_score(proximity_scores)
    lcoe_score = calculate_lcoe_score(
        project.get("latitude", 0),
        project.get("longitude", 0),
        project.get("technology_type", ""),
    )
    tnuos_score = calculate_tnuos_score(
        project.get("latitude", 0),
        project.get("longitude", 0),
    )

    return {
        "capacity": capacity_score,
        "development_stage": stage_score,
        "technology": tech_score,
        "grid_infrastructure": grid_score,
        "digital_infrastructure": digital_score,
        "water_resources": water_score,
        "lcoe_resource_quality": lcoe_score,
        "tnuos_transmission_costs": tnuos_score,
    }

def calculate_persona_weighted_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    persona: PersonaType = "hyperscaler",
    perspective: str = "demand",
) -> Dict[str, Any]:
    weights = PERSONA_WEIGHTS[persona]
    if perspective == "supply":
        adjusted = weights.copy()
        adjusted["development_stage"] = weights["development_stage"] * 1.2
        adjusted["digital_infrastructure"] = weights["digital_infrastructure"] * 0.5
        adjusted["lcoe_resource_quality"] = weights["lcoe_resource_quality"] * 0.8
        total = sum(adjusted.values())
        weights = {key: value / total for key, value in adjusted.items()}

    # Use the new builder function
    component_scores = build_persona_component_scores(project, proximity_scores, persona, perspective)

    weighted_score = (
        component_scores["capacity"] * weights["capacity"]
        + component_scores["development_stage"] * weights["development_stage"]
        + component_scores["technology"] * weights["technology"]
        + component_scores["grid_infrastructure"] * weights["grid_infrastructure"]
        + component_scores["digital_infrastructure"] * weights["digital_infrastructure"]
        + component_scores["water_resources"] * weights["water_resources"]
        + component_scores["lcoe_resource_quality"] * weights["lcoe_resource_quality"]
        + component_scores["tnuos_transmission_costs"] * weights.get("tnuos_transmission_costs", 0.0)
    )

    final_internal_score = min(100.0, max(10.0, weighted_score))
    display_rating = final_internal_score / 10.0
    color = get_color_from_score(final_internal_score)
    description = get_rating_description(final_internal_score)

    return {
        "investment_rating": round(display_rating, 1),
        "rating_description": description,
        "color_code": color,
        "component_scores": {
            key: round(value, 1) for key, value in component_scores.items()
        },
        "weighted_contributions": {
            key: round(component_scores[key] * weights.get(key, 0.0), 1)
            for key in component_scores
        },
        "persona": persona,
        "persona_weights": weights,
        "internal_total_score": round(final_internal_score, 1),
        "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
    }

def calculate_persona_topsis_score(
    component_scores: Sequence[Dict[str, float]],
    weights: Dict[str, float],
) -> Dict[str, Any]:
    """Apply TOPSIS using persona weights, supporting positive and negative impacts."""

    if not component_scores:
        return {
            "scores": [],
            "ideal_solution": {},
            "anti_ideal_solution": {},
        }

    component_keys = list(component_scores[0].keys())
    denominators: Dict[str, float] = {}
    for key in component_keys:
        sum_squares = sum((scores.get(key, 0.0) or 0.0) ** 2 for scores in component_scores)
        denominators[key] = math.sqrt(sum_squares) or 1e-9

    weighted_vectors: List[Dict[str, Dict[str, float]]] = []
    for scores in component_scores:
        normalized: Dict[str, float] = {}
        weighted: Dict[str, float] = {}
        for key in component_keys:
            raw_value = scores.get(key, 0.0) or 0.0
            denominator = denominators[key]
            normalized_value = raw_value / denominator if denominator else 0.0
            weight = weights.get(key, 0.0)
            weighted_value = normalized_value * weight
            normalized[key] = normalized_value
            weighted[key] = weighted_value
        weighted_vectors.append(
            {
                "normalized_scores": normalized,
                "weighted_normalized_scores": weighted,
            }
        )

    ideal_solution: Dict[str, float] = {}
    anti_ideal_solution: Dict[str, float] = {}
    for key in component_keys:
        values = [vector["weighted_normalized_scores"][key] for vector in weighted_vectors]
        ideal_solution[key] = max(values)
        anti_ideal_solution[key] = min(values)

    results: List[Dict[str, Any]] = []
    for vector in weighted_vectors:
        weighted = vector["weighted_normalized_scores"]
        distance_to_ideal = math.sqrt(
            sum((weighted[key] - ideal_solution[key]) ** 2 for key in component_keys)
        )
        distance_to_anti_ideal = math.sqrt(
            sum((weighted[key] - anti_ideal_solution[key]) ** 2 for key in component_keys)
        )
        closeness = 0.0
        denominator = distance_to_ideal + distance_to_anti_ideal
        if denominator > 0:
            closeness = distance_to_anti_ideal / denominator
        elif distance_to_ideal == 0 and distance_to_anti_ideal == 0:
            closeness = 1.0
        results.append(
            {
                "normalized_scores": vector["normalized_scores"],
                "weighted_normalized_scores": weighted,
                "distance_to_ideal": distance_to_ideal,
                "distance_to_anti_ideal": distance_to_anti_ideal,
                "closeness_coefficient": closeness,
            }
        )

    return {
        "scores": results,
        "ideal_solution": ideal_solution,
        "anti_ideal_solution": anti_ideal_solution,
    }

def calculate_custom_weighted_score(
    project: Dict[str, Any],
    proximity_scores: Dict[str, float],
    custom_weights: Dict[str, float],
) -> Dict[str, Any]:
    capacity_score = calculate_capacity_component_score(project.get("capacity_mw", 0) or 0)
    stage_score = calculate_development_stage_score(project.get("development_status_short", ""))
    tech_score = calculate_technology_score(project.get("technology_type", ""))
    grid_score = calculate_grid_infrastructure_score(proximity_scores)
    digital_score = calculate_digital_infrastructure_score(proximity_scores)
    water_score = calculate_water_resources_score(proximity_scores)
    lcoe_score = calculate_lcoe_score(project.get("latitude", 0), project.get("longitude", 0), project.get("technology_type", ""))
    tnuos_score = calculate_tnuos_score(project.get("latitude", 0), project.get("longitude", 0))

    weighted_score = (
        capacity_score * custom_weights.get("capacity", 0.0)
        + stage_score * custom_weights.get("development_stage", 0.0)
        + tech_score * custom_weights.get("technology", 0.0)
        + grid_score * custom_weights.get("grid_infrastructure", 0.0)
        + digital_score * custom_weights.get("digital_infrastructure", 0.0)
        + water_score * custom_weights.get("water_resources", 0.0)
        + lcoe_score * custom_weights.get("lcoe_resource_quality", 0.0)
        + tnuos_score * custom_weights.get("tnuos_transmission_costs", 0.0)
    )

    final_internal_score = min(100.0, max(10.0, weighted_score))
    display_rating = final_internal_score / 10.0
    color = get_color_from_score(final_internal_score)
    description = get_rating_description(final_internal_score)

    return {
        "investment_rating": round(display_rating, 1),
        "rating_description": description,
        "color_code": color,
        "component_scores": {
            "capacity": round(capacity_score, 1),
            "development_stage": round(stage_score, 1),
            "technology": round(tech_score, 1),
            "grid_infrastructure": round(grid_score, 1),
            "digital_infrastructure": round(digital_score, 1),
            "water_resources": round(water_score, 1),
            "lcoe_resource_quality": round(lcoe_score, 1),
        },
        "weighted_contributions": {
            "capacity": round(capacity_score * custom_weights.get("capacity", 0.0), 1),
            "development_stage": round(stage_score * custom_weights.get("development_stage", 0.0), 1),
            "technology": round(tech_score * custom_weights.get("technology", 0.0), 1),
            "grid_infrastructure": round(
                grid_score * custom_weights.get("grid_infrastructure", 0.0),
                1,
            ),
            "digital_infrastructure": round(
                digital_score * custom_weights.get("digital_infrastructure", 0.0),
                1,
            ),
            "water_resources": round(water_score * custom_weights.get("water_resources", 0.0), 1),
            "lcoe_resource_quality": round(
                lcoe_score * custom_weights.get("lcoe_resource_quality", 0.0),
                1,
            ),
        },
        "persona": "custom",
        "persona_weights": custom_weights,
        "internal_total_score": round(final_internal_score, 1),
        "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
    }

def calculate_base_investment_score_renewable(project: Dict[str, Any]) -> float:
    capacity = project.get("capacity_mw", 0) or 0
    status = str(project.get("development_status_short", "")).lower()
    tech = str(project.get("technology_type", "")).lower()
    if capacity >= 200:
        capacity_score = 100.0
    elif capacity >= 100:
        capacity_score = 90.0
    elif capacity >= 50:
        capacity_score = 75.0
    elif capacity >= 25:
        capacity_score = 60.0
    elif capacity >= 10:
        capacity_score = 45.0
    elif capacity >= 5:
        capacity_score = 30.0
    else:
        capacity_score = 15.0

    if "operational" in status:
        stage_score = 100.0
    elif "construction" in status:
        stage_score = 90.0
    elif "granted" in status:
        stage_score = 75.0
    elif "submitted" in status:
        stage_score = 50.0
    elif "planning" in status:
        stage_score = 30.0
    elif "pre-planning" in status:
        stage_score = 20.0
    else:
        stage_score = 10.0

    if "solar" in tech:
        tech_score = 90.0
    elif "battery" in tech:
        tech_score = 85.0
    elif "wind" in tech:
        tech_score = 80.0
    elif "hybrid" in tech:
        tech_score = 75.0
    else:
        tech_score = 60.0

    base_score = capacity_score * 0.30 + stage_score * 0.50 + tech_score * 0.20
    return min(100.0, max(10.0, base_score))


def calculate_infrastructure_bonus_renewable(proximity_scores: Dict[str, float]) -> float:
    grid_bonus = 0.0
    substation_score = proximity_scores.get("substation_score", 0.0)
    transmission_score = proximity_scores.get("transmission_score", 0.0)
    if substation_score > 40:
        grid_bonus += 15.0
    elif substation_score > 25:
        grid_bonus += 10.0
    elif substation_score > 10:
        grid_bonus += 5.0
    if transmission_score > 30:
        grid_bonus += 10.0
    elif transmission_score > 15:
        grid_bonus += 5.0
    grid_bonus = min(25.0, grid_bonus)

    digital_bonus = 0.0
    fiber_score = proximity_scores.get("fiber_score", 0.0)
    ixp_score = proximity_scores.get("ixp_score", 0.0)
    if fiber_score > 15:
        digital_bonus += 5.0
    elif fiber_score > 8:
        digital_bonus += 3.0
    if ixp_score > 8:
        digital_bonus += 5.0
    elif ixp_score > 4:
        digital_bonus += 2.0
    digital_bonus = min(10.0, digital_bonus)

    water_bonus = 0.0
    water_score = proximity_scores.get("water_score", 0.0)
    if water_score > 10:
        water_bonus = 5.0
    elif water_score > 5:
        water_bonus = 3.0
    elif water_score > 2:
        water_bonus = 1.0

    return grid_bonus + digital_bonus + water_bonus


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


def calculate_best_customer_match(project: Dict[str, Any], proximity_scores: Dict[str, float]) -> Dict[str, Any]:
    customer_scores: Dict[str, float] = {}
    for persona in ["hyperscaler", "colocation", "edge_computing"]:
        capacity_mw = project.get("capacity_mw", 0)
        capacity_range = PERSONA_CAPACITY_RANGES[persona]
        if capacity_range["min"] <= capacity_mw <= capacity_range["max"]:
            scoring_result = calculate_persona_weighted_score(project, proximity_scores, persona)  # type: ignore[arg-type]
            customer_scores[persona] = scoring_result["investment_rating"]
        else:
            customer_scores[persona] = 2.0

    best_customer = max(customer_scores.keys(), key=lambda key: customer_scores[key])
    best_score = customer_scores[best_customer]

    return {
        "best_customer_match": best_customer,
        "customer_match_scores": customer_scores,
        "best_match_score": round(best_score, 1),
        "capacity_mw": project.get("capacity_mw", 0),
        "suitable_customers": [persona for persona, score in customer_scores.items() if score >= 6.0],
    }


def filter_projects_by_persona_capacity(projects: List[Dict[str, Any]], persona: PersonaType) -> List[Dict[str, Any]]:
    capacity_range = PERSONA_CAPACITY_RANGES[persona]
    filtered = []
    for project in projects:
        capacity_mw = project.get("capacity_mw", 0)
        if capacity_range["min"] <= capacity_mw <= capacity_range["max"]:
            filtered.append(project)
    return filtered


async def calculate_proximity_scores_batch(projects: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    if not projects:
        return []

    catalog = await INFRASTRUCTURE_CACHE.get_catalog()
    results: List[Dict[str, float]] = []

    for project in projects:
        project_lat = _coerce_float(project.get("latitude"))
        project_lon = _coerce_float(project.get("longitude"))
        if project_lat is None or project_lon is None:
            continue

        proximity_scores: Dict[str, float] = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "total_proximity_bonus": 0.0,
            "nearest_distances": {},
        }

        nearest_distances: Dict[str, float] = {}

        substation = _nearest_point(
            catalog.substations_index,
            catalog.substations,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["substation"],
        )
        if substation:
            distance, _ = substation
            proximity_scores["substation_score"] = exponential_score(distance, 30.0)
            nearest_distances["substation_km"] = round(distance, 1)

        transmission = _nearest_line(
            catalog.transmission_index,
            catalog.transmission_lines,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["transmission"],
        )
        if transmission:
            distance, _ = transmission
            proximity_scores["transmission_score"] = exponential_score(distance, 30.0)
            nearest_distances["transmission_km"] = round(distance, 1)

        fiber = _nearest_line(
            catalog.fiber_index,
            catalog.fiber_cables,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["fiber"],
        )
        if fiber:
            distance, _ = fiber
            proximity_scores["fiber_score"] = exponential_score(distance, 15.0)
            nearest_distances["fiber_km"] = round(distance, 1)

        ixp = _nearest_point(
            catalog.ixp_index,
            catalog.internet_exchange_points,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["ixp"],
        )
        if ixp:
            distance, _ = ixp
            proximity_scores["ixp_score"] = exponential_score(distance, 40.0)
            nearest_distances["ixp_km"] = round(distance, 1)

        water_point = _nearest_point(
            catalog.water_point_index,
            catalog.water_points,
            project_lat,
            project_lon,
            INFRASTRUCTURE_SEARCH_RADIUS_KM["water"],
        )
        water_line = _nearest_line(
            catalog.water_line_index,
            catalog.water_lines,
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

        results.append(proximity_scores)

    return results

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


@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Infranodal API v2.1 with Persona-Based Scoring", "status": "active"}


@app.get("/health")
async def health() -> Dict[str, Any]:
    try:
        print("🔄 Testing database connection...")
        data = await query_supabase("renewable_projects?select=count")
        count = len(data)
        print(f"✅ Database connected: {count} records")
        return {"status": "healthy", "database": "connected", "projects": count}
    except Exception as exc:  # pragma: no cover - diagnostic logging
        print(f"❌ Database error: {exc}")
        return {"status": "degraded", "database": "disconnected", "error": str(exc)}


@app.get("/api/projects")
async def get_projects(
    limit: int = Query(1000),
    technology: Optional[str] = None,
    country: Optional[str] = None,
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring"),
) -> List[Dict[str, Any]]:
    query_parts = ["renewable_projects?select=*"]
    filters = []
    if technology:
        filters.append(f"technology_type.ilike.%{technology}%")
    if country:
        filters.append(f"country.ilike.%{country}%")
    if filters:
        query_parts.append("&".join(filters))
    query_parts.append(f"limit={limit}")
    projects = await query_supabase("&".join(query_parts))

    for project in projects:
        dummy_proximity = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "nearest_distances": {},
        }
        if persona:
            rating_result = calculate_persona_weighted_score(project, dummy_proximity, persona)
        else:
            rating_result = calculate_enhanced_investment_rating(project, dummy_proximity)
        project.update(
            {
                "investment_rating": rating_result["investment_rating"],
                "rating_description": rating_result["rating_description"],
                "color_code": rating_result["color_code"],
                "component_scores": rating_result.get("component_scores"),
                "weighted_contributions": rating_result.get("weighted_contributions"),
                "persona": rating_result.get("persona"),
                "base_score": rating_result.get("base_investment_score", rating_result["investment_rating"]),
                "infrastructure_bonus": rating_result.get("infrastructure_bonus", 0.0),
            }
        )
    return projects


@app.get("/api/projects/geojson")
async def get_geojson(
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring"),
) -> Dict[str, Any]:
    projects = await query_supabase("renewable_projects?select=*&limit=500")
    features: List[Dict[str, Any]] = []

    for project in projects:
        if not project.get("longitude") or not project.get("latitude"):
            continue
        dummy_proximity = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "nearest_distances": {},
        }
        if persona:
            rating_result = calculate_persona_weighted_score(project, dummy_proximity, persona)
        else:
            rating_result = calculate_enhanced_investment_rating(project, dummy_proximity)

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [project["longitude"], project["latitude"]],
                },
                "properties": {
                    "ref_id": project["ref_id"],
                    "site_name": project["site_name"],
                    "technology_type": project["technology_type"],
                    "operator": project.get("operator"),
                    "capacity_mw": project.get("capacity_mw"),
                    "county": project.get("county"),
                    "country": project.get("country"),
                    "investment_rating": rating_result["investment_rating"],
                    "rating_description": rating_result["rating_description"],
                    "color_code": rating_result["color_code"],
                    "component_scores": rating_result.get("component_scores"),
                    "weighted_contributions": rating_result.get("weighted_contributions"),
                    "persona": rating_result.get("persona"),
                    "base_score": rating_result.get("base_investment_score", rating_result["investment_rating"]),
                    "infrastructure_bonus": rating_result.get("infrastructure_bonus", 0.0),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


@app.post("/api/user-sites/score")
async def score_user_sites(
    sites: List[UserSite],
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring"),
) -> Dict[str, Any]:
    if not sites:
        raise HTTPException(400, "No sites provided")

    for index, site in enumerate(sites):
        if not (49.8 <= site.latitude <= 60.9) or not (-10.8 <= site.longitude <= 2.0):
            raise HTTPException(400, f"Site {index + 1}: Coordinates outside UK bounds")
        if not (5 <= site.capacity_mw <= 500):
            raise HTTPException(400, f"Site {index + 1}: Capacity must be between 5-500 MW")
        if not (2025 <= site.commissioning_year <= 2035):
            raise HTTPException(400, f"Site {index + 1}: Commissioning year must be between 2025-2035")

    scoring_mode = "persona-based" if persona else "renewable energy"
    print(f"🔄 Scoring {len(sites)} user-submitted sites with {scoring_mode.upper()} system...")
    start_time = time.time()

    sites_for_calc: List[Dict[str, Any]] = []
    for site in sites:
        sites_for_calc.append(
            {
                "site_name": site.site_name,
                "technology_type": site.technology_type,
                "capacity_mw": site.capacity_mw,
                "latitude": site.latitude,
                "longitude": site.longitude,
                "commissioning_year": site.commissioning_year,
                "is_btm": site.is_btm,
                "development_status_short": "planning",
            }
        )

    proximity_scores = await calculate_proximity_scores_batch(sites_for_calc)

    scored_sites: List[Dict[str, Any]] = []
    for index, site_data in enumerate(sites_for_calc):
        prox_scores = (
            proximity_scores[index]
            if index < len(proximity_scores)
            else {
                "substation_score": 0.0,
                "transmission_score": 0.0,
                "fiber_score": 0.0,
                "ixp_score": 0.0,
                "water_score": 0.0,
                "total_proximity_bonus": 0.0,
                "nearest_distances": {},
            }
        )
        if persona:
            rating_result = calculate_persona_weighted_score(site_data, prox_scores, persona)
        else:
            rating_result = calculate_enhanced_investment_rating(site_data, prox_scores)

        scored_sites.append(
            {
                "site_name": site_data["site_name"],
                "technology_type": site_data["technology_type"],
                "capacity_mw": site_data["capacity_mw"],
                "commissioning_year": site_data["commissioning_year"],
                "is_btm": site_data["is_btm"],
                "coordinates": [site_data["longitude"], site_data["latitude"]],
                "investment_rating": rating_result["investment_rating"],
                "rating_description": rating_result["rating_description"],
                "color_code": rating_result["color_code"],
                "component_scores": rating_result.get("component_scores"),
                "weighted_contributions": rating_result.get("weighted_contributions"),
                "persona": rating_result.get("persona"),
                "base_score": rating_result.get("base_investment_score", rating_result["investment_rating"]),
                "infrastructure_bonus": rating_result.get("infrastructure_bonus", 0.0),
                "nearest_infrastructure": rating_result["nearest_infrastructure"],
                "methodology": f"{scoring_mode} scoring system",
            }
        )

    processing_time = time.time() - start_time
    print(f"✅ User sites scored with {scoring_mode.upper()} SYSTEM in {processing_time:.2f}s")

    return {
        "sites": scored_sites,
        "metadata": {
            "scoring_system": f"{scoring_mode} - 1.0-10.0 Investment Rating Scale",
            "persona": persona,
            "processing_time_seconds": round(processing_time, 2),
            "algorithm_version": "2.1 - Persona-Based Infrastructure Proximity Enhanced",
            "rating_scale": {
                "9.0-10.0": "Excellent - Premium investment opportunity",
                "8.0-8.9": "Very Good - Strong investment potential",
                "7.0-7.9": "Good - Solid investment opportunity",
                "6.0-6.9": "Above Average - Moderate investment potential",
                "5.0-5.9": "Average - Standard investment opportunity",
                "4.0-4.9": "Below Average - Limited investment appeal",
                "3.0-3.9": "Poor - Significant investment challenges",
                "2.0-2.9": "Very Poor - High risk investment",
                "1.0-1.9": "Bad - Unfavorable investment conditions",
            },
        },
    }


@app.get("/api/projects/enhanced")
async def get_enhanced_geojson(
    limit: int = Query(1000, description="Number of projects to process"),
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring"),
    apply_capacity_filter: bool = Query(True, description="Filter projects by persona capacity requirements"),
    custom_weights: Optional[str] = Query(None, description="JSON string of custom weights (overrides persona)"),
    scoring_method: Literal["weighted_sum", "topsis"] = Query(
        "weighted_sum",
        description="Scoring method to apply (weighted_sum or topsis)",
    ),
    dc_demand_mw: Optional[float] = Query(None, description="DC facility demand in MW for capacity gating"),
    source_table: str = Query(
        "renewable_projects",
        description="Source table - will be demand_sites for power devs in future",
    ),
) -> Dict[str, Any]:
    start_time = time.time()
    parsed_custom_weights = None
    if custom_weights:
        try:
            parsed_custom_weights = json.loads(custom_weights)
            total = sum(parsed_custom_weights.values())
            if total and abs(total - 1.0) > 0.01:
                parsed_custom_weights = {key: value / total for key, value in parsed_custom_weights.items()}
        except (json.JSONDecodeError, AttributeError):
            parsed_custom_weights = None

    active_scoring_method = scoring_method.lower()
    use_topsis = active_scoring_method == "topsis"
    scoring_mode = "custom weights" if parsed_custom_weights else ("persona-based" if persona else "renewable energy")
    print(
        "🚀 ENHANCED ENDPOINT WITH "
        f"{scoring_mode.upper()} SCORING [{active_scoring_method.upper()}] - Processing {limit} projects..."
    )

    try:
        projects = await query_supabase(f"{source_table}?select=*&limit={limit}")
        print(f"✅ Loaded {len(projects)} projects from {source_table}")
        if source_table != "renewable_projects":
            print(f"⚠️ Note: {source_table} table requested but using renewable_projects as placeholder")
        if persona and apply_capacity_filter:
            original_count = len(projects)
            projects = filter_projects_by_persona_capacity(projects, persona)
            print(f"🎯 Filtered to {len(projects)} projects for {persona} (was {original_count})")
        if persona:
            dc_thresholds = {"hyperscaler": 50.0, "colocation": 5.0, "edge_computing": 1.0}
            min_capacity = dc_thresholds.get(persona, 1.0)
            capacity_gated: List[Dict[str, Any]] = []
            for project in projects:
                project_capacity = project.get("capacity_mw", 0) or 0
                if project_capacity >= min_capacity * 0.9:
                    capacity_gated.append(project)
            if len(capacity_gated) != len(projects):
                print(
                    f"⚡ Capacity gating: {len(capacity_gated)}/{len(projects)} projects meet minimum capacity for {persona}"
                )
            projects = capacity_gated
    except Exception as exc:
        print(f"❌ Database error: {exc}")
        return {"error": "Database connection failed", "type": "FeatureCollection", "features": []}
        # Continuation of get_enhanced_geojson function
    
    valid_projects = [project for project in projects if project.get("longitude") and project.get("latitude")]
    print(f"📍 {len(valid_projects)} projects have valid coordinates")
    if not valid_projects:
        return {"type": "FeatureCollection", "features": [], "metadata": {"error": "No projects with valid coordinates"}}

    try:
        print("🔄 Starting batch proximity calculation...")
        batch_start = time.time()
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects)
        batch_time = time.time() - batch_start
        print(f"✅ Batch proximity calculation completed in {batch_time:.2f}s")
    except Exception as exc:  # pragma: no cover - fallback path
        print(f"❌ Error in batch proximity calculation: {exc}")
        all_proximity_scores = [
            {
                "substation_score": 0.0,
                "transmission_score": 0.0,
                "fiber_score": 0.0,
                "ixp_score": 0.0,
                "water_score": 0.0,
                "total_proximity_bonus": 0.0,
                "nearest_distances": {},
            }
            for _ in valid_projects
        ]

    def get_proximity_scores_for_index(idx: int) -> Dict[str, float]:
        if idx < len(all_proximity_scores):
            return all_proximity_scores[idx]
        return {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "total_proximity_bonus": 0.0,
            "nearest_distances": {},
        }

    # TOPSIS-specific variables
    topsis_component_scores: List[Dict[str, float]] = []
    topsis_results: List[Dict[str, Any]] = []
    topsis_ideal_solution: Dict[str, float] = {}
    topsis_anti_ideal_solution: Dict[str, float] = {}
    weights_for_topsis: Dict[str, float] = {}
    topsis_persona_label: Optional[str] = persona
    persona_for_components: Optional[str] = persona if persona else None

    if use_topsis:
        # Determine weights for TOPSIS
        if parsed_custom_weights:
            weights_for_topsis = parsed_custom_weights
            persona_for_components = "custom"
            topsis_persona_label = persona or "custom"
        elif persona:
            weights_for_topsis = PERSONA_WEIGHTS[persona]
            persona_for_components = persona
            topsis_persona_label = persona
        else:
            topsis_persona_label = "hyperscaler"
            weights_for_topsis = PERSONA_WEIGHTS[topsis_persona_label]
            persona_for_components = topsis_persona_label
            print(
                "⚠️ TOPSIS requested without persona/custom weights; defaulting to hyperscaler persona weights"
            )

        # Collect component scores for all projects
        for index, project in enumerate(valid_projects):
            proximity_scores = get_proximity_scores_for_index(index)
            component_scores = build_persona_component_scores(
                project,
                proximity_scores,
                persona_for_components,
            )
            topsis_component_scores.append(component_scores)

        # Calculate TOPSIS scores
        topsis_output = calculate_persona_topsis_score(topsis_component_scores, weights_for_topsis)
        topsis_results = topsis_output.get("scores", []) if topsis_output else []
        topsis_ideal_solution = topsis_output.get("ideal_solution", {}) if topsis_output else {}
        topsis_anti_ideal_solution = topsis_output.get("anti_ideal_solution", {}) if topsis_output else {}

    features: List[Dict[str, Any]] = []
    for index, project in enumerate(valid_projects):
        try:
            proximity_scores = get_proximity_scores_for_index(index)
            
            if use_topsis:
                # TOPSIS scoring path
                component_scores = (
                    topsis_component_scores[index]
                    if index < len(topsis_component_scores)
                    else build_persona_component_scores(
                        project,
                        proximity_scores,
                        persona_for_components,
                    )
                )
                topsis_info = topsis_results[index] if index < len(topsis_results) else None
                
                if not topsis_info:
                    # Fallback to weighted sum if TOPSIS fails
                    if parsed_custom_weights:
                        rating_result = calculate_custom_weighted_score(
                            project, proximity_scores, parsed_custom_weights
                        )
                    elif persona:
                        rating_result = calculate_persona_weighted_score(
                            project, proximity_scores, persona
                        )
                    else:
                        rating_result = calculate_enhanced_investment_rating(project, proximity_scores)
                else:
                    # Use TOPSIS results
                    closeness = topsis_info.get("closeness_coefficient", 0.0)
                    internal_total_score = 10.0 + closeness * 90.0
                    display_rating = round(internal_total_score / 10.0, 1)
                    color = get_color_from_score(internal_total_score)
                    description = get_rating_description(internal_total_score)
                    
                    component_scores_rounded = {
                        key: round(value, 1) for key, value in component_scores.items()
                    }
                    weighted_contributions = {
                        key: round(component_scores.get(key, 0.0) * weights_for_topsis.get(key, 0.0), 1)
                        for key in component_scores
                    }
                    
                    rating_result = {
                        "investment_rating": display_rating,
                        "rating_description": description,
                        "color_code": color,
                        "component_scores": component_scores_rounded,
                        "weighted_contributions": weighted_contributions,
                        "persona": topsis_persona_label,
                        "persona_weights": weights_for_topsis,
                        "internal_total_score": round(internal_total_score, 1),
                        "nearest_infrastructure": proximity_scores.get("nearest_distances", {}),
                        "topsis_metrics": {
                            "distance_to_ideal": topsis_info.get("distance_to_ideal"),
                            "distance_to_anti_ideal": topsis_info.get("distance_to_anti_ideal"),
                            "closeness_coefficient": closeness,
                            "weighted_normalized_scores": topsis_info.get("weighted_normalized_scores"),
                            "normalized_scores": topsis_info.get("normalized_scores"),
                        },
                        "scoring_methodology": "Persona TOPSIS scoring (closeness scaled to 1-10)",
                    }
            else:
                # Traditional weighted sum scoring
                if parsed_custom_weights:
                    rating_result = calculate_custom_weighted_score(
                        project, proximity_scores, parsed_custom_weights
                    )
                elif persona:
                    rating_result = calculate_persona_weighted_score(project, proximity_scores, persona)
                else:
                    rating_result = calculate_enhanced_investment_rating(project, proximity_scores)

            # Build feature properties
            properties: Dict[str, Any] = {
                "ref_id": project["ref_id"],
                "site_name": project["site_name"],
                "technology_type": project["technology_type"],
                "operator": project.get("operator"),
                "capacity_mw": project.get("capacity_mw"),
                "development_status_short": project.get("development_status_short"),
                "county": project.get("county"),
                "country": project.get("country"),
                "investment_rating": rating_result["investment_rating"],
                "rating_description": rating_result["rating_description"],
                "color_code": rating_result["color_code"],
                "component_scores": rating_result.get("component_scores"),
                "weighted_contributions": rating_result.get("weighted_contributions"),
                "nearest_infrastructure": rating_result["nearest_infrastructure"],
                "persona": rating_result.get("persona"),
                "persona_weights": rating_result.get("persona_weights"),
                "base_score": rating_result.get("base_investment_score", rating_result["investment_rating"]),
                "infrastructure_bonus": rating_result.get("infrastructure_bonus", 0.0),
                "internal_total_score": rating_result.get("internal_total_score"),
            }

            # Add TOPSIS-specific metrics if using TOPSIS
            if use_topsis and "topsis_metrics" in rating_result:
                properties["topsis_metrics"] = rating_result["topsis_metrics"]
                properties["scoring_methodology"] = rating_result.get("scoring_methodology")

            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [project["longitude"], project["latitude"]],
                    },
                    "properties": properties,
                }
            )
        except Exception as exc:  # pragma: no cover - per-project failure fallback
            print(f"❌ Error processing project {index + 1}: {exc}")
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [project["longitude"], project["latitude"]],
                    },
                    "properties": {
                        "ref_id": project["ref_id"],
                        "site_name": project["site_name"],
                        "operator": project.get("operator"),
                        "technology_type": project["technology_type"],
                        "capacity_mw": project.get("capacity_mw"),
                        "county": project.get("county"),
                        "country": project.get("country"),
                        "investment_rating": 5.0,
                        "rating_description": "Average",
                        "color_code": "#FFFF00",
                        "nearest_infrastructure": {},
                    },
                }
            )

    processing_time = time.time() - start_time
    if persona:
        print(
            f"🎯 PERSONA-BASED SCORING ({persona.upper()}) COMPLETE: {len(features)} features in {processing_time:.2f}s"
        )
    else:
        print(f"🎯 RENEWABLE ENERGY SCORING COMPLETE: {len(features)} features in {processing_time:.2f}s")

    # Build metadata
    metadata: Dict[str, Any] = {
        "scoring_system": f"{scoring_mode} - 1.0-10.0 display scale",
        "scoring_method": active_scoring_method,
        "persona": persona,
        "processing_time_seconds": round(processing_time, 2),
        "projects_processed": len(features),
        "algorithm_version": "2.1 - Persona-Based Infrastructure Scoring",
        "performance_optimization": "Cached infrastructure + batch proximity scoring",
        "rating_distribution": calculate_rating_distribution(features),
        "rating_scale_guide": {
            "excellent": "9.0-10.0",
            "very_good": "8.0-8.9",
            "good": "7.0-7.9",
            "above_average": "6.0-6.9",
            "average": "5.0-5.9",
            "below_average": "4.0-4.9",
        },
    }

    # Add TOPSIS-specific metadata if using TOPSIS
    if use_topsis:
        metadata.update(
            {
                "topsis_ideal_solution": {
                    key: round(value, 6) for key, value in topsis_ideal_solution.items()
                },
                "topsis_anti_ideal_solution": {
                    key: round(value, 6) for key, value in topsis_anti_ideal_solution.items()
                },
                "topsis_persona_reference": topsis_persona_label,
            }
        )

    return {"type": "FeatureCollection", "features": features, "metadata": metadata}


@app.get("/api/infrastructure/transmission")
async def get_transmission_lines() -> Dict[str, Any]:
    lines = await query_supabase("transmission_lines?select=*")
    features: List[Dict[str, Any]] = []
    for line in lines or []:
        if not line.get("path_coordinates"):
            continue
        try:
            coordinates = json.loads(line["path_coordinates"])
        except (TypeError, json.JSONDecodeError):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coordinates},
                "properties": {
                    "name": line.get("line_name"),
                    "voltage_kv": line.get("voltage_kv"),
                    "operator": line.get("operator"),
                    "type": "transmission_line",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/substations")
async def get_substations() -> Dict[str, Any]:
    stations = await query_supabase("substations?select=*")
    features: List[Dict[str, Any]] = []
    for station in stations or []:
        lat = station.get("Lat") or station.get("latitude")
        lon = station.get("Long") or station.get("longitude")
        if lat is None or lon is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "name": station.get("SUBST_NAME"),
                    "operator": station.get("COMPANY"),
                    "voltage_kv": station.get("VOLTAGE_HIGH"),
                    "capacity_mva": station.get("capacity_mva"),
                    "constraint_status": station.get("CONSTRAINT STATUS"),
                    "type": "substation",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/gsp")
async def get_gsp_boundaries() -> Dict[str, Any]:
    boundaries = await query_supabase("electrical_grid?type=eq.gsp_boundary&select=*")
    features: List[Dict[str, Any]] = []
    for boundary in boundaries or []:
        geometry = boundary.get("geometry")
        if not geometry:
            continue
        if isinstance(geometry, str):
            try:
                geometry = json.loads(geometry)
            except json.JSONDecodeError:
                continue
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "name": boundary.get("name"),
                    "operator": boundary.get("operator", "NESO"),
                    "type": "gsp_boundary",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/fiber")
async def get_fiber_cables() -> Dict[str, Any]:
    cables = await query_supabase("fiber_cables?select=*")
    features: List[Dict[str, Any]] = []
    for cable in cables or []:
        if not cable.get("route_coordinates"):
            continue
        try:
            coordinates = json.loads(cable["route_coordinates"])
        except (TypeError, json.JSONDecodeError):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coordinates},
                "properties": {
                    "name": cable.get("cable_name"),
                    "operator": cable.get("operator"),
                    "cable_type": cable.get("cable_type"),
                    "type": "fiber_cable",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/tnuos")
async def get_tnuos_zones() -> Dict[str, Any]:
    zones = await query_supabase("tnuos_zones?tariff_year=eq.2024-25&select=*")
    features: List[Dict[str, Any]] = []
    for zone in zones or []:
        geometry = zone.get("geometry")
        if not geometry:
            continue
        if isinstance(geometry, str):
            try:
                geometry = json.loads(geometry)
            except json.JSONDecodeError:
                continue
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "zone_id": zone.get("zone_id"),
                    "zone_name": zone.get("zone_name"),
                    "tariff_pounds_per_kw": zone.get("generation_tariff_pounds_per_kw"),
                    "tariff_year": zone.get("tariff_year"),
                    "effective_from": zone.get("effective_from"),
                    "type": "tnuos_zone",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/ixp")
async def get_internet_exchanges() -> Dict[str, Any]:
    ixps = await query_supabase("internet_exchange_points?select=*")
    features: List[Dict[str, Any]] = []
    for ixp in ixps or []:
        if not ixp.get("longitude") or not ixp.get("latitude"):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [ixp["longitude"], ixp["latitude"]]},
                "properties": {
                    "name": ixp.get("ixp_name"),
                    "operator": ixp.get("operator"),
                    "city": ixp.get("city"),
                    "networks": ixp.get("connected_networks"),
                    "capacity_gbps": ixp.get("capacity_gbps"),
                    "type": "ixp",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/infrastructure/water")
async def get_water_resources() -> Dict[str, Any]:
    water_sources = await query_supabase("water_resources?select=*")
    features: List[Dict[str, Any]] = []
    for water in water_sources or []:
        if not water.get("coordinates"):
            continue
        try:
            coordinates = json.loads(water["coordinates"])
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(coordinates, (list, tuple)) and len(coordinates) == 2 and all(
            isinstance(coord, (int, float)) for coord in coordinates
        ):
            geometry = {"type": "Point", "coordinates": coordinates}
        else:
            geometry = {"type": "LineString", "coordinates": coordinates}
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "name": water.get("resource_name"),
                    "resource_type": water.get("resource_type"),
                    "water_quality": water.get("water_quality"),
                    "flow_rate": water.get("flow_rate_liters_sec"),
                    "capacity": water.get("capacity_million_liters"),
                    "type": "water_resource",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/projects/compare-scoring")
async def compare_scoring_systems(
    limit: int = Query(10, description="Projects to compare"),
    persona: PersonaType = Query("hyperscaler", description="Persona for comparison"),
) -> Dict[str, Any]:
    projects = await query_supabase(f"renewable_projects?select=*&limit={limit}")
    comparison: List[Dict[str, Any]] = []
    for project in projects:
        if not project.get("longitude") or not project.get("latitude"):
            continue
        dummy_proximity = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "nearest_distances": {},
        }
        renewable_rating = calculate_enhanced_investment_rating(project, dummy_proximity)
        persona_rating = calculate_persona_weighted_score(project, dummy_proximity, persona)
        comparison.append(
            {
                "site_name": project.get("site_name"),
                "capacity_mw": project.get("capacity_mw"),
                "technology_type": project.get("technology_type"),
                "renewable_energy_system": {
                    "investment_rating": renewable_rating["investment_rating"],
                    "rating_description": renewable_rating["rating_description"],
                    "color": renewable_rating["color_code"],
                },
                "persona_system": {
                    "persona": persona,
                    "investment_rating": persona_rating["investment_rating"],
                    "rating_description": persona_rating["rating_description"],
                    "color": persona_rating["color_code"],
                    "component_scores": persona_rating["component_scores"],
                    "weighted_contributions": persona_rating["weighted_contributions"],
                },
            }
        )
    return {
        "comparison": comparison,
        "summary": {
            "renewable_system": "Traditional renewable energy scoring (capacity, stage, tech)",
            "persona_system": f"{persona} data center scoring with custom weightings",
            "persona_weights": PERSONA_WEIGHTS[persona],
            "migration_benefits": [
                "Scoring tailored to specific data center requirements",
                "Transparent component breakdown showing why sites score differently",
                "Infrastructure priorities matching real deployment needs",
                "Better investment decision making for specific use cases",
            ],
        },
    }


@app.post("/api/projects/power-developer-analysis")
async def analyze_for_power_developer(
    criteria: Dict[str, Any],
    site_location: Optional[Dict[str, float]] = None,
    target_persona: PersonaType = "hyperscaler",
    limit: int = Query(150),
) -> Dict[str, Any]:
    source_table = "renewable_projects"
    print(f"🔄 Power Developer Analysis - Using {source_table} as placeholder for demand sites")
    projects = await query_supabase(f"{source_table}?select=*&limit={limit}")

    auto_calculated_values: Dict[str, Any] = {}
    if site_location and criteria:
        lat = site_location.get("lat")
        lng = site_location.get("lng")
        if lat is not None and lng is not None:
            proximity_list = await calculate_proximity_scores_batch(
                [{"latitude": lat, "longitude": lng}]
            )
            prox = proximity_list[0] if proximity_list else None
            if prox and criteria.get("grid_infrastructure") == -1:
                score = calculate_grid_infrastructure_score(prox)
                auto_calculated_values["grid_infrastructure"] = {
                    "score": score,
                    "details": prox.get("nearest_distances", {}),
                }
                criteria["grid_infrastructure"] = score
            if prox and criteria.get("digital_infrastructure") == -1:
                score = calculate_digital_infrastructure_score(prox)
                auto_calculated_values["digital_infrastructure"] = {
                    "score": score,
                    "details": prox.get("nearest_distances", {}),
                }
                criteria["digital_infrastructure"] = score
            if prox and criteria.get("water_resources") == -1:
                score = calculate_water_resources_score(prox)
                auto_calculated_values["water_resources"] = {
                    "score": score,
                    "details": prox.get("nearest_distances", {}),
                }
                criteria["water_resources"] = score

    return {
        "projects": projects,
        "criteria": criteria,
        "auto_calculated_values": auto_calculated_values,
        "target_persona": target_persona,
    }


@app.get("/api/projects/customer-match")
async def get_customer_match_projects(
    target_customer: PersonaType = Query("hyperscaler", description="Target customer persona"),
    limit: int = Query(1000, description="Number of projects to analyze"),
) -> Dict[str, Any]:
    projects = await query_supabase(f"renewable_projects?select=*&limit={limit}")
    filtered_projects = filter_projects_by_persona_capacity(projects, target_customer)

    customer_analysis: List[Dict[str, Any]] = []
    for project in filtered_projects:
        if not project.get("longitude") or not project.get("latitude"):
            continue
        dummy_proximity = {
            "substation_score": 0.0,
            "transmission_score": 0.0,
            "fiber_score": 0.0,
            "ixp_score": 0.0,
            "water_score": 0.0,
            "nearest_distances": {},
        }
        customer_match = calculate_best_customer_match(project, dummy_proximity)
        target_scoring = calculate_persona_weighted_score(project, dummy_proximity, target_customer)
        customer_analysis.append(
            {
                "project_id": project.get("ref_id"),
                "site_name": project.get("site_name"),
                "technology_type": project.get("technology_type"),
                "capacity_mw": project.get("capacity_mw"),
                "county": project.get("county"),
                "coordinates": [project.get("longitude"), project.get("latitude")],
                "target_customer": target_customer,
                "target_customer_score": target_scoring["investment_rating"],
                "target_customer_rating": target_scoring["rating_description"],
                "best_customer_match": customer_match["best_customer_match"],
                "customer_match_scores": customer_match["customer_match_scores"],
                "suitable_customers": customer_match["suitable_customers"],
                "component_scores": target_scoring["component_scores"],
                "weighted_contributions": target_scoring["weighted_contributions"],
            }
        )

    return {
        "target_customer": target_customer,
        "projects_analyzed": len(customer_analysis),
        "capacity_range": PERSONA_CAPACITY_RANGES[target_customer],
        "projects": customer_analysis,
        "metadata": {
            "algorithm_version": "2.3 - Bidirectional Customer Matching",
            "total_projects_before_filtering": len(projects),
            "projects_after_capacity_filtering": len(filtered_projects),
        },
    }

def map_technology_type(tech_string: str):
    if not FINANCIAL_MODEL_AVAILABLE:
        return "solar_pv"
    mapping = {
        "solar": TechnologyType.SOLAR_PV,
        "solar_pv": TechnologyType.SOLAR_PV,
        "wind": TechnologyType.WIND,
        "battery": TechnologyType.BATTERY,
        "solar_battery": TechnologyType.SOLAR_BATTERY,
        "solar_bess": TechnologyType.SOLAR_BATTERY,
        "wind_battery": TechnologyType.WIND_BATTERY,
    }
    return mapping.get(tech_string.lower(), TechnologyType.SOLAR_PV)


def create_technology_params(request: FinancialModelRequest) -> TechnologyParams:
    return TechnologyParams(
        capacity_mw=request.capacity_mw,
        capex_per_mw=request.capex_per_kw * 1000,
        opex_per_mw_year=request.opex_fix_per_mw_year,
        degradation_rate_annual=request.degradation,
        lifetime_years=request.project_life,
        capacity_factor=request.capacity_factor,
        battery_capacity_mwh=request.battery_capacity_mwh,
        battery_capex_per_mwh=request.battery_capex_per_mwh,
        battery_cycles_per_year=request.battery_cycles_per_year,
    )


def create_utility_market_prices(request: FinancialModelRequest) -> MarketPrices:
    return MarketPrices(
        base_power_price=request.merchant_price,
        power_price_escalation=0.025,
        ppa_price=request.ppa_price,
        ppa_duration_years=request.ppa_duration,
        ppa_escalation=request.ppa_escalation,
        ppa_percentage=0.7,
        capacity_payment=request.capacity_market_per_mw_year / 1000,
        frequency_response_price=(
            request.ancillary_per_mw_year / (8760 * 0.1) if request.ancillary_per_mw_year > 0 else 0
        ),
    )


def create_btm_market_prices(request: FinancialModelRequest) -> MarketPrices:
    annual_generation = request.capacity_mw * 8760 * request.capacity_factor
    grid_savings_per_mwh = (
        (request.grid_savings_factor * request.tnd_costs_per_year) / annual_generation
        if annual_generation > 0
        else 0
    )
    return MarketPrices(
        base_power_price=request.merchant_price,
        power_price_escalation=0.025,
        retail_electricity_price=request.ppa_price,
        retail_price_escalation=request.ppa_escalation,
        grid_charges=grid_savings_per_mwh,
        demand_charges=0,
    )


def extract_revenue_breakdown(cashflow_df) -> RevenueBreakdown:
    if cashflow_df is None or len(cashflow_df) == 0:
        return RevenueBreakdown(energyRev=0, capacityRev=0, ancillaryRev=0, gridSavings=0, opexTotal=0)
    operating_years = cashflow_df[cashflow_df["year"] > 0]
    energy_rev = 0.0
    capacity_rev = 0.0
    ancillary_rev = 0.0
    grid_savings = 0.0
    opex_total = operating_years["opex"].sum() if "opex" in operating_years.columns else 0.0
    for column in operating_years.columns:
        if not column.startswith("revenue_"):
            continue
        values = operating_years[column].sum()
        if "ppa" in column or "merchant" in column or "energy_savings" in column:
            energy_rev += values
        elif "capacity" in column:
            capacity_rev += values
        elif "frequency_response" in column or "ancillary" in column:
            ancillary_rev += values
        elif "grid_charges" in column:
            grid_savings += values
    return RevenueBreakdown(
        energyRev=energy_rev,
        capacityRev=capacity_rev,
        ancillaryRev=ancillary_rev,
        gridSavings=grid_savings,
        opexTotal=opex_total,
    )


@app.post("/api/financial-model", response_model=FinancialModelResponse)
async def calculate_financial_model(request: FinancialModelRequest) -> FinancialModelResponse:
    if not FINANCIAL_MODEL_AVAILABLE:
        raise HTTPException(500, "Financial model not available - renewable_model.py not found")
    try:
        print(f"🔄 Processing financial model request: {request.technology}, {request.capacity_mw}MW")
        tech_params = create_technology_params(request)
        financial_assumptions = FinancialAssumptions(
            discount_rate=request.discount_rate,
            inflation_rate=request.inflation_rate,
            tax_rate=request.tax_rate,
        )
        tech_type = map_technology_type(request.technology)
        utility_prices = create_utility_market_prices(request)
        utility_model = RenewableFinancialModel(
            project_name="Utility Scale Analysis",
            technology_type=tech_type,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=utility_prices,
            financial_assumptions=financial_assumptions,
        )
        btm_prices = create_btm_market_prices(request)
        btm_model = RenewableFinancialModel(
            project_name="Behind-the-Meter Analysis",
            technology_type=tech_type,
            project_type=ProjectType.BEHIND_THE_METER,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=btm_prices,
            financial_assumptions=financial_assumptions,
        )
        print("🔄 Running utility-scale analysis...")
        utility_results = utility_model.run_analysis()
        print("🔄 Running behind-the-meter analysis...")
        btm_results = btm_model.run_analysis()
        utility_cashflows = utility_model.cashflow_df["net_cashflow"].tolist()
        btm_cashflows = btm_model.cashflow_df["net_cashflow"].tolist()
        utility_breakdown = extract_revenue_breakdown(utility_model.cashflow_df)
        btm_breakdown = extract_revenue_breakdown(btm_model.cashflow_df)
        irr_uplift = (
            (btm_results["irr"] - utility_results["irr"]) if (btm_results["irr"] and utility_results["irr"]) else 0
        )
        npv_delta = btm_results["npv"] - utility_results["npv"]
        print(
            f"✅ Financial analysis complete: Utility IRR={utility_results['irr']:.3f}, "
            f"BTM IRR={btm_results['irr']:.3f}"
        )
        return FinancialModelResponse(
            standard=ModelResults(
                irr=utility_results["irr"],
                npv=utility_results["npv"],
                cashflows=utility_cashflows,
                breakdown=utility_breakdown,
                lcoe=utility_results["lcoe"],
                payback_simple=utility_results["payback_simple"],
                payback_discounted=utility_results["payback_discounted"],
            ),
            autoproducer=ModelResults(
                irr=btm_results["irr"],
                npv=btm_results["npv"],
                cashflows=btm_cashflows,
                breakdown=btm_breakdown,
                lcoe=btm_results["lcoe"],
                payback_simple=btm_results["payback_simple"],
                payback_discounted=btm_results["payback_discounted"],
            ),
            metrics={
                "total_capex": utility_results["capex_total"],
                "capex_per_mw": utility_results["capex_per_mw"],
                "irr_uplift": irr_uplift,
                "npv_delta": npv_delta,
                "annual_generation": request.capacity_mw * 8760 * request.capacity_factor,
            },
            success=True,
            message="Financial analysis completed successfully",
        )
    except Exception as exc:  # pragma: no cover - forward error to client
        import traceback
        error_msg = f"Financial model calculation failed: {exc}"
        print(f"❌ {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": error_msg, "error_type": type(exc).__name__},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)



