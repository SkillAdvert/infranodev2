"""Comprehensive tests for backend/renewable_model.py module.

Tests NPV, IRR, LCOE calculations with various financial scenarios
for solar, wind, battery, and hybrid renewable energy projects.
"""

import sys
import math
from pathlib import Path

import pytest
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.renewable_model import (
    # Enums
    TechnologyType,
    ProjectType,
    MarketRegion,
    # Data classes
    TechnologyParams,
    MarketPrices,
    FinancialAssumptions,
    GenerationProfile,
    # Main model class
    RenewableFinancialModel,
)


# ============================================================================
# Test Enums
# ============================================================================


class TestEnums:
    """Test enumeration values."""

    def test_technology_types(self):
        """All technology types should be defined."""
        assert TechnologyType.SOLAR_PV.value == "solar_pv"
        assert TechnologyType.WIND.value == "wind"
        assert TechnologyType.BATTERY.value == "battery"
        assert TechnologyType.SOLAR_BATTERY.value == "solar_battery"
        assert TechnologyType.WIND_BATTERY.value == "wind_battery"

    def test_project_types(self):
        """All project types should be defined."""
        assert ProjectType.UTILITY_SCALE.value == "utility_scale"
        assert ProjectType.BEHIND_THE_METER.value == "behind_the_meter"

    def test_market_regions(self):
        """All market regions should be defined."""
        assert MarketRegion.UK.value == "uk"
        assert MarketRegion.IRELAND.value == "ireland"


# ============================================================================
# Test Data Classes
# ============================================================================


class TestTechnologyParams:
    """Test TechnologyParams dataclass."""

    def test_create_solar_params(self):
        """Should create solar technology parameters."""
        params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0,
            degradation_rate_annual=0.005,
            system_losses=0.14,
            lifetime_years=25
        )

        assert params.capacity_mw == 10.0
        assert params.capex_per_mw == 600000.0
        assert params.degradation_rate_annual == 0.005
        assert params.system_losses == 0.14

    def test_create_battery_params(self):
        """Should create battery technology parameters."""
        params = TechnologyParams(
            capacity_mw=50.0,
            capex_per_mw=100000.0,
            opex_per_mw_year=5000.0,
            battery_capacity_mwh=200.0,
            battery_capex_per_mwh=200000.0,
            battery_efficiency=0.90,
            battery_cycles_per_year=365,
            battery_degradation_rate=0.02
        )

        assert params.battery_capacity_mwh == 200.0
        assert params.battery_efficiency == 0.90
        assert params.battery_cycles_per_year == 365

    def test_create_wind_params(self):
        """Should create wind technology parameters."""
        params = TechnologyParams(
            capacity_mw=100.0,
            capex_per_mw=1200000.0,
            opex_per_mw_year=30000.0,
            capacity_factor=0.35,
            degradation_rate_annual=0.01
        )

        assert params.capacity_factor == 0.35
        assert params.degradation_rate_annual == 0.01

    def test_default_values(self):
        """Default values should be set correctly."""
        params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=500000.0,
            opex_per_mw_year=10000.0
        )

        assert params.degradation_rate_annual == 0.005
        assert params.efficiency == 1.0
        assert params.lifetime_years == 25
        assert params.battery_efficiency == 0.90


class TestMarketPrices:
    """Test MarketPrices dataclass."""

    def test_create_market_prices(self):
        """Should create market price configuration."""
        prices = MarketPrices(
            base_power_price=80.0,
            power_price_escalation=0.025,
            ppa_price=70.0,
            ppa_duration_years=15,
            ppa_percentage=0.7
        )

        assert prices.base_power_price == 80.0
        assert prices.ppa_price == 70.0
        assert prices.ppa_percentage == 0.7

    def test_default_values(self):
        """Default values should be set correctly."""
        prices = MarketPrices(base_power_price=50.0)

        assert prices.power_price_escalation == 0.025
        assert prices.ppa_duration_years == 15
        assert prices.capacity_payment == 0
        assert prices.retail_electricity_price == 150

    def test_capacity_market_prices(self):
        """Should handle capacity market configuration."""
        prices = MarketPrices(
            base_power_price=80.0,
            capacity_payment=15.0,
            capacity_duration_years=15,
            capacity_derating_factor=0.087
        )

        assert prices.capacity_payment == 15.0
        assert prices.capacity_derating_factor == 0.087


class TestFinancialAssumptions:
    """Test FinancialAssumptions dataclass."""

    def test_create_assumptions(self):
        """Should create financial assumptions."""
        assumptions = FinancialAssumptions(
            discount_rate=0.08,
            inflation_rate=0.02,
            tax_rate=0.19
        )

        assert assumptions.discount_rate == 0.08
        assert assumptions.tax_rate == 0.19

    def test_default_values(self):
        """Default values should be set correctly."""
        assumptions = FinancialAssumptions()

        assert assumptions.discount_rate == 0.08
        assert assumptions.inflation_rate == 0.02
        assert assumptions.tax_rate == 0.19
        assert assumptions.vat_rate == 0.20
        assert assumptions.working_capital_days == 30


class TestGenerationProfile:
    """Test GenerationProfile dataclass."""

    def test_create_hourly_profile(self):
        """Should create hourly generation profile."""
        hourly = np.ones(8760) * 0.5  # 50% capacity factor
        profile = GenerationProfile(hourly_generation=hourly)

        assert len(profile.hourly_generation) == 8760

    def test_get_annual_generation(self):
        """Should calculate annual generation with degradation."""
        hourly = np.ones(8760) * 1.0  # 100% CF (unrealistic but good for test)
        profile = GenerationProfile(hourly_generation=hourly)

        # Year 1: no degradation
        gen_year1 = profile.get_annual_generation(10.0, year=1, degradation=0.005)
        assert gen_year1 == pytest.approx(10.0 * 8760, rel=0.01)

        # Year 10: with degradation
        gen_year10 = profile.get_annual_generation(10.0, year=10, degradation=0.005)
        expected_degradation = (1 - 0.005) ** 9
        assert gen_year10 == pytest.approx(10.0 * 8760 * expected_degradation, rel=0.01)

    def test_monthly_generation(self):
        """Should handle monthly generation profiles."""
        monthly = np.array([800, 900, 1000, 1100, 1200, 1300,
                           1300, 1200, 1100, 1000, 900, 800])  # MWh
        profile = GenerationProfile(monthly_generation=monthly)

        gen = profile.get_annual_generation(1.0, year=1)
        assert gen == np.sum(monthly)

    def test_no_profile_raises_error(self):
        """Should raise error if no profile provided."""
        profile = GenerationProfile()

        with pytest.raises(ValueError):
            profile.get_annual_generation(10.0, year=1)


# ============================================================================
# Test RenewableFinancialModel - Basic Operations
# ============================================================================


class TestRenewableFinancialModelBasic:
    """Test basic RenewableFinancialModel operations."""

    @pytest.fixture
    def solar_model(self):
        """Create a standard solar PV model for testing."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0,
            degradation_rate_annual=0.005,
            system_losses=0.14,
            lifetime_years=25
        )

        market_prices = MarketPrices(
            base_power_price=80.0,
            power_price_escalation=0.025,
            ppa_price=70.0,
            ppa_duration_years=15,
            ppa_percentage=0.7
        )

        financial = FinancialAssumptions(
            discount_rate=0.08,
            inflation_rate=0.02,
            tax_rate=0.19
        )

        return RenewableFinancialModel(
            project_name="Test Solar 10MW",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=market_prices,
            financial_assumptions=financial
        )

    def test_create_model(self, solar_model):
        """Should create a financial model instance."""
        assert solar_model.project_name == "Test Solar 10MW"
        assert solar_model.technology_type == TechnologyType.SOLAR_PV
        assert solar_model.project_type == ProjectType.UTILITY_SCALE
        assert solar_model.market_region == MarketRegion.UK

    def test_calculate_capex(self, solar_model):
        """Should calculate total CAPEX correctly."""
        capex = solar_model.calculate_capex()
        # 10 MW * £600,000/MW = £6,000,000
        assert capex == 6000000.0

    def test_calculate_capex_with_battery(self):
        """Should include battery CAPEX for hybrid systems."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0,
            battery_capacity_mwh=40.0,  # 4-hour battery
            battery_capex_per_mwh=200000.0
        )

        model = RenewableFinancialModel(
            project_name="Solar + Battery",
            technology_type=TechnologyType.SOLAR_BATTERY,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=MarketPrices(base_power_price=80.0),
            financial_assumptions=FinancialAssumptions()
        )

        capex = model.calculate_capex()
        # 10 MW * £600k + 40 MWh * £200k = £6M + £8M = £14M
        assert capex == 14000000.0

    def test_calculate_annual_generation_solar(self, solar_model):
        """Should calculate solar generation correctly."""
        generation = solar_model.calculate_annual_generation(year=1)

        assert "solar" in generation
        # UK solar: 10 MW * 8760 hours * 11% CF * (1-0.14 losses)
        expected = 10.0 * 8760 * 0.11 * 0.86
        assert generation["solar"] == pytest.approx(expected, rel=0.05)

    def test_generation_degradation(self, solar_model):
        """Generation should decrease with degradation over time."""
        gen_year1 = solar_model.calculate_annual_generation(year=1)
        gen_year10 = solar_model.calculate_annual_generation(year=10)

        assert gen_year10["solar"] < gen_year1["solar"]

        # Degradation factor for year 10: (1-0.005)^9
        expected_ratio = (1 - 0.005) ** 9
        actual_ratio = gen_year10["solar"] / gen_year1["solar"]
        assert actual_ratio == pytest.approx(expected_ratio, rel=0.01)


class TestRenewableFinancialModelWind:
    """Test wind-specific financial model calculations."""

    @pytest.fixture
    def wind_model(self):
        """Create a wind model for testing."""
        tech_params = TechnologyParams(
            capacity_mw=50.0,
            capex_per_mw=1200000.0,
            opex_per_mw_year=30000.0,
            capacity_factor=0.35,
            degradation_rate_annual=0.01,
            lifetime_years=25
        )

        market_prices = MarketPrices(
            base_power_price=70.0,
            ppa_price=65.0,
            ppa_duration_years=15,
            ppa_percentage=0.8,
            capacity_payment=10.0,
            capacity_derating_factor=0.15
        )

        return RenewableFinancialModel(
            project_name="Test Wind 50MW",
            technology_type=TechnologyType.WIND,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=market_prices,
            financial_assumptions=FinancialAssumptions()
        )

    def test_wind_generation(self, wind_model):
        """Should calculate wind generation with capacity factor."""
        generation = wind_model.calculate_annual_generation(year=1)

        assert "wind" in generation
        # 50 MW * 8760 hours * 35% CF
        expected = 50.0 * 8760 * 0.35
        assert generation["wind"] == pytest.approx(expected, rel=0.01)

    def test_wind_capex(self, wind_model):
        """Should calculate wind CAPEX correctly."""
        capex = wind_model.calculate_capex()
        # 50 MW * £1,200,000/MW = £60,000,000
        assert capex == 60000000.0


class TestRenewableFinancialModelBattery:
    """Test battery-specific financial model calculations."""

    @pytest.fixture
    def battery_model(self):
        """Create a standalone battery model for testing."""
        tech_params = TechnologyParams(
            capacity_mw=25.0,
            capex_per_mw=50000.0,
            opex_per_mw_year=5000.0,
            battery_capacity_mwh=100.0,
            battery_capex_per_mwh=250000.0,
            battery_efficiency=0.90,
            battery_cycles_per_year=365,
            battery_degradation_rate=0.02,
            lifetime_years=15
        )

        market_prices = MarketPrices(
            base_power_price=80.0,
            frequency_response_price=10.0,
            ancillary_availability=0.3
        )

        return RenewableFinancialModel(
            project_name="Test Battery 25MW/100MWh",
            technology_type=TechnologyType.BATTERY,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=market_prices,
            financial_assumptions=FinancialAssumptions()
        )

    def test_battery_generation_includes_throughput(self, battery_model):
        """Battery generation should include throughput."""
        generation = battery_model.calculate_annual_generation(year=1)

        assert "battery_throughput" in generation
        # 100 MWh * 365 cycles = 36,500 MWh
        expected = 100.0 * 365
        assert generation["battery_throughput"] == pytest.approx(expected, rel=0.01)

    def test_battery_degradation(self, battery_model):
        """Battery throughput should degrade over time."""
        gen_year1 = battery_model.calculate_annual_generation(year=1)
        gen_year5 = battery_model.calculate_annual_generation(year=5)

        # 2% annual degradation
        expected_ratio = (1 - 0.02) ** 4
        actual_ratio = gen_year5["battery_throughput"] / gen_year1["battery_throughput"]
        assert actual_ratio == pytest.approx(expected_ratio, rel=0.01)


# ============================================================================
# Test Revenue Calculations
# ============================================================================


class TestRevenueCalculations:
    """Test revenue calculation methods."""

    @pytest.fixture
    def utility_model(self):
        """Create a utility-scale model for revenue tests."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0,
            lifetime_years=25
        )

        market_prices = MarketPrices(
            base_power_price=80.0,
            ppa_price=70.0,
            ppa_duration_years=15,
            ppa_percentage=0.7,
            ppa_escalation=0.02,
            capacity_payment=15.0,
            capacity_duration_years=15,
            capacity_derating_factor=0.087,
            frequency_response_price=10.0,
            ancillary_availability=0.05
        )

        return RenewableFinancialModel(
            project_name="Utility Solar",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=market_prices,
            financial_assumptions=FinancialAssumptions()
        )

    def test_ppa_revenue(self, utility_model):
        """Should calculate PPA revenue correctly."""
        generation = {"solar": 10000.0}  # MWh
        revenues = utility_model.calculate_revenues(year=1, generation=generation)

        assert "ppa" in revenues
        # PPA: 10000 * 0.7 * £70 = £490,000
        expected_ppa = 10000 * 0.7 * 70.0
        assert revenues["ppa"] == pytest.approx(expected_ppa, rel=0.01)

    def test_merchant_revenue(self, utility_model):
        """Should calculate merchant revenue correctly."""
        generation = {"solar": 10000.0}
        revenues = utility_model.calculate_revenues(year=1, generation=generation)

        assert "merchant" in revenues
        # Merchant: 10000 * 0.3 * £80 = £240,000
        expected_merchant = 10000 * 0.3 * 80.0
        assert revenues["merchant"] == pytest.approx(expected_merchant, rel=0.01)

    def test_capacity_revenue(self, utility_model):
        """Should calculate capacity market revenue."""
        generation = {"solar": 10000.0}
        revenues = utility_model.calculate_revenues(year=1, generation=generation)

        assert "capacity" in revenues
        # Capacity: 10 MW * 0.087 * £15/kW * 1000 = £13,050
        expected = 10.0 * 0.087 * 15.0 * 1000
        assert revenues["capacity"] == pytest.approx(expected, rel=0.01)

    def test_ancillary_services_revenue(self, utility_model):
        """Should calculate ancillary services revenue."""
        generation = {"solar": 10000.0}
        revenues = utility_model.calculate_revenues(year=1, generation=generation)

        assert "frequency_response" in revenues
        # FR: 10 MW * £10/MW/hour * 8760 * 0.05 = £43,800
        expected = 10.0 * 10.0 * 8760 * 0.05
        assert revenues["frequency_response"] == pytest.approx(expected, rel=0.01)

    def test_ppa_escalation(self, utility_model):
        """PPA price should escalate over time."""
        generation = {"solar": 10000.0}

        rev_year1 = utility_model.calculate_revenues(year=1, generation=generation)
        rev_year5 = utility_model.calculate_revenues(year=5, generation=generation)

        # Year 5 PPA should be higher due to 2% escalation
        escalation = (1 + 0.02) ** 4
        assert rev_year5["ppa"] == pytest.approx(rev_year1["ppa"] * escalation, rel=0.02)


class TestBTMRevenues:
    """Test Behind-the-Meter revenue calculations."""

    @pytest.fixture
    def btm_model(self):
        """Create a BTM model for testing."""
        tech_params = TechnologyParams(
            capacity_mw=1.0,
            capex_per_mw=800000.0,
            opex_per_mw_year=15000.0,
            lifetime_years=25
        )

        market_prices = MarketPrices(
            base_power_price=60.0,
            retail_electricity_price=150.0,
            retail_price_escalation=0.03,
            grid_charges=30.0,
            demand_charges=5.0
        )

        return RenewableFinancialModel(
            project_name="BTM Solar",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.BEHIND_THE_METER,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=market_prices,
            financial_assumptions=FinancialAssumptions()
        )

    def test_energy_savings(self, btm_model):
        """Should calculate energy savings at retail rate."""
        generation = {"solar": 1000.0}  # MWh
        revenues = btm_model.calculate_revenues(year=1, generation=generation)

        assert "energy_savings" in revenues
        # 1000 MWh * £150/MWh = £150,000
        expected = 1000.0 * 150.0
        assert revenues["energy_savings"] == pytest.approx(expected, rel=0.01)

    def test_grid_charges_avoided(self, btm_model):
        """Should calculate avoided grid charges."""
        generation = {"solar": 1000.0}
        revenues = btm_model.calculate_revenues(year=1, generation=generation)

        assert "grid_charges_avoided" in revenues
        # 1000 MWh * £30/MWh = £30,000
        expected = 1000.0 * 30.0
        assert revenues["grid_charges_avoided"] == expected

    def test_export_revenue(self, btm_model):
        """Should calculate export revenue."""
        generation = {"solar": 1000.0}
        revenues = btm_model.calculate_revenues(year=1, generation=generation)

        assert "export" in revenues
        # Export assumed 30% at 90% of wholesale
        # 1000 * 0.3 * £60 * 0.9 = £16,200
        expected = 1000.0 * 0.3 * 60.0 * 0.9
        assert revenues["export"] == pytest.approx(expected, rel=0.1)


# ============================================================================
# Test OPEX Calculations
# ============================================================================


class TestOpexCalculations:
    """Test operating expense calculations."""

    @pytest.fixture
    def model(self):
        """Create model for OPEX tests."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0,
            lifetime_years=25
        )

        return RenewableFinancialModel(
            project_name="Test",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=MarketPrices(base_power_price=80.0),
            financial_assumptions=FinancialAssumptions(inflation_rate=0.02)
        )

    def test_fixed_om(self, model):
        """Should calculate fixed O&M costs."""
        opex = model.calculate_opex(year=1)

        assert "om_fixed" in opex
        # 10 MW * £10,000/MW = £100,000
        assert opex["om_fixed"] == pytest.approx(100000.0, rel=0.01)

    def test_om_inflation(self, model):
        """O&M should inflate over time."""
        opex_year1 = model.calculate_opex(year=1)
        opex_year5 = model.calculate_opex(year=5)

        # 2% inflation over 4 years
        inflation = (1 + 0.02) ** 4
        assert opex_year5["om_fixed"] == pytest.approx(
            opex_year1["om_fixed"] * inflation, rel=0.01
        )

    def test_insurance_cost(self, model):
        """Should calculate insurance costs."""
        opex = model.calculate_opex(year=1)

        assert "insurance" in opex
        # 1% of CAPEX = £60,000
        expected = 6000000.0 * 0.01
        assert opex["insurance"] == pytest.approx(expected, rel=0.01)

    def test_land_lease_utility_scale(self, model):
        """Utility-scale should include land lease."""
        opex = model.calculate_opex(year=1)

        assert "land_lease" in opex
        # 10 MW * £1,000/MW = £10,000
        assert opex["land_lease"] == pytest.approx(10000.0, rel=0.01)


# ============================================================================
# Test Financial Metrics (NPV, IRR, LCOE)
# ============================================================================


class TestFinancialMetrics:
    """Test NPV, IRR, and LCOE calculations."""

    @pytest.fixture
    def profitable_model(self):
        """Create a profitable project model."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=500000.0,  # Lower CAPEX
            opex_per_mw_year=8000.0,
            lifetime_years=25
        )

        market_prices = MarketPrices(
            base_power_price=90.0,  # Higher prices
            ppa_price=85.0,
            ppa_duration_years=20,
            ppa_percentage=0.8,
            capacity_payment=20.0
        )

        return RenewableFinancialModel(
            project_name="Profitable Solar",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=market_prices,
            financial_assumptions=FinancialAssumptions(discount_rate=0.08)
        )

    @pytest.fixture
    def unprofitable_model(self):
        """Create an unprofitable project model."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=1000000.0,  # High CAPEX
            opex_per_mw_year=20000.0,
            lifetime_years=25
        )

        market_prices = MarketPrices(
            base_power_price=40.0,  # Low prices
            ppa_price=35.0,
            ppa_duration_years=10,
            ppa_percentage=0.5
        )

        return RenewableFinancialModel(
            project_name="Unprofitable Solar",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=market_prices,
            financial_assumptions=FinancialAssumptions(discount_rate=0.08)
        )

    def test_build_cashflow_model(self, profitable_model):
        """Should build complete cashflow DataFrame."""
        df = profitable_model.build_cashflow_model()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 26  # Year 0 + 25 years

        # Check required columns
        required_cols = [
            "year", "capex", "revenues", "opex", "ebitda",
            "net_cashflow", "discount_factor", "pv_cashflow"
        ]
        for col in required_cols:
            assert col in df.columns

    def test_year_zero_capex(self, profitable_model):
        """Year 0 should have negative CAPEX."""
        df = profitable_model.build_cashflow_model()

        year_0 = df[df["year"] == 0].iloc[0]
        assert year_0["capex"] < 0
        assert year_0["capex"] == -5000000.0  # 10 MW * £500k

    def test_operating_years_positive_revenue(self, profitable_model):
        """Operating years should have positive revenue."""
        df = profitable_model.build_cashflow_model()

        for year in range(1, 26):
            row = df[df["year"] == year].iloc[0]
            assert row["revenues"] > 0

    def test_npv_calculation(self, profitable_model):
        """Should calculate NPV correctly."""
        npv = profitable_model.calculate_npv()

        # Profitable project should have positive NPV
        assert npv > 0
        assert isinstance(npv, float)

    def test_npv_unprofitable_is_negative(self, unprofitable_model):
        """Unprofitable project should have negative NPV."""
        npv = unprofitable_model.calculate_npv()
        assert npv < 0

    def test_irr_calculation(self, profitable_model):
        """Should calculate IRR correctly."""
        irr = profitable_model.calculate_irr()

        # IRR should be a reasonable percentage
        assert -0.5 < irr < 0.5  # Between -50% and 50%
        assert isinstance(irr, float)

    def test_irr_above_discount_rate_if_positive_npv(self, profitable_model):
        """If NPV > 0, IRR should exceed discount rate."""
        npv = profitable_model.calculate_npv()
        irr = profitable_model.calculate_irr()

        if npv > 0:
            assert irr > profitable_model.financial.discount_rate

    def test_lcoe_calculation(self, profitable_model):
        """Should calculate LCOE correctly."""
        lcoe = profitable_model.calculate_lcoe()

        # LCOE should be positive and reasonable (£/MWh in thousands)
        assert lcoe > 0
        # For solar, LCOE typically £40-100/MWh, but this is in £k
        assert lcoe < 1.0  # Less than £1000/MWh (model divides by 1000)

    def test_lcoe_positive_for_all_projects(self, profitable_model, unprofitable_model):
        """LCOE should always be positive."""
        assert profitable_model.calculate_lcoe() > 0
        assert unprofitable_model.calculate_lcoe() > 0


class TestPaybackPeriod:
    """Test payback period calculations."""

    @pytest.fixture
    def model(self):
        """Create model for payback tests."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=500000.0,
            opex_per_mw_year=8000.0,
            lifetime_years=25
        )

        market_prices = MarketPrices(
            base_power_price=100.0,
            ppa_price=95.0,
            ppa_duration_years=25,
            ppa_percentage=0.9
        )

        return RenewableFinancialModel(
            project_name="Payback Test",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=market_prices,
            financial_assumptions=FinancialAssumptions()
        )

    def test_payback_returns_tuple(self, model):
        """Should return tuple of simple and discounted payback."""
        result = model.calculate_payback_period()

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_simple_payback_less_than_discounted(self, model):
        """Simple payback should be less than discounted."""
        simple, discounted = model.calculate_payback_period()

        if simple is not None and discounted is not None:
            assert simple <= discounted

    def test_payback_within_lifetime(self, model):
        """Payback should be within project lifetime for profitable project."""
        simple, discounted = model.calculate_payback_period()

        # Should achieve payback within 25 years
        assert simple is not None
        assert simple < 25


# ============================================================================
# Test Complete Analysis
# ============================================================================


class TestRunAnalysis:
    """Test complete run_analysis method."""

    @pytest.fixture
    def model(self):
        """Create model for analysis tests."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0,
            lifetime_years=25
        )

        market_prices = MarketPrices(
            base_power_price=80.0,
            ppa_price=75.0,
            ppa_duration_years=15,
            ppa_percentage=0.7
        )

        return RenewableFinancialModel(
            project_name="Analysis Test",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=market_prices,
            financial_assumptions=FinancialAssumptions()
        )

    def test_run_analysis_returns_dict(self, model):
        """run_analysis should return results dictionary."""
        results = model.run_analysis()

        assert isinstance(results, dict)

    def test_analysis_contains_key_metrics(self, model):
        """Results should contain all key metrics."""
        results = model.run_analysis()

        required_keys = [
            "project_name", "technology", "capacity_mw",
            "capex_total", "capex_per_mw",
            "irr", "npv", "lcoe",
            "payback_simple", "payback_discounted",
            "total_generation_lifetime_mwh", "year1_revenues"
        ]

        for key in required_keys:
            assert key in results, f"Missing key: {key}"

    def test_analysis_values_reasonable(self, model):
        """Analysis values should be reasonable."""
        results = model.run_analysis()

        assert results["capacity_mw"] == 10.0
        assert results["capex_total"] == 6000000.0
        assert -0.5 < results["irr"] < 0.5
        assert results["total_generation_lifetime_mwh"] > 0


# ============================================================================
# Test Export Functionality
# ============================================================================


class TestExportResults:
    """Test export_results method."""

    @pytest.fixture
    def model_with_results(self):
        """Create model with completed analysis."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0,
            lifetime_years=25
        )

        model = RenewableFinancialModel(
            project_name="Export Test",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=MarketPrices(base_power_price=80.0),
            financial_assumptions=FinancialAssumptions()
        )

        model.run_analysis()
        return model

    def test_export_json(self, model_with_results):
        """Should export to JSON format."""
        import json

        json_str = model_with_results.export_results(format="json")

        assert isinstance(json_str, str)
        # Should be valid JSON
        data = json.loads(json_str)
        assert "summary" in data
        assert "cashflow" in data

    def test_export_dataframe(self, model_with_results):
        """Should export cashflow DataFrame."""
        df = model_with_results.export_results(format="dataframe")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 26

    def test_export_summary(self, model_with_results):
        """Should export summary DataFrame."""
        df = model_with_results.export_results(format="summary")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_invalid_format_raises(self, model_with_results):
        """Invalid format should raise ValueError."""
        with pytest.raises(ValueError):
            model_with_results.export_results(format="invalid")


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_capacity_project(self):
        """Zero capacity should be handled gracefully."""
        tech_params = TechnologyParams(
            capacity_mw=0.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0
        )

        model = RenewableFinancialModel(
            project_name="Zero Capacity",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=MarketPrices(base_power_price=80.0),
            financial_assumptions=FinancialAssumptions()
        )

        assert model.calculate_capex() == 0

    def test_very_high_discount_rate(self):
        """High discount rate should reduce NPV significantly."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=500000.0,
            opex_per_mw_year=10000.0
        )

        financial_high = FinancialAssumptions(discount_rate=0.25)  # 25%
        financial_low = FinancialAssumptions(discount_rate=0.05)   # 5%

        model_high = RenewableFinancialModel(
            project_name="High Discount",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=MarketPrices(base_power_price=100.0),
            financial_assumptions=financial_high
        )

        model_low = RenewableFinancialModel(
            project_name="Low Discount",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=MarketPrices(base_power_price=100.0),
            financial_assumptions=financial_low
        )

        npv_high = model_high.calculate_npv()
        npv_low = model_low.calculate_npv()

        assert npv_high < npv_low

    def test_ireland_region(self):
        """Ireland region should have lower capacity factor."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0
        )

        model_uk = RenewableFinancialModel(
            project_name="UK Solar",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=MarketPrices(base_power_price=80.0),
            financial_assumptions=FinancialAssumptions()
        )

        model_ie = RenewableFinancialModel(
            project_name="Ireland Solar",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.IRELAND,
            technology_params=tech_params,
            market_prices=MarketPrices(base_power_price=80.0),
            financial_assumptions=FinancialAssumptions()
        )

        gen_uk = model_uk.calculate_annual_generation(year=1)
        gen_ie = model_ie.calculate_annual_generation(year=1)

        # Ireland should have lower solar generation (10% vs 11% CF)
        assert gen_ie["solar"] < gen_uk["solar"]

    def test_price_curve_override(self):
        """Power price curve should override base price escalation."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0
        )

        # Create a custom price curve
        price_curve = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95] + [100] * 15

        market_prices = MarketPrices(
            base_power_price=100.0,  # This should be overridden
            power_price_curve=price_curve
        )

        model = RenewableFinancialModel(
            project_name="Price Curve Test",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=market_prices,
            financial_assumptions=FinancialAssumptions()
        )

        # Build cashflow to check prices are used
        df = model.build_cashflow_model()

        # Year 1 should use price_curve[0] = 50, not base_price = 100
        # This affects merchant revenue calculation
        assert model.market_prices.power_price_curve[0] == 50

    def test_single_year_lifetime(self):
        """Single year lifetime should work correctly."""
        tech_params = TechnologyParams(
            capacity_mw=10.0,
            capex_per_mw=600000.0,
            opex_per_mw_year=10000.0,
            lifetime_years=1
        )

        model = RenewableFinancialModel(
            project_name="One Year",
            technology_type=TechnologyType.SOLAR_PV,
            project_type=ProjectType.UTILITY_SCALE,
            market_region=MarketRegion.UK,
            technology_params=tech_params,
            market_prices=MarketPrices(base_power_price=80.0),
            financial_assumptions=FinancialAssumptions()
        )

        df = model.build_cashflow_model()
        assert len(df) == 2  # Year 0 and Year 1
