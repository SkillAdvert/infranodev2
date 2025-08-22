from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Infranodal API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# Debug startup
print(f"✅ SUPABASE_URL: {SUPABASE_URL}")
print(f"✅ SUPABASE_KEY exists: {bool(SUPABASE_KEY)}")

async def query_supabase(endpoint: str):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{SUPABASE_URL}/rest/v1/{endpoint}", headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(500, f"Database error: {response.status_code}")

def calculate_score(project: Dict) -> Dict:
    score = 0
    capacity = project.get('capacity_mw', 0) or 0
    status = str(project.get('development_status_short', '')).lower()
    tech = str(project.get('technology_type', '')).lower()
    
    if capacity >= 100: score += 40
    elif capacity >= 50: score += 30
    elif capacity >= 20: score += 20
    else: score += 10
    
    if 'operational' in status: score += 40
    elif 'construction' in status: score += 35
    elif 'granted' in status: score += 30
    elif 'submitted' in status: score += 20
    else: score += 10
    
    if 'solar' in tech: score += 20
    elif 'battery' in tech: score += 18
    else: score += 15
    
    if score >= 80: grade, color = "A+", "#00FF00"
    elif score >= 70: grade, color = "A", "#7FFF00"
    elif score >= 60: grade, color = "B+", "#FFFF00"
    elif score >= 50: grade, color = "B", "#FFA500"
    elif score >= 40: grade, color = "C", "#FF4500"
    else: grade, color = "D", "#FF0000"
    
    return {"investment_score": score, "investment_grade": grade, "color_code": color}

@app.get("/")
async def root():
    return {"message": "Infranodal API v2.0", "status": "active"}

@app.get("/health")
async def health():
    try:
        print("🔄 Testing database connection...")
        data = await query_supabase("renewable_projects?select=count")
        count = len(data)
        print(f"✅ Database connected: {count} records")
        return {"status": "healthy", "database": "connected", "projects": count}
    except Exception as e:
        print(f"❌ Database error: {e}")
        return {"status": "degraded", "database": "disconnected", "error": str(e)}

@app.get("/api/projects")
async def get_projects(
    limit: int = Query(100), 
    technology: Optional[str] = None,
    country: Optional[str] = None
):
    query_parts = ["renewable_projects?select=*"]
    filters = []
    
    if technology: filters.append(f"technology_type.ilike.%{technology}%")
    if country: filters.append(f"country.ilike.%{country}%")
    if filters: query_parts.append("&".join(filters))
    query_parts.append(f"limit={limit}")
    
    projects = await query_supabase("&".join(query_parts))
    
    for project in projects:
        project.update(calculate_score(project))
    
    return projects

@app.get("/api/projects/geojson")
async def get_geojson():
    projects = await query_supabase("renewable_projects?select=*&limit=500")
    features = []
    
    for project in projects:
        if not project.get('longitude') or not project.get('latitude'):
            continue
        
        project.update(calculate_score(project))
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [project['longitude'], project['latitude']]},
            "properties": {
                "ref_id": project['ref_id'],
                "site_name": project['site_name'],
                "technology_type": project['technology_type'],
                "capacity_mw": project.get('capacity_mw'),
                "county": project.get('county'),
                "investment_score": project['investment_score'],
                "investment_grade": project['investment_grade'],
                "color_code": project['color_code']
            }
        })
    
    return {"type": "FeatureCollection", "features": features}

# Step 4: Add these new endpoints to your main.py file
# Add them AFTER your existing project endpoints
# This teaches your API how to serve infrastructure data

import json

@app.get("/api/infrastructure/transmission")
async def get_transmission_lines():
    """Get power lines for the map"""
    lines = await query_supabase("transmission_lines?select=*")
    
    features = []
    for line in lines or []:
        if not line.get('path_coordinates'):
            continue
            
        try:
            # Convert the coordinate text back into a list
            coordinates = json.loads(line['path_coordinates'])
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": {
                    "name": line['line_name'],
                    "voltage_kv": line['voltage_kv'],
                    "operator": line['operator'],
                    "type": "transmission_line"
                }
            })
        except:
            continue  # Skip if coordinates are broken
    
    return {"type": "FeatureCollection", "features": features}

@app.get("/api/infrastructure/substations")
async def get_substations():
    """Get electrical substations for the map"""
    stations = await query_supabase("substations?select=*")
    
    features = []
    for station in stations or []:
        if not station.get('longitude') or not station.get('latitude'):
            continue
            
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [station['longitude'], station['latitude']]
            },
            "properties": {
                "name": station['substation_name'],
                "operator": station['operator'],
                "voltage_kv": station['primary_voltage_kv'],
                "capacity_mva": station['capacity_mva'],
                "type": "substation"
            }
        })
    
    return {"type": "FeatureCollection", "features": features}

@app.get("/api/infrastructure/fiber")
async def get_fiber_cables():
    """Get internet cables for the map"""
    cables = await query_supabase("fiber_cables?select=*")
    
    features = []
    for cable in cables or []:
        if not cable.get('route_coordinates'):
            continue
            
        try:
            coordinates = json.loads(cable['route_coordinates'])
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": {
                    "name": cable['cable_name'],
                    "operator": cable['operator'],
                    "cable_type": cable['cable_type'],
                    "type": "fiber_cable"
                }
            })
        except:
            continue
    
    return {"type": "FeatureCollection", "features": features}

@app.get("/api/infrastructure/ixp")
async def get_internet_exchanges():
    """Get internet exchange points for the map"""
    ixps = await query_supabase("internet_exchange_points?select=*")
    
    features = []
    for ixp in ixps or []:
        if not ixp.get('longitude') or not ixp.get('latitude'):
            continue
            
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [ixp['longitude'], ixp['latitude']]
            },
            "properties": {
                "name": ixp['ixp_name'],
                "operator": ixp['operator'],
                "city": ixp['city'],
                "networks": ixp['connected_networks'],
                "capacity_gbps": ixp['capacity_gbps'],
                "type": "ixp"
            }
        })
    
    return {"type": "FeatureCollection", "features": features}

@app.get("/api/infrastructure/water")
async def get_water_resources():
    """Get water sources for the map"""
    water_sources = await query_supabase("water_resources?select=*")
    
    features = []
    for water in water_sources or []:
        if not water.get('coordinates'):
            continue
            
        try:
            coordinates = json.loads(water['coordinates'])
            
            # Check if it's a single point or a line/area
            if len(coordinates) == 2 and isinstance(coordinates[0], (int, float)):
                # Single point (like a lake)
                geometry = {
                    "type": "Point",
                    "coordinates": coordinates
                }
            else:
                # Multiple points (like a river)
                geometry = {
                    "type": "LineString",
                    "coordinates": coordinates
                }
            
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "name": water['resource_name'],
                    "resource_type": water['resource_type'],
                    "water_quality": water['water_quality'],
                    "flow_rate": water.get('flow_rate_liters_sec'),
                    "capacity": water.get('capacity_million_liters'),
                    "type": "water_resource"
                }
            })
        except:
            continue
    
    return {"type": "FeatureCollection", "features": features}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

