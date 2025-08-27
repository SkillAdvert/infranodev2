from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, List
import httpx
import os
import json
import time
import subprocess
import sys
from math import radians, sin, cos, asin, sqrt
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Infranodal API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# Debug startup
print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"SUPABASE_KEY exists: {bool(SUPABASE_KEY)}")

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
        print("Testing database connection...")
        data = await query_supabase("renewable_projects?select=count")
        count = len(data)
        print(f"Database connected: {count} records")
        return {"status": "healthy", "database": "connected", "projects": count}
    except Exception as e:
        print(f"Database error: {e}")
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
                "operator": project.get('operator'),
                "capacity_mw": project.get('capacity_mw'),
                "county": project.get('county'),
                "investment_score": project['investment_score'],
                "investment_grade": project['investment_grade'],
                "color_code": project['color_code']
            }
        })
    
    return {"type": "FeatureCollection", "features": features}

# SCORING ALGORITHM - OPTIMIZED VERSION
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points on Earth in kilometers"""
    R = 6371  # Earth radius (km)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    lat1, lat2 = radians(lat1), radians(lat2)
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

def exponential_score(distance_km: float, d_max: float = 100, s_max: float = 50) -> float:
    """Exponential decay scoring: closer infrastructure = exponentially better score"""
    if distance_km >= d_max:
        return 0
    
    k = 4.6 / d_max  # ln(100) ≈ 4.6, gives good decay curve
    score = s_max * (2.718 ** (-k * distance_km))
    return max(0, score)

def point_to_line_segment_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate shortest distance from point to line segment using haversine"""
    A = px - x1
    B = py - y1
    C = x2 - x1
    D = y2 - y1
    
    dot = A * C + B * D
    len_sq = C * C + D * D
    
    if len_sq == 0:
        return haversine(px, py, x1, y1)
    
    param = dot / len_sq
    
    if param < 0:
        closest_x, closest_y = x1, y1
    elif param > 1:
        closest_x, closest_y = x2, y2
    else:
        closest_x = x1 + param * C
        closest_y = y1 + param * D
    
    return haversine(px, py, closest_x, closest_y)

# OPTIMIZED: Load infrastructure once, score multiple projects
async def calculate_proximity_scores_batch(projects: List[Dict]) -> List[Dict]:
    """OPTIMIZED: Calculate proximity scores for multiple projects efficiently"""
    
    print("Loading all infrastructure data once...")
    load_start = time.time()
    
    # Load ALL infrastructure data once (instead of per project)
    try:
        substations = await query_supabase("substations?select=*")
        transmission_lines = await query_supabase("transmission_lines?select=*")
        fiber_cables = await query_supabase("fiber_cables?select=*")
        internet_exchange_points = await query_supabase("internet_exchange_points?select=*")
        water_resources = await query_supabase("water_resources?select=*")
        
        load_time = time.time() - load_start
        print(f"Infrastructure loaded in {load_time:.2f}s:")
        print(f"   - Substations: {len(substations or [])}")
        print(f"   - Transmission: {len(transmission_lines or [])}")
        print(f"   - Fiber: {len(fiber_cables or [])}")
        print(f"   - IXPs: {len(internet_exchange_points or [])}")
        print(f"   - Water: {len(water_resources or [])}")
        
    except Exception as e:
        print(f"Error loading infrastructure: {e}")
        return []
    
    # Now process each project against the cached data
    results = []
    for i, project in enumerate(projects):
        if not project.get('longitude') or not project.get('latitude'):
            continue
            
        project_lat = project['latitude']
        project_lng = project['longitude']
        
        proximity_scores = {
            'substation_score': 0,
            'transmission_score': 0,
            'fiber_score': 0,
            'ixp_score': 0,
            'water_score': 0,
            'total_proximity_bonus': 0,
            'nearest_distances': {}
        }
        
        # 1. SUBSTATIONS (using cached data)
        substation_distances = []
        for substation in substations or []:
            if not substation.get('latitude') or not substation.get('longitude'):
                continue
            
            distance = haversine(project_lat, project_lng, substation['latitude'], substation['longitude'])
            if distance <= 100:  # 100km cutoff
                substation_distances.append(distance)
        
        if substation_distances:
            nearest_substation = min(substation_distances)
            proximity_scores['substation_score'] = exponential_score(nearest_substation)
            proximity_scores['nearest_distances']['substation_km'] = round(nearest_substation, 1)
        
        # 2. TRANSMISSION LINES
        transmission_distances = []
        for line in transmission_lines or []:
            if not line.get('path_coordinates'):
                continue
            
            try:
                coordinates = json.loads(line['path_coordinates'])
                min_distance_to_line = float('inf')
                
                for j in range(len(coordinates) - 1):
                    seg_distance = point_to_line_segment_distance(
                        project_lat, project_lng,
                        coordinates[j][1], coordinates[j][0],  # lat, lon
                        coordinates[j+1][1], coordinates[j+1][0]
                    )
                    min_distance_to_line = min(min_distance_to_line, seg_distance)
                
                if min_distance_to_line <= 100:
                    transmission_distances.append(min_distance_to_line)
            except:
                continue
        
        if transmission_distances:
            nearest_transmission = min(transmission_distances)
            proximity_scores['transmission_score'] = exponential_score(nearest_transmission)
            proximity_scores['nearest_distances']['transmission_km'] = round(nearest_transmission, 1)
        
        # 3. FIBER CABLES
        fiber_distances = []
        for cable in fiber_cables or []:
            if not cable.get('route_coordinates'):
                continue
            
            try:
                coordinates = json.loads(cable['route_coordinates'])
                min_distance_to_cable = float('inf')
                
                for j in range(len(coordinates) - 1):
                    seg_distance = point_to_line_segment_distance(
                        project_lat, project_lng,
                        coordinates[j][1], coordinates[j][0],
                        coordinates[j+1][1], coordinates[j+1][0]
                    )
                    min_distance_to_cable = min(min_distance_to_cable, seg_distance)
                
                if min_distance_to_cable <= 100:
                    fiber_distances.append(min_distance_to_cable)
            except:
                continue
        
        if fiber_distances:
            nearest_fiber = min(fiber_distances)
            proximity_scores['fiber_score'] = exponential_score(nearest_fiber, s_max=20)
            proximity_scores['nearest_distances']['fiber_km'] = round(nearest_fiber, 1)
        
        # 4. INTERNET EXCHANGE POINTS
        ixp_distances = []
        for ixp in internet_exchange_points or []:
            if not ixp.get('latitude') or not ixp.get('longitude'):
                continue
            
            distance = haversine(project_lat, project_lng, ixp['latitude'], ixp['longitude'])
            if distance <= 100:
                ixp_distances.append(distance)
        
        if ixp_distances:
            nearest_ixp = min(ixp_distances)
            proximity_scores['ixp_score'] = exponential_score(nearest_ixp, s_max=10)
            proximity_scores['nearest_distances']['ixp_km'] = round(nearest_ixp, 1)
        
        # 5. WATER RESOURCES
        water_distances = []
        for water in water_resources or []:
            if not water.get('coordinates'):
                continue
            
            try:
                coordinates = json.loads(water['coordinates'])
                
                if len(coordinates) == 2 and isinstance(coordinates[0], (int, float)):
                    # Single point (lake/reservoir)
                    distance = haversine(project_lat, project_lng, coordinates[1], coordinates[0])
                else:
                    # Line (river)
                    min_distance_to_water = float('inf')
                    for j in range(len(coordinates) - 1):
                        seg_distance = point_to_line_segment_distance(
                            project_lat, project_lng,
                            coordinates[j][1], coordinates[j][0],
                            coordinates[j+1][1], coordinates[j+1][0]
                        )
                        min_distance_to_water = min(min_distance_to_water, seg_distance)
                    distance = min_distance_to_water
                
                if distance <= 100:
                    water_distances.append(distance)
            except:
                continue
        
        if water_distances:
            nearest_water = min(water_distances)
            proximity_scores['water_score'] = exponential_score(nearest_water, s_max=15)
            proximity_scores['nearest_distances']['water_km'] = round(nearest_water, 1)
        
        # Calculate total proximity bonus
        proximity_scores['total_proximity_bonus'] = (
            proximity_scores['substation_score'] +
            proximity_scores['transmission_score'] + 
            proximity_scores['fiber_score'] +
            proximity_scores['ixp_score'] +
            proximity_scores['water_score']
        )
        
        results.append(proximity_scores)
    
    return results

def calculate_enhanced_score(project: Dict, proximity_scores: Dict) -> Dict:
    """Combine original project scoring with proximity bonus"""
    
    # Get original score
    original_scoring = calculate_score(project)
    base_score = original_scoring['investment_score']
    
    # Add proximity bonus
    proximity_bonus = min(proximity_scores['total_proximity_bonus'], 95)
    enhanced_score = min(base_score + proximity_bonus, 195)
    
    # Enhanced grading scale
    if enhanced_score >= 170: grade, color = "A++", "#00DD00"
    elif enhanced_score >= 150: grade, color = "A+", "#00FF00"  
    elif enhanced_score >= 130: grade, color = "A", "#7FFF00"
    elif enhanced_score >= 110: grade, color = "B+", "#FFFF00"
    elif enhanced_score >= 90: grade, color = "B", "#FFA500"
    elif enhanced_score >= 70: grade, color = "C+", "#FF7700"
    elif enhanced_score >= 50: grade, color = "C", "#FF4500"
    else: grade, color = "D", "#FF0000"
    
    return {
        "base_investment_score": base_score,
        "proximity_bonus": round(proximity_bonus, 1),
        "enhanced_investment_score": round(enhanced_score, 1),
        "investment_grade": grade,
        "color_code": color,
        "proximity_details": proximity_scores
    }

# Infrastructure endpoints
@app.get("/api/infrastructure/transmission")
async def get_transmission_lines():
    """Get power lines for the map"""
    try:
        print("Fetching transmission lines...")
        lines = await query_supabase("transmission_lines?select=*&limit=500")
        print(f"Retrieved {len(lines or [])} transmission lines from database")
        
        if not lines:
            print("No transmission lines found in database")
            return {"type": "FeatureCollection", "features": []}
        
        features = []
        processed_count = 0
        error_count = 0
        
        for line in lines:
            try:
                if not line.get('path_coordinates'):
                    continue
                    
                coordinates = json.loads(line['path_coordinates'])
                
                # Validate coordinates format
                if not isinstance(coordinates, list) or len(coordinates) < 2:
                    continue
                    
                # Check if coordinates are valid numbers
                valid_coords = []
                for coord in coordinates:
                    if isinstance(coord, list) and len(coord) >= 2:
                        try:
                            lng, lat = float(coord[0]), float(coord[1])
                            # Basic UK/Ireland bounds check
                            if -15.0 <= lng <= 5.0 and 48.0 <= lat <= 62.0:
                                valid_coords.append([lng, lat])
                        except (ValueError, TypeError):
                            continue
                
                if len(valid_coords) < 2:
                    continue
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": valid_coords
                    },
                    "properties": {
                        "name": line.get('line_name', 'Transmission Line'),
                        "voltage_kv": line.get('voltage_kv'),
                        "operator": line.get('operator', 'Unknown'),
                        "type": "transmission_line"
                    }
                })
                processed_count += 1
                
            except json.JSONDecodeError as e:
                error_count += 1
                print(f"JSON decode error for line: {e}")
                continue
            except Exception as e:
                error_count += 1
                print(f"Processing error for line: {e}")
                continue
        
        print(f"Transmission lines processed: {processed_count} valid, {error_count} errors")
        
        return {"type": "FeatureCollection", "features": features}
        
    except Exception as e:
        print(f"Critical error in transmission endpoint: {e}")
        return {"type": "FeatureCollection", "features": [], "error": str(e)}

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

@app.get("/api/infrastructure/gsp")
async def get_gsp_boundaries():
    """Get GSP boundary polygons for the map"""
    boundaries = await query_supabase("electrical_grid?type=eq.gsp_boundary&select=*")
    
    features = []
    for boundary in boundaries or []:
        if not boundary.get('geom'):
            continue
            
        try:
            # Handle different geometry formats
            geom = boundary['geom']
            
            # If geometry is a string, parse it
            if isinstance(geom, str):
                geom = json.loads(geom)
            
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "name": boundary.get('name', 'GSP Boundary'),
                    "operator": boundary.get('operator', 'NESO'),
                    "type": "gsp_boundary"
                }
            })
        except Exception as e:
            print(f"Error processing GSP boundary: {e}")
            continue
    
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

@app.get("/api/infrastructure/network")
async def get_network_infrastructure():
    """Get network infrastructure - alias for fiber"""
    return await get_fiber_cables()

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
            
            if len(coordinates) == 2 and isinstance(coordinates[0], (int, float)):
                geometry = {
                    "type": "Point",
                    "coordinates": coordinates
                }
            else:
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

# ADMIN ENDPOINTS - Trigger data fetching
@app.post("/admin/fetch-gsp")
async def admin_fetch_gsp():
    """Run GSP boundaries fetch script"""
    try:
        print("Running fetch_gsp_boundaries.py...")
        result = subprocess.run(
            [sys.executable, "fetch_gsp_boundaries.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": "GSP boundaries fetched successfully",
                "output": result.stdout,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "GSP fetch failed",
                "error": result.stderr,
                "timestamp": datetime.now().isoformat()
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "GSP fetch timed out (>5 minutes)",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"GSP fetch error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/admin/fetch-fiber")
async def admin_fetch_fiber():
    """Run fiber data fetch script"""
    try:
        print("Running fetch_fiber_data.py...")
        result = subprocess.run(
            [sys.executable, "fetch_fiber_data.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": "Fiber data fetched successfully",
                "output": result.stdout,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "Fiber fetch failed",
                "error": result.stderr,
                "timestamp": datetime.now().isoformat()
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Fiber fetch timed out (>5 minutes)",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Fiber fetch error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/admin/fetch-network")
async def admin_fetch_network():
    """Run network data fetch script"""
    try:
        print("Running fetch_network.py...")
        result = subprocess.run(
            [sys.executable, "fetch_network.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": "Network data fetched successfully",
                "output": result.stdout,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "Network fetch failed",
                "error": result.stderr,
                "timestamp": datetime.now().isoformat()
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Network fetch timed out (>5 minutes)",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Network fetch error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/admin/sync-all")
async def admin_sync_all():
    """Run all infrastructure fetch scripts in sequence"""
    results = {}
    
    # GSP Boundaries
    try:
        print("Step 1/3: Running fetch_gsp_boundaries.py...")
        result = subprocess.run(
            [sys.executable, "fetch_gsp_boundaries.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        results["gsp"] = {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout if result.returncode == 0 else result.stderr
        }
    except Exception as e:
        results["gsp"] = {"status": "error", "output": str(e)}
    
    # Fiber Data
    try:
        print("Step 2/3: Running fetch_fiber_data.py...")
        result = subprocess.run(
            [sys.executable, "fetch_fiber_data.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        results["fiber"] = {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout if result.returncode == 0 else result.stderr
        }
    except Exception as e:
        results["fiber"] = {"status": "error", "output": str(e)}
    
    # Network Data
    try:
        print("Step 3/3: Running fetch_network.py...")
        result = subprocess.run(
            [sys.executable, "fetch_network.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        results["network"] = {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout if result.returncode == 0 else result.stderr
        }
    except Exception as e:
        results["network"] = {"status": "error", "output": str(e)}
    
    # Overall status
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    overall_status = "success" if success_count == 3 else "partial" if success_count > 0 else "failed"
    
    return {
        "overall_status": overall_status,
        "completed": success_count,
        "total": 3,
        "results": results,
        "timestamp": datetime.now().isoformat(),
        "message": f"Sync completed: {success_count}/3 scripts successful"
    }

# OPTIMIZED ENHANCED ENDPOINT - BATCH VERSION
@app.get("/api/projects/enhanced")
async def get_enhanced_geojson(limit: int = Query(50, description="Number of projects to process")):
    """OPTIMIZED BATCH VERSION: Get projects with enhanced proximity-based scoring"""
    start_time = time.time()
    
    print(f"ENHANCED ENDPOINT CALLED (BATCH VERSION) - Processing {limit} projects...")
    
    try:
        projects = await query_supabase(f"renewable_projects?select=*&limit={limit}")
        print(f"Loaded {len(projects)} projects from database")
    except Exception as e:
        print(f"Database error: {e}")
        return {"error": "Database connection failed", "type": "FeatureCollection", "features": []}
    
    # Filter projects with valid coordinates
    valid_projects = []
    for project in projects:
        if project.get('longitude') and project.get('latitude'):
            valid_projects.append(project)
    
    print(f"{len(valid_projects)} projects have valid coordinates")
    
    if not valid_projects:
        return {"type": "FeatureCollection", "features": [], "metadata": {"error": "No projects with valid coordinates"}}
    
    try:
        # BATCH PROCESSING: Calculate all proximity scores at once
        print("Starting batch proximity calculation...")
        batch_start = time.time()
        
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects)
        
        batch_time = time.time() - batch_start
        print(f"Batch proximity calculation completed in {batch_time:.2f}s")
        
    except Exception as e:
        print(f"Error in batch proximity calculation: {e}")
        # Fallback to basic scoring
        all_proximity_scores = []
        for _ in valid_projects:
            all_proximity_scores.append({
                'substation_score': 0, 'transmission_score': 0, 'fiber_score': 0,
                'ixp_score': 0, 'water_score': 0, 'total_proximity_bonus': 0,
                'nearest_distances': {}
            })
    
    # Build features with enhanced scoring
    features = []
    for i, project in enumerate(valid_projects):
        try:
            if i < len(all_proximity_scores):
                proximity_scores = all_proximity_scores[i]
            else:
                # Fallback scoring
                proximity_scores = {
                    'substation_score': 0, 'transmission_score': 0, 'fiber_score': 0,
                    'ixp_score': 0, 'water_score': 0, 'total_proximity_bonus': 0,
                    'nearest_distances': {}
                }
            
            enhanced_scoring = calculate_enhanced_score(project, proximity_scores)
            
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [project['longitude'], project['latitude']]},
                "properties": {
                    "ref_id": project['ref_id'],
                    "site_name": project['site_name'],
                    "technology_type": project['technology_type'],
                    "operator": project.get('operator'), 
                    "capacity_mw": project.get('capacity_mw'),
                    "county": project.get('county'),
                    "country": project.get('country'),
                    "base_score": enhanced_scoring['base_investment_score'],
                    "proximity_bonus": enhanced_scoring['proximity_bonus'],
                    "enhanced_score": enhanced_scoring['enhanced_investment_score'],
                    "investment_grade": enhanced_scoring['investment_grade'],
                    "color_code": enhanced_scoring['color_code'],
                    "nearest_infrastructure": enhanced_scoring['proximity_details']['nearest_distances']
                }
            })
            
        except Exception as e:
            print(f"Error processing project {i+1}: {e}")
            # Add basic scoring as fallback
            basic_score = calculate_score(project)
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [project['longitude'], project['latitude']]},
                "properties": {
                    "ref_id": project['ref_id'],
                    "site_name": project['site_name'],
                    "operator": project.get('operator'),  
                    "technology_type": project['technology_type'],
                    "capacity_mw": project.get('capacity_mw'),
                    "county": project.get('county'),
                    "country": project.get('country'),
                    "base_score": basic_score['investment_score'],
                    "proximity_bonus": 0,
                    "enhanced_score": basic_score['investment_score'],
                    "investment_grade": basic_score['investment_grade'],
                    "color_code": basic_score['color_code'],
                    "nearest_infrastructure": {}
                }
            })
    
    processing_time = time.time() - start_time
    print(f"BATCH ENHANCED ENDPOINT COMPLETE: {len(features)} features in {processing_time:.2f}s")
    
    return {
        "type": "FeatureCollection", 
        "features": features,
        "metadata": {
            "processing_time_seconds": round(processing_time, 2),
            "projects_processed": len(features),
            "algorithm_status": "OPTIMIZED: Batch proximity scoring",
            "performance_improvement": f"Expected 10-50x faster than individual processing",
            "batch_optimization": "Infrastructure loaded once, not per project"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
