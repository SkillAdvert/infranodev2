"""Data models for the Infranodal API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel


# ============================================================================
# USER-FACING MODELS
# ============================================================================


class UserSite(BaseModel):
    """User-submitted site for scoring."""

    site_name: str
    technology_type: str
    capacity_mw: float
    latitude: float
    longitude: float
    commissioning_year: int
    is_btm: bool
    capacity_factor: Optional[float] = None
    development_status_short: Optional[str] = "planning"


class FinancialModelRequest(BaseModel):
    """Request for financial model calculation."""

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
    """Breakdown of revenue components."""

    energyRev: float
    capacityRev: float
    ancillaryRev: float
    gridSavings: float
    opexTotal: float


class ModelResults(BaseModel):
    """Results from financial model calculation."""

    irr: Optional[float]
    npv: float
    cashflows: List[float]
    breakdown: RevenueBreakdown
    lcoe: float
    payback_simple: Optional[float]
    payback_discounted: Optional[float]


class FinancialModelResponse(BaseModel):
    """Response from financial model endpoint."""

    standard: ModelResults
    autoproducer: ModelResults
    metrics: Dict[str, float]
    success: bool
    message: str


# ============================================================================
# TEC CONNECTION MODELS
# ============================================================================


class TecConnectionProperties(BaseModel):
    """Properties for a TEC connection."""

    id: Union[int, str]
    project_name: str
    operator: Optional[str] = None
    customer_name: Optional[str] = None
    capacity_mw: Optional[float] = None
    mw_delta: Optional[float] = None
    technology_type: Optional[str] = None
    plant_type: Optional[str] = None
    project_status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    connection_site: Optional[str] = None
    substation_name: Optional[str] = None
    voltage: Optional[float] = None
    constraint_status: Optional[str] = None
    created_at: Optional[str] = None
    agreement_type: Optional[str] = None
    effective_from: Optional[str] = None


class TecConnectionGeometry(BaseModel):
    """Geometry for a TEC connection (GeoJSON)."""

    type: str = "Point"
    coordinates: List[float]


class TecConnectionFeature(BaseModel):
    """GeoJSON feature for a TEC connection."""

    type: str = "Feature"
    geometry: TecConnectionGeometry
    properties: TecConnectionProperties
    id: Optional[str] = None


class TecConnectionsResponse(BaseModel):
    """Response containing multiple TEC connections."""

    type: str = "FeatureCollection"
    features: List[TecConnectionFeature]
    count: int


# ============================================================================
# INFRASTRUCTURE MODELS (Dataclasses)
# ============================================================================


@dataclass
class PointFeature:
    """Represents a point infrastructure feature."""

    lat: float
    lon: float
    data: Dict[str, Any]


@dataclass
class LineFeature:
    """Represents a line infrastructure feature."""

    coordinates: List[Tuple[float, float]]
    segments: List[Tuple[float, float, float, float]]
    bbox: Tuple[float, float, float, float]
    data: Dict[str, Any]


@dataclass
class InfrastructureCatalog:
    """Complete infrastructure catalog with all features and indices."""

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
