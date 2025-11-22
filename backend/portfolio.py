"""
Portfolio Optimization Module for Renewable Energy Projects

Provides Markowitz-style portfolio optimization capabilities including:
- Multi-project portfolio scoring
- Correlation analysis between projects
- Optimal capacity allocation
- Geographic diversification scoring
- Risk-adjusted portfolio returns (Sharpe, Sortino, Treynor)
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Literal
from enum import Enum

from backend.scoring import (
    calculate_technology_score,
    calculate_tnuos_score,
    estimate_capacity_factor,
    get_color_from_score,
    get_rating_description,
)


class RiskProfile(Enum):
    """Risk tolerance profiles for portfolio optimization."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class ProjectReturns:
    """Expected returns and risk metrics for a single project."""
    ref_id: str
    expected_return: float  # Annual expected return (%)
    volatility: float  # Standard deviation of returns (%)
    capacity_mw: float
    technology_type: str
    latitude: float
    longitude: float
    investment_rating: float = 0.0

    # Optional financial metrics
    irr: Optional[float] = None
    npv: Optional[float] = None
    lcoe: Optional[float] = None


@dataclass
class PortfolioAllocation:
    """Optimal allocation for a project in the portfolio."""
    ref_id: str
    weight: float  # Allocation weight (0-1)
    capacity_mw: float
    allocated_capacity_mw: float  # weight * capacity_mw
    contribution_to_return: float
    contribution_to_risk: float
    marginal_risk: float


@dataclass
class PortfolioMetrics:
    """Comprehensive portfolio performance metrics."""
    # Basic portfolio stats
    total_capacity_mw: float
    project_count: int

    # Return metrics
    expected_return: float
    weighted_average_rating: float

    # Risk metrics
    portfolio_volatility: float
    portfolio_variance: float
    max_drawdown: float
    value_at_risk_95: float
    conditional_var_95: float

    # Risk-adjusted returns
    sharpe_ratio: float
    sortino_ratio: float
    treynor_ratio: float
    information_ratio: float

    # Diversification metrics
    diversification_ratio: float
    concentration_hhi: float  # Herfindahl-Hirschman Index
    effective_num_projects: float

    # Geographic diversification
    geographic_score: float
    technology_mix_score: float
    regional_concentration: Dict[str, float] = field(default_factory=dict)
    technology_breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class EfficientFrontierPoint:
    """A single point on the efficient frontier."""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]
    allocations: List[PortfolioAllocation]


@dataclass
class CorrelationMatrix:
    """Correlation and covariance matrices for portfolio projects."""
    project_ids: List[str]
    correlation_matrix: np.ndarray
    covariance_matrix: np.ndarray
    technology_correlations: Dict[Tuple[str, str], float]
    geographic_correlations: Dict[Tuple[str, str], float]


# Technology correlation priors based on generation characteristics
TECHNOLOGY_CORRELATION_PRIORS: Dict[Tuple[str, str], float] = {
    ("solar", "solar"): 1.0,
    ("wind", "wind"): 1.0,
    ("battery", "battery"): 1.0,
    ("solar", "wind"): 0.25,  # Low correlation - different generation profiles
    ("wind", "solar"): 0.25,
    ("solar", "battery"): 0.15,  # Battery smooths solar output
    ("battery", "solar"): 0.15,
    ("wind", "battery"): 0.20,
    ("battery", "wind"): 0.20,
    ("hybrid", "solar"): 0.60,
    ("solar", "hybrid"): 0.60,
    ("hybrid", "wind"): 0.55,
    ("wind", "hybrid"): 0.55,
    ("hybrid", "battery"): 0.40,
    ("battery", "hybrid"): 0.40,
    ("hybrid", "hybrid"): 0.70,
}

# UK regional zones for geographic analysis
UK_REGIONS: Dict[str, Dict[str, float]] = {
    "scotland_north": {"lat_min": 57.0, "lat_max": 61.0, "lng_min": -8.0, "lng_max": -1.0},
    "scotland_south": {"lat_min": 55.0, "lat_max": 57.0, "lng_min": -6.0, "lng_max": -2.0},
    "north_england": {"lat_min": 53.5, "lat_max": 55.0, "lng_min": -3.5, "lng_max": 0.0},
    "midlands": {"lat_min": 52.0, "lat_max": 53.5, "lng_min": -3.0, "lng_max": 0.5},
    "wales": {"lat_min": 51.3, "lat_max": 53.5, "lng_min": -5.5, "lng_max": -2.5},
    "east_england": {"lat_min": 51.5, "lat_max": 53.0, "lng_min": 0.0, "lng_max": 2.0},
    "south_east": {"lat_min": 50.5, "lat_max": 52.0, "lng_min": -1.5, "lng_max": 1.5},
    "south_west": {"lat_min": 50.0, "lat_max": 52.0, "lng_min": -5.5, "lng_max": -2.0},
}


def _get_technology_type(tech: str) -> str:
    """Normalize technology type string."""
    tech_lower = str(tech).lower()
    if "solar" in tech_lower:
        return "solar"
    if "wind" in tech_lower:
        return "wind"
    if "battery" in tech_lower or "bess" in tech_lower:
        return "battery"
    if "hybrid" in tech_lower:
        return "hybrid"
    return "other"


def _get_region(lat: float, lng: float) -> str:
    """Determine UK region from coordinates."""
    for region, bounds in UK_REGIONS.items():
        if (bounds["lat_min"] <= lat <= bounds["lat_max"] and
            bounds["lng_min"] <= lng <= bounds["lng_max"]):
            return region
    return "other"


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate great-circle distance between two points in km."""
    R = 6371.0  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def estimate_project_returns(
    project: Dict[str, Any],
    base_return: float = 8.0,
    base_volatility: float = 15.0,
) -> ProjectReturns:
    """
    Estimate expected returns and volatility for a project based on its characteristics.

    Returns are estimated based on:
    - Technology type and associated capacity factor
    - Development stage (more advanced = lower risk premium)
    - Location (TNUoS impact on costs)
    - Investment rating from scoring module
    """
    ref_id = project.get("ref_id", "unknown")
    capacity_mw = float(project.get("capacity_mw", 0) or 0)
    tech_type = str(project.get("technology_type", "")).lower()
    lat = float(project.get("latitude", 0) or 0)
    lng = float(project.get("longitude", 0) or 0)
    dev_status = str(project.get("development_status_short", "")).lower()
    investment_rating = float(project.get("investment_rating", 5.0) or 5.0)

    # Technology-based return adjustments
    tech_return_adj = {
        "solar": 0.5,
        "wind": 1.0,
        "battery": 1.5,
        "hybrid": 1.2,
        "other": 0.0,
    }

    # Technology-based volatility adjustments
    tech_vol_adj = {
        "solar": -2.0,  # Lower volatility
        "wind": 3.0,    # Higher volatility
        "battery": 5.0,  # Highest volatility (market dependent)
        "hybrid": 1.0,
        "other": 2.0,
    }

    # Development stage adjustments (more advanced = lower risk)
    stage_vol_adj = {
        "operational": -5.0,
        "under construction": -2.0,
        "consented": 0.0,
        "in planning": 3.0,
        "concept": 5.0,
    }

    # Get capacity factor for return estimation
    capacity_factor = estimate_capacity_factor(tech_type, lat)

    # TNUoS impact on returns
    tnuos_score = calculate_tnuos_score(lat, lng)
    tnuos_return_adj = (tnuos_score - 50) / 100  # -0.5 to +0.5

    # Rating-based return adjustment
    rating_return_adj = (investment_rating - 5.0) * 0.3

    # Calculate expected return
    tech_key = _get_technology_type(tech_type)
    expected_return = (
        base_return +
        tech_return_adj.get(tech_key, 0) +
        tnuos_return_adj +
        rating_return_adj +
        (capacity_factor - 25) / 50  # Capacity factor bonus
    )

    # Calculate volatility
    stage_adj = 0.0
    for status, adj in stage_vol_adj.items():
        if status in dev_status:
            stage_adj = adj
            break

    volatility = (
        base_volatility +
        tech_vol_adj.get(tech_key, 0) +
        stage_adj
    )

    # Ensure reasonable bounds
    expected_return = max(2.0, min(20.0, expected_return))
    volatility = max(5.0, min(40.0, volatility))

    return ProjectReturns(
        ref_id=ref_id,
        expected_return=expected_return,
        volatility=volatility,
        capacity_mw=capacity_mw,
        technology_type=tech_type,
        latitude=lat,
        longitude=lng,
        investment_rating=investment_rating,
        irr=project.get("irr"),
        npv=project.get("npv"),
        lcoe=project.get("lcoe"),
    )


def build_correlation_matrix(
    project_returns: List[ProjectReturns],
    distance_decay_km: float = 200.0,
) -> CorrelationMatrix:
    """
    Build correlation and covariance matrices for portfolio projects.

    Correlation is estimated based on:
    - Technology type (different technologies have lower correlation)
    - Geographic distance (distant projects have lower correlation)
    """
    n = len(project_returns)
    if n == 0:
        return CorrelationMatrix(
            project_ids=[],
            correlation_matrix=np.array([[]]),
            covariance_matrix=np.array([[]]),
            technology_correlations={},
            geographic_correlations={},
        )

    project_ids = [p.ref_id for p in project_returns]
    correlation_matrix = np.zeros((n, n))
    technology_correlations: Dict[Tuple[str, str], float] = {}
    geographic_correlations: Dict[Tuple[str, str], float] = {}

    for i in range(n):
        for j in range(n):
            if i == j:
                correlation_matrix[i, j] = 1.0
                continue

            p1 = project_returns[i]
            p2 = project_returns[j]

            # Technology correlation
            tech1 = _get_technology_type(p1.technology_type)
            tech2 = _get_technology_type(p2.technology_type)
            tech_corr = TECHNOLOGY_CORRELATION_PRIORS.get(
                (tech1, tech2),
                0.5 if tech1 == tech2 else 0.3
            )

            # Geographic correlation (decay with distance)
            distance = _haversine_distance(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
            geo_corr = math.exp(-distance / distance_decay_km)

            # Combined correlation (weighted average)
            combined_corr = 0.6 * tech_corr + 0.4 * geo_corr
            combined_corr = max(0.0, min(1.0, combined_corr))

            correlation_matrix[i, j] = combined_corr
            technology_correlations[(p1.ref_id, p2.ref_id)] = tech_corr
            geographic_correlations[(p1.ref_id, p2.ref_id)] = geo_corr

    # Build covariance matrix
    volatilities = np.array([p.volatility / 100 for p in project_returns])
    covariance_matrix = np.outer(volatilities, volatilities) * correlation_matrix

    return CorrelationMatrix(
        project_ids=project_ids,
        correlation_matrix=correlation_matrix,
        covariance_matrix=covariance_matrix,
        technology_correlations=technology_correlations,
        geographic_correlations=geographic_correlations,
    )


def calculate_portfolio_variance(
    weights: np.ndarray,
    covariance_matrix: np.ndarray,
) -> float:
    """Calculate portfolio variance given weights and covariance matrix."""
    return float(np.dot(weights.T, np.dot(covariance_matrix, weights)))


def calculate_portfolio_return(
    weights: np.ndarray,
    expected_returns: np.ndarray,
) -> float:
    """Calculate portfolio expected return given weights and returns."""
    return float(np.dot(weights, expected_returns))


def optimize_portfolio_markowitz(
    project_returns: List[ProjectReturns],
    correlation_matrix: CorrelationMatrix,
    target_return: Optional[float] = None,
    risk_profile: RiskProfile = RiskProfile.MODERATE,
    max_weight: float = 0.4,
    min_weight: float = 0.0,
    max_iterations: int = 1000,
) -> Tuple[Dict[str, float], PortfolioMetrics]:
    """
    Markowitz-style mean-variance portfolio optimization.

    Uses gradient descent to find optimal weights that minimize portfolio
    variance for a given target return (or maximize Sharpe ratio if no target).

    Args:
        project_returns: List of ProjectReturns for each project
        correlation_matrix: Correlation and covariance matrices
        target_return: Optional target portfolio return
        risk_profile: Risk tolerance level
        max_weight: Maximum allocation to single project
        min_weight: Minimum allocation to any included project
        max_iterations: Maximum optimization iterations

    Returns:
        Tuple of (optimal_weights dict, PortfolioMetrics)
    """
    n = len(project_returns)
    if n == 0:
        return {}, PortfolioMetrics(
            total_capacity_mw=0, project_count=0, expected_return=0,
            weighted_average_rating=0, portfolio_volatility=0, portfolio_variance=0,
            max_drawdown=0, value_at_risk_95=0, conditional_var_95=0,
            sharpe_ratio=0, sortino_ratio=0, treynor_ratio=0, information_ratio=0,
            diversification_ratio=0, concentration_hhi=0, effective_num_projects=0,
            geographic_score=0, technology_mix_score=0,
        )

    # Extract returns and covariance
    returns = np.array([p.expected_return / 100 for p in project_returns])
    cov_matrix = correlation_matrix.covariance_matrix

    # Risk profile adjustments
    risk_aversion = {
        RiskProfile.CONSERVATIVE: 3.0,
        RiskProfile.MODERATE: 1.5,
        RiskProfile.AGGRESSIVE: 0.5,
    }[risk_profile]

    # Initialize with equal weights
    weights = np.ones(n) / n

    # Risk-free rate for Sharpe calculation
    risk_free_rate = 0.04

    # Gradient descent optimization
    learning_rate = 0.01

    for iteration in range(max_iterations):
        # Calculate current portfolio metrics
        port_return = calculate_portfolio_return(weights, returns)
        port_variance = calculate_portfolio_variance(weights, cov_matrix)
        port_std = math.sqrt(port_variance)

        # Objective: maximize (return - risk_aversion * variance)
        # Or minimize variance subject to target return
        if target_return is not None:
            # Minimize variance + penalty for missing target
            return_penalty = 100 * (port_return - target_return / 100) ** 2
            gradient = 2 * np.dot(cov_matrix, weights) + return_penalty * np.sign(port_return - target_return / 100)
        else:
            # Maximize Sharpe ratio (equivalent to minimizing neg-Sharpe)
            if port_std > 0:
                sharpe = (port_return - risk_free_rate) / port_std
                # Gradient of negative Sharpe ratio
                grad_return = -1 / port_std
                grad_var = (port_return - risk_free_rate) / (2 * port_std ** 3)
                gradient = grad_return * returns + grad_var * 2 * np.dot(cov_matrix, weights)
                # Add risk aversion penalty
                gradient += risk_aversion * 2 * np.dot(cov_matrix, weights)
            else:
                gradient = np.zeros(n)

        # Update weights
        weights = weights - learning_rate * gradient

        # Project back to valid simplex (weights sum to 1, bounded)
        weights = np.clip(weights, min_weight, max_weight)
        weight_sum = np.sum(weights)
        if weight_sum > 0:
            weights = weights / weight_sum
        else:
            weights = np.ones(n) / n

        # Check convergence
        if iteration > 0 and np.max(np.abs(gradient)) < 1e-6:
            break

    # Build results
    optimal_weights = {p.ref_id: float(w) for p, w in zip(project_returns, weights)}

    # Calculate final metrics
    metrics = calculate_portfolio_metrics(project_returns, optimal_weights, correlation_matrix)

    return optimal_weights, metrics


def calculate_portfolio_metrics(
    project_returns: List[ProjectReturns],
    weights: Dict[str, float],
    correlation_matrix: CorrelationMatrix,
    risk_free_rate: float = 0.04,
    market_return: float = 0.08,
    market_volatility: float = 0.15,
) -> PortfolioMetrics:
    """
    Calculate comprehensive portfolio metrics.

    Includes return metrics, risk metrics, risk-adjusted returns, and diversification measures.
    """
    if not project_returns or not weights:
        return PortfolioMetrics(
            total_capacity_mw=0, project_count=0, expected_return=0,
            weighted_average_rating=0, portfolio_volatility=0, portfolio_variance=0,
            max_drawdown=0, value_at_risk_95=0, conditional_var_95=0,
            sharpe_ratio=0, sortino_ratio=0, treynor_ratio=0, information_ratio=0,
            diversification_ratio=0, concentration_hhi=0, effective_num_projects=0,
            geographic_score=0, technology_mix_score=0,
        )

    # Map projects by ID
    project_map = {p.ref_id: p for p in project_returns}

    # Get ordered weights and returns
    ordered_projects = [p for p in project_returns if p.ref_id in weights]
    weight_array = np.array([weights.get(p.ref_id, 0) for p in ordered_projects])
    return_array = np.array([p.expected_return / 100 for p in ordered_projects])
    volatility_array = np.array([p.volatility / 100 for p in ordered_projects])
    rating_array = np.array([p.investment_rating for p in ordered_projects])
    capacity_array = np.array([p.capacity_mw for p in ordered_projects])

    # Basic stats
    total_capacity = float(np.sum(capacity_array * weight_array) / max(np.sum(weight_array), 1e-9) * len(ordered_projects))
    project_count = len([w for w in weight_array if w > 0.01])

    # Portfolio return
    expected_return = float(np.dot(weight_array, return_array) * 100)
    weighted_avg_rating = float(np.dot(weight_array, rating_array))

    # Portfolio variance and volatility
    cov_matrix = correlation_matrix.covariance_matrix
    if cov_matrix.shape[0] == len(weight_array):
        port_variance = calculate_portfolio_variance(weight_array, cov_matrix)
    else:
        # Fallback if matrices don't align
        port_variance = float(np.dot(weight_array ** 2, volatility_array ** 2))

    port_volatility = math.sqrt(max(0, port_variance)) * 100

    # VaR and CVaR (parametric, assuming normal distribution)
    z_95 = 1.645
    value_at_risk_95 = expected_return - z_95 * port_volatility
    conditional_var_95 = expected_return - 2.063 * port_volatility  # Expected shortfall

    # Maximum drawdown estimation (simplified)
    max_drawdown = port_volatility * 2.5  # Rough approximation

    # Risk-adjusted returns
    excess_return = expected_return / 100 - risk_free_rate

    # Sharpe ratio
    sharpe_ratio = excess_return / (port_volatility / 100) if port_volatility > 0 else 0

    # Sortino ratio (using downside deviation)
    downside_returns = return_array[return_array < risk_free_rate]
    if len(downside_returns) > 0:
        downside_dev = float(np.std(downside_returns - risk_free_rate))
    else:
        downside_dev = port_volatility / 100 / 2
    sortino_ratio = excess_return / downside_dev if downside_dev > 0 else sharpe_ratio

    # Treynor ratio (using market beta)
    # Simplified: assume beta = portfolio_vol / market_vol * correlation
    beta = (port_volatility / 100) / market_volatility * 0.7
    treynor_ratio = excess_return / beta if beta > 0 else 0

    # Information ratio (vs benchmark)
    tracking_error = abs(expected_return / 100 - market_return)
    information_ratio = (expected_return / 100 - market_return) / tracking_error if tracking_error > 0 else 0

    # Diversification metrics
    # Diversification ratio: sum of weighted vols / portfolio vol
    weighted_vol_sum = float(np.dot(weight_array, volatility_array))
    diversification_ratio = weighted_vol_sum / (port_volatility / 100) if port_volatility > 0 else 1.0

    # Herfindahl-Hirschman Index (concentration)
    concentration_hhi = float(np.sum(weight_array ** 2))

    # Effective number of projects (inverse HHI)
    effective_num_projects = 1 / concentration_hhi if concentration_hhi > 0 else len(ordered_projects)

    # Geographic diversification score
    geographic_score, regional_concentration = _calculate_geographic_diversification(
        ordered_projects, weight_array
    )

    # Technology mix score
    technology_mix_score, tech_breakdown = _calculate_technology_diversification(
        ordered_projects, weight_array
    )

    return PortfolioMetrics(
        total_capacity_mw=total_capacity,
        project_count=project_count,
        expected_return=expected_return,
        weighted_average_rating=weighted_avg_rating,
        portfolio_volatility=port_volatility,
        portfolio_variance=port_variance * 10000,  # Convert to percentage squared
        max_drawdown=max_drawdown,
        value_at_risk_95=value_at_risk_95,
        conditional_var_95=conditional_var_95,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        treynor_ratio=treynor_ratio,
        information_ratio=information_ratio,
        diversification_ratio=diversification_ratio,
        concentration_hhi=concentration_hhi,
        effective_num_projects=effective_num_projects,
        geographic_score=geographic_score,
        technology_mix_score=technology_mix_score,
        regional_concentration=regional_concentration,
        technology_breakdown=tech_breakdown,
    )


def _calculate_geographic_diversification(
    projects: List[ProjectReturns],
    weights: np.ndarray,
) -> Tuple[float, Dict[str, float]]:
    """Calculate geographic diversification score and regional breakdown."""
    regional_weights: Dict[str, float] = {}

    for project, weight in zip(projects, weights):
        region = _get_region(project.latitude, project.longitude)
        regional_weights[region] = regional_weights.get(region, 0) + weight

    # Geographic HHI (lower is more diversified)
    geo_hhi = sum(w ** 2 for w in regional_weights.values())

    # Convert to score (0-100, higher is better)
    max_regions = len(UK_REGIONS)
    min_hhi = 1 / max_regions  # Perfect diversification

    if geo_hhi >= 1:
        geo_score = 0
    else:
        geo_score = 100 * (1 - geo_hhi) / (1 - min_hhi)

    return float(geo_score), regional_weights


def _calculate_technology_diversification(
    projects: List[ProjectReturns],
    weights: np.ndarray,
) -> Tuple[float, Dict[str, float]]:
    """Calculate technology mix diversification score."""
    tech_weights: Dict[str, float] = {}

    for project, weight in zip(projects, weights):
        tech = _get_technology_type(project.technology_type)
        tech_weights[tech] = tech_weights.get(tech, 0) + weight

    # Technology HHI
    tech_hhi = sum(w ** 2 for w in tech_weights.values())

    # Bonus for complementary technologies (solar + wind is better than 2x solar)
    complementary_bonus = 0
    if "solar" in tech_weights and "wind" in tech_weights:
        complementary_bonus = 0.1 * min(tech_weights["solar"], tech_weights["wind"])
    if "battery" in tech_weights:
        complementary_bonus += 0.05 * tech_weights["battery"]

    # Convert to score
    max_techs = 4  # solar, wind, battery, hybrid
    min_hhi = 1 / max_techs

    if tech_hhi >= 1:
        tech_score = 0
    else:
        tech_score = 100 * (1 - tech_hhi) / (1 - min_hhi)

    tech_score = min(100, tech_score + complementary_bonus * 100)

    return float(tech_score), tech_weights


def calculate_efficient_frontier(
    project_returns: List[ProjectReturns],
    correlation_matrix: CorrelationMatrix,
    num_points: int = 20,
    max_weight: float = 0.4,
    min_weight: float = 0.0,
) -> List[EfficientFrontierPoint]:
    """
    Calculate the efficient frontier for the portfolio.

    Returns a series of optimal portfolios ranging from minimum variance
    to maximum return.
    """
    if not project_returns:
        return []

    # Find return range
    min_return = min(p.expected_return for p in project_returns)
    max_return = max(p.expected_return for p in project_returns)

    frontier_points = []

    for i in range(num_points):
        # Target return for this point
        target_return = min_return + (max_return - min_return) * i / (num_points - 1)

        # Optimize for this target
        weights, metrics = optimize_portfolio_markowitz(
            project_returns,
            correlation_matrix,
            target_return=target_return,
            max_weight=max_weight,
            min_weight=min_weight,
        )

        # Build allocations
        allocations = []
        for p in project_returns:
            w = weights.get(p.ref_id, 0)
            if w > 0.001:
                allocations.append(PortfolioAllocation(
                    ref_id=p.ref_id,
                    weight=w,
                    capacity_mw=p.capacity_mw,
                    allocated_capacity_mw=w * p.capacity_mw,
                    contribution_to_return=w * p.expected_return,
                    contribution_to_risk=w * p.volatility,
                    marginal_risk=0,  # Would require additional calculation
                ))

        frontier_points.append(EfficientFrontierPoint(
            expected_return=metrics.expected_return,
            volatility=metrics.portfolio_volatility,
            sharpe_ratio=metrics.sharpe_ratio,
            weights=weights,
            allocations=allocations,
        ))

    return frontier_points


def calculate_multi_project_portfolio_score(
    projects: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Calculate comprehensive portfolio scoring for multiple projects.

    This is the main entry point for portfolio analysis.

    Args:
        projects: List of project dictionaries with standard fields
        weights: Optional custom weights. If None, equal weights are used.

    Returns:
        Dictionary with portfolio scores and metrics
    """
    if not projects:
        return {
            "portfolio_score": 0,
            "rating_description": "No Projects",
            "color_code": "#CC0000",
            "metrics": None,
            "allocations": [],
            "correlation_summary": {},
        }

    # Convert projects to returns
    project_returns = [estimate_project_returns(p) for p in projects]

    # Use equal weights if not provided
    if weights is None:
        n = len(projects)
        weights = {p.ref_id: 1.0 / n for p in project_returns}

    # Build correlation matrix
    corr_matrix = build_correlation_matrix(project_returns)

    # Optimize portfolio
    optimal_weights, metrics = optimize_portfolio_markowitz(
        project_returns,
        corr_matrix,
        risk_profile=RiskProfile.MODERATE,
    )

    # Calculate portfolio score (composite of multiple factors)
    # Weight: rating (30%), Sharpe (25%), diversification (25%), geographic (20%)
    rating_component = metrics.weighted_average_rating * 10  # Scale to 100
    sharpe_component = min(100, max(0, metrics.sharpe_ratio * 33))  # Sharpe of 3 = 100
    div_component = min(100, metrics.diversification_ratio * 50)
    geo_component = metrics.geographic_score

    portfolio_score = (
        0.30 * rating_component +
        0.25 * sharpe_component +
        0.25 * div_component +
        0.20 * geo_component
    )

    # Build allocations
    allocations = []
    for p in project_returns:
        w = optimal_weights.get(p.ref_id, 0)
        allocations.append({
            "ref_id": p.ref_id,
            "weight": round(w, 4),
            "weight_pct": round(w * 100, 2),
            "capacity_mw": p.capacity_mw,
            "expected_return": round(p.expected_return, 2),
            "volatility": round(p.volatility, 2),
            "technology_type": p.technology_type,
        })

    # Sort by weight
    allocations.sort(key=lambda x: x["weight"], reverse=True)

    # Correlation summary
    avg_correlation = float(np.mean(corr_matrix.correlation_matrix))
    min_correlation = float(np.min(corr_matrix.correlation_matrix[corr_matrix.correlation_matrix < 1]))
    max_correlation = float(np.max(corr_matrix.correlation_matrix[corr_matrix.correlation_matrix < 1]))

    return {
        "portfolio_score": round(portfolio_score, 1),
        "rating_description": get_rating_description(portfolio_score),
        "color_code": get_color_from_score(portfolio_score),
        "metrics": {
            "total_capacity_mw": round(metrics.total_capacity_mw, 2),
            "project_count": metrics.project_count,
            "expected_return_pct": round(metrics.expected_return, 2),
            "weighted_average_rating": round(metrics.weighted_average_rating, 2),
            "portfolio_volatility_pct": round(metrics.portfolio_volatility, 2),
            "sharpe_ratio": round(metrics.sharpe_ratio, 3),
            "sortino_ratio": round(metrics.sortino_ratio, 3),
            "treynor_ratio": round(metrics.treynor_ratio, 3),
            "value_at_risk_95_pct": round(metrics.value_at_risk_95, 2),
            "diversification_ratio": round(metrics.diversification_ratio, 3),
            "concentration_hhi": round(metrics.concentration_hhi, 4),
            "effective_num_projects": round(metrics.effective_num_projects, 2),
            "geographic_score": round(metrics.geographic_score, 1),
            "technology_mix_score": round(metrics.technology_mix_score, 1),
            "regional_breakdown": {k: round(v, 4) for k, v in metrics.regional_concentration.items()},
            "technology_breakdown": {k: round(v, 4) for k, v in metrics.technology_breakdown.items()},
        },
        "allocations": allocations,
        "correlation_summary": {
            "average_correlation": round(avg_correlation, 3),
            "min_correlation": round(min_correlation, 3) if min_correlation < float('inf') else 0,
            "max_correlation": round(max_correlation, 3) if max_correlation > float('-inf') else 1,
        },
        "efficient_frontier_available": True,
    }


def calculate_optimal_allocation(
    projects: List[Dict[str, Any]],
    total_investment_mw: Optional[float] = None,
    risk_profile: RiskProfile = RiskProfile.MODERATE,
    max_single_project_pct: float = 40.0,
    min_projects: int = 3,
    constraints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calculate optimal capacity allocation across projects.

    Args:
        projects: List of project dictionaries
        total_investment_mw: Total MW to allocate (if None, uses sum of project capacities)
        risk_profile: Risk tolerance level
        max_single_project_pct: Maximum % allocation to single project
        min_projects: Minimum number of projects in portfolio
        constraints: Optional additional constraints (e.g., max per technology)

    Returns:
        Dictionary with optimal allocations and portfolio metrics
    """
    if not projects or len(projects) < min_projects:
        return {
            "success": False,
            "error": f"Need at least {min_projects} projects for portfolio optimization",
            "allocations": [],
        }

    project_returns = [estimate_project_returns(p) for p in projects]
    corr_matrix = build_correlation_matrix(project_returns)

    # Optimize
    max_weight = max_single_project_pct / 100
    min_weight = 0.01 if len(projects) > 10 else 0.0

    optimal_weights, metrics = optimize_portfolio_markowitz(
        project_returns,
        corr_matrix,
        risk_profile=risk_profile,
        max_weight=max_weight,
        min_weight=min_weight,
    )

    # Calculate allocations
    if total_investment_mw is None:
        total_investment_mw = sum(p.capacity_mw for p in project_returns)

    allocations = []
    for p in project_returns:
        w = optimal_weights.get(p.ref_id, 0)
        allocated_mw = w * total_investment_mw

        allocations.append({
            "ref_id": p.ref_id,
            "weight": round(w, 4),
            "allocated_capacity_mw": round(allocated_mw, 2),
            "original_capacity_mw": p.capacity_mw,
            "utilization_pct": round(100 * allocated_mw / p.capacity_mw, 1) if p.capacity_mw > 0 else 0,
            "expected_return_pct": round(p.expected_return, 2),
            "risk_contribution_pct": round(w * p.volatility, 2),
        })

    # Sort by allocation
    allocations.sort(key=lambda x: x["weight"], reverse=True)

    return {
        "success": True,
        "total_investment_mw": round(total_investment_mw, 2),
        "risk_profile": risk_profile.value,
        "allocations": allocations,
        "portfolio_metrics": {
            "expected_return_pct": round(metrics.expected_return, 2),
            "portfolio_volatility_pct": round(metrics.portfolio_volatility, 2),
            "sharpe_ratio": round(metrics.sharpe_ratio, 3),
            "diversification_ratio": round(metrics.diversification_ratio, 3),
        },
        "constraints_applied": {
            "max_single_project_pct": max_single_project_pct,
            "min_projects": min_projects,
        },
    }


def analyze_portfolio_correlations(
    projects: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Detailed correlation analysis between projects.

    Returns technology and geographic correlation breakdown.
    """
    if len(projects) < 2:
        return {
            "error": "Need at least 2 projects for correlation analysis",
            "correlations": [],
        }

    project_returns = [estimate_project_returns(p) for p in projects]
    corr_matrix = build_correlation_matrix(project_returns)

    # Build pairwise correlations
    correlations = []
    n = len(project_returns)

    for i in range(n):
        for j in range(i + 1, n):
            p1 = project_returns[i]
            p2 = project_returns[j]

            tech_corr = corr_matrix.technology_correlations.get((p1.ref_id, p2.ref_id), 0)
            geo_corr = corr_matrix.geographic_correlations.get((p1.ref_id, p2.ref_id), 0)
            combined = corr_matrix.correlation_matrix[i, j]

            distance = _haversine_distance(p1.latitude, p1.longitude, p2.latitude, p2.longitude)

            correlations.append({
                "project_1": p1.ref_id,
                "project_2": p2.ref_id,
                "technology_1": _get_technology_type(p1.technology_type),
                "technology_2": _get_technology_type(p2.technology_type),
                "combined_correlation": round(combined, 3),
                "technology_correlation": round(tech_corr, 3),
                "geographic_correlation": round(geo_corr, 3),
                "distance_km": round(distance, 1),
            })

    # Sort by correlation (lowest first - best for diversification)
    correlations.sort(key=lambda x: x["combined_correlation"])

    # Summary statistics
    all_corrs = [c["combined_correlation"] for c in correlations]

    return {
        "pairwise_correlations": correlations,
        "summary": {
            "average_correlation": round(np.mean(all_corrs), 3),
            "median_correlation": round(np.median(all_corrs), 3),
            "min_correlation": round(min(all_corrs), 3),
            "max_correlation": round(max(all_corrs), 3),
            "std_correlation": round(np.std(all_corrs), 3),
        },
        "best_diversifying_pairs": correlations[:5],
        "highest_correlated_pairs": correlations[-5:][::-1],
    }


def calculate_risk_adjusted_returns(
    projects: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
    benchmark_return: float = 8.0,
    benchmark_volatility: float = 15.0,
    risk_free_rate: float = 4.0,
) -> Dict[str, Any]:
    """
    Calculate comprehensive risk-adjusted return metrics for the portfolio.

    Returns Sharpe, Sortino, Treynor, and other risk-adjusted metrics.
    """
    if not projects:
        return {"error": "No projects provided"}

    project_returns = [estimate_project_returns(p) for p in projects]

    # Use equal weights if not provided
    if weights is None:
        n = len(projects)
        weights = {p.ref_id: 1.0 / n for p in project_returns}

    corr_matrix = build_correlation_matrix(project_returns)
    metrics = calculate_portfolio_metrics(
        project_returns,
        weights,
        corr_matrix,
        risk_free_rate=risk_free_rate / 100,
        market_return=benchmark_return / 100,
        market_volatility=benchmark_volatility / 100,
    )

    # Additional metrics
    return {
        "portfolio_return_pct": round(metrics.expected_return, 2),
        "portfolio_volatility_pct": round(metrics.portfolio_volatility, 2),
        "benchmark_return_pct": benchmark_return,
        "benchmark_volatility_pct": benchmark_volatility,
        "risk_free_rate_pct": risk_free_rate,
        "risk_adjusted_metrics": {
            "sharpe_ratio": round(metrics.sharpe_ratio, 3),
            "sortino_ratio": round(metrics.sortino_ratio, 3),
            "treynor_ratio": round(metrics.treynor_ratio, 3),
            "information_ratio": round(metrics.information_ratio, 3),
        },
        "risk_metrics": {
            "value_at_risk_95_pct": round(metrics.value_at_risk_95, 2),
            "conditional_var_95_pct": round(metrics.conditional_var_95, 2),
            "max_drawdown_pct": round(metrics.max_drawdown, 2),
        },
        "interpretation": {
            "sharpe_assessment": _interpret_sharpe(metrics.sharpe_ratio),
            "risk_level": _interpret_risk_level(metrics.portfolio_volatility),
            "diversification_assessment": _interpret_diversification(metrics.diversification_ratio),
        },
    }


def _interpret_sharpe(sharpe: float) -> str:
    """Interpret Sharpe ratio value."""
    if sharpe >= 2.0:
        return "Excellent risk-adjusted returns"
    if sharpe >= 1.0:
        return "Good risk-adjusted returns"
    if sharpe >= 0.5:
        return "Acceptable risk-adjusted returns"
    if sharpe >= 0:
        return "Marginal risk-adjusted returns"
    return "Poor risk-adjusted returns (negative)"


def _interpret_risk_level(volatility: float) -> str:
    """Interpret portfolio volatility."""
    if volatility < 10:
        return "Low risk"
    if volatility < 15:
        return "Moderate risk"
    if volatility < 25:
        return "Elevated risk"
    return "High risk"


def _interpret_diversification(ratio: float) -> str:
    """Interpret diversification ratio."""
    if ratio >= 1.5:
        return "Well diversified - significant risk reduction from diversification"
    if ratio >= 1.2:
        return "Moderately diversified"
    if ratio >= 1.0:
        return "Limited diversification benefit"
    return "No diversification benefit"


__all__ = [
    # Enums
    "RiskProfile",
    # Data classes
    "ProjectReturns",
    "PortfolioAllocation",
    "PortfolioMetrics",
    "EfficientFrontierPoint",
    "CorrelationMatrix",
    # Core functions
    "estimate_project_returns",
    "build_correlation_matrix",
    "calculate_portfolio_variance",
    "calculate_portfolio_return",
    "optimize_portfolio_markowitz",
    "calculate_portfolio_metrics",
    "calculate_efficient_frontier",
    # High-level API functions
    "calculate_multi_project_portfolio_score",
    "calculate_optimal_allocation",
    "analyze_portfolio_correlations",
    "calculate_risk_adjusted_returns",
]
