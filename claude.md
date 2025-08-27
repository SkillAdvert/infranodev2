# Infranodal - Renewable Energy Investment Analysis Platform

## Project Overview
Interactive web application enabling renewable energy investors and developers to assess site viability through proximity-based infrastructure scoring. The platform combines existing project databases with real-time infrastructure analysis, providing investment grades from D to A++ based on comprehensive scoring algorithms.

## Current Architecture

### Backend (Production Ready)
- **Framework**: FastAPI with Python 3.9+
- **Database**: Supabase PostgreSQL with PostGIS extensions
- **Deployment**: Render.com at `https://infranodev2.onrender.com`
- **Performance**: Batch processing optimization (10-50x faster than individual queries)
- **Data Sources**: 
  - NESO GSP boundary data (333 features) 
  - OpenStreetMap telecommunications infrastructure (549+ segments)
  - Manual infrastructure datasets (substations, IXPs, water resources)

### Frontend (React + TypeScript)
- **Framework**: React 18 + TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **Mapping**: Mapbox GL JS with professional infrastructure visualization
- **State Management**: React hooks with optimized re-rendering
- **Build System**: Vite/Create React App compatible

### Database Schema
```sql
-- Core Tables (Production)
renewable_projects (100+ records) - Existing UK renewable projects
electrical_grid - GSP boundaries and grid infrastructure  
transmission_lines - Power transmission network
substations - Electrical substations with capacity data
fiber_cables - Telecommunications fiber networks
internet_exchange_points - Data center connectivity hubs
water_resources - Water sources for cooling/operations
```

## Investment Scoring Algorithm (Production Tested)

### Base Investment Score (0-100 points)
- **Project Capacity**: 
  - 100MW+ = 40 points (utility-scale premium)
  - 50-100MW = 30 points (commercial scale)
  - 20-50MW = 20 points (distributed scale)
  - <20MW = 10 points (small scale)
- **Development Status**: 
  - Operational = 40 points (revenue generating)
  - Under Construction = 35 points (low execution risk)
  - Planning Granted = 30 points (regulatory approval secured)
  - Application Submitted = 20 points (planning risk)
  - Early Planning = 10 points (high risk)
- **Technology Premium**: 
  - Solar PV = 20 points (proven technology)
  - Battery Storage = 18 points (grid services value)
  - Wind/Other = 15 points (baseline)

### Infrastructure Proximity Bonus (0-95 points)
**Distance-based exponential decay scoring:**
- **Grid Connection Access**: Up to 50 points
  - Substations (primary connection points)
  - Transmission lines (using point-to-line distance algorithms)
- **Digital Infrastructure**: Up to 20 points
  - Fiber optic networks (co-location opportunities)
- **Strategic Infrastructure**: Up to 25 points
  - Internet Exchange Points (10 points - data center proximity)
  - Water Resources (15 points - cooling/operations)

**Distance Calculation Methods:**
- Point-to-point: Haversine formula for accuracy
- Point-to-line: Geometric shortest distance algorithms
- Exponential decay: f(d) = s_max * e^(-4.6d/d_max) where d_max=100km

### Enhanced Investment Grades
- **Total Range**: 0-195 points (base + proximity)
- **A++ (170-195)**: Premium investment opportunities with optimal infrastructure access
- **A+ (150-169)**: Strong opportunities with good infrastructure
- **A (130-149)**: Good opportunities with adequate access
- **B+ (110-129)**: Moderate opportunities, some infrastructure gaps
- **B (90-109)**: Baseline viability, limited infrastructure benefits
- **C+ (70-89)**: Below-average opportunities, infrastructure challenges
- **C (50-69)**: Poor infrastructure access, high development costs
- **D (0-49)**: Unfavorable locations for development

## API Endpoints (Production)

### Core Data Endpoints
```http
GET /api/projects/enhanced?limit=100
# Returns: Enhanced scored renewable projects with proximity analysis

GET /api/projects/geojson  
# Returns: Basic project data in GeoJSON format

POST /api/user-sites/score
# Payload: User-defined site parameters
# Returns: Real-time investment scoring and infrastructure analysis
```

### Infrastructure Visualization Endpoints
```http
GET /api/infrastructure/transmission   # Power transmission lines
GET /api/infrastructure/substations    # Electrical substations
GET /api/infrastructure/gsp           # Grid Supply Point boundaries
GET /api/infrastructure/fiber         # Telecommunications fiber
GET /api/infrastructure/ixp          # Internet Exchange Points  
GET /api/infrastructure/water        # Water resources
```

### Health & Diagnostics
```http
GET /health                          # System health check
GET /                               # API status and version
```

## Component Architecture

### DynamicSiteMap.tsx (Core Map Interface)
**Responsibilities:**
- Mapbox GL integration with UK/Ireland bounds (49.8-60.9°N, -10.8-2.0°E)
- Project visualization with investment-grade color coding
- Infrastructure layer management and styling
- Interactive popups with detailed project/infrastructure information
- Clustering for performance at scale
- Click-to-place functionality for site assessment

**Current Issues:**
- TypeScript interface mismatch in infrastructure toggle handlers
- MapLayerControls component creates UI duplication and confusion
- Infrastructure layer visualization disabled due to compilation errors

**Technical Specifications:**
```typescript
interface Project {
  properties: {
    ref_id?: string;
    site_name: string;
    technology_type: string;
    capacity_mw: number;
    investment_grade: string;
    enhanced_score?: number;
    proximity_bonus?: number;
    county: string;
    country: string;
  };
}
```

### MapOverlayControls.tsx (Infrastructure Controls)
**Purpose:** Professional infrastructure layer toggles positioned as map overlays
**Status:** Working but needs interface type corrections (icon: string -> React.ReactNode)
**Styling:** Professional Lucide icons replacing emoji placeholders

### MapLayerControls.tsx (Deprecated)
**Issues:** 
- Persona switching (renewable vs datacenter) adds confusion for MVP
- Conceptual layers don't align with actual infrastructure data
- Creates control duplication with MapOverlayControls
**Recommendation:** Remove entirely for MVP simplicity

### DataUploadPanel.tsx (Site Assessment)
**Features:**
- Interactive site builder with form validation
- Two-site comparison capability  
- Map coordinate placement integration
- Real-time API scoring integration
- Results visualization with scoring breakdown

**Validation Rules:**
```javascript
{
  capacity_mw: 5-500,           // MW range validation
  latitude: 49.8-60.9,         // UK bounds only
  longitude: -10.8-2.0,        // UK bounds only  
  commissioning_year: 2025-2035, // Future projects
  technology_type: ["Solar", "Wind", "Battery", "Hybrid"]
}
```

## Data Fetching & Integration

### Current Data Pipeline
1. **fetch_gsp_boundaries.py**: NESO official GSP data (333 polygons)
2. **fetch_fiber_data.py**: Telecommunications infrastructure via Overpass API  
3. **fetch_network.py**: Additional network infrastructure aggregation
4. **main.py**: Centralized API serving with batch optimization

### Infrastructure Data Status
- **Working**: GSP boundaries, fiber networks, substations, IXPs
- **Issues**: Transmission lines endpoint timeouts (500 status codes)
- **Performance**: 17+ seconds full dataset load, optimized with batch processing

### Deployment Workflow  
**Current Process:**
1. Run data fetching scripts locally against production Supabase
2. Deploy clean main.py (without admin endpoints) to Render
3. Frontend connects to production API endpoints

**Rationale:** Local data fetching avoids Render execution environment limitations and timeout issues

## Current Development Status

### Production Ready Features
- Investment scoring algorithm with proximity calculations
- Real-time site assessment API with validation
- Professional map interface with project visualization  
- Infrastructure data serving (most layers working)
- UK-focused coordinate validation and bounds checking
- Batch-optimized performance for multiple site scoring

### Active Issues Requiring Resolution
1. **TypeScript Interface Mismatches**: 
   - MapOverlayControls icon prop type (string vs ReactNode)
   - Infrastructure toggle handler parameter types
2. **Infrastructure Visualization**: 
   - Transmission endpoint 500 errors
   - Layer compilation issues in frontend
3. **Component Architecture**:
   - Duplicate control systems (MapLayerControls vs MapOverlayControls)
   - UI inconsistency between technical and investor interfaces

### Not Yet Implemented
- PDF report generation (placeholder toast notifications only)
- Data center deployment recommendations based on scoring
- Financial modeling integration for ROI calculations
- Site data persistence (currently client-side session only)

## Technical Debt & Optimization Opportunities

### Frontend Performance
- Map component re-renders can be optimized with useCallback dependencies
- Infrastructure data loading should be lazy-loaded per layer
- GeoJSON parsing could be moved to web workers for large datasets

### Backend Optimizations  
- Transmission lines endpoint needs query optimization or data pagination
- Infrastructure endpoints could benefit from spatial indexing
- Batch scoring algorithms already optimized (10-50x improvement achieved)

### UI/UX Improvements for Investor Readiness
- Replace technical jargon with investor-friendly language
- Consolidate duplicate control interfaces
- Implement professional styling consistent with shadcn/ui design system
- Add empty states and loading indicators throughout

## Environment Configuration

### Required Environment Variables
```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Mapping (Frontend)  
MAPBOX_PUBLIC_TOKEN=pk.your-mapbox-token

# API Configuration
API_BASE_URL=https://infranodev2.onrender.com  # Production
```

### Development Dependencies
```json
{
  "mapbox-gl": "^2.15.0",
  "@supabase/supabase-js": "^2.38.0", 
  "lucide-react": "^0.263.1",
  "recharts": "^2.8.0",
  "tailwindcss": "^3.3.0"
}
```

## Testing & Quality Assurance

### Verified Working Workflows
1. **Site Assessment**: Form validation → coordinate placement → API scoring → results display
2. **Project Visualization**: Database query → GeoJSON conversion → map rendering → popup interactions
3. **Infrastructure Integration**: Layer toggling → API fetching → map overlay rendering
4. **Investment Scoring**: Proximity calculation → exponential scoring → grade assignment

### Known Performance Characteristics
- **API Response Times**: <2s for individual site scoring, <5s for batch processing
- **Map Rendering**: <1s for 100+ projects with clustering
- **Infrastructure Loading**: 2-17s depending on layer complexity
- **Database Query Performance**: Optimized with spatial indexing on coordinate fields

## Next Development Priorities

### Critical Path (MVP Completion)
1. **Fix TypeScript Interface Issues**: Resolve compilation errors blocking infrastructure visualization
2. **Consolidate Control Components**: Remove MapLayerControls, optimize MapOverlayControls positioning
3. **Resolve Transmission Endpoint**: Debug 500 errors and implement proper error handling
4. **Professional UI Polish**: Consistent Lucide icons, responsive layout, investor-appropriate terminology

### Enhancement Phase  
1. **PDF Export Implementation**: Professional reports with maps, scoring details, and investment recommendations
2. **Data Center Recommendations**: AI-generated deployment suggestions based on infrastructure scoring
3. **Advanced Financial Modeling**: ROI calculations incorporating proximity-based cost savings
4. **Enhanced Visualization**: Heat maps, comparative analysis tools, custom styling options

### Future Platform Development
1. **Multi-Region Support**: Expand beyond UK boundaries to EU and other markets
2. **Real-Time Data Integration**: Live grid pricing, capacity availability, planning application status
3. **Collaboration Features**: Multi-user access, shared project workspaces, stakeholder reporting
4. **Advanced Analytics**: Machine learning for development risk assessment, market trend analysis

## Architectural Decisions & Rationale

### Why Batch Processing Infrastructure Queries
Individual proximity calculations were taking 30+ seconds per site. Batch processing loads all infrastructure once and processes multiple sites against cached data, achieving 10-50x performance improvements.

### Why UK Geographic Bounds Only
Initial market focus enables deeper infrastructure data integration and regulatory understanding. Expansion to other regions requires similar infrastructure dataset development and local market knowledge.

### Why No Browser Storage APIs  
Claude.ai artifact environment limitations prevent localStorage/sessionStorage usage. All state management uses React hooks with session-based persistence.

### Why Exponential Distance Scoring
Linear distance scoring doesn't reflect the dramatic cost differences between nearby vs. distant infrastructure. Exponential decay better models real-world infrastructure connection costs and development feasibility.

This documentation reflects the current production state as of December 2024, including both working functionality and known issues requiring resolution.
