"""Simulation engine for renewable financial models."""
from __future__ import annotations

from typing import Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd

from .models import (
    FinancialAssumptions,
    GenerationProfile,
    MarketPrices,
    MarketRegion,
    ProjectType,
    TechnologyParams,
    TechnologyType,
)


class RenewableFinancialModel:
    """Main financial model class."""

    def __init__(
        self,
        project_name: str,
        technology_type: TechnologyType,
        project_type: ProjectType,
        market_region: MarketRegion,
        technology_params: TechnologyParams,
        market_prices: MarketPrices,
        financial_assumptions: FinancialAssumptions,
        generation_profile: Optional[GenerationProfile] = None,
    ) -> None:
        self.project_name = project_name
        self.technology_type = technology_type
        self.project_type = project_type
        self.market_region = market_region
        self.tech_params = technology_params
        self.market_prices = market_prices
        self.financial = financial_assumptions
        self.generation_profile = generation_profile
        self.cashflow_df: Optional[pd.DataFrame] = None
        self.results: Dict[str, Union[str, float, Optional[float]]] = {}

    def calculate_capex(self) -> float:
        capex = self.tech_params.capacity_mw * self.tech_params.capex_per_mw
        if self.technology_type in [TechnologyType.SOLAR_BATTERY, TechnologyType.WIND_BATTERY]:
            if self.tech_params.battery_capacity_mwh and self.tech_params.battery_capex_per_mwh:
                capex += (
                    self.tech_params.battery_capacity_mwh * self.tech_params.battery_capex_per_mwh
                )
        return capex

    def calculate_annual_generation(self, year: int) -> Dict[str, float]:
        generation: Dict[str, float] = {}

        if self.technology_type in [TechnologyType.SOLAR_PV, TechnologyType.SOLAR_BATTERY]:
            degradation_factor = (1 - self.tech_params.degradation_rate_annual) ** (year - 1)
            if self.generation_profile and self.generation_profile.hourly_generation is not None:
                base_generation = (
                    float(np.sum(self.generation_profile.hourly_generation))
                    * self.tech_params.capacity_mw
                )
            else:
                hours_per_year = 8760
                capacity_factor = 0.11 if self.market_region == MarketRegion.UK else 0.10
                base_generation = self.tech_params.capacity_mw * hours_per_year * capacity_factor

            generation["solar"] = (
                base_generation * degradation_factor * (1 - self.tech_params.system_losses)
            )

        elif self.technology_type in [TechnologyType.WIND, TechnologyType.WIND_BATTERY]:
            degradation_factor = (1 - self.tech_params.degradation_rate_annual) ** (year - 1)
            if self.generation_profile and self.generation_profile.hourly_generation is not None:
                base_generation = (
                    float(np.sum(self.generation_profile.hourly_generation))
                    * self.tech_params.capacity_mw
                )
            else:
                hours_per_year = 8760
                capacity_factor = self.tech_params.capacity_factor or 0.30
                base_generation = self.tech_params.capacity_mw * hours_per_year * capacity_factor

            generation["wind"] = base_generation * degradation_factor

        if self.technology_type in [TechnologyType.BATTERY, TechnologyType.SOLAR_BATTERY, TechnologyType.WIND_BATTERY]:
            if self.tech_params.battery_capacity_mwh and self.tech_params.battery_cycles_per_year:
                battery_degradation = (1 - self.tech_params.battery_degradation_rate) ** (year - 1)
                generation["battery_throughput"] = (
                    self.tech_params.battery_capacity_mwh
                    * self.tech_params.battery_cycles_per_year
                    * battery_degradation
                )

        return generation

    def _get_power_price(self, year: int) -> float:
        if not year or year < 1:
            raise ValueError(f"Invalid year: {year}")

        if self.market_prices.power_price_curve and year <= len(self.market_prices.power_price_curve):
            return self.market_prices.power_price_curve[year - 1]
        if not self.market_prices.base_power_price:
            raise ValueError("No base power price provided and no price curve available")
        power_price_escalation = (1 + self.market_prices.power_price_escalation) ** (year - 1)
        return self.market_prices.base_power_price * power_price_escalation

    def calculate_revenues(self, year: int, generation: Dict[str, float]) -> Dict[str, float]:
        revenues: Dict[str, float] = {}
        total_generation = sum(g for key, g in generation.items() if key != "battery_throughput")

        if self.project_type == ProjectType.UTILITY_SCALE:
            if self.market_prices.ppa_price and year <= self.market_prices.ppa_duration_years:
                ppa_escalation = (1 + self.market_prices.ppa_escalation) ** (year - 1)
                ppa_generation = total_generation * self.market_prices.ppa_percentage
                revenues["ppa"] = ppa_generation * self.market_prices.ppa_price * ppa_escalation
                merchant_generation = total_generation * (1 - self.market_prices.ppa_percentage)
            else:
                merchant_generation = total_generation

            power_price = self._get_power_price(year)
            revenues["merchant"] = merchant_generation * power_price

            if self.market_prices.capacity_payment > 0 and year <= self.market_prices.capacity_duration_years:
                capacity_mw = self.tech_params.capacity_mw * self.market_prices.capacity_derating_factor
                revenues["capacity"] = capacity_mw * self.market_prices.capacity_payment * 1000

            if self.market_prices.frequency_response_price > 0:
                ancillary_hours = 8760 * self.market_prices.ancillary_availability
                revenues["frequency_response"] = (
                    self.tech_params.capacity_mw
                    * self.market_prices.frequency_response_price
                    * ancillary_hours
                )

            if "battery_throughput" in generation:
                power_price = self._get_power_price(year)
                price_spread = power_price * 0.3
                revenues["battery_arbitrage"] = (
                    generation["battery_throughput"] * price_spread * self.tech_params.battery_efficiency
                )

        elif self.project_type == ProjectType.BEHIND_THE_METER:
            base_price = self.market_prices.base_power_price or 45.0
            if self.market_prices.power_price_curve and year <= len(self.market_prices.power_price_curve):
                power_price = self.market_prices.power_price_curve[year - 1]
            else:
                power_price_escalation = (1 + self.market_prices.power_price_escalation) ** (year - 1)
                power_price = base_price * power_price_escalation

            retail_escalation = (1 + self.market_prices.retail_price_escalation) ** (year - 1)
            retail_price = self.market_prices.retail_electricity_price * retail_escalation

            revenues["energy_savings"] = total_generation * retail_price
            revenues["grid_charges_avoided"] = total_generation * self.market_prices.grid_charges

            if self.market_prices.demand_charges > 0:
                if self.tech_params.battery_capacity_mwh:
                    monthly_savings = (
                        self.tech_params.battery_capacity_mwh * self.market_prices.demand_charges
                    )
                    revenues["demand_charge_savings"] = monthly_savings * 12

            if self.generation_profile and self.generation_profile.hourly_consumption is not None:
                hourly_gen = self.generation_profile.hourly_generation * self.tech_params.capacity_mw
                hourly_consumption = self.generation_profile.hourly_consumption
                hourly_export = np.maximum(hourly_gen - hourly_consumption, 0)
                export_generation = float(np.sum(hourly_export))
            else:
                export_generation = total_generation * 0.3

            export_price = power_price * 0.9
            revenues["export"] = export_generation * export_price

        return revenues

    def calculate_opex(self, year: int) -> Dict[str, float]:
        opex: Dict[str, float] = {}
        inflation_factor = (1 + self.financial.inflation_rate) ** (year - 1)
        opex["om_fixed"] = (
            self.tech_params.capacity_mw * self.tech_params.opex_per_mw_year * inflation_factor
        )

        if self.tech_params.battery_capacity_mwh and year % 10 == 0:
            opex["battery_overhaul"] = (
                self.tech_params.battery_capacity_mwh
                * self.tech_params.battery_capex_per_mwh
                * 0.3
            )

        opex["insurance"] = self.calculate_capex() * 0.01 * inflation_factor

        if self.project_type == ProjectType.UTILITY_SCALE:
            opex["land_lease"] = self.tech_params.capacity_mw * 1000 * inflation_factor

        return opex

    def build_cashflow_model(self) -> pd.DataFrame:
        years = range(0, self.tech_params.lifetime_years + 1)
        cashflow_data = []

        for year in years:
            row: Dict[str, Union[int, float]] = {"year": year}
            if year == 0:
                row["capex"] = -self.calculate_capex()
                row["revenues"] = 0
                row["opex"] = 0
                row["ebitda"] = row["revenues"] - row["opex"]
                row["tax"] = 0
                row["net_cashflow"] = row["capex"]
            else:
                generation = self.calculate_annual_generation(year)
                revenues = self.calculate_revenues(year, generation)
                opex = self.calculate_opex(year)

                row["capex"] = 0
                row["generation_mwh"] = sum(
                    g for key, g in generation.items() if key != "battery_throughput"
                )

                for rev_stream, value in revenues.items():
                    row[f"revenue_{rev_stream}"] = value
                row["revenues"] = sum(revenues.values())

                for cost_item, value in opex.items():
                    row[f"opex_{cost_item}"] = value
                row["opex"] = sum(opex.values())

                row["ebitda"] = row["revenues"] - row["opex"]
                row["depreciation"] = self.calculate_capex() / self.tech_params.lifetime_years
                row["ebt"] = row["ebitda"] - row["depreciation"]
                row["tax"] = max(0, row["ebt"] * self.financial.tax_rate)
                row["net_income"] = row["ebt"] - row["tax"]
                row["net_cashflow"] = row["ebitda"] - row["tax"]

            row["discount_factor"] = 1 / (1 + self.financial.discount_rate) ** year
            row["pv_cashflow"] = row["net_cashflow"] * row["discount_factor"]
            cashflow_data.append(row)

        self.cashflow_df = pd.DataFrame(cashflow_data)
        return self.cashflow_df

    def calculate_lcoe(self) -> float:
        if self.cashflow_df is None:
            self.build_cashflow_model()

        pv_generation = 0.0
        for year in range(1, self.tech_params.lifetime_years + 1):
            generation = float(
                self.cashflow_df.loc[self.cashflow_df["year"] == year, "generation_mwh"].values[0]
            )
            discount_factor = 1 / (1 + self.financial.discount_rate) ** year
            pv_generation += generation * discount_factor

        pv_costs = abs(
            float(self.cashflow_df.loc[self.cashflow_df["year"] == 0, "capex"].values[0])
        )
        for year in range(1, self.tech_params.lifetime_years + 1):
            opex = float(self.cashflow_df.loc[self.cashflow_df["year"] == year, "opex"].values[0])
            discount_factor = 1 / (1 + self.financial.discount_rate) ** year
            pv_costs += opex * discount_factor

        if pv_generation <= 0:
            return float("inf")
        return (pv_costs / 1000) / pv_generation

    def calculate_irr(self) -> float:
        if self.cashflow_df is None:
            self.build_cashflow_model()
        cashflows = self.cashflow_df["net_cashflow"].values
        try:
            irr = float(np.irr(cashflows))
        except Exception:
            irr = self._calculate_irr_newton(cashflows)
        return irr

    def _calculate_irr_newton(self, cashflows: np.ndarray, max_iter: int = 100) -> float:
        rate = 0.1
        tolerance = 1e-6

        for _ in range(max_iter):
            npv = 0.0
            dnpv = 0.0
            for t, cf in enumerate(cashflows):
                npv += cf / (1 + rate) ** t
                dnpv -= t * cf / (1 + rate) ** (t + 1)

            if abs(dnpv) < tolerance:
                break

            rate_new = rate - npv / dnpv
            if abs(rate_new - rate) < tolerance:
                return rate_new
            rate = rate_new

        return rate

    def calculate_npv(self) -> float:
        if self.cashflow_df is None:
            self.build_cashflow_model()
        return float(self.cashflow_df["pv_cashflow"].sum())

    def calculate_payback_period(self) -> Tuple[float, float]:
        if self.cashflow_df is None:
            self.build_cashflow_model()

        cumulative_cf = self.cashflow_df["net_cashflow"].cumsum()
        simple_payback: Optional[float] = None
        for idx, value in cumulative_cf.items():
            if value > 0:
                simple_payback = float(self.cashflow_df.loc[idx, "year"])
                if idx > 0:
                    prev_value = float(cumulative_cf.iloc[idx - 1])
                    current_cf = float(self.cashflow_df.loc[idx, "net_cashflow"])
                    simple_payback -= prev_value / current_cf
                break

        cumulative_pv = self.cashflow_df["pv_cashflow"].cumsum()
        discounted_payback: Optional[float] = None
        for idx, value in cumulative_pv.items():
            if value > 0:
                discounted_payback = float(self.cashflow_df.loc[idx, "year"])
                if idx > 0:
                    prev_value = float(cumulative_pv.iloc[idx - 1])
                    current_pv = float(self.cashflow_df.loc[idx, "pv_cashflow"])
                    discounted_payback -= prev_value / current_pv
                break

        return simple_payback or float("nan"), discounted_payback or float("nan")

    def run_analysis(self) -> Dict[str, Union[str, float, Optional[float]]]:
        self.build_cashflow_model()
        payback_simple, payback_discounted = self.calculate_payback_period()
        self.results = {
            "project_name": self.project_name,
            "technology": self.technology_type.value,
            "project_type": self.project_type.value,
            "market_region": self.market_region.value,
            "capacity_mw": self.tech_params.capacity_mw,
            "capex_total": self.calculate_capex(),
            "capex_per_mw": self.calculate_capex() / self.tech_params.capacity_mw,
            "irr": self.calculate_irr(),
            "npv": self.calculate_npv(),
            "lcoe": self.calculate_lcoe(),
            "payback_simple": payback_simple,
            "payback_discounted": payback_discounted,
            "total_generation_lifetime_mwh": float(self.cashflow_df["generation_mwh"].sum()),
            "year1_revenues": float(
                self.cashflow_df.loc[self.cashflow_df["year"] == 1, "revenues"].values[0]
            ),
        }

        year1_row = self.cashflow_df[self.cashflow_df["year"] == 1].iloc[0]
        revenue_streams = [col for col in self.cashflow_df.columns if col.startswith("revenue_")]
        for stream in revenue_streams:
            self.results[f"year1_{stream}"] = float(year1_row[stream])

        return self.results

    def export_results(self, format: str = "json") -> Union[str, pd.DataFrame]:
        from datetime import datetime

        if format == "json":
            import json

            export_data = {
                "summary": self.results,
                "cashflow": self.cashflow_df.to_dict("records") if self.cashflow_df is not None else None,
                "timestamp": datetime.now().isoformat(),
                "model_version": "1.0.0",
            }
            return json.dumps(export_data, indent=2, default=str)
        if format == "dataframe":
            return self.cashflow_df
        if format == "summary":
            return pd.DataFrame([self.results])
        raise ValueError(f"Unsupported export format: {format}")


__all__ = ["RenewableFinancialModel"]
