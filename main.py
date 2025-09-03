from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, List, Literal
import httpx
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import json
import time
from math import radians, sin, cos, asin, sqrt

load_dotenv()

app = FastAPI(title="Infranodal API", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# Debug startup
print(f"✅ SUPABASE_URL: {SUPABASE_URL}")
print(f"✅ SUPABASE_KEY exists: {bool(SUPABASE_KEY)}")

# Define persona types
PersonaType = Literal["hyperscaler", "colocation", "edge_computing"]

# Persona weight definitions
PERSONA_WEIGHTS = {
    "hyperscaler": {
        "capacity": 0.35,              # High capacity critical for large deployments
        "development_stage": 0.25,     # Operational sites preferred for quick deployment
        "technology": 0.10,            # Technology type less critical
        "grid_infrastructure": 0.20,   # Reliable power essential
        "digital_infrastructure": 0.05, # Fiber important but not critical
        "water_resources": 0.05        # Water for cooling systems
    },
    
    "colocation": {
        "capacity": 0.15,              # Smaller capacity needs
        "development_stage": 0.20,     # Flexible on development stage
        "technology": 0.10,            # Technology type flexible
        "grid_infrastructure": 0.25,   # Power reliability critical
        "digital_infrastructure": 0.25, # Connectivity is key for colocation
        "water_resources": 0.05        # Basic cooling needs
    },
    
    "edge_computing": {
        "capacity": 0.10,              # Small capacity requirements
        "development_stage": 0.30,     # Quick deployment critical
        "technology": 0.15,            # Technology flexibility important
        "grid_infrastructure": 0.15,   # Moderate power needs
        "digital_infrastructure": 0.25, # Low latency connectivity critical
        "water_resources": 0.05        # Minimal cooling needs
    }
}

# User site data model
class UserSite(BaseModel):
    site_name: str
    technology_type: str
    capacity_mw: float
    latitude: float
    longitude: float
    commissioning_year: int
    is_btm: bool

async def query_supabase(endpoint: str):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{SUPABASE_URL}/rest/v1/{endpoint}", headers=headers)
        if response.status_code == 200:
            return response.json()
        raise HTTPException(500, f"Database error: {response.status_code}")

# ==================== DISTANCE CALCULATIONS ====================

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

# ==================== COLOR AND DESCRIPTION FUNCTIONS ====================

def get_color_from_score(score_out_of_100: float) -> str:
    """Map 10-100 internal score to color code (displayed as 1.0-10.0)"""
    # Convert to display scale for color mapping
    display_score = score_out_of_100 / 10.0
    
    if display_score >= 9.0: return "#00DD00"      # Excellent - Dark Green
    elif display_score >= 8.0: return "#33FF33"   # Very Good - Bright Green  
    elif display_score >= 7.0: return "#7FFF00"   # Good - Light Green
    elif display_score >= 6.0: return "#CCFF00"   # Above Average - Yellow-Green
    elif display_score >= 5.0: return "#FFFF00"   # Average - Yellow
    elif display_score >= 4.0: return "#FFCC00"   # Below Average - Orange-Yellow
    elif display_score >= 3.0: return "#FF9900"   # Poor - Orange
    elif display_score >= 2.0: return "#FF6600"   # Very Poor - Red-Orange
    elif display_score >= 1.0: return "#FF3300"   # Bad - Red
    else: return "#CC0000"                         # Very Bad - Dark Red

def get_rating_description(score_out_of_100: float) -> str:
    """Get descriptive rating for 10-100 internal score (displayed as 1.0-10.0)"""
    # Convert to display scale for description
    display_score = score_out_of_100 / 10.0
    
    if display_score >= 9.0: return "Excellent"
    elif display_score >= 8.0: return "Very Good"
    elif display_score >= 7.0: return "Good"
    elif display_score >= 6.0: return "Above Average"
    elif display_score >= 5.0: return "Average"
    elif display_score >= 4.0: return "Below Average"
    elif display_score >= 3.0: return "Poor"
    elif display_score >= 2.0: return "Very Poor"
    elif display_score >= 1.0: return "Bad"
    else: return "Very Bad"

# ==================== COMPONENT SCORING FUNCTIONS ====================

def calculate_capacity_component_score(capacity_mw: float) -> float:
    """Score capacity on 10-100 scale based on data center requirements"""
    if capacity_mw >= 100: return 100.0      # Hyperscale requirements
    elif capacity_mw >= 50: return 85.0      # Large enterprise
    elif capacity_mw >= 25: return 70.0      # Medium enterprise  
    elif capacity_mw >= 10: return 55.0      # Small enterprise
    elif capacity_mw >= 5: return 40.0       # Edge computing
    elif capacity_mw >= 1: return 25.0       # Micro edge
    else: return 10.0                        # Too small

def calculate_development_stage_score(status: str) -> float:
    """Score development stage on 10-100 scale"""
    status = str(status).lower()
    if 'operational' in status: return 100.0         # Immediate deployment
    elif 'construction' in status: return 85.0       # Near-term deployment
    elif 'granted' in status: return 70.0           # Planning approved
    elif 'submitted' in status: return 45.0         # Planning pending
    elif 'planning' in status: return 25.0          # Early stage
    else: return 10.0                               # Unknown/conceptual

def calculate_technology_score(tech_type: str) -> float:
    """Score technology type on 10-100 scale for data center suitability"""
    tech = str(tech_type).lower()
    if 'solar' in tech: return 90.0          # Clean, predictable power
    elif 'battery' in tech: return 95.0      # Grid stability, peak shaving
    elif 'wind' in tech: return 75.0         # Variable but clean
    elif 'hybrid' in tech: return 85.0       # Balanced approach
    else: return 60.0                        # Other technologies

def calculate_grid_infrastructure_score(proximity_scores: Dict) -> float:
    """Score grid infrastructure access on 10-100 scale"""
    substation_score = proximity_scores.get('substation_score', 0)
    transmission_score = proximity_scores.get('transmission_score', 0)
    
    # Convert exponential proximity scores to 10-100 scale
    grid_score = 10.0  # Base score
    
    # Substations (primary connection)
    if substation_score > 40: grid_score += 45.0      # Excellent proximity
    elif substation_score > 25: grid_score += 30.0    # Good proximity
    elif substation_score > 10: grid_score += 15.0    # Moderate proximity
    
    # Transmission lines (backup/alternative)
    if transmission_score > 30: grid_score += 30.0    # Direct line access
    elif transmission_score > 15: grid_score += 15.0  # Near transmission
    
    return min(100.0, grid_score)

def calculate_digital_infrastructure_score(proximity_scores: Dict) -> float:
    """Score digital connectivity on 10-100 scale"""
    fiber_score = proximity_scores.get('fiber_score', 0)
    ixp_score = proximity_scores.get('ixp_score', 0)
    
    digital_score = 10.0  # Base score
    
    # Fiber optic networks
    if fiber_score > 15: digital_score += 40.0        # Excellent fiber access
    elif fiber_score > 8: digital_score += 25.0       # Good fiber access
    elif fiber_score > 3: digital_score += 10.0       # Basic fiber access
    
    # Internet Exchange Points
    if ixp_score > 8: digital_score += 35.0           # Near major IXP
    elif ixp_score > 4: digital_score += 20.0         # Regional IXP access
    elif ixp_score > 1: digital_score += 10.0         # Basic IXP access
    
    return min(100.0, digital_score)

def calculate_water_resources_score(proximity_scores: Dict) -> float:
    """Score water resources access on 10-100 scale"""
    water_score = proximity_scores.get('water_score', 0)
    
    base_score = 40.0  # Base score (many sites don't need water cooling)
    
    if water_score > 10: return 100.0        # Excellent water access
    elif water_score > 5: return 80.0        # Good water access
    elif water_score > 2: return 60.0        # Basic water access
    else: return base_score                   # Air cooling sufficient

# ==================== PERSONA-BASED SCORING ====================

def calculate_persona_weighted_score(
    project: Dict, 
    proximity_scores: Dict, 
    persona: PersonaType = "hyperscaler"
) -> Dict:
    """
    Calculate investment rating based on persona-specific weightings
    
    Returns scores on 10-100 internal scale, displayed as 1.0-10.0
    """
    
    weights = PERSONA_WEIGHTS[persona]
    
    # Calculate component scores (10-100 scale)
    capacity_score = calculate_capacity_component_score(project.get('capacity_mw', 0))
    stage_score = calculate_development_stage_score(project.get('development_status_short', ''))
    tech_score = calculate_technology_score(project.get('technology_type', ''))
    grid_score = calculate_grid_infrastructure_score(proximity_scores)
    digital_score = calculate_digital_infrastructure_score(proximity_scores)
    water_score = calculate_water_resources_score(proximity_scores)
    
    # Apply persona-specific weights
    weighted_score = (
        capacity_score * weights["capacity"] +
        stage_score * weights["development_stage"] +
        tech_score * weights["technology"] +
        grid_score * weights["grid_infrastructure"] +
        digital_score * weights["digital_infrastructure"] +
        water_score * weights["water_resources"]
    )
    
    # Ensure score stays within 10-100 range
    final_internal_score = min(100.0, max(10.0, weighted_score))
    
    # Convert to display scale (1.0-10.0)
    display_rating = final_internal_score / 10.0
    
    # Get color and description
    color = get_color_from_score(final_internal_score)
    description = get_rating_description(final_internal_score)
    
    return {
        # Display scores
        "investment_rating": round(display_rating, 1),
        "rating_description": description,
        "color_code": color,
        
        # Component breakdown for transparency
        "component_scores": {
            "capacity": round(capacity_score, 1),
            "development_stage": round(stage_score, 1),
            "technology": round(tech_score, 1),
            "grid_infrastructure": round(grid_score, 1),
            "digital_infrastructure": round(digital_score, 1),
            "water_resources": round(water_score, 1)
        },
        
        # Weighted contributions
        "weighted_contributions": {
            "capacity": round(capacity_score * weights["capacity"], 1),
            "development_stage": round(stage_score * weights["development_stage"], 1),
            "technology": round(tech_score * weights["technology"], 1),
            "grid_infrastructure": round(grid_score * weights["grid_infrastructure"], 1),
            "digital_infrastructure": round(digital_score * weights["digital_infrastructure"], 1),
            "water_resources": round(water_score * weights["water_resources"], 1)
        },
        
        # Persona information
        "persona": persona,
        "persona_weights": weights,
        "internal_total_score": round(final_internal_score, 1),
        "nearest_infrastructure": proximity_scores.get('nearest_distances', {})
    }

# ==================== TRADITIONAL RENEWABLE ENERGY SCORING ====================

def calculate_base_investment_score_renewable(project: Dict) -> float:
    """Traditional renewable energy base scoring (10-100)"""
    capacity = project.get('capacity_mw', 0) or 0
    status = str(project.get('development_status_short', '')).lower()
    tech = str(project.get('technology_type', '')).lower()
    
    # Capacity scoring
    if capacity >= 200: capacity_score = 100.0
    elif capacity >= 100: capacity_score = 90.0
    elif capacity >= 50: capacity_score = 75.0
    elif capacity >= 25: capacity_score = 60.0
    elif capacity >= 10: capacity_score = 45.0
    elif capacity >= 5: capacity_score = 30.0
    else: capacity_score = 15.0
    
    # Stage scoring
    if 'operational' in status: stage_score = 100.0
    elif 'construction' in status: stage_score = 90.0
    elif 'granted' in status: stage_score = 75.0
    elif 'submitted' in status: stage_score = 50.0
    elif 'planning' in status: stage_score = 30.0
    elif 'pre-planning' in status: stage_score = 20.0
    else: stage_score = 10.0
    
    # Technology scoring
    if 'solar' in tech: tech_score = 90.0
    elif 'battery' in tech: tech_score = 85.0
    elif 'wind' in tech: tech_score = 80.0
    elif 'hybrid' in tech: tech_score = 75.0
    else: tech_score = 60.0
    
    # Weighted combination (traditional renewable weights)
    base_score = (
        capacity_score * 0.30 +
        stage_score * 0.50 +
        tech_score * 0.20
    )
    
    return min(100.0, max(10.0, base_score))

def calculate_infrastructure_bonus_renewable(proximity_scores: Dict) -> float:
    """Traditional renewable infrastructure bonus (0-40)"""
    # Grid Infrastructure (0-25 points)
    grid_bonus = 0.0
    substation_score = proximity_scores.get('substation_score', 0)
    transmission_score = proximity_scores.get('transmission_score', 0)
    
    if substation_score > 40: grid_bonus += 15.0
    elif substation_score > 25: grid_bonus += 10.0
    elif substation_score > 10: grid_bonus += 5.0
    
    if transmission_score > 30: grid_bonus += 10.0
    elif transmission_score > 15: grid_bonus += 5.0
    
    grid_bonus = min(25.0, grid_bonus)
    
    # Digital Infrastructure (0-10 points)
    digital_bonus = 0.0
    fiber_score = proximity_scores.get('fiber_score', 0)
    ixp_score = proximity_scores.get('ixp_score', 0)
    
    if fiber_score > 15: digital_bonus += 5.0
    elif fiber_score > 8: digital_bonus += 3.0
    
    if ixp_score > 8: digital_bonus += 5.0
    elif ixp_score > 4: digital_bonus += 2.0
    
    digital_bonus = min(10.0, digital_bonus)
    
    # Water Resources (0-5 points)
    water_bonus = 0.0
    water_score = proximity_scores.get('water_score', 0)
    
    if water_score > 10: water_bonus = 5.0
    elif water_score > 5: water_bonus = 3.0
    elif water_score > 2: water_bonus = 1.0
    
    return grid_bonus + digital_bonus + water_bonus

def calculate_enhanced_investment_rating(project: Dict, proximity_scores: Dict, persona: Optional[PersonaType] = None) -> Dict:
    """
    Main scoring function that handles both renewable energy and data center personas
    """
    
    # If persona specified, use persona-based scoring for data centers
    if persona is not None:
        return calculate_persona_weighted_score(project, proximity_scores, persona)
    
    # Use traditional renewable energy scoring
    # Calculate base investment fundamentals (10-100)
    base_score = calculate_base_investment_score_renewable(project)
    
    # Calculate infrastructure proximity bonus (0-40)
    infrastructure_bonus = calculate_infrastructure_bonus_renewable(proximity_scores)
    
    # Combine scores (cap at 100 for clean 10.0 display)
    total_internal_score = min(100.0, base_score + infrastructure_bonus)
    
    # Convert to display scale (1.0-10.0)
    display_rating = total_internal_score / 10.0
    
    # Get color and description
    color = get_color_from_score(total_internal_score)
    description = get_rating_description(total_internal_score)
    
    return {
        # Display scores (for users)
        "base_investment_score": round(base_score / 10.0, 1),           # Display as X.X/10
        "infrastructure_bonus": round(infrastructure_bonus / 10.0, 1),  # Display as +X.X/10
        "investment_rating": round(display_rating, 1),                  # Display as X.X/10
        
        # UI elements
        "rating_description": description,
        "color_code": color,
        "nearest_infrastructure": proximity_scores.get('nearest_distances', {}),
        "internal_total_score": round(total_internal_score, 1),
        "scoring_methodology": "Traditional renewable energy scoring (10-100 internal, 1.0-10.0 display)"
    }

# ==================== BATCH PROXIMITY CALCULATION ====================

async def calculate_proximity_scores_batch(projects: List[Dict]) -> List[Dict]:
    """OPTIMIZED: Calculate proximity scores for multiple projects efficiently"""
    
    print("🔄 Loading all infrastructure data once...")
    load_start = time.time()
    
    # Load ALL infrastructure data once (instead of per project)
    try:
        substations = await query_supabase("substations?select=*")
        transmission_lines = await query_supabase("transmission_lines?select=*")
        fiber_cables = await query_supabase("fiber_cables?select=*")
        internet_exchange_points = await query_supabase("internet_exchange_points?select=*")
        water_resources = await query_supabase("water_resources?select=*")
        
        load_time = time.time() - load_start
        print(f"✅ Infrastructure loaded in {load_time:.2f}s:")
        print(f"   - Substations: {len(substations or [])}")
        print(f"   - Transmission: {len(transmission_lines or [])}")
        print(f"   - Fiber: {len(fiber_cables or [])}")
        print(f"   - IXPs: {len(internet_exchange_points or [])}")
        print(f"   - Water: {len(water_resources or [])}")
        
    except Exception as e:
        print(f"❌ Error loading infrastructure: {e}")
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

def calculate_rating_distribution(features: List[Dict]) -> Dict:
    """Calculate distribution of ratings for metadata"""
    distribution = {
        "excellent": 0, "very_good": 0, "good": 0, "above_average": 0, "average": 0,
        "below_average": 0, "poor": 0, "very_poor": 0, "bad": 0
    }
    
    for feature in features:
        rating = feature.get("properties", {}).get("investment_rating", 0)
        if rating >= 9.0: distribution["excellent"] += 1
        elif rating >= 8.0: distribution["very_good"] += 1
        elif rating >= 7.0: distribution["good"] += 1
        elif rating >= 6.0: distribution["above_average"] += 1
        elif rating >= 5.0: distribution["average"] += 1
        elif rating >= 4.0: distribution["below_average"] += 1
        elif rating >= 3.0: distribution["poor"] += 1
        elif rating >= 2.0: distribution["very_poor"] += 1
        else: distribution["bad"] += 1
    
    return distribution

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {"message": "Infranodal API v2.1 with Persona-Based Scoring", "status": "active"}

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
    country: Optional[str] = None,
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring")
):
    """Get projects with persona-based or renewable energy scoring"""
    query_parts = ["renewable_projects?select=*"]
    filters = []
    
    if technology: filters.append(f"technology_type.ilike.%{technology}%")
    if country: filters.append(f"country.ilike.%{country}%")
    if filters: query_parts.append("&".join(filters))
    query_parts.append(f"limit={limit}")
    
    projects = await query_supabase("&".join(query_parts))
    
    for project in projects:
        # Use persona-based scoring if persona specified, otherwise renewable energy scoring
        dummy_proximity = {
            'substation_score': 0, 'transmission_score': 0, 'fiber_score': 0,
            'ixp_score': 0, 'water_score': 0, 'nearest_distances': {}
        }
        
        if persona:
            rating_result = calculate_persona_weighted_score(project, dummy_proximity, persona)
        else:
            rating_result = calculate_enhanced_investment_rating(project, dummy_proximity)
        
        # Add new rating fields
        project.update({
            "investment_rating": rating_result['investment_rating'],
            "rating_description": rating_result['rating_description'],
            "color_code": rating_result['color_code'],
            "component_scores": rating_result.get('component_scores'),
            "weighted_contributions": rating_result.get('weighted_contributions'),
            "persona": rating_result.get('persona'),
            "base_score": rating_result.get('base_investment_score', rating_result['investment_rating']),
            "infrastructure_bonus": rating_result.get('infrastructure_bonus', 0.0)
        })
    
    return projects

@app.get("/api/projects/geojson")
async def get_geojson(persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring")):
    """Get projects GeoJSON with persona-based or renewable energy scoring"""
    projects = await query_supabase("renewable_projects?select=*&limit=500")
    features = []
    
    for project in projects:
        if not project.get('longitude') or not project.get('latitude'):
            continue
        
        # Use persona-based scoring if persona specified, otherwise renewable energy scoring
        dummy_proximity = {
            'substation_score': 0, 'transmission_score': 0, 'fiber_score': 0,
            'ixp_score': 0, 'water_score': 0, 'nearest_distances': {}
        }
        
        if persona:
            rating_result = calculate_persona_weighted_score(project, dummy_proximity, persona)
        else:
            rating_result = calculate_enhanced_investment_rating(project, dummy_proximity)
        
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
                
                # NEW 1-10 rating system
                "investment_rating": rating_result['investment_rating'],
                "rating_description": rating_result['rating_description'], 
                "color_code": rating_result['color_code'],
                "component_scores": rating_result.get('component_scores'),
                "weighted_contributions": rating_result.get('weighted_contributions'),
                "persona": rating_result.get('persona'),
                "base_score": rating_result.get('base_investment_score', rating_result['investment_rating']),
                "infrastructure_bonus": rating_result.get('infrastructure_bonus', 0.0)
            }
        })
    
    return {"type": "FeatureCollection", "features": features}

@app.post("/api/user-sites/score")
async def score_user_sites(
    sites: List[UserSite],
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring")
):
    """Score user-uploaded sites with persona-based or renewable energy scoring"""
    
    if not sites:
        raise HTTPException(400, "No sites provided")
    
    # Validate sites
    for i, site in enumerate(sites):
        # Validate coordinates (UK bounds)
        if not (49.8 <= site.latitude <= 60.9) or not (-10.8 <= site.longitude <= 2.0):
            raise HTTPException(400, f"Site {i+1}: Coordinates outside UK bounds")
        
        # Validate capacity
        if not (5 <= site.capacity_mw <= 500):
            raise HTTPException(400, f"Site {i+1}: Capacity must be between 5-500 MW")
        
        # Validate commissioning year
        if not (2025 <= site.commissioning_year <= 2035):
            raise HTTPException(400, f"Site {i+1}: Commissioning year must be between 2025-2035")
    
    scoring_mode = "persona-based" if persona else "renewable energy"
    print(f"🔄 Scoring {len(sites)} user-submitted sites with {scoring_mode.upper()} system...")
    start_time = time.time()
    
    try:
        # Convert to format expected by proximity calculator
        sites_for_calc = []
        for site in sites:
            sites_for_calc.append({
                'site_name': site.site_name,
                'technology_type': site.technology_type,
                'capacity_mw': site.capacity_mw,
                'latitude': site.latitude,
                'longitude': site.longitude,
                'commissioning_year': site.commissioning_year,
                'is_btm': site.is_btm,
                # Add default status for scoring
                'development_status_short': 'planning'
            })
        
        # Calculate proximity scores in batch
        proximity_scores = await calculate_proximity_scores_batch(sites_for_calc)
        
        # Score each site with selected system
        scored_sites = []
        for i, site_data in enumerate(sites_for_calc):
            # Get proximity scores for this site
            if i < len(proximity_scores):
                prox_scores = proximity_scores[i]
            else:
                # Fallback scoring
                prox_scores = {
                    'substation_score': 0, 'transmission_score': 0, 'fiber_score': 0,
                    'ixp_score': 0, 'water_score': 0, 'total_proximity_bonus': 0,
                    'nearest_distances': {}
                }
            
            # Calculate rating based on persona or renewable energy
            if persona:
                rating_result = calculate_persona_weighted_score(site_data, prox_scores, persona)
            else:
                rating_result = calculate_enhanced_investment_rating(site_data, prox_scores)
            
            result = {
                "site_name": site_data['site_name'],
                "technology_type": site_data['technology_type'],
                "capacity_mw": site_data['capacity_mw'],
                "commissioning_year": site_data['commissioning_year'],
                "is_btm": site_data['is_btm'],
                "coordinates": [site_data['longitude'], site_data['latitude']],
                
                # NEW 1-10 RATING SYSTEM
                "investment_rating": rating_result['investment_rating'],
                "rating_description": rating_result['rating_description'],
                "color_code": rating_result['color_code'],
                "component_scores": rating_result.get('component_scores'),
                "weighted_contributions": rating_result.get('weighted_contributions'),
                "persona": rating_result.get('persona'),
                "base_score": rating_result.get('base_investment_score', rating_result['investment_rating']),
                "infrastructure_bonus": rating_result.get('infrastructure_bonus', 0.0),
                
                # Detailed breakdown for transparency
                "nearest_infrastructure": rating_result['nearest_infrastructure'],
                "methodology": f"{scoring_mode} scoring system"
            }
            
            scored_sites.append(result)
        
        processing_time = time.time() - start_time
        print(f"✅ User sites scored with {scoring_mode.upper()} SYSTEM in {processing_time:.2f}s")
        
        return {
            "sites": scored_sites,
            "metadata": {
                "scoring_system": f"{scoring_mode} - 1.0-10.0 Investment Rating Scale",
                "persona": persona,
                "processing_time_seconds": round(processing_time, 2),
                "algorithm_version": "2.1 - Persona-Based Infrastructure Proximity Enhanced",
                "rating_scale": {
                    "9.0-10.0": "Excellent - Premium investment opportunity",
                    "8.0-8.9": "Very Good - Strong investment potential", 
                    "7.0-7.9": "Good - Solid investment opportunity",
                    "6.0-6.9": "Above Average - Moderate investment potential",
                    "5.0-5.9": "Average - Standard investment opportunity",
                    "4.0-4.9": "Below Average - Limited investment appeal",
                    "3.0-3.9": "Poor - Significant investment challenges",
                    "2.0-2.9": "Very Poor - High risk investment",
                    "1.0-1.9": "Bad - Unfavorable investment conditions"
                }
            }
        }
        
    except Exception as e:
        print(f"❌ Error scoring user sites: {e}")
        raise HTTPException(500, f"Scoring failed: {str(e)}")

@app.get("/api/projects/enhanced")
async def get_enhanced_geojson(
    limit: int = Query(50, description="Number of projects to process"),
    persona: Optional[PersonaType] = Query(None, description="Data center persona for custom scoring")
):
    """ENHANCED BATCH VERSION: Get projects with persona-based or renewable energy scoring"""
    start_time = time.time()
    
    scoring_mode = "persona-based" if persona else "renewable energy"
    print(f"🚀 ENHANCED ENDPOINT WITH {scoring_mode.upper()} SCORING - Processing {limit} projects...")
    
    try:
        projects = await query_supabase(f"renewable_projects?select=*&limit={limit}")
        print(f"✅ Loaded {len(projects)} projects from database")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return {"error": "Database connection failed", "type": "FeatureCollection", "features": []}
    
    # Filter projects with valid coordinates
    valid_projects = []
    for project in projects:
        if project.get('longitude') and project.get('latitude'):
            valid_projects.append(project)
    
    print(f"📍 {len(valid_projects)} projects have valid coordinates")
    
    if not valid_projects:
        return {"type": "FeatureCollection", "features": [], "metadata": {"error": "No projects with valid coordinates"}}
    
    try:
        # BATCH PROCESSING: Calculate all proximity scores at once
        print("🔄 Starting batch proximity calculation...")
        batch_start = time.time()
        
        all_proximity_scores = await calculate_proximity_scores_batch(valid_projects)
        
        batch_time = time.time() - batch_start
        print(f"✅ Batch proximity calculation completed in {batch_time:.2f}s")
        
    except Exception as e:
        print(f"❌ Error in batch proximity calculation: {e}")
        # Fallback to basic scoring
        all_proximity_scores = []
        for _ in valid_projects:
            all_proximity_scores.append({
                'substation_score': 0, 'transmission_score': 0, 'fiber_score': 0,
                'ixp_score': 0, 'water_score': 0, 'total_proximity_bonus': 0,
                'nearest_distances': {}
            })
    
    # Build features with scoring based on persona
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
            
            # Use persona-based scoring if persona specified, otherwise renewable energy scoring
            if persona:
                rating_result = calculate_persona_weighted_score(project, proximity_scores, persona)
            else:
                rating_result = calculate_enhanced_investment_rating(project, proximity_scores)
            
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
                    
                    # NEW UNIFIED RATING SYSTEM
                    "investment_rating": rating_result['investment_rating'],
                    "rating_description": rating_result['rating_description'],
                    "color_code": rating_result['color_code'],
                    
                    # Scoring breakdown
                    "component_scores": rating_result.get('component_scores'),
                    "weighted_contributions": rating_result.get('weighted_contributions'),
                    "nearest_infrastructure": rating_result['nearest_infrastructure'],
                    
                    # Persona information (if applicable)
                    "persona": rating_result.get('persona'),
                    "persona_weights": rating_result.get('persona_weights'),
                    
                    # Legacy compatibility
                    "base_score": rating_result.get('base_investment_score', rating_result['investment_rating']),
                    "infrastructure_bonus": rating_result.get('infrastructure_bonus', 0.0),
                    "internal_total_score": rating_result.get('internal_total_score')
                }
            })
            
        except Exception as e:
            print(f"❌ Error processing project {i+1}: {e}")
            # Add fallback scoring
            fallback_rating = {
                'investment_rating': 5.0,
                'rating_description': 'Average',
                'color_code': '#FFFF00',
                'nearest_infrastructure': {}
            }
            
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
                    
                    # Fallback rating
                    "investment_rating": fallback_rating['investment_rating'],
                    "rating_description": fallback_rating['rating_description'],
                    "color_code": fallback_rating['color_code'],
                    "nearest_infrastructure": fallback_rating['nearest_infrastructure']
                }
            })
    
    processing_time = time.time() - start_time
    
    if persona:
        print(f"🎯 PERSONA-BASED SCORING ({persona.upper()}) COMPLETE: {len(features)} features in {processing_time:.2f}s")
    else:
        print(f"🎯 RENEWABLE ENERGY SCORING COMPLETE: {len(features)} features in {processing_time:.2f}s")
    
    return {
        "type": "FeatureCollection", 
        "features": features,
        "metadata": {
            "scoring_system": f"{scoring_mode} - 1.0-10.0 display scale",
            "persona": persona,
            "processing_time_seconds": round(processing_time, 2),
            "projects_processed": len(features),
            "algorithm_version": "2.1 - Persona-Based Infrastructure Scoring",
            "performance_optimization": "Batch proximity scoring (10-50x faster)",
            "rating_distribution": calculate_rating_distribution(features),
            "rating_scale_guide": {
                "excellent": "9.0-10.0",
                "very_good": "8.0-8.9", 
                "good": "7.0-7.9",
                "above_average": "6.0-6.9",
                "average": "5.0-5.9",
                "below_average": "4.0-4.9",
            }
        }
    }

# ==================== INFRASTRUCTURE ENDPOINTS ====================

@app.get("/api/infrastructure/transmission")
async def get_transmission_lines():
    """Get power lines for the map"""
    lines = await query_supabase("transmission_lines?select=*")
    
    features = []
    for line in lines or []:
        if not line.get('path_coordinates'):
            continue
            
        try:
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
            continue
    
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

@app.get("/api/infrastructure/gsp")
async def get_gsp_boundaries():
    """Get GSP boundary polygons for the map"""
    boundaries = await query_supabase("electrical_grid?type=eq.gsp_boundary&select=*")
    
    features = []
    for boundary in boundaries or []:
        if not boundary.get('geometry'):
            continue
            
        try:
            # Handle different geometry formats
            geom = boundary['geometry']
            
            # If geometry is a string, parse it
            if isinstance(geom, str):
                geom = json.loads(geom)
            
            # If it's PostGIS format, you may need to convert
            # For now, assume it's already in GeoJSON format
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "name": boundary['name'],
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

@app.get("/api/infrastructure/tnuos")
async def get_tnuos_zones():
    """Get TNUoS zones for the map"""
    zones = await query_supabase("tnuos_zones?tariff_year=eq.2024-25&select=*")
    
    features = []
    for zone in zones or []:
        if not zone.get('geometry'):
            continue
            
        try:
            # Handle geometry - it might be a string or already parsed
            geometry = zone['geometry']
            if isinstance(geometry, str):
                geometry = json.loads(geometry)
            
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "zone_id": zone.get('zone_id'),
                    "zone_name": zone.get('zone_name'),
                    "tariff_pounds_per_kw": zone.get('generation_tariff_pounds_per_kw'),
                    "tariff_year": zone.get('tariff_year'),
                    "effective_from": zone.get('effective_from'),
                    "type": "tnuos_zone"
                }
            })
        except Exception as e:
            print(f"Error processing TNUoS zone {zone.get('zone_id', 'unknown')}: {e}")
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

# ==================== COMPARISON ENDPOINT FOR TESTING ====================

@app.get("/api/projects/compare-scoring")
async def compare_scoring_systems(
    limit: int = Query(10, description="Projects to compare"),
    persona: PersonaType = Query("hyperscaler", description="Persona for comparison")
):
    """Compare traditional renewable vs persona-based scoring systems"""
    
    projects = await query_supabase(f"renewable_projects?select=*&limit={limit}")
    
    comparison = []
    for project in projects:
        if not project.get('longitude') or not project.get('latitude'):
            continue
        
        # Dummy proximity for comparison
        dummy_proximity = {
            'substation_score': 0, 'transmission_score': 0, 'fiber_score': 0,
            'ixp_score': 0, 'water_score': 0, 'nearest_distances': {}
        }
        
        # OLD SYSTEM (renewable energy scoring)
        renewable_rating = calculate_enhanced_investment_rating(project, dummy_proximity)
        
        # NEW SYSTEM (persona-based scoring)
        persona_rating = calculate_persona_weighted_score(project, dummy_proximity, persona)
        
        comparison.append({
            "site_name": project.get('site_name'),
            "capacity_mw": project.get('capacity_mw'),
            "technology_type": project.get('technology_type'),
            "renewable_energy_system": {
                "investment_rating": renewable_rating['investment_rating'],
                "rating_description": renewable_rating['rating_description'],
                "color": renewable_rating['color_code']
            },
            "persona_system": {
                "persona": persona,
                "investment_rating": persona_rating['investment_rating'],
                "rating_description": persona_rating['rating_description'],
                "color": persona_rating['color_code'],
                "component_scores": persona_rating['component_scores'],
                "weighted_contributions": persona_rating['weighted_contributions']
            }
        })
    
    return {
        "comparison": comparison,
        "summary": {
            "renewable_system": "Traditional renewable energy scoring (capacity, stage, tech)",
            "persona_system": f"{persona} data center scoring with custom weightings",
            "persona_weights": PERSONA_WEIGHTS[persona],
            "migration_benefits": [
                "Scoring tailored to specific data center requirements",
                "Transparent component breakdown showing why sites score differently", 
                "Infrastructure priorities matching real deployment needs",
                "Better investment decision making for specific use cases"
            ]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)




