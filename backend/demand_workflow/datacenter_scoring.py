"""
Data Center Developer Scoring Workflow

This module provides the scoring logic for data center developers evaluating
renewable energy projects and potential site locations. It supports both
persona-based scoring (hyperscaler, colocation, edge_computing) and standard
renewable energy scoring.

Key Features:
- User site validation (UK bounds, capacity, commissioning year)
- Infrastructure proximity scoring
- Persona-weighted scoring based on data center type
- Investment rating calculation
"""

import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel


class UserSite(BaseModel):
    """
    Data center site submitted by user for scoring.

    Attributes:
        site_name: Name/identifier for the site
        technology_type: Type of renewable technology (e.g., 'solar', 'wind')
        capacity_mw: Site capacity in megawatts
        latitude: Site latitude coordinate
        longitude: Site longitude coordinate
        commissioning_year: Expected year of commissioning
        is_btm: Whether this is a behind-the-meter project
        capacity_factor: Optional capacity factor for the site
        development_status_short: Development status (default: 'planning')
    """
    site_name: str
    technology_type: str
    capacity_mw: float
    latitude: float
    longitude: float
    commissioning_year: int
    is_btm: bool
    capacity_factor: Optional[float] = None
    development_status_short: Optional[str] = "planning"


async def score_user_sites(
    sites: List[UserSite],
    persona: Optional[str],
    calculate_proximity_scores_batch,
    calculate_persona_weighted_score,
    calculate_enhanced_investment_rating,
) -> Dict[str, Any]:
    """
    Score user-submitted data center sites for investment potential.

    This is the main entry point for the data center developer workflow.
    It validates sites, calculates infrastructure proximity, and applies
    either persona-based or standard scoring.

    Args:
        sites: List of user sites to score
        persona: Optional data center persona ('hyperscaler', 'colocation', 'edge_computing')
        calculate_proximity_scores_batch: Function to calculate infrastructure proximity
        calculate_persona_weighted_score: Function to calculate persona-weighted scores
        calculate_enhanced_investment_rating: Function to calculate standard investment rating

    Returns:
        Dictionary containing scored sites and metadata

    Raises:
        HTTPException: If validation fails (invalid coordinates, capacity, or year)
    """
    if not sites:
        raise HTTPException(400, "No sites provided")

    # Validate all sites
    for index, site in enumerate(sites):
        if not (49.8 <= site.latitude <= 60.9) or not (-10.8 <= site.longitude <= 2.0):
            raise HTTPException(400, f"Site {index + 1}: Coordinates outside UK bounds")
        if not (5 <= site.capacity_mw <= 500):
            raise HTTPException(400, f"Site {index + 1}: Capacity must be between 5-500 MW")
        if not (2025 <= site.commissioning_year <= 2035):
            raise HTTPException(400, f"Site {index + 1}: Commissioning year must be between 2025-2035")

    scoring_mode = "persona-based" if persona else "renewable energy"
    print(f"🔄 Scoring {len(sites)} user-submitted sites with {scoring_mode.upper()} system...")
    start_time = time.time()

    # Convert sites to calculation format
    sites_for_calc: List[Dict[str, Any]] = []
    for site in sites:
        sites_for_calc.append(
            {
                "site_name": site.site_name,
                "technology_type": site.technology_type,
                "capacity_mw": site.capacity_mw,
                "latitude": site.latitude,
                "longitude": site.longitude,
                "commissioning_year": site.commissioning_year,
                "is_btm": site.is_btm,
                "development_status_short": site.development_status_short or "planning",
                "capacity_factor": site.capacity_factor,
            }
        )

    # Calculate infrastructure proximity scores
    proximity_scores = await calculate_proximity_scores_batch(sites_for_calc)

    # Score each site
    scored_sites: List[Dict[str, Any]] = []
    for index, site_data in enumerate(sites_for_calc):
        prox_scores = (
            proximity_scores[index]
            if index < len(proximity_scores)
            else {
                "substation_score": 0.0,
                "transmission_score": 0.0,
                "fiber_score": 0.0,
                "ixp_score": 0.0,
                "water_score": 0.0,
                "total_proximity_bonus": 0.0,
                "nearest_distances": {},
            }
        )

        # Apply persona-based or standard scoring
        if persona:
            rating_result = calculate_persona_weighted_score(
                site_data, prox_scores, persona, "demand", None, None
            )
        else:
            rating_result = calculate_enhanced_investment_rating(site_data, prox_scores)

        scored_sites.append(
            {
                "site_name": site_data["site_name"],
                "technology_type": site_data["technology_type"],
                "capacity_mw": site_data["capacity_mw"],
                "commissioning_year": site_data["commissioning_year"],
                "is_btm": site_data["is_btm"],
                "coordinates": [site_data["longitude"], site_data["latitude"]],
                "investment_rating": rating_result["investment_rating"],
                "rating_description": rating_result["rating_description"],
                "color_code": rating_result["color_code"],
                "component_scores": rating_result.get("component_scores"),
                "weighted_contributions": rating_result.get("weighted_contributions"),
                "persona": rating_result.get("persona"),
                "base_score": rating_result.get("base_investment_score", rating_result["investment_rating"]),
                "infrastructure_bonus": rating_result.get("infrastructure_bonus", 0.0),
                "nearest_infrastructure": rating_result["nearest_infrastructure"],
                "methodology": f"{scoring_mode} scoring system",
            }
        )

    processing_time = time.time() - start_time
    print(f"✅ User sites scored with {scoring_mode.upper()} SYSTEM in {processing_time:.2f}s")

    return {
        "sites": scored_sites,
        "metadata": {
            "scoring_system": f"{scoring_mode} - 1.0-10.0 Investment Rating Scale",
            "persona": persona,
            "processing_time_seconds": round(processing_time, 2),
            "algorithm_version": "2.1 - Persona-Based Infrastructure Proximity Enhanced",
            "rating_scale": {
                "9.0-10.0": "Excellent - Premium investment opportunity",
                "8.0-8.9": "Very Good - Strong investment potential",
                "7.0-7.9": "Good - Solid investment opportunity",
                "6.0-6.9": "Above Average - Moderate investment potential",
                "5.0-5.9": "Average - Standard investment opportunity",
                "4.0-4.9": "Below Average - Limited investment appeal",
                "3.0-3.9": "Poor - Significant investment challenges",
                "2.0-2.9": "Very Poor - High risk investment",
                "1.0-1.9": "Bad - Unfavorable investment conditions",
            },
        },
    }
