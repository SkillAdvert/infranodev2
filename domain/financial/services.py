"""Service layer orchestrating renewable financial scenarios."""
from typing import Dict, List, Optional

from pydantic import BaseModel

from .models import (
    FinancialAssumptions,
    MarketPrices,
    MarketRegion,
    ProjectType,
    TechnologyParams,
    TechnologyType,
)
from .simulation import RenewableFinancialModel


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


def map_technology_type(tech_string: str) -> TechnologyType:
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
        frequency_response_price=request.ancillary_per_mw_year / (8760 * 0.1) if request.ancillary_per_mw_year else 0,
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


def extract_cashflows(model: RenewableFinancialModel) -> List[float]:
    if model.cashflow_df is None:
        model.build_cashflow_model()
    return [float(value) for value in model.cashflow_df["net_cashflow"].tolist()]


def run_financial_models(request: FinancialModelRequest) -> Dict[str, object]:
    tech_params = create_technology_params(request)
    financial_assumptions = FinancialAssumptions(
        discount_rate=request.discount_rate,
        inflation_rate=request.inflation_rate,
        tax_rate=request.tax_rate,
    )

    standard_model = RenewableFinancialModel(
        project_name="Utility Scale",
        technology_type=map_technology_type(request.technology),
        project_type=ProjectType.UTILITY_SCALE,
        market_region=MarketRegion.UK,
        technology_params=tech_params,
        market_prices=create_utility_market_prices(request),
        financial_assumptions=financial_assumptions,
    )

    autoproducer_model = RenewableFinancialModel(
        project_name="Behind the Meter",
        technology_type=map_technology_type(request.technology),
        project_type=ProjectType.BEHIND_THE_METER,
        market_region=MarketRegion.UK,
        technology_params=tech_params,
        market_prices=create_btm_market_prices(request),
        financial_assumptions=financial_assumptions,
    )

    standard_results = standard_model.run_analysis()
    autoproducer_results = autoproducer_model.run_analysis()

    return FinancialModelResponse(
        standard=_to_model_results(standard_results, standard_model),
        autoproducer=_to_model_results(autoproducer_results, autoproducer_model),
        metrics={
            "capex": standard_results["capex_total"],
            "lcoe": standard_results["lcoe"],
            "irr_delta": autoproducer_results["irr"] - standard_results["irr"],
        },
        success=True,
        message="Financial model calculated",
    )


__all__ = [
    "FinancialModelRequest",
    "FinancialModelResponse",
    "ModelResults",
    "RevenueBreakdown",
    "create_btm_market_prices",
    "create_technology_params",
    "create_utility_market_prices",
    "map_technology_type",
    "run_financial_models",
]


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


def _to_model_results(results: Dict[str, float], model: RenewableFinancialModel) -> ModelResults:
    if model.cashflow_df is None:
        model.build_cashflow_model()
    opex_total = float(model.cashflow_df["opex"].sum()) if model.cashflow_df is not None else 0.0
    return ModelResults(
        irr=results["irr"],
        npv=results["npv"],
        cashflows=extract_cashflows(model),
        breakdown=RevenueBreakdown(
            energyRev=float(
                results.get("year1_revenue_ppa", 0)
                + results.get("year1_revenue_merchant", 0)
                + results.get("year1_revenue_energy_savings", 0)
            ),
            capacityRev=float(results.get("year1_revenue_capacity", 0)),
            ancillaryRev=float(results.get("year1_revenue_frequency_response", 0)),
            gridSavings=float(results.get("year1_revenue_grid_charges_avoided", 0)),
            opexTotal=opex_total,
        ),
        lcoe=results["lcoe"],
        payback_simple=results["payback_simple"],
        payback_discounted=results["payback_discounted"],
    )
