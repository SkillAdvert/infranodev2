"""
Test script for ML-based data center location recommendations
Run this after starting the FastAPI server
"""

import requests
import json

# Your existing data center locations
existing_datacenters = [
    {"latitude": 57.1437, "longitude": -2.0981, "name": "IFB Union Street"},
    {"latitude": 57.1378, "longitude": -2.1663, "name": "Brightsolid Aberdeen"},
    {"latitude": 57.16, "longitude": -2.1567, "name": "Brightsolid data centre"},
    {"latitude": 57.2111, "longitude": -2.2037, "name": "CNSFTC DATA CENTRE"},
    {"latitude": 57.23273125, "longitude": -2.0789625, "name": "Unknown"},
    {"latitude": 51.7634, "longitude": -0.2242, "name": "Computacentre"},
]

# API endpoint
url = "http://127.0.0.1:8000/api/ml/datacenter-locations"

# Request payload
payload = {
    "existing_locations": existing_datacenters,
    "num_candidates": 100,  # Test with 100 random locations
    "top_n": 15,  # Get top 15 recommendations
}

print("=" * 80)
print("🤖 TESTING ML DATA CENTER LOCATION RECOMMENDATION API")
print("=" * 80)
print(f"\n📤 Sending request with {len(existing_datacenters)} existing data center locations...")
print(f"   Will evaluate {payload['num_candidates']} candidate locations")
print(f"   Requesting top {payload['top_n']} recommendations\n")

try:
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()

    result = response.json()

    print("✅ SUCCESS! Received ML recommendations\n")
    print("=" * 80)
    print("📊 MODEL INFORMATION")
    print("=" * 80)

    model_info = result["model_info"]
    print(f"Model Type: {model_info['model_type']}")
    print(f"Training Samples: {model_info['training_samples']}")
    print(f"Candidates Evaluated: {model_info['candidates_evaluated']}")
    print(f"Threshold Score: {model_info['threshold_score']}")
    print(f"Processing Time: {result['processing_time_seconds']}s")

    print("\n📈 Feature Weights:")
    for feature, weight in model_info["feature_weights"].items():
        print(f"   {feature}: {weight}")

    print("\n📊 Mean Infrastructure Scores (from existing data centers):")
    for feature, score in model_info["mean_infrastructure_scores"].items():
        print(f"   {feature}: {score}")

    print("\n" + "=" * 80)
    print(f"🎯 TOP {len(result['top_recommendations'])} RECOMMENDED LOCATIONS")
    print("=" * 80)

    for i, rec in enumerate(result["top_recommendations"], 1):
        print(f"\n{i}. Location ({rec['latitude']}, {rec['longitude']})")
        print(f"   Composite Score: {rec['composite_score']}")
        print(f"   Percentile Rank: {rec['percentile_rank']}%")
        print(f"   Recommendation: {rec['recommendation']}")

        print(f"   Infrastructure Scores:")
        for infra, score in rec["feature_scores"].items():
            print(f"      • {infra}: {score}")

        print(f"   Distances to Infrastructure (km):")
        for infra, dist in rec["distances_km"].items():
            if dist < 100:  # Only show nearby infrastructure
                print(f"      • {infra}: {dist:.1f} km")

    print("\n" + "=" * 80)
    print("💾 Saving results to: ml_recommendations.json")
    print("=" * 80)

    with open("ml_recommendations.json", "w") as f:
        json.dump(result, f, indent=2)

    print("\n✅ Complete! You can now visualize these locations on a map.")
    print("   Recommended locations have composite scores >= threshold")

except requests.exceptions.ConnectionError:
    print("❌ ERROR: Cannot connect to API server")
    print("   Please start the server first:")
    print("   python main.py")
except requests.exceptions.Timeout:
    print("❌ ERROR: Request timed out")
    print("   Try reducing num_candidates or increasing timeout")
except requests.exceptions.HTTPError as e:
    print(f"❌ HTTP ERROR: {e}")
    print(f"   Response: {e.response.text}")
except Exception as e:
    print(f"❌ UNEXPECTED ERROR: {e}")
