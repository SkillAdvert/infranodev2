"""Pytest configuration and shared fixtures for backend tests."""

import sys
from pathlib import Path

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# ============================================================================
# Shared Fixtures - Project Data
# ============================================================================


@pytest.fixture
def sample_project():
    """Create a sample project dictionary."""
    return {
        "ref_id": "proj-001",
        "site_name": "Sample Solar Farm",
        "capacity_mw": 50.0,
        "technology_type": "solar",
        "development_status_short": "in planning",
        "latitude": 51.5,
        "longitude": -0.1,
        "county": "Kent",
        "operator": "Test Developer Ltd"
    }


@pytest.fixture
def sample_projects():
    """Create a list of sample projects."""
    return [
        {
            "ref_id": f"proj-{i:03d}",
            "site_name": f"Project {i}",
            "capacity_mw": 10.0 + i * 10,
            "technology_type": "solar" if i % 2 == 0 else "wind",
            "development_status_short": "in planning",
            "latitude": 51.0 + i * 0.5,
            "longitude": -0.1 - i * 0.2,
        }
        for i in range(10)
    ]


@pytest.fixture
def sample_tec_row():
    """Create a sample TEC connections row."""
    return {
        "id": 12345,
        "project_name": "TEC Wind Farm",
        "capacity_mw": 100.0,
        "technology_type": "Wind",
        "development_status": "Under Construction",
        "constraint_status": "Constrained",
        "connection_site": "Substation Alpha",
        "substation_name": "Grid Point Beta",
        "voltage": 400,
        "latitude": 53.5,
        "longitude": -2.5,
        "customer_name": "Wind Energy Corp"
    }


# ============================================================================
# Shared Fixtures - Proximity Scores
# ============================================================================


@pytest.fixture
def sample_proximity_scores():
    """Create sample proximity scores."""
    return {
        "substation_score": 75.0,
        "transmission_score": 70.0,
        "fiber_score": 65.0,
        "ixp_score": 50.0,
        "water_score": 80.0,
        "total_proximity_bonus": 340.0,
        "nearest_distances": {
            "substation_km": 15.0,
            "transmission_km": 20.0,
            "fiber_km": 25.0,
            "ixp_km": 100.0,
            "water_km": 5.0
        }
    }


@pytest.fixture
def sample_proximity_scores_close():
    """Create proximity scores for a location close to all infrastructure."""
    return {
        "substation_score": 95.0,
        "transmission_score": 90.0,
        "fiber_score": 92.0,
        "ixp_score": 85.0,
        "water_score": 98.0,
        "total_proximity_bonus": 460.0,
        "nearest_distances": {
            "substation_km": 2.0,
            "transmission_km": 5.0,
            "fiber_km": 3.0,
            "ixp_km": 20.0,
            "water_km": 1.0
        }
    }


@pytest.fixture
def sample_proximity_scores_far():
    """Create proximity scores for a location far from all infrastructure."""
    return {
        "substation_score": 10.0,
        "transmission_score": 15.0,
        "fiber_score": 8.0,
        "ixp_score": 5.0,
        "water_score": 20.0,
        "total_proximity_bonus": 58.0,
        "nearest_distances": {
            "substation_km": 100.0,
            "transmission_km": 80.0,
            "fiber_km": 120.0,
            "ixp_km": 200.0,
            "water_km": 50.0
        }
    }


# ============================================================================
# Shared Fixtures - Financial Model
# ============================================================================


@pytest.fixture
def sample_tech_params():
    """Create sample technology parameters."""
    from backend.renewable_model import TechnologyParams
    return TechnologyParams(
        capacity_mw=10.0,
        capex_per_mw=600000.0,
        opex_per_mw_year=10000.0,
        degradation_rate_annual=0.005,
        system_losses=0.14,
        lifetime_years=25
    )


@pytest.fixture
def sample_market_prices():
    """Create sample market prices."""
    from backend.renewable_model import MarketPrices
    return MarketPrices(
        base_power_price=80.0,
        power_price_escalation=0.025,
        ppa_price=70.0,
        ppa_duration_years=15,
        ppa_percentage=0.7,
        ppa_escalation=0.02
    )


@pytest.fixture
def sample_financial_assumptions():
    """Create sample financial assumptions."""
    from backend.renewable_model import FinancialAssumptions
    return FinancialAssumptions(
        discount_rate=0.08,
        inflation_rate=0.02,
        tax_rate=0.19
    )


# ============================================================================
# Async Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_supabase_query():
    """Create a mock async Supabase query function."""
    from unittest.mock import AsyncMock

    async def query(_endpoint: str, limit: int = 1000):
        return []

    return AsyncMock(side_effect=query)


@pytest.fixture
def mock_proximity_batch():
    """Create a mock async proximity batch function."""
    from unittest.mock import AsyncMock

    async def batch(projects):
        return [
            {
                "substation_score": 50.0,
                "transmission_score": 50.0,
                "fiber_score": 50.0,
                "ixp_score": 50.0,
                "water_score": 50.0,
                "nearest_distances": {}
            }
            for _ in projects
        ]

    return AsyncMock(side_effect=batch)


# ============================================================================
# Coordinate Test Data
# ============================================================================


@pytest.fixture
def uk_coordinates():
    """Sample UK coordinates for testing."""
    return [
        {"name": "London", "lat": 51.5074, "lon": -0.1278},
        {"name": "Manchester", "lat": 53.4808, "lon": -2.2426},
        {"name": "Edinburgh", "lat": 55.9533, "lon": -3.1883},
        {"name": "Cardiff", "lat": 51.4816, "lon": -3.1791},
        {"name": "Belfast", "lat": 54.5973, "lon": -5.9301},
    ]


@pytest.fixture
def ireland_coordinates():
    """Sample Ireland coordinates for testing."""
    return [
        {"name": "Dublin", "lat": 53.3498, "lon": -6.2603},
        {"name": "Cork", "lat": 51.8985, "lon": -8.4756},
        {"name": "Galway", "lat": 53.2707, "lon": -9.0568},
    ]


# ============================================================================
# Test Categories by Capacity
# ============================================================================


@pytest.fixture
def edge_computing_projects():
    """Projects suitable for edge computing (0.4-5 MW)."""
    return [
        {"ref_id": f"edge-{i}", "capacity_mw": 0.5 + i * 0.5, "latitude": 51.0, "longitude": -0.1}
        for i in range(10)
    ]


@pytest.fixture
def colocation_projects():
    """Projects suitable for colocation (5-30 MW)."""
    return [
        {"ref_id": f"colo-{i}", "capacity_mw": 5.0 + i * 2.5, "latitude": 52.0, "longitude": -1.0}
        for i in range(10)
    ]


@pytest.fixture
def hyperscaler_projects():
    """Projects suitable for hyperscaler (30-250 MW)."""
    return [
        {"ref_id": f"hyper-{i}", "capacity_mw": 30.0 + i * 20.0, "latitude": 53.0, "longitude": -2.0}
        for i in range(10)
    ]


# ============================================================================
# Helper Functions as Fixtures
# ============================================================================


@pytest.fixture
def assert_score_bounded():
    """Helper to assert a score is in valid range."""
    def _assert(score, name="score"):
        assert 0.0 <= score <= 100.0, f"{name} = {score} is out of [0, 100] range"
    return _assert


@pytest.fixture
def assert_rating_bounded():
    """Helper to assert an investment rating is in valid range."""
    def _assert(rating, name="rating"):
        assert 0.0 <= rating <= 10.0, f"{name} = {rating} is out of [0, 10] range"
    return _assert
