"""
Generate a large-scale test dataset of synthetic data center locations
Useful for testing ML system scalability with 1000+ locations
"""

import csv
import random
from typing import List, Tuple

# Major UK cities/regions with typical data center concentrations
UK_DATACENTER_HUBS = {
    "London": {"lat": 51.5074, "lon": -0.1278, "weight": 0.35, "radius": 0.5},
    "Manchester": {"lat": 53.4808, "lon": -2.2426, "weight": 0.12, "radius": 0.3},
    "Birmingham": {"lat": 52.4862, "lon": -1.8904, "weight": 0.08, "radius": 0.25},
    "Leeds": {"lat": 53.8008, "lon": -1.5491, "weight": 0.06, "radius": 0.2},
    "Edinburgh": {"lat": 55.9533, "lon": -3.1883, "weight": 0.08, "radius": 0.25},
    "Glasgow": {"lat": 55.8642, "lon": -4.2518, "weight": 0.06, "radius": 0.2},
    "Bristol": {"lat": 51.4545, "lon": -2.5879, "weight": 0.05, "radius": 0.2},
    "Cardiff": {"lat": 51.4816, "lon": -3.1791, "weight": 0.04, "radius": 0.15},
    "Newcastle": {"lat": 54.9783, "lon": -1.6178, "weight": 0.04, "radius": 0.15},
    "Aberdeen": {"lat": 57.1497, "lon": -2.0943, "weight": 0.03, "radius": 0.15},
    "Reading": {"lat": 51.4543, "lon": -0.9781, "weight": 0.03, "radius": 0.15},
    "Southampton": {"lat": 50.9097, "lon": -1.4044, "weight": 0.02, "radius": 0.1},
    "Nottingham": {"lat": 52.9548, "lon": -1.1581, "weight": 0.02, "radius": 0.1},
    "Liverpool": {"lat": 53.4084, "lon": -2.9916, "weight": 0.02, "radius": 0.1},
}


def generate_datacenter_location(hub_name: str, hub_data: dict) -> Tuple[float, float, str]:
    """Generate a single data center location near a hub"""
    # Add random offset within radius (in degrees)
    lat_offset = random.gauss(0, hub_data["radius"] / 2)
    lon_offset = random.gauss(0, hub_data["radius"] / 2)

    lat = hub_data["lat"] + lat_offset
    lon = hub_data["lon"] + lon_offset

    # Generate facility type
    facility_types = [
        "Colocation Facility",
        "Hyperscale Data Center",
        "Edge Computing Node",
        "Enterprise Data Center",
        "Cloud Provider Facility",
        "Telecom Data Center",
        "Managed Hosting Facility",
    ]

    facility_type = random.choice(facility_types)
    ref_suffix = random.randint(1, 999)

    name = f"{hub_name} {facility_type} #{ref_suffix}"

    return lat, lon, name


def generate_large_dataset(num_locations: int = 1500, output_file: str = "large_datacenter_dataset.csv"):
    """Generate large dataset of synthetic data center locations"""
    print(f"🏗️  Generating {num_locations} synthetic data center locations...")

    locations = []

    # Calculate how many locations per hub based on weights
    for hub_name, hub_data in UK_DATACENTER_HUBS.items():
        count = int(num_locations * hub_data["weight"])
        print(f"   {hub_name}: {count} locations")

        for i in range(count):
            lat, lon, name = generate_datacenter_location(hub_name, hub_data)
            locations.append({
                "Postcode": f"{hub_name[:2].upper()}{random.randint(10, 99)}{random.randint(1, 9)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}",
                "Data Centre Name": name,
                "Data Centre Address": "",
                "Longitude": round(lon, 6),
                "Latitude": round(lat, 6),
                "ref_id": len(locations) + 1,
            })

    # Write to CSV
    print(f"\n💾 Writing to {output_file}...")

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["Postcode", "Data Centre Name", "Data Centre Address", "Longitude", "Latitude", "ref_id"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(locations)

    print(f"✅ Generated {len(locations)} locations")
    print(f"   File: {output_file}")
    print(f"   Size: {len(locations)} rows")

    # Print statistics
    print(f"\n📊 Dataset Statistics:")
    print(f"   Total locations: {len(locations)}")
    print(f"   Geographic coverage: {len(UK_DATACENTER_HUBS)} major UK hubs")

    lat_values = [loc["Latitude"] for loc in locations]
    lon_values = [loc["Longitude"] for loc in locations]

    print(f"   Latitude range: {min(lat_values):.2f} to {max(lat_values):.2f}")
    print(f"   Longitude range: {min(lon_values):.2f} to {max(lon_values):.2f}")

    return output_file


if __name__ == "__main__":
    import sys

    num_locations = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    output_file = sys.argv[2] if len(sys.argv) > 2 else "large_datacenter_dataset.csv"

    print("=" * 80)
    print("📍 LARGE-SCALE DATA CENTER DATASET GENERATOR")
    print("=" * 80)
    print(f"\nTarget: {num_locations} locations")
    print(f"Output: {output_file}\n")

    generate_large_dataset(num_locations, output_file)

    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print("=" * 80)
    print(f"\nTo test with this dataset:")
    print(f"   python test_ml_endpoint.py {output_file}")
