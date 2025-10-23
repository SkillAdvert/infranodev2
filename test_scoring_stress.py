"""
Stress Test for Project Scoring Algorithm

Tests the scoring algorithm across different:
- User personas (hyperscaler, colocation, edge_computing, custom)
- Project types (various capacities, development stages, technologies, locations)
- Infrastructure proximity scenarios

This helps identify edge cases, biases, and improvement opportunities.
"""

import asyncio
import json
from typing import Dict, Any, List
from main import (
    calculate_persona_weighted_score,
    calculate_custom_weighted_score,
    build_persona_component_scores,
    PERSONA_WEIGHTS,
    PersonaType,
)


# Test project scenarios
TEST_PROJECTS = [
    # Hyperscaler-ideal: Large capacity, good stage, excellent infrastructure
    {
        "name": "Hyperscaler Dream Site",
        "project": {
            "capacity_mw": 150,
            "development_status_short": "application submitted",
            "technology_type": "Solar",
            "latitude": 51.5,  # London area (higher TNUoS)
            "longitude": -0.1,
        },
        "proximity_scores": {
            "nearest_distances": {
                "substation_km": 2.0,
                "transmission_km": 5.0,
                "fiber_km": 1.0,
                "ixp_km": 10.0,
                "water_km": 3.0,
            }
        },
    },
    # Colocation-ideal: Medium capacity, fiber-rich, moderate infrastructure
    {
        "name": "Colocation Sweet Spot",
        "project": {
            "capacity_mw": 25,
            "development_status_short": "revised",
            "technology_type": "Hybrid",
            "latitude": 53.5,  # Manchester area
            "longitude": -2.2,
        },
        "proximity_scores": {
            "nearest_distances": {
                "substation_km": 5.0,
                "transmission_km": 15.0,
                "fiber_km": 0.5,
                "ixp_km": 2.0,
                "water_km": 8.0,
            }
        },
    },
    # Edge-ideal: Small capacity, ultra-fast deployment, latency-optimized
    {
        "name": "Edge Computing Ideal",
        "project": {
            "capacity_mw": 3,
            "development_status_short": "no application required",
            "technology_type": "Battery",
            "latitude": 52.2,  # Midlands
            "longitude": -1.5,
        },
        "proximity_scores": {
            "nearest_distances": {
                "substation_km": 8.0,
                "transmission_km": 20.0,
                "fiber_km": 0.2,
                "ixp_km": 1.5,
                "water_km": 15.0,
            }
        },
    },
    # Worst case: Small capacity, poor stage, remote location
    {
        "name": "Worst Case Scenario",
        "project": {
            "capacity_mw": 2,
            "development_status_short": "application refused",
            "technology_type": "Solar",
            "latitude": 57.5,  # North Scotland
            "longitude": -3.5,
        },
        "proximity_scores": {
            "nearest_distances": {
                "substation_km": 50.0,
                "transmission_km": 80.0,
                "fiber_km": 40.0,
                "ixp_km": 200.0,
                "water_km": 30.0,
            }
        },
    },
    # Medium everything: Average across the board
    {
        "name": "Average Project",
        "project": {
            "capacity_mw": 50,
            "development_status_short": "awaiting construction",
            "technology_type": "Wind",
            "latitude": 52.5,  # Central England
            "longitude": -1.8,
        },
        "proximity_scores": {
            "nearest_distances": {
                "substation_km": 10.0,
                "transmission_km": 25.0,
                "fiber_km": 5.0,
                "ixp_km": 15.0,
                "water_km": 12.0,
            }
        },
    },
    # Scotland site: Great TNUoS, remote infrastructure
    {
        "name": "Scotland Remote (Low TNUoS)",
        "project": {
            "capacity_mw": 100,
            "development_status_short": "application submitted",
            "technology_type": "Wind",
            "latitude": 58.0,  # North Scotland
            "longitude": -4.0,
        },
        "proximity_scores": {
            "nearest_distances": {
                "substation_km": 30.0,
                "transmission_km": 50.0,
                "fiber_km": 25.0,
                "ixp_km": 150.0,
                "water_km": 10.0,
            }
        },
    },
    # Under construction: Poor for BTM but shows different scoring
    {
        "name": "Under Construction Site",
        "project": {
            "capacity_mw": 75,
            "development_status_short": "under construction",
            "technology_type": "Solar",
            "latitude": 51.0,  # South England
            "longitude": -1.0,
        },
        "proximity_scores": {
            "nearest_distances": {
                "substation_km": 5.0,
                "transmission_km": 12.0,
                "fiber_km": 2.0,
                "ixp_km": 8.0,
                "water_km": 6.0,
            }
        },
    },
    # Operational: Worst for BTM intervention
    {
        "name": "Operational Site",
        "project": {
            "capacity_mw": 200,
            "development_status_short": "operational",
            "technology_type": "Hybrid",
            "latitude": 53.0,  # Yorkshire
            "longitude": -1.2,
        },
        "proximity_scores": {
            "nearest_distances": {
                "substation_km": 1.0,
                "transmission_km": 3.0,
                "fiber_km": 0.5,
                "ixp_km": 5.0,
                "water_km": 2.0,
            }
        },
    },
]


def print_separator(char="=", length=100):
    """Print a separator line."""
    print(char * length)


def print_section_header(title: str):
    """Print a formatted section header."""
    print_separator()
    print(f"{title:^100}")
    print_separator()
    print()


def print_component_breakdown(components: Dict[str, float], weights: Dict[str, float]):
    """Print component scores and their weighted contributions."""
    print(f"{'Component':<25} {'Raw Score':>12} {'Weight':>10} {'Contribution':>15}")
    print("-" * 70)

    total_weighted = 0.0
    for key in components.keys():
        raw = components[key]
        weight = weights.get(key, 0.0)
        contribution = raw * weight
        total_weighted += contribution
        print(f"{key:<25} {raw:>12.1f} {weight:>10.3f} {contribution:>15.2f}")

    print("-" * 70)
    print(f"{'TOTAL WEIGHTED SCORE':<25} {'':<12} {'':<10} {total_weighted:>15.2f}")
    print()


def analyze_persona_scoring(project_name: str, project: Dict[str, Any],
                            proximity_scores: Dict[str, float],
                            persona: PersonaType):
    """Analyze scoring for a specific persona."""
    print(f"\n--- {persona.upper()} PERSONA ---\n")

    result = calculate_persona_weighted_score(
        project=project,
        proximity_scores=proximity_scores,
        persona=persona,
        perspective="demand",
        user_max_price_mwh=None,
    )

    print(f"Final Investment Rating: {result['investment_rating']}/10")
    print(f"Rating Description: {result['rating_description']}")
    print(f"Color Code: {result['color_code']}")
    print(f"Internal Score: {result['internal_total_score']}/100\n")

    print_component_breakdown(
        result['component_scores'],
        result['persona_weights']
    )

    return result


def analyze_custom_scoring(project_name: str, project: Dict[str, Any],
                           proximity_scores: Dict[str, float]):
    """Analyze custom weighted scoring."""
    print(f"\n--- CUSTOM WEIGHTS (Equal Distribution) ---\n")

    # Create equal weights for all 8 components in custom scoring
    custom_weights = {
        "capacity": 0.125,
        "development_stage": 0.125,
        "technology": 0.125,
        "grid_infrastructure": 0.125,
        "digital_infrastructure": 0.125,
        "water_resources": 0.125,
        "lcoe_resource_quality": 0.125,
        "tnuos_transmission_costs": 0.125,
    }

    result = calculate_custom_weighted_score(
        project=project,
        proximity_scores=proximity_scores,
        custom_weights=custom_weights,
    )

    print(f"Final Investment Rating: {result['investment_rating']}/10")
    print(f"Rating Description: {result['rating_description']}")
    print(f"Color Code: {result['color_code']}")
    print(f"Internal Score: {result['internal_total_score']}/100\n")

    print_component_breakdown(
        result['component_scores'],
        custom_weights
    )

    return result


def stress_test_all_scenarios():
    """Run stress test across all project scenarios and personas."""

    print_section_header("PROJECT SCORING ALGORITHM STRESS TEST")

    results_summary = []

    for test_case in TEST_PROJECTS:
        project_name = test_case["name"]
        project = test_case["project"]
        proximity_scores = test_case["proximity_scores"]

        print_section_header(f"TEST CASE: {project_name}")

        # Print project details
        print("PROJECT DETAILS:")
        print(f"  Capacity: {project['capacity_mw']} MW")
        print(f"  Development Stage: {project['development_status_short']}")
        print(f"  Technology: {project['technology_type']}")
        print(f"  Location: ({project['latitude']}, {project['longitude']})")
        print(f"\nINFRASTRUCTURE PROXIMITY:")
        for key, value in proximity_scores["nearest_distances"].items():
            print(f"  {key}: {value} km")
        print("\n")

        # Test each persona
        persona_results = {}

        # Hyperscaler
        persona_results['hyperscaler'] = analyze_persona_scoring(
            project_name, project, proximity_scores, "hyperscaler"
        )

        # Colocation
        persona_results['colocation'] = analyze_persona_scoring(
            project_name, project, proximity_scores, "colocation"
        )

        # Edge Computing
        persona_results['edge_computing'] = analyze_persona_scoring(
            project_name, project, proximity_scores, "edge_computing"
        )

        # Custom (Equal Weights)
        persona_results['custom'] = analyze_custom_scoring(
            project_name, project, proximity_scores
        )

        # Summary
        summary = {
            "project_name": project_name,
            "capacity_mw": project['capacity_mw'],
            "stage": project['development_status_short'],
            "scores": {
                "hyperscaler": persona_results['hyperscaler']['investment_rating'],
                "colocation": persona_results['colocation']['investment_rating'],
                "edge_computing": persona_results['edge_computing']['investment_rating'],
                "custom": persona_results['custom']['investment_rating'],
            }
        }
        results_summary.append(summary)

        print("\n")

    # Print comparison summary
    print_section_header("SUMMARY: CROSS-PERSONA COMPARISON")

    print(f"{'Project Name':<30} {'Hyperscaler':>13} {'Colocation':>13} {'Edge':>13} {'Custom':>13}")
    print("-" * 85)

    for summary in results_summary:
        print(f"{summary['project_name']:<30} "
              f"{summary['scores']['hyperscaler']:>13.1f} "
              f"{summary['scores']['colocation']:>13.1f} "
              f"{summary['scores']['edge_computing']:>13.1f} "
              f"{summary['scores']['custom']:>13.1f}")

    print("\n")

    # Analyze persona biases
    print_section_header("PERSONA BIAS ANALYSIS")

    for persona in ['hyperscaler', 'colocation', 'edge_computing']:
        scores = [s['scores'][persona] for s in results_summary]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        score_range = max_score - min_score

        print(f"\n{persona.upper()}:")
        print(f"  Average Score: {avg_score:.2f}/10")
        print(f"  Score Range: {min_score:.1f} - {max_score:.1f} (range: {score_range:.1f})")
        print(f"  Weights Profile:")
        for component, weight in PERSONA_WEIGHTS[persona].items():
            print(f"    {component}: {weight:.3f} ({weight*100:.1f}%)")

    print("\n")


def test_edge_cases():
    """Test extreme edge cases."""
    print_section_header("EDGE CASE TESTING")

    edge_cases = [
        {
            "name": "Zero Capacity",
            "project": {
                "capacity_mw": 0,
                "development_status_short": "application submitted",
                "technology_type": "Solar",
                "latitude": 51.5,
                "longitude": -0.1,
            },
            "proximity_scores": {
                "nearest_distances": {
                    "substation_km": 5.0,
                    "transmission_km": 10.0,
                    "fiber_km": 2.0,
                    "ixp_km": 5.0,
                    "water_km": 3.0,
                }
            },
        },
        {
            "name": "Massive Capacity (1000 MW)",
            "project": {
                "capacity_mw": 1000,
                "development_status_short": "application submitted",
                "technology_type": "Wind",
                "latitude": 51.5,
                "longitude": -0.1,
            },
            "proximity_scores": {
                "nearest_distances": {
                    "substation_km": 5.0,
                    "transmission_km": 10.0,
                    "fiber_km": 2.0,
                    "ixp_km": 5.0,
                    "water_km": 3.0,
                }
            },
        },
        {
            "name": "Perfect Infrastructure (All 0km)",
            "project": {
                "capacity_mw": 100,
                "development_status_short": "application submitted",
                "technology_type": "Hybrid",
                "latitude": 51.5,
                "longitude": -0.1,
            },
            "proximity_scores": {
                "nearest_distances": {
                    "substation_km": 0.1,
                    "transmission_km": 0.1,
                    "fiber_km": 0.1,
                    "ixp_km": 0.1,
                    "water_km": 0.1,
                }
            },
        },
        {
            "name": "Remote Island (500km to everything)",
            "project": {
                "capacity_mw": 100,
                "development_status_short": "application submitted",
                "technology_type": "Wind",
                "latitude": 60.0,
                "longitude": -1.0,
            },
            "proximity_scores": {
                "nearest_distances": {
                    "substation_km": 500.0,
                    "transmission_km": 500.0,
                    "fiber_km": 500.0,
                    "ixp_km": 500.0,
                    "water_km": 500.0,
                }
            },
        },
    ]

    for edge_case in edge_cases:
        print(f"\nEDGE CASE: {edge_case['name']}")
        print("-" * 70)

        for persona in ['hyperscaler', 'colocation', 'edge_computing']:
            result = calculate_persona_weighted_score(
                project=edge_case['project'],
                proximity_scores=edge_case['proximity_scores'],
                persona=persona,
                perspective="demand",
            )
            print(f"  {persona:<20} Score: {result['investment_rating']:>5.1f}/10 "
                  f"({result['rating_description']})")

    print("\n")


def analyze_score_sensitivity():
    """Analyze how sensitive scores are to different variables."""
    print_section_header("SENSITIVITY ANALYSIS")

    # Base project
    base_project = {
        "capacity_mw": 100,
        "development_status_short": "application submitted",
        "technology_type": "Solar",
        "latitude": 51.5,
        "longitude": -0.1,
    }

    base_proximity = {
        "nearest_distances": {
            "substation_km": 10.0,
            "transmission_km": 20.0,
            "fiber_km": 5.0,
            "ixp_km": 10.0,
            "water_km": 8.0,
        }
    }

    print("\n1. CAPACITY SENSITIVITY (Hyperscaler Persona)")
    print("-" * 70)
    capacities = [1, 5, 10, 25, 50, 100, 200, 400, 800]
    print(f"{'Capacity (MW)':<15} {'Score':>10} {'Rating':>30}")
    print("-" * 60)

    for capacity in capacities:
        test_proj = base_project.copy()
        test_proj['capacity_mw'] = capacity
        result = calculate_persona_weighted_score(
            project=test_proj,
            proximity_scores=base_proximity,
            persona="hyperscaler",
        )
        print(f"{capacity:<15} {result['investment_rating']:>10.1f} {result['rating_description']:>30}")

    print("\n2. DEVELOPMENT STAGE SENSITIVITY (All Personas)")
    print("-" * 70)

    stages = [
        "operational",
        "under construction",
        "awaiting construction",
        "application submitted",
        "revised",
        "no application required",
        "application refused",
    ]

    print(f"{'Stage':<30} {'Hyperscaler':>12} {'Colocation':>12} {'Edge':>12}")
    print("-" * 70)

    for stage in stages:
        test_proj = base_project.copy()
        test_proj['development_status_short'] = stage

        scores = []
        for persona in ['hyperscaler', 'colocation', 'edge_computing']:
            result = calculate_persona_weighted_score(
                project=test_proj,
                proximity_scores=base_proximity,
                persona=persona,
            )
            scores.append(result['investment_rating'])

        print(f"{stage:<30} {scores[0]:>12.1f} {scores[1]:>12.1f} {scores[2]:>12.1f}")

    print("\n3. INFRASTRUCTURE PROXIMITY SENSITIVITY (Colocation)")
    print("-" * 70)

    distances = [0.5, 2, 5, 10, 20, 50, 100, 200]
    print(f"{'Distance (km)':<15} {'Score':>10} {'Rating':>30}")
    print("-" * 60)

    for dist in distances:
        test_proximity = {
            "nearest_distances": {
                "substation_km": dist,
                "transmission_km": dist * 2,
                "fiber_km": dist,
                "ixp_km": dist,
                "water_km": dist,
            }
        }
        result = calculate_persona_weighted_score(
            project=base_project,
            proximity_scores=test_proximity,
            persona="colocation",
        )
        print(f"{dist:<15} {result['investment_rating']:>10.1f} {result['rating_description']:>30}")

    print("\n")


if __name__ == "__main__":
    print("\n")
    print("=" * 100)
    print("SCORING ALGORITHM COMPREHENSIVE STRESS TEST")
    print("=" * 100)
    print("\n")

    # Run all tests
    stress_test_all_scenarios()
    test_edge_cases()
    analyze_score_sensitivity()

    print_section_header("TEST COMPLETE")
    print("Review the output above to identify:")
    print("  1. Persona-specific biases and appropriateness")
    print("  2. Score distribution and variance")
    print("  3. Edge case handling")
    print("  4. Component weight balance")
    print("  5. Opportunities for algorithm improvement")
    print("\n")
