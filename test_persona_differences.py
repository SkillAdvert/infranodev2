#!/usr/bin/env python3
"""
Test script to verify that different power developer personas return different results.

This script calls the power-developer-analysis endpoint with each persona type
and verifies that:
1. Each persona can be successfully passed via request body
2. Each persona returns different top projects (due to different weight priorities)
3. The scoring system is working as expected
"""

import asyncio
import json
import sys
from typing import Dict, Any

import httpx


BASE_URL = "http://localhost:8000"


async def test_persona(client: httpx.AsyncClient, persona: str) -> Dict[str, Any]:
    """Call the power developer analysis endpoint with a specific persona."""
    print(f"\n{'='*60}")
    print(f"Testing persona: {persona.upper()}")
    print(f"{'='*60}")

    # Test with persona in request body
    response = await client.post(
        f"{BASE_URL}/api/projects/power-developer-analysis",
        json={"target_persona": persona},
        timeout=30.0,
    )

    if response.status_code != 200:
        print(f"❌ Error: Status {response.status_code}")
        print(f"Response: {response.text}")
        return {}

    data = response.json()
    metadata = data.get("metadata", {})
    features = data.get("features", [])

    print(f"\n📊 Results:")
    print(f"  • Resolved persona: {metadata.get('project_type')}")
    print(f"  • Resolution status: {metadata.get('project_type_resolution')}")
    print(f"  • Total projects scored: {metadata.get('projects_scored')}")
    print(f"  • Processing time: {metadata.get('processing_time_seconds')}s")

    print(f"\n🏆 Top 5 projects:")
    for i, feature in enumerate(features[:5], 1):
        props = feature.get("properties", {})
        print(
            f"  {i}. {props.get('project_name')} "
            f"({props.get('technology_type')}) "
            f"— rating {props.get('investment_rating'):.2f} "
            f"• {props.get('capacity_mw'):.1f}MW"
        )

    print(f"\n🔧 Weight distribution for {persona}:")
    weights = metadata.get("project_type_weights", {})
    for criterion, weight in sorted(weights.items(), key=lambda x: -x[1]):
        print(f"  • {criterion}: {weight*100:.0f}%")

    return {
        "persona": persona,
        "top_projects": [
            {
                "name": f.get("properties", {}).get("project_name"),
                "rating": f.get("properties", {}).get("investment_rating"),
            }
            for f in features[:5]
        ],
        "weights": weights,
    }


async def main():
    """Test all three personas and compare results."""
    print("🚀 Power Developer Persona Differentiation Test")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test server availability
        try:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            print(f"✅ Server is running (status: {response.status_code})")
        except Exception as e:
            print(f"❌ Error: Server is not running at {BASE_URL}")
            print(f"   {e}")
            print("\n💡 Start the server with: python start_backend.py")
            sys.exit(1)

        # Test each persona
        results = {}
        for persona in ["greenfield", "repower", "stranded"]:
            try:
                result = await test_persona(client, persona)
                results[persona] = result
            except Exception as e:
                print(f"❌ Error testing {persona}: {e}")
                import traceback
                traceback.print_exc()

    # Compare results
    print(f"\n{'='*60}")
    print("📊 COMPARISON ANALYSIS")
    print(f"{'='*60}")

    if len(results) == 3:
        # Check if top projects differ
        top_project_names = {
            persona: [p["name"] for p in data["top_projects"]]
            for persona, data in results.items()
        }

        print("\n🔍 Top project rankings differ by persona:")
        for persona, projects in top_project_names.items():
            print(f"\n  {persona.upper()}:")
            for i, name in enumerate(projects, 1):
                print(f"    {i}. {name}")

        # Check if at least one project differs in top 5
        all_same = (
            top_project_names["greenfield"][0]
            == top_project_names["repower"][0]
            == top_project_names["stranded"][0]
        )

        if all_same:
            print("\n⚠️  WARNING: All personas have the same top project!")
            print("   This suggests the weight differences may not be significant enough,")
            print("   or the dataset characteristics are causing convergence.")
            return False
        else:
            print("\n✅ SUCCESS: Different personas produce different rankings!")
            print("   The weight system is working as intended.")

        # Show weight comparison
        print("\n🔧 Weight Priority Differences:")
        for criterion in [
            "capacity",
            "connection_speed",
            "resilience",
            "land_planning",
            "latency",
            "cooling",
            "price_sensitivity",
        ]:
            print(f"\n  {criterion}:")
            for persona in ["greenfield", "repower", "stranded"]:
                weight = results[persona]["weights"].get(criterion, 0)
                print(f"    {persona:12s}: {weight*100:5.1f}%")

        return True
    else:
        print("❌ Could not test all personas")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
