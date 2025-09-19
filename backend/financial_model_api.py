"""
FastAPI wrapper for the RenewableFinancialModel
Exposes financial calculations as REST API for the frontend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import traceback

# Import our financial model classes
from renewable_model import (
    RenewableFinancialModel, TechnologyParams, MarketPrices, 
    FinancialAssumptions, TechnologyType, ProjectType, MarketRegion
)

app = FastAPI(
    title="Infranodal Financial Model API",
    description="Professional-grade renewable energy financial modeling",
    version="1.0.0"
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models matching the frontend service
class FinancialModelRequest(BaseModel):
    # Basic project information
    technology: str
    capacity_mw: float
    capacity_factor: float
    project_life: int
    degradation: float
    
    # Cost information
    capex_per_kw: float
    devex_abs: float
    devex_pct: float
    opex_fix_per_mw_year: float
    opex_var_per_mwh: float
    tnd_costs_per_year: float
    
    # Revenue information
    ppa_price: float
    ppa_escalation: float
    ppa_duration: int
    merchant_price: float
    capacity_market_per_mw_year: float
    ancillary_per_mw_year: float
    
    # Financial information
    discount_rate: float
    inflation_rate: float
    tax_rate: float = 0.19
    grid_savings_factor: float
    
    # Optional battery information
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

def map_technology_type(tech_string: str) -> TechnologyType:
    """Map frontend technology string to enum"""
    mapping = {
        'solar': TechnologyType.SOLAR_PV,
        'solar_pv': TechnologyType.SOLAR_PV,
        'wind': TechnologyType.WIND,
        'battery': TechnologyType.BATTERY,
        'solar_battery': TechnologyType.SOLAR_BATTERY,
        'solar_bess': TechnologyType.SOLAR_BATTERY,
        'wind_battery': TechnologyType.WIND_BATTERY,
    }
    return mapping.get(tech_string.lower(), TechnologyType.SOLAR_PV)

def create_technology_params(request: FinancialModelRequest) -> TechnologyParams:
    """Create TechnologyParams from request"""
    return TechnologyParams(
        capacity_mw=request.capacity_mw,
        capex_per_mw=request.capex_per_kw * 1000,  # Convert kW to MW
        opex_per_mw_year=request.opex_fix_per_mw_year,
        degradation_rate_annual=request.degradation,
        lifetime_years=request.project_life,
        capacity_factor=request.capacity_factor,
        battery_capacity_mwh=request.battery_capacity_mwh,
        battery_capex_per_mwh=request.battery_capex_per_mwh,
        battery_cycles_per_year=request.battery_cycles_per_year,
    )

def create_utility_market_prices(request: FinancialModelRequest) -> MarketPrices:
    """Create MarketPrices for utility-scale project"""
    return MarketPrices(
        base_power_price=request.merchant_price,
        power_price_escalation=0.025,  # 2.5% default
        ppa_price=request.ppa_price,
        ppa_duration_years=request.ppa_duration,
        ppa_escalation=request.ppa_escalation,
        ppa_percentage=0.7,  # 70% under PPA
        capacity_payment=request.capacity_market_per_mw_year / 1000,  # Convert to £/kW
        frequency_response_price=request.ancillary_per_mw_year / (8760 * 0.1),  # Rough conversion
    )

def create_btm_market_prices(request: FinancialModelRequest) -> MarketPrices:
    """Create MarketPrices for behind-the-meter project"""
    # Calculate first year generation for grid savings conversion
    annual_generation = request.capacity_mw * 8760 * request.capacity_factor
    grid_savings_per_mwh = (request.grid_savings_factor * request.tnd_costs_per_year) / annual_generation if annual_generation > 0 else 0
    
    return MarketPrices(
        base_power_price=request.merchant_price,
        power_price_escalation=0.025,
        retail_electricity_price=request.ppa_price,  # Use PPA price as retail equivalent
        retail_price_escalation=request.ppa_escalation,
        grid_charges=grid_savings_per_mwh,
        demand_charges=0,  # Simplified for now
    )

def extract_revenue_breakdown(cashflow_df) -> RevenueBreakdown:
    """Extract revenue breakdown from cashflow DataFrame"""
    if cashflow_df is None or len(cashflow_df) == 0:
        return RevenueBreakdown(
            energyRev=0, capacityRev=0, ancillaryRev=0, 
            gridSavings=0, opexTotal=0
        )
    
    # Sum revenues across all years (excluding year 0)
    operating_years = cashflow_df[cashflow_df['year'] > 0]
    
    energy_rev = 0
    capacity_rev = 0
    ancillary_rev = 0
    grid_savings = 0
    opex_total = operating_years['opex'].sum() if 'opex' in operating_years.columns else 0
    
    # Sum revenue streams if they exist
    for col in operating_years.columns:
        if col.startswith('revenue_'):
            values = operating_years[col].sum()
            if 'ppa' in col or 'merchant' in col or 'energy_savings' in col:
                energy_rev += values
            elif 'capacity' in col:
                capacity_rev += values
            elif 'frequency_response' in col or 'ancillary' in col:
                ancillary_rev += values
            elif 'grid_charges' in col:
                grid_savings += values
    
    return RevenueBreakdown(
        energyRev=energy_rev,
        capacityRev=capacity_rev,
        ancillaryRev=ancillary_rev,
        gridSavings=grid_savings,
        opexTotal=opex_total,
    )

@app.get("/")
async def root():
    return {"message": "Infranodal Financial Model API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Financial model API is running"}

@app.post("/api/financial-model", response_model=FinancialModelResponse)
async def calculate_financial_model(request: FinancialModelRequest):
    """Calculate financial model for both utility-scale and behind-the-meter scenarios"""
    
    try:
        # Create common parameters
        tech_params = create_technology_params(request)
        financial_assumptions = FinancialAssumptions(
            discount_rate=request.discount_rate,
            inflation_rate=request.inflation_rate,
            tax_rate=request.tax_rate,
        )
        
        # Technology type mapping
        tech_type = map_technology_type(request.technology)
        
        # Create utility-scale model
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
        
        # Create behind-the-meter model
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
        
        # Run analyses
        utility_results = utility_model.run_analysis()
        btm_results = btm_model.run_analysis()
        
        # Extract cashflows
        utility_cashflows = utility_model.cashflow_df['net_cashflow'].tolist()
        btm_cashflows = btm_model.cashflow_df['net_cashflow'].tolist()
        
        # Extract revenue breakdowns
        utility_breakdown = extract_revenue_breakdown(utility_model.cashflow_df)
        btm_breakdown = extract_revenue_breakdown(btm_model.cashflow_df)
        
        # Calculate metrics
        irr_uplift = (btm_results['irr'] - utility_results['irr']) if (btm_results['irr'] and utility_results['irr']) else 0
        npv_delta = btm_results['npv'] - utility_results['npv']
        
        # Build response
        response = FinancialModelResponse(
            standard=ModelResults(
                irr=utility_results['irr'],
                npv=utility_results['npv'],
                cashflows=utility_cashflows,
                breakdown=utility_breakdown,
                lcoe=utility_results['lcoe'],
                payback_simple=utility_results['payback_simple'],
                payback_discounted=utility_results['payback_discounted'],
            ),
            autoproducer=ModelResults(
                irr=btm_results['irr'],
                npv=btm_results['npv'],
                cashflows=btm_cashflows,
                breakdown=btm_breakdown,
                lcoe=btm_results['lcoe'],
                payback_simple=btm_results['payback_simple'],
                payback_discounted=btm_results['payback_discounted'],
            ),
            metrics={
                'total_capex': utility_results['capex_total'],
                'capex_per_mw': utility_results['capex_per_mw'],
                'irr_uplift': irr_uplift,
                'npv_delta': npv_delta,
                'annual_generation': request.capacity_mw * 8760 * request.capacity_factor,
            },
            success=True,
            message="Financial analysis completed successfully"
        )
        
        return response
        
    except Exception as e:
        print(f"Error in financial model calculation: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Return error response
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Financial model calculation failed: {str(e)}",
                "error_type": type(e).__name__
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
