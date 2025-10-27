"""Financial model functions for renewable energy projects."""

from __future__ import annotations

from models import FinancialModelRequest, RevenueBreakdown

# Check if financial model is available
try:
    from backend.renewable_model import (
        MarketPrices,
        TechnologyParams,
        TechnologyType,
    )
    FINANCIAL_MODEL_AVAILABLE = True
except ImportError:
    FINANCIAL_MODEL_AVAILABLE = False


def map_technology_type(tech_string: str):
    """Map technology string to TechnologyType enum."""
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
    """Create technology parameters from financial model request."""
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
    """Create market prices for utility-scale project."""
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
    """Create market prices for behind-the-meter project."""
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
    """Extract revenue breakdown from cashflow dataframe."""
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
