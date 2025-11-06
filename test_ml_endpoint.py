"""
Test script for ML-based data center location recommendations
Run this after starting the FastAPI server

Usage:
    python test_ml_endpoint.py                          # Use default CSV
    python test_ml_endpoint.py custom_datacenters.csv   # Use custom CSV
"""

import requests
import json
import csv
import sys
from pathlib import Path


def load_datacenters_from_csv(csv_path: str) -> list:
    """Load data center locations from CSV file"""
    datacenters = []

    print(f"📂 Loading data centers from: {csv_path}")

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                lat = float(row.get('Latitude', row.get('latitude', 0)))
                lon = float(row.get('Longitude', row.get('longitude', 0)))
                name = row.get('Data Centre Name', row.get('name', row.get('Postcode', 'Unknown')))

                if lat != 0 and lon != 0:  # Filter out invalid coordinates
                    datacenters.append({
                        "latitude": lat,
                        "longitude": lon,
                        "name": name.strip() if name else "Unknown"
                    })
            except (ValueError, KeyError) as e:
                print(f"⚠️  Skipping invalid row: {e}")
                continue

    # Remove duplicates based on coordinates (within 0.001 degrees ~100m)
    unique_datacenters = []
    seen_coords = set()

    for dc in datacenters:
        coord_key = (round(dc['latitude'], 3), round(dc['longitude'], 3))
        if coord_key not in seen_coords:
            unique_datacenters.append(dc)
            seen_coords.add(coord_key)

    print(f"✅ Loaded {len(datacenters)} locations ({len(unique_datacenters)} unique)")
    return unique_datacenters


# Determine CSV file to use
csv_file = sys.argv[1] if len(sys.argv) > 1 else "existing_datacenters.csv"

if not Path(csv_file).exists():
    print(f"❌ ERROR: CSV file not found: {csv_file}")
    print(f"\nUsage: python test_ml_endpoint.py [csv_file]")
    sys.exit(1)

# Load data centers from CSV
existing_datacenters = load_datacenters_from_csv(csv_file)

if not existing_datacenters:
    print("❌ ERROR: No valid data centers found in CSV")
    sys.exit(1)

# API endpoint
url = "http://127.0.0.1:8000/api/ml/datacenter-locations"

# Request payload - adjust candidates based on training set size
num_candidates = min(100, len(existing_datacenters) * 10)  # 10x training data
top_n = min(15, max(10, len(existing_datacenters) // 2))  # At least 10, or half training set

payload = {
    "existing_locations": existing_datacenters,
    "num_candidates": num_candidates,
    "top_n": top_n,
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
