import json
import os
import requests
from dotenv import load_dotenv
from typing import Dict, List

# Load environment variables
load_dotenv()

# TNUoS tariff data for 2024-25 (example rates - replace with actual data)
TNUOS_TARIFFS = {
    "GZ1": {"rate": 15.32, "name": "North Scotland"},
    "GZ2": {"rate": 14.87, "name": "South Scotland"},
    "GZ3": {"rate": 13.45, "name": "Borders"},
    "GZ4": {"rate": 12.98, "name": "Central Scotland"},
    "GZ5": {"rate": 11.67, "name": "Argyll"},
    "GZ6": {"rate": 10.34, "name": "Dumfries"},
    "GZ7": {"rate": 9.87, "name": "Ayr"},
    "GZ8": {"rate": 8.92, "name": "Central Belt"},
    "GZ9": {"rate": 7.56, "name": "Lothian"},
    "GZ10": {"rate": 6.23, "name": "Southern Scotland"},
    "GZ11": {"rate": 5.67, "name": "North East England"},
    "GZ12": {"rate": 4.89, "name": "Yorkshire"},
    "GZ13": {"rate": 4.12, "name": "Humber"},
    "GZ14": {"rate": 3.78, "name": "North West England"},
    "GZ15": {"rate": 2.95, "name": "East Midlands"},
    "GZ16": {"rate": 2.34, "name": "West Midlands"},
    "GZ17": {"rate": 1.87, "name": "East England"},
    "GZ18": {"rate": 1.45, "name": "South Wales"},
    "GZ19": {"rate": 0.98, "name": "North Wales"},
    "GZ20": {"rate": 0.67, "name": "Pembroke"},
    "GZ21": {"rate": -0.12, "name": "South West England"},
    "GZ22": {"rate": -0.45, "name": "Cornwall"},
    "GZ23": {"rate": -0.78, "name": "London"},
    "GZ24": {"rate": -1.23, "name": "South East England"},
    "GZ25": {"rate": -1.56, "name": "Kent"},
    "GZ26": {"rate": -1.89, "name": "Southern England"},
    "GZ27": {"rate": -2.34, "name": "Solent"}
}

def load_tnuos_geojson(file_path: str) -> Dict:
    """Load the TNUoS GeoJSON file"""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find {file_path}")
        print("Make sure the TNUoS GeoJSON file is in your project directory")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {file_path}")
        return None

def process_tnuos_features(geojson_data: Dict) -> List[Dict]:
    """Process GeoJSON features and add tariff data"""
    processed_features = []
    
    if not geojson_data or 'features' not in geojson_data:
        print("Error: Invalid GeoJSON structure")
        return []
    
    print(f"Processing {len(geojson_data['features'])} TNUoS zones...")
    
    for feature in geojson_data['features']:
        if 'properties' not in feature or 'layer' not in feature['properties']:
            print("Warning: Skipping feature without layer property")
            continue
            
        # Extract zone ID from layer name (e.g., "GZ1" from layer "GZ1")
        zone_id = feature['properties']['layer']
        
        if zone_id not in TNUOS_TARIFFS:
            print(f"Warning: No tariff data for zone {zone_id}")
            continue
            
        # Get tariff information
        tariff_info = TNUOS_TARIFFS[zone_id]
        
        # Prepare the database record
        record = {
            'zone_id': zone_id,
            'zone_name': tariff_info['name'],
            'geometry': json.dumps(feature['geometry']),
            'generation_tariff_pounds_per_kw': tariff_info['rate'],
            'tariff_year': '2024-25',
            'effective_from': '2024-04-01'
        }
        
        processed_features.append(record)
        print(f"  Processed {zone_id}: {tariff_info['name']} (£{tariff_info['rate']}/kW)")
    
    return processed_features

def upload_to_supabase(features: List[Dict]):
    """Upload processed features to Supabase"""
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: Missing Supabase credentials in .env file")
        print("Make sure you have SUPABASE_URL and SUPABASE_ANON_KEY set")
        return
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # Clear existing TNUoS data
    print("Clearing existing TNUoS data...")
    delete_url = f"{SUPABASE_URL}/rest/v1/tnuos_zones"
    delete_response = requests.delete(delete_url, headers=headers)
    print(f"Clear status: {delete_response.status_code}")
    
    if not features:
        print("No features to upload")
        return
    
    # Upload new data in batches
    batch_size = 10
    total_uploaded = 0
    
    for i in range(0, len(features), batch_size):
        batch = features[i:i + batch_size]
        
        insert_url = f"{SUPABASE_URL}/rest/v1/tnuos_zones"
        response = requests.post(insert_url, json=batch, headers=headers)
        
        if response.status_code == 201:
            total_uploaded += len(batch)
            print(f"Uploaded batch {i//batch_size + 1}: {len(batch)} zones (Total: {total_uploaded})")
        else:
            print(f"Error uploading batch: {response.status_code}")
            print(f"Response: {response.text}")
            break
    
    print(f"\nTNUoS upload complete: {total_uploaded} zones uploaded")
    
    # Show summary
    if total_uploaded > 0:
        print("\nZones uploaded:")
        for feature in features:
            rate = feature['generation_tariff_pounds_per_kw']
            print(f"  {feature['zone_id']}: {feature['zone_name']} (£{rate}/kW)")

def main():
    print("TNUoS Data Upload Tool")
    print("=" * 40)
    
    # Load GeoJSON file
    geojson_file = "tnuosgenzones_geojs.geojson"  # Your uploaded file
    geojson_data = load_tnuos_geojson(geojson_file)
    
    if not geojson_data:
        return
    
    # Process features
    processed_features = process_tnuos_features(geojson_data)
    
    if not processed_features:
        print("No valid features to upload")
        return
    
    # Upload to Supabase
    upload_to_supabase(processed_features)
    
print("File Upload Complete")

if __name__ == "__main__":
    main()