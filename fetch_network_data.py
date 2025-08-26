import requests
import json
import time
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

def fetch_uk_power_substations() -> List[Dict]:
   """Fetch high voltage substations (32kV+) from UK Power Networks"""
   
   base_url = "https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets"
   
   # Try common dataset names for substations
   possible_datasets = [
       "ukpn-substation-data",
       "substations",
       "electrical-substations",
       "power-substations"
   ]
   
   all_substations = []
   
   for dataset in possible_datasets:
       url = f"{base_url}/{dataset}/records"
       params = {
           "limit": 1000,
           "where": "voltage_kv >= 32"  # 32kV and above only
       }
       
       print(f"Trying dataset: {dataset}")
       
       try:
           response = requests.get(url, params=params, timeout=30)
           if response.status_code == 200:
               data = response.json()
               records = data.get('results', [])
               print(f"  Found {len(records)} high voltage substations")
               all_substations.extend(records)
               break  # Stop after first successful dataset
           else:
               print(f"  Dataset not found: {response.status_code}")
               
       except requests.exceptions.RequestException as e:
           print(f"  Error accessing {dataset}: {e}")
           continue
   
   return all_substations

def fetch_uk_transmission_lines() -> List[Dict]:
   """Fetch transmission lines from UK Power Networks"""
   
   base_url = "https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets"
   
   possible_datasets = [
       "ukpn-overhead-line-data",
       "transmission-lines",
       "overhead-lines",
       "power-lines"
   ]
   
   all_lines = []
   
   for dataset in possible_datasets:
       url = f"{base_url}/{dataset}/records"
       params = {
           "limit": 1000,
           "where": "voltage_kv >= 32"
       }
       
       print(f"Trying transmission dataset: {dataset}")
       
       try:
           response = requests.get(url, params=params, timeout=30)
           if response.status_code == 200:
               data = response.json()
               records = data.get('results', [])
               print(f"  Found {len(records)} transmission lines")
               all_lines.extend(records)
               break
           else:
               print(f"  Dataset not found: {response.status_code}")
               
       except requests.exceptions.RequestException as e:
           print(f"  Error accessing {dataset}: {e}")
           continue
   
   return all_lines

def process_substations(raw_data: List[Dict]) -> List[Dict]:
   """Convert UK Power Networks substation data to database format"""
   processed_substations = []
   
   for record in raw_data:
       fields = record.get('record', {}).get('fields', {})
       
       # Extract coordinates (may be in different field names)
       coords = None
       for coord_field in ['geopoint', 'coordinates', 'location', 'geo_point_2d']:
           if coord_field in fields:
               coords = fields[coord_field]
               break
       
       if not coords:
           continue
           
       # Handle different coordinate formats
       if isinstance(coords, dict):
           lat, lng = coords.get('lat'), coords.get('lon')
       elif isinstance(coords, list) and len(coords) == 2:
           lat, lng = coords[1], coords[0]  # Often [lng, lat] format
       else:
           continue
           
       substation_entry = {
           'substation_name': fields.get('name', fields.get('substation_name', f"Substation {record.get('recordid', 'Unknown')}")),
           'operator': fields.get('operator', 'UK Power Networks'),
           'latitude': lat,
           'longitude': lng,
           'primary_voltage_kv': fields.get('voltage_kv', fields.get('voltage', 33)),
           'capacity_mva': fields.get('capacity_mva', fields.get('capacity', None))
       }
       
       processed_substations.append(substation_entry)
   
   return processed_substations

def process_transmission_lines(raw_data: List[Dict]) -> List[Dict]:
   """Convert transmission line data to database format"""
   processed_lines = []
   
   for record in raw_data:
       fields = record.get('record', {}).get('fields', {})
       
       # Look for line geometry
       geometry = fields.get('geometry', fields.get('geo_shape', fields.get('coordinates')))
       
       if not geometry:
           continue
           
       line_entry = {
           'line_name': fields.get('name', fields.get('line_name', f"Line {record.get('recordid', 'Unknown')}")),
           'operator': fields.get('operator', 'UK Power Networks'),
           'voltage_kv': fields.get('voltage_kv', fields.get('voltage', 132)),
           'path_coordinates': json.dumps(geometry) if geometry else None
       }
       
       processed_lines.append(line_entry)
   
   return processed_lines

def upload_substations_to_supabase(substations_data: List[Dict]):
   """Upload substations to Supabase"""
   
   SUPABASE_URL = os.getenv("SUPABASE_URL")
   SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
   
   if not SUPABASE_URL or not SUPABASE_KEY:
       print("Missing Supabase credentials")
       return
   
   headers = {
       "apikey": SUPABASE_KEY,
       "Authorization": f"Bearer {SUPABASE_KEY}",
       "Content-Type": "application/json"
   }
   
   # Clear existing substations
   delete_url = f"{SUPABASE_URL}/rest/v1/substations"
   delete_response = requests.delete(delete_url, headers=headers)
   print(f"Cleared existing substations: {delete_response.status_code}")
   
   if not substations_data:
       print("No substation data to upload")
       return
   
   # Show voltage breakdown
   voltages = {}
   for sub in substations_data:
       voltage = sub.get('primary_voltage_kv', 'Unknown')
       voltages[voltage] = voltages.get(voltage, 0) + 1
   
   print("Voltage level breakdown:")
   for voltage, count in sorted(voltages.items()):
       print(f"  {voltage} kV: {count} substations")
   
   # Upload in batches
   batch_size = 50
   total_uploaded = 0
   
   for i in range(0, len(substations_data), batch_size):
       batch = substations_data[i:i + batch_size]
       
       insert_url = f"{SUPABASE_URL}/rest/v1/substations"
       response = requests.post(insert_url, json=batch, headers=headers)
       
       if response.status_code == 201:
           total_uploaded += len(batch)
           print(f"Uploaded substation batch {i//batch_size + 1}: {len(batch)} (Total: {total_uploaded})")
       else:
           print(f"Error uploading substations: {response.status_code} - {response.text}")
           break
       
       time.sleep(1)
   
   print(f"Substation upload complete: {total_uploaded} substations")

def upload_transmission_lines_to_supabase(lines_data: List[Dict]):
   """Upload transmission lines to Supabase"""
   
   SUPABASE_URL = os.getenv("SUPABASE_URL")
   SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
   
   headers = {
       "apikey": SUPABASE_KEY,
       "Authorization": f"Bearer {SUPABASE_KEY}",
       "Content-Type": "application/json"
   }
   
   # Clear existing transmission lines
   delete_url = f"{SUPABASE_URL}/rest/v1/transmission_lines"
   delete_response = requests.delete(delete_url, headers=headers)
   print(f"Cleared existing transmission lines: {delete_response.status_code}")
   
   if not lines_data:
       print("No transmission line data to upload")
       return
   
   batch_size = 50
   total_uploaded = 0
   
   for i in range(0, len(lines_data), batch_size):
       batch = lines_data[i:i + batch_size]
       
       insert_url = f"{SUPABASE_URL}/rest/v1/transmission_lines"
       response = requests.post(insert_url, json=batch, headers=headers)
       
       if response.status_code == 201:
           total_uploaded += len(batch)
           print(f"Uploaded transmission batch {i//batch_size + 1}: {len(batch)} (Total: {total_uploaded})")
       else:
           print(f"Error uploading transmission lines: {response.status_code} - {response.text}")
           break
       
       time.sleep(1)
   
   print(f"Transmission line upload complete: {total_uploaded} lines")

def main():
   print("Starting UK Power Networks high voltage infrastructure collection...")
   print("Target: 32kV+ substations and transmission lines")
   
   # Fetch substations
   print("\n=== FETCHING SUBSTATIONS ===")
   raw_substations = fetch_uk_power_substations()
   
   if raw_substations:
       processed_substations = process_substations(raw_substations)
       print(f"Processed {len(processed_substations)} substations")
       upload_substations_to_supabase(processed_substations)
   else:
       print("No substation data found")
   
   # Fetch transmission lines
   print("\n=== FETCHING TRANSMISSION LINES ===")
   raw_lines = fetch_uk_transmission_lines()
   
   if raw_lines:
       processed_lines = process_transmission_lines(raw_lines)
       print(f"Processed {len(processed_lines)} transmission lines")
       upload_transmission_lines_to_supabase(processed_lines)
   else:
       print("No transmission line data found")

if __name__ == "__main__":
   main()
