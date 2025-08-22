import pandas as pd
import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def import_csv():
    df = pd.read_csv("Project List.csv")
    projects = []
    
    for _, row in df.iterrows():
        try:
            x, y = float(row['X-coordinate']), float(row['Y-coordinate'])
            lon = (x - 400000) / 100000 - 2.0
            lat = (y - 100000) / 111000 + 49.0
            if not (-8 <= lon <= 2 and 49 <= lat <= 61): lon, lat = None, None
        except: lon, lat = None, None
        
        if pd.notna(row['Ref ID']) and pd.notna(row['Site Name']):
            projects.append({
                'ref_id': int(row['Ref ID']),
                'site_name': str(row['Site Name']).strip(),
                'operator': str(row['Operator (or Applicant)']).strip() if pd.notna(row['Operator (or Applicant)']) else None,
                'technology_type': str(row['Technology Type']).strip(),
                'capacity_mw': float(row['Installed Capacity (MWelec)']) if pd.notna(row['Installed Capacity (MWelec)']) else None,
                'development_status': str(row['Development Status']).strip() if pd.notna(row['Development Status']) else None,
                'development_status_short': str(row['Development Status (short)']).strip() if pd.notna(row['Development Status (short)']) else None,
                'county': str(row['County']).strip() if pd.notna(row['County']) else None,
                'country': str(row['Country']).strip() if pd.notna(row['Country']) else None,
                'longitude': lon,
                'latitude': lat
            })
    
    headers = {"apikey": os.getenv("SUPABASE_ANON_KEY"), "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}", "Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        for i in range(0, len(projects), 100):
            batch = projects[i:i+100]
            response = await client.post(f"{os.getenv('SUPABASE_URL')}/rest/v1/renewable_projects", headers=headers, json=batch, timeout=30)
            print(f"Batch {i//100 + 1}: {'✅' if response.status_code in [200, 201] else '❌'}")
    
    print(f"✅ Import complete: {len(projects)} projects")

asyncio.run(import_csv())