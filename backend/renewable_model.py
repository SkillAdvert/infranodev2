"""
Renewable Energy Financial Model for UK/Ireland Markets
Supports: Solar PV, Wind, Battery Storage, Hybrid Systems
Markets: Utility-scale and Behind-the-Meter
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Tuple
from enum import Enum
import json
from datetime import datetime, timedelta

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
    """Technology-specific parameters"""
    capacity_mw: float
    capex_per_mw: float
    opex_per_mw_year: float
    degradation_rate_annual: float = 0.005  # 0.5% for solar
    efficiency: float = 1.0
    lifetime_years: int = 25
    
    # Battery specific
    battery_capacity_mwh: Optional[float] = None
    battery_capex_per_mwh: Optional[float] = None
    battery_efficiency: float = 0.90  # Round-trip efficiency
    battery_cycles_per_year: Optional[int] = None
    battery_degradation_rate: float = 0.02  # 2% annual
    
    # Wind specific
    capacity_factor: Optional[float] = None
    
    # Solar specific
    system_losses: float = 0.14  # DC to AC losses, soiling, etc.

@dataclass
class MarketPrices:
    """Market price inputs and projections"""
    base_power_price: float  # £/MWh
    power_price_escalation: float = 0.025  # 2.5% annual
    power_price_curve: Optional[List[float]] = None  # Override with specific curve
    
    ppa_price: Optional[float] = None  # £/MWh for contracted portion
    ppa_duration_years: int = 15
    ppa_escalation: float = 0.02
    ppa_percentage: float = 0.7  # Percentage of generation under PPA
    
    # Capacity market (UK/Ireland specific)
    capacity_payment: float = 0  # £/kW/year
    capacity_duration_years: int = 15
    capacity_derating_factor: float = 1.0  # Technology-specific derating
    
    # Ancillary services
    frequency_response_price: float = 0  # £/MW/hour
    reserve_price: float = 0  # £/MW/hour
    ancillary_availability: float = 0.1  # Percentage of time available
    
    # Behind-the-meter specific
    retail_electricity_price: float = 150  # £/MWh
    retail_price_escalation: float = 0.03
    grid_charges: float = 30  # £/MWh avoided
    demand_charges: float = 0  # £/kW/month

@dataclass
class FinancialAssumptions:
    """Core financial assumptions"""
    discount_rate: float = 0.08  # 8% WACC
    inflation_rate: float = 0.02
    tax_rate: float = 0.19  # UK corporation tax
    vat_rate: float = 0.20
    
    # Debt assumptions (if needed later)
    debt_ratio: float = 0
    debt_rate: float = 0
    debt_term_years: int = 0
    
    # Working capital
    working_capital_days: int = 30
    dsra_months: int = 0  # Debt service reserve account

@dataclass
class GenerationProfile:
    """Generation and consumption profiles"""
    hourly_generation: Optional[np.ndarray] = None  # 8760 hours
    hourly_consumption: Optional[np.ndarray] = None  # For BTM projects
    monthly_generation: Optional[np.ndarray] = None  # Alternative to hourly
    
    def get_annual_generation(self, capacity_mw: float, year: int = 1, degradation: float = 0) -> float:
        """Calculate annual generation accounting for degradation"""
        degradation_factor = (1 - degradation) ** (year - 1)
        
        if self.hourly_generation is not None:
            return np.sum(self.hourly_generation) * capacity_mw * degradation_factor
        elif self.monthly_generation is not None:
            return np.sum(self.monthly_generation) * capacity_mw * degradation_factor
        else:
            raise ValueError("No generation profile provided")

class RenewableFinancialModel:
    """Main financial model class"""
    
    def __init__(
        self,
        project_name: str,
        technology_type: TechnologyType,
        project_type: ProjectType,
        market_region: MarketRegion,
        technology_params: TechnologyParams,
        market_prices: MarketPrices,
        financial_assumptions: FinancialAssumptions,
        generation_profile: Optional[GenerationProfile] = None
    ):
        self.project_name = project_name
        self.technology_type = technology_type
        self.project_type = project_type
        self.market_region = market_region
        self.tech_params = technology_params
        self.market_prices = market_prices
        self.financial = financial_assumptions
        self.generation_profile = generation_profile
        
        # Initialize results storage
        self.cashflow_df: Optional[pd.DataFrame] = None
        self.results: Dict = {}
        
    def calculate_capex(self) -> float:
        """Calculate total capital expenditure"""
        capex = self.tech_params.capacity_mw * self.tech_params.capex_per_mw
        
        # Add battery capex if hybrid system
        if self.technology_type in [TechnologyType.SOLAR_BATTERY, TechnologyType.WIND_BATTERY]:
            if self.tech_params.battery_capacity_mwh and self.tech_params.battery_capex_per_mwh:
                capex += self.tech_params.battery_capacity_mwh * self.tech_params.battery_capex_per_mwh
        
        return capex
    
    def calculate_annual_generation(self, year: int) -> Dict[str, float]:
        """Calculate annual generation by source"""
        generation = {}
        
        if self.technology_type in [TechnologyType.SOLAR_PV, TechnologyType.SOLAR_BATTERY]:
            # Solar generation with degradation
            degradation_factor = (1 - self.tech_params.degradation_rate_annual) ** (year - 1)
            if self.generation_profile and self.generation_profile.hourly_generation is not None:
                base_generation = np.sum(self.generation_profile.hourly_generation) * self.tech_params.capacity_mw
            else:
                # Simplified calculation based on capacity factor
                hours_per_year = 8760
                capacity_factor = 0.11 if self.market_region == MarketRegion.UK else 0.10  # UK/Ireland typical
                base_generation = self.tech_params.capacity_mw * hours_per_year * capacity_factor
            
            generation['solar'] = base_generation * degradation_factor * (1 - self.tech_params.system_losses)
        
        elif self.technology_type in [TechnologyType.WIND, TechnologyType.WIND_BATTERY]:
            # Wind generation with degradation
            degradation_factor = (1 - self.tech_params.degradation_rate_annual) ** (year - 1)
            if self.generation_profile and self.generation_profile.hourly_generation is not None:
                base_generation = np.sum(self.generation_profile.hourly_generation) * self.tech_params.capacity_mw
            else:
                # Use capacity factor
                hours_per_year = 8760
                capacity_factor = self.tech_params.capacity_factor or 0.30  # Typical onshore wind
                base_generation = self.tech_params.capacity_mw * hours_per_year * capacity_factor
            
            generation['wind'] = base_generation * degradation_factor
        
        # Battery arbitrage (simplified)
        if self.technology_type in [TechnologyType.BATTERY, TechnologyType.SOLAR_BATTERY, TechnologyType.WIND_BATTERY]:
            if self.tech_params.battery_capacity_mwh and self.tech_params.battery_cycles_per_year:
                battery_degradation = (1 - self.tech_params.battery_degradation_rate) ** (year - 1)
                generation['battery_throughput'] = (
                    self.tech_params.battery_capacity_mwh * 
                    self.tech_params.battery_cycles_per_year * 
                    battery_degradation
                )
        
        return generation
    
    def calculate_revenues(self, year: int, generation: Dict[str, float]) -> Dict[str, float]:
        print(f"DEBUG: calculate_revenues called for year {year}, project_type: {self.project_type}")
        """Calculate all revenue streams"""
        revenues = {}
        
        total_generation = sum([g for k, g in generation.items() if k != 'battery_throughput'])
        
        if self.project_type == ProjectType.UTILITY_SCALE:
            # PPA revenues
            if self.market_prices.ppa_price and year <= self.market_prices.ppa_duration_years:
                ppa_escalation = (1 + self.market_prices.ppa_escalation) ** (year - 1)
                ppa_generation = total_generation * self.market_prices.ppa_percentage
                revenues['ppa'] = ppa_generation * self.market_prices.ppa_price * ppa_escalation
                
                # Merchant revenues (remaining generation)
                merchant_generation = total_generation * (1 - self.market_prices.ppa_percentage)
            else:
                merchant_generation = total_generation
            
            # Merchant power revenues
            if self.market_prices.power_price_curve and year <= len(self.market_prices.power_price_curve):
                power_price = self.market_prices.power_price_curve[year - 1]
            else:
                power_price_escalation = (1 + self.market_prices.power_price_escalation) ** (year - 1)
                power_price = self.market_prices.base_power_price * power_price_escalation
            
            revenues['merchant'] = merchant_generation * power_price
            
            # Capacity market revenues
            if self.market_prices.capacity_payment > 0 and year <= self.market_prices.capacity_duration_years:
                capacity_mw = self.tech_params.capacity_mw * self.market_prices.capacity_derating_factor
                revenues['capacity'] = capacity_mw * self.market_prices.capacity_payment * 1000  # Convert to £/MW
            
            # Ancillary services
            if self.market_prices.frequency_response_price > 0:
                ancillary_hours = 8760 * self.market_prices.ancillary_availability
                revenues['frequency_response'] = (
                    self.tech_params.capacity_mw * 
                    self.market_prices.frequency_response_price * 
                    ancillary_hours
                )
            
            # Battery arbitrage revenues
            if 'battery_throughput' in generation:
                # Simplified arbitrage calculation
                price_spread = power_price * 0.3  # Assume 30% average price spread
                revenues['battery_arbitrage'] = (
                    generation['battery_throughput'] * 
                    price_spread * 
                    self.tech_params.battery_efficiency
                )
        
        elif self.project_type == ProjectType.BEHIND_THE_METER:
            # Calculate self-consumption savings
            retail_escalation = (1 + self.market_prices.retail_price_escalation) ** (year - 1)
            retail_price = self.market_prices.retail_electricity_price * retail_escalation
            
            # Energy cost savings
            revenues['energy_savings'] = total_generation * retail_price
            
            # Grid charges avoided
            revenues['grid_charges_avoided'] = total_generation * self.market_prices.grid_charges
            
            # Demand charge savings (if applicable)
            if self.market_prices.demand_charges > 0:
                # Simplified - assume reduces peak by battery capacity
                if self.tech_params.battery_capacity_mwh:
                    monthly_savings = self.tech_params.battery_capacity_mwh * self.market_prices.demand_charges
                    revenues['demand_charge_savings'] = monthly_savings * 12
            
            # Export revenues (if generation exceeds consumption)
            if self.generation_profile and self.generation_profile.hourly_consumption is not None:
                # Calculate actual export based on profiles
                hourly_gen = self.generation_profile.hourly_generation * self.tech_params.capacity_mw
                hourly_consumption = self.generation_profile.hourly_consumption
                hourly_export = np.maximum(hourly_gen - hourly_consumption, 0)
                export_generation = np.sum(hourly_export)
            else:
                # Simplified assumption: 30% exported
                export_generation = total_generation * 0.3
            
            export_price = power_price * 0.9  # Assume 90% of wholesale price for exports
            revenues['export'] = export_generation * export_price
        
        return revenues
    
    def calculate_opex(self, year: int) -> Dict[str, float]:
        """Calculate operating expenses"""
        opex = {}
        
        # Base O&M costs
        inflation_factor = (1 + self.financial.inflation_rate) ** (year - 1)
        opex['om_fixed'] = self.tech_params.capacity_mw * self.tech_params.opex_per_mw_year * inflation_factor
        
        # Battery replacement costs (simplified - major overhaul every 10 years)
        if self.tech_params.battery_capacity_mwh and year % 10 == 0:
            opex['battery_overhaul'] = self.tech_params.battery_capacity_mwh * self.tech_params.battery_capex_per_mwh * 0.3
        
        # Insurance (1% of capex)
        opex['insurance'] = self.calculate_capex() * 0.01 * inflation_factor
        
        # Land lease (if utility scale)
        if self.project_type == ProjectType.UTILITY_SCALE:
            opex['land_lease'] = self.tech_params.capacity_mw * 1000 * inflation_factor  # £1000/MW/year
        
        return opex
    
    def build_cashflow_model(self) -> pd.DataFrame:
        """Build complete cashflow model"""
        years = range(0, self.tech_params.lifetime_years + 1)
        cashflow_data = []
        
        for year in years:
            row = {'year': year}
            
            if year == 0:
                # Initial investment
                row['capex'] = -self.calculate_capex()
                row['revenues'] = 0
                row['opex'] = 0
                row['ebitda'] = row['revenues'] - row['opex']
                row['tax'] = 0
                row['net_cashflow'] = row['capex']
            else:
                # Operating years
                generation = self.calculate_annual_generation(year)
                revenues = self.calculate_revenues(year, generation)
                opex = self.calculate_opex(year)
                
                row['capex'] = 0
                row['generation_mwh'] = sum([g for k, g in generation.items() if k != 'battery_throughput'])
                
                # Revenue breakdown
                for rev_stream, value in revenues.items():
                    row[f'revenue_{rev_stream}'] = value
                row['revenues'] = sum(revenues.values())
                
                # Opex breakdown
                for cost_item, value in opex.items():
                    row[f'opex_{cost_item}'] = value
                row['opex'] = sum(opex.values())
                
                # EBITDA and tax
                row['ebitda'] = row['revenues'] - row['opex']
                row['depreciation'] = self.calculate_capex() / self.tech_params.lifetime_years
                row['ebt'] = row['ebitda'] - row['depreciation']
                row['tax'] = max(0, row['ebt'] * self.financial.tax_rate)
                row['net_income'] = row['ebt'] - row['tax']
                row['net_cashflow'] = row['ebitda'] - row['tax']  # Add back depreciation (non-cash)
            
            # Discounting
            row['discount_factor'] = 1 / (1 + self.financial.discount_rate) ** year
            row['pv_cashflow'] = row['net_cashflow'] * row['discount_factor']
            
            cashflow_data.append(row)
        
        self.cashflow_df = pd.DataFrame(cashflow_data)
        return self.cashflow_df
    
    def calculate_lcoe(self) -> float:
        """Calculate Levelized Cost of Energy"""
        if self.cashflow_df is None:
            self.build_cashflow_model()
        
        # Calculate present value of generation
        pv_generation = 0
        for year in range(1, self.tech_params.lifetime_years + 1):
            generation = self.cashflow_df.loc[self.cashflow_df['year'] == year, 'generation_mwh'].values[0]
            discount_factor = 1 / (1 + self.financial.discount_rate) ** year
            pv_generation += generation * discount_factor
        
        # Calculate present value of costs (capex + opex)
        pv_costs = abs(self.cashflow_df.loc[self.cashflow_df['year'] == 0, 'capex'].values[0])
        for year in range(1, self.tech_params.lifetime_years + 1):
            opex = self.cashflow_df.loc[self.cashflow_df['year'] == year, 'opex'].values[0]
            discount_factor = 1 / (1 + self.financial.discount_rate) ** year
            pv_costs += opex * discount_factor
        
        lcoe = pv_costs / pv_generation if pv_generation > 0 else float('inf')
        return lcoe
    
    def calculate_irr(self) -> float:
        """Calculate Internal Rate of Return"""
        if self.cashflow_df is None:
            self.build_cashflow_model()
        
        cashflows = self.cashflow_df['net_cashflow'].values
        
        # Use numpy's IRR calculation
        try:
            irr = np.irr(cashflows)
        except:
            # Fallback to manual calculation if numpy.irr fails
            irr = self._calculate_irr_newton(cashflows)
        
        return irr
    
    def _calculate_irr_newton(self, cashflows: np.ndarray, max_iter: int = 100) -> float:
        """Newton-Raphson method for IRR calculation"""
        rate = 0.1  # Initial guess
        tolerance = 1e-6
        
        for _ in range(max_iter):
            # Calculate NPV and its derivative
            npv = 0
            dnpv = 0
            for t, cf in enumerate(cashflows):
                npv += cf / (1 + rate) ** t
                dnpv -= t * cf / (1 + rate) ** (t + 1)
            
            # Newton-Raphson update
            if abs(dnpv) < tolerance:
                break
            
            rate_new = rate - npv / dnpv
            
            if abs(rate_new - rate) < tolerance:
                return rate_new
            
            rate = rate_new
        
        return rate
    
    def calculate_npv(self) -> float:
        """Calculate Net Present Value"""
        if self.cashflow_df is None:
            self.build_cashflow_model()
        
        return self.cashflow_df['pv_cashflow'].sum()
    
    def calculate_payback_period(self) -> Tuple[float, float]:
        """Calculate simple and discounted payback periods"""
        if self.cashflow_df is None:
            self.build_cashflow_model()
        
        # Simple payback
        cumulative_cf = self.cashflow_df['net_cashflow'].cumsum()
        simple_payback = None
        for idx, value in cumulative_cf.items():
            if value > 0:
                simple_payback = self.cashflow_df.loc[idx, 'year']
                # Interpolate for more accurate result
                if idx > 0:
                    prev_value = cumulative_cf.iloc[idx - 1]
                    current_cf = self.cashflow_df.loc[idx, 'net_cashflow']
                    simple_payback -= prev_value / current_cf
                break
        
        # Discounted payback
        cumulative_pv = self.cashflow_df['pv_cashflow'].cumsum()
        discounted_payback = None
        for idx, value in cumulative_pv.items():
            if value > 0:
                discounted_payback = self.cashflow_df.loc[idx, 'year']
                # Interpolate
                if idx > 0:
                    prev_value = cumulative_pv.iloc[idx - 1]
                    current_pv = self.cashflow_df.loc[idx, 'pv_cashflow']
                    discounted_payback -= prev_value / current_pv
                break
        
        return simple_payback, discounted_payback
    
    def run_analysis(self) -> Dict:
        """Run complete financial analysis"""
        # Build cashflow model
        self.build_cashflow_model()
        
        # Calculate key metrics
        self.results = {
            'project_name': self.project_name,
            'technology': self.technology_type.value,
            'project_type': self.project_type.value,
            'market_region': self.market_region.value,
            'capacity_mw': self.tech_params.capacity_mw,
            'capex_total': self.calculate_capex(),
            'capex_per_mw': self.calculate_capex() / self.tech_params.capacity_mw,
            'irr': self.calculate_irr(),
            'npv': self.calculate_npv(),
            'lcoe': self.calculate_lcoe(),
            'payback_simple': self.calculate_payback_period()[0],
            'payback_discounted': self.calculate_payback_period()[1],
            'total_generation_lifetime_mwh': self.cashflow_df['generation_mwh'].sum(),
            'year1_revenues': self.cashflow_df.loc[self.cashflow_df['year'] == 1, 'revenues'].values[0],
        }
        
        # Add revenue breakdown for year 1
        year1_row = self.cashflow_df[self.cashflow_df['year'] == 1].iloc[0]
        revenue_streams = [col for col in self.cashflow_df.columns if col.startswith('revenue_')]
        for stream in revenue_streams:
            self.results[f'year1_{stream}'] = year1_row[stream]
        
        return self.results
    
    def sensitivity_analysis(self, parameters: Dict[str, List[float]]) -> pd.DataFrame:
        """Run sensitivity analysis on key parameters"""
        sensitivity_results = []
        
        # Store original values
        original_values = {}
        for param, values in parameters.items():
            if '.' in param:
                obj_name, attr_name = param.split('.')
                obj = getattr(self, obj_name)
                original_values[param] = getattr(obj, attr_name)
            else:
                original_values[param] = getattr(self, param)
        
        # Run sensitivity for each parameter
        for param, values in parameters.items():
            for value in values:
                # Set new value
                if '.' in param:
                    obj_name, attr_name = param.split('.')
                    obj = getattr(self, obj_name)
                    setattr(obj, attr_name, value)
                else:
                    setattr(self, param, value)
                
                # Recalculate
                self.cashflow_df = None  # Reset cashflow
                results = self.run_analysis()
                
                sensitivity_results.append({
                    'parameter': param,
                    'value': value,
                    'irr': results['irr'],
                    'npv': results['npv'],
                    'lcoe': results['lcoe']
                })
                
                # Restore original value
                if '.' in param:
                    obj_name, attr_name = param.split('.')
                    obj = getattr(self, obj_name)
                    setattr(obj, attr_name, original_values[param])
                else:
                    setattr(self, param, original_values[param])
        
        return pd.DataFrame(sensitivity_results)
    
    def compare_to_btm(self, btm_model: 'RenewableFinancialModel') -> Dict:
        """Compare utility-scale project to behind-the-meter alternative"""
        utility_results = self.run_analysis()
        btm_results = btm_model.run_analysis()
        
        comparison = {
            'utility_scale': {
                'irr': utility_results['irr'],
                'npv': utility_results['npv'],
                'lcoe': utility_results['lcoe'],
                'capex': utility_results['capex_total']
            },
            'behind_the_meter': {
                'irr': btm_results['irr'],
                'npv': btm_results['npv'],
                'lcoe': btm_results['lcoe'],
                'capex': btm_results['capex_total']
            },
            'delta': {
                'irr': btm_results['irr'] - utility_results['irr'],
                'npv': btm_results['npv'] - utility_results['npv'],
                'lcoe': btm_results['lcoe'] - utility_results['lcoe'],
                'capex': btm_results['capex_total'] - utility_results['capex_total']
            },
            'recommendation': 'behind_the_meter' if btm_results['irr'] > utility_results['irr'] else 'utility_scale'
        }
        
        return comparison
    
    def export_results(self, format: str = 'json') -> Union[str, pd.DataFrame]:
        """Export results in various formats"""
        if format == 'json':
            export_data = {
                'summary': self.results,
                'cashflow': self.cashflow_df.to_dict('records') if self.cashflow_df is not None else None,
                'timestamp': datetime.now().isoformat(),
                'model_version': '1.0.0'
            }
            return json.dumps(export_data, indent=2, default=str)
        
        elif format == 'dataframe':
            return self.cashflow_df
        
        elif format == 'summary':
            return pd.DataFrame([self.results])
        
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Example usage and testing
if __name__ == "__main__":
    # Example: 10MW Solar PV project in UK
    tech_params = TechnologyParams(
        capacity_mw=10,
        capex_per_mw=600000,  # £600k/MW
        opex_per_mw_year=10000,  # £10k/MW/year
        degradation_rate_annual=0.005,
        system_losses=0.14,
        lifetime_years=25
    )
    
    market_prices = MarketPrices(
        base_power_price=80,  # £80/MWh
        power_price_escalation=0.025,
        ppa_price=70,  # £70/MWh
        ppa_duration_years=15,
        ppa_percentage=0.7,
        capacity_payment=15,  # £15/kW/year
        capacity_derating_factor=0.087,  # Solar derating in UK
        frequency_response_price=10,  # £10/MW/hour
        ancillary_availability=0.05
    )
    
    financial_assumptions = FinancialAssumptions(
        discount_rate=0.08,
        inflation_rate=0.02,
        tax_rate=0.19
    )
    
    # Create and run model
    model = RenewableFinancialModel(
        project_name="UK Solar Farm 10MW",
        technology_type=TechnologyType.SOLAR_PV,
        project_type=ProjectType.UTILITY_SCALE,
        market_region=MarketRegion.UK,
        technology_params=tech_params,
        market_prices=market_prices,
        financial_assumptions=financial_assumptions
    )
    
    results = model.run_analysis()
    print(f"Project IRR: {results['irr']:.2%}")
    print(f"Project NPV: £{results['npv']:,.0f}")
    print(f"LCOE: £{results['lcoe']:.2f}/MWh")
