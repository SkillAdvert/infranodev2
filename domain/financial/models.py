"""Domain models for renewable financial analysis."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

import numpy as np


class TechnologyType(Enum):
    SOLAR_PV = "solar_pv"
    WIND = "wind"
    BATTERY = "battery"
    SOLAR_BATTERY = "solar_battery"
    WIND_BATTERY = "wind_battery"


class ProjectType(Enum):
    UTILITY_SCALE = "utility_scale"
    BEHIND_THE_METER = "behind_the_meter"


class MarketRegion(Enum):
    UK = "uk"
    IRELAND = "ireland"


@dataclass
class TechnologyParams:
    capacity_mw: float
    capex_per_mw: float
    opex_per_mw_year: float
    degradation_rate_annual: float = 0.005
    efficiency: float = 1.0
    lifetime_years: int = 25
    battery_capacity_mwh: Optional[float] = None
    battery_capex_per_mwh: Optional[float] = None
    battery_efficiency: float = 0.90
    battery_cycles_per_year: Optional[int] = None
    battery_degradation_rate: float = 0.02
    capacity_factor: Optional[float] = None
    system_losses: float = 0.14


@dataclass
class MarketPrices:
    base_power_price: float
    power_price_escalation: float = 0.025
    power_price_curve: Optional[List[float]] = None
    ppa_price: Optional[float] = None
    ppa_duration_years: int = 15
    ppa_escalation: float = 0.02
    ppa_percentage: float = 0.7
    capacity_payment: float = 0
    capacity_duration_years: int = 15
    capacity_derating_factor: float = 1.0
    frequency_response_price: float = 0
    reserve_price: float = 0
    ancillary_availability: float = 0.1
    retail_electricity_price: float = 150
    retail_price_escalation: float = 0.03
    grid_charges: float = 30
    demand_charges: float = 0


@dataclass
class FinancialAssumptions:
    discount_rate: float = 0.08
    inflation_rate: float = 0.02
    tax_rate: float = 0.19
    vat_rate: float = 0.20
    debt_ratio: float = 0
    debt_rate: float = 0
    debt_term_years: int = 0
    working_capital_days: int = 30
    dsra_months: int = 0


@dataclass
class GenerationProfile:
    hourly_generation: Optional[np.ndarray] = None
    hourly_consumption: Optional[np.ndarray] = None
    monthly_generation: Optional[np.ndarray] = None

    def get_annual_generation(
        self, capacity_mw: float, year: int = 1, degradation: float = 0
    ) -> float:
        degradation_factor = (1 - degradation) ** (year - 1)

        if self.hourly_generation is not None:
            return float(np.sum(self.hourly_generation) * capacity_mw * degradation_factor)
        if self.monthly_generation is not None:
            return float(np.sum(self.monthly_generation) * capacity_mw * degradation_factor)
        raise ValueError("No generation profile provided")


__all__ = [
    "FinancialAssumptions",
    "GenerationProfile",
    "MarketPrices",
    "MarketRegion",
    "ProjectType",
    "TechnologyParams",
    "TechnologyType",
]
