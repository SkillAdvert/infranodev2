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

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
