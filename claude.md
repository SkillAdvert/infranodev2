# Infranodal - Renewable Energy Investment Analysis Platform
NB Hero can be changed here: https://github.com/SkillAdvert/infranode-cloud-flow/blob/main/src/pages/PersonaSelection.tsx
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

# Infranodal - Renewable Energy Investment Analysis Platform

## Project Overview
Interactive web application enabling renewable energy investors and data center developers to assess site viability through AI-powered infrastructure scoring. The platform combines existing project databases with real-time infrastructure analysis, providing investment ratings from 1.0-10.0 based on persona-specific algorithms and comprehensive proximity scoring.

## Current Architecture

### Backend (Production Ready)
- **Framework**: FastAPI with Python 3.9+
- **Database**: Supabase PostgreSQL with PostGIS extensions
- **Deployment**: Render.com at `https://infranodev2.onrender.com`
- **Performance**: Batch processing optimization (10-50x faster than individual queries)
- **AI Integration**: Ready for Claude/OpenAI integration via Supabase Edge Functions
- **Data Sources**: 
  - NESO GSP boundary data (333 features) 
  - OpenStreetMap telecommunications infrastructure (549+ segments)
  - Manual infrastructure datasets (substations, IXPs, water resources)

### Frontend (React + TypeScript)
- **Framework**: React 18 + TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components (optimized subset)
- **Mapping**: Mapbox GL JS with professional infrastructure visualization
- **State Management**: React hooks with optimized re-rendering
- **Build System**: Vite/Create React App compatible
- **AI Chat**: Integrated persona-aware AI chatbot for project analysis

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

## NEW: Persona-Based Investment Scoring (2.1 Algorithm)

### Data Center Personas
- **Hyperscaler**: High capacity focus (35% weight), reliable power (20%), quick deployment (25%)
- **Colocation**: Balanced approach with connectivity emphasis (25% digital infrastructure)  
- **Edge Computing**: Small capacity (10%), quick deployment critical (30%), low latency (25%)

### Investment Rating Scale (1.0-10.0)
**Internal scoring**: 10-100 points, displayed as 1.0-10.0 for user clarity

**Rating Descriptions:**
- **9.0-10.0**: Excellent - Premium investment opportunity
- **8.0-8.9**: Very Good - Strong investment potential  
- **7.0-7.9**: Good - Solid investment opportunity
- **6.0-6.9**: Above Average - Moderate investment potential
- **5.0-5.9**: Average - Standard investment opportunity
- **4.0-4.9**: Below Average - Limited investment appeal
- **3.0-3.9**: Poor - Significant investment challenges
- **2.0-2.9**: Very Poor - High risk investment
- **1.0-1.9**: Bad - Unfavorable investment conditions

### Component Scoring (10-100 Internal Scale)
1. **Capacity Score**: 
   - 100MW+ = 100 points (hyperscale)
   - 50MW+ = 85 points (large enterprise)
   - 25MW+ = 70 points (medium enterprise)
   - 10MW+ = 55 points (small enterprise)
   - 5MW+ = 40 points (edge computing)

2. **Development Stage**: 
   - Operational = 100 points (immediate deployment)
   - Construction = 85 points (near-term)
   - Granted = 70 points (planning approved)
   - Submitted = 45 points (pending approval)

3. **Technology Suitability**:
   - Battery = 95 points (grid stability + peak shaving)
   - Solar = 90 points (clean, predictable)
   - Hybrid = 85 points (balanced approach)
   - Wind = 75 points (variable but clean)

4. **Grid Infrastructure** (10-100):
   - Excellent substation proximity (>40 exponential score) = 45 bonus points
   - Good substation proximity (>25) = 30 bonus points
   - Direct transmission access (>30) = 30 bonus points

5. **Digital Infrastructure** (10-100):
   - Excellent fiber access (>15 exponential score) = 40 bonus points
   - Major IXP proximity (>8) = 35 bonus points
   - Regional connectivity = scaled bonuses

6. **Water Resources** (40-100):
   - Excellent access (>10 exponential score) = 100 points
   - Good access (>5) = 80 points
   - Basic access (>2) = 60 points
   - Air cooling sufficient = 40 points (baseline)

## API Endpoints (Production)

### Enhanced Scoring Endpoints
```http
GET /api/projects/enhanced?limit=100&persona=hyperscaler
# Returns: Persona-weighted scored projects with 1.0-10.0 rating system

POST /api/user-sites/score?persona=colocation
# Payload: User-defined site parameters + persona selection
# Returns: Persona-specific investment scoring and infrastructure analysis

GET /api/projects/compare-scoring?persona=edge_computing
# Returns: Side-by-side comparison of renewable vs persona-based scoring
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

## Component Architecture Updates

### DynamicSiteMap.tsx (UPDATED - Fixed Interface Issues)
**Current State**: ✅ Working with new 1.0-10.0 rating system
**Responsibilities:**
- Mapbox GL integration with UK/Ireland region switching
- Project visualization with investment rating color coding (1.0-10.0 scale)
- Infrastructure layer management with proper TypeScript interfaces
- Interactive popups with persona-specific scoring details
- Clustering for performance at scale
- Click-to-place functionality for site assessment

**Interface Updates:**
```typescript
interface Project {
  properties: {
    ref_id?: string;
    site_name: string;
    technology_type: string;
    capacity_mw: number;
    // NEW: 1.0-10.0 Rating System
    investment_rating: number;           // Display score 1.0-10.0
    rating_description: string;          // "Excellent", "Good", etc.
    color_code: string;                  // Color for visualization
    // Optional persona-specific data
    component_scores?: any;
    weighted_contributions?: any;
    persona?: string;
    nearest_infrastructure?: any;
  };
}
```

### NEW: AI Project Analysis Component
**AIProjectAnalysis.tsx**: 
- Persona-specific suitability scoring for individual projects
- AI-generated strengths, concerns, and recommendations
- Integration with Supabase Edge Functions
- Professional dialog interface with tabbed persona comparison

**Integration Points:**
- Project list items (clickable AI analysis button)
- Map popups (analyze this project link)
- Chatbot context (project-aware conversations)

### PersonaSelector.tsx (NEW)
**Purpose**: Data center persona selection and explanation interface
**Features**:
- Visual persona comparison with weightings
- Real-time scoring preview
- Educational content about each persona type
- Seamless integration with dashboard state

### Enhanced Chat Integration
**RenewableAIChatbox.tsx** (UPDATED):
- Context-aware conversations based on selected persona
- Project-specific analysis capabilities  
- Integration with location-based context
- Professional renewable energy domain knowledge

## Data Center Persona Integration

### Persona Weightings
```python
PERSONA_WEIGHTS = {
    "hyperscaler": {
        "capacity": 0.35,              # High capacity critical
        "development_stage": 0.25,     # Operational sites preferred
        "technology": 0.10,            # Technology type less critical
        "grid_infrastructure": 0.20,   # Reliable power essential
        "digital_infrastructure": 0.05,# Fiber important but not critical
        "water_resources": 0.05        # Water for cooling systems
    },
    "colocation": {
        "capacity": 0.15,              # Smaller capacity needs
        "development_stage": 0.20,     # Flexible on development stage
        "technology": 0.10,            # Technology type flexible
        "grid_infrastructure": 0.25,   # Power reliability critical
        "digital_infrastructure": 0.25,# Connectivity is key
        "water_resources": 0.05        # Basic cooling needs
    },
    "edge_computing": {
        "capacity": 0.10,              # Small capacity requirements
        "development_stage": 0.30,     # Quick deployment critical
        "technology": 0.15,            # Technology flexibility important
        "grid_infrastructure": 0.15,   # Moderate power needs
        "digital_infrastructure": 0.25,# Low latency connectivity critical
        "water_resources": 0.05        # Minimal cooling needs
    }
}
```

### AI Analysis Integration
Projects can now be analyzed through multiple lenses:
1. **Traditional Renewable Scoring**: Capacity + stage + technology focus
2. **Persona-Specific Scoring**: Weighted by data center requirements
3. **AI Comparative Analysis**: Strengths/concerns for each persona type

## Frontend Optimization (NEW)

### UI Component Cleanup
**Removed 20+ unused shadcn/ui components** for better performance:
- accordion, breadcrumb, calendar, carousel, chart, checkbox
- command, context-menu, drawer, form, hover-card, menubar  
- navigation-menu, pagination, progress, radio-group, resizable
- separator, sheet, sidebar, skeleton, switch, sonner, toast

**Retained essential components**:
- button, card, input, badge, tabs, dialog, alert, tooltip, slider, select

### Performance Improvements
- Reduced bundle size by ~40% through component removal
- Optimized map re-renders with useCallback dependencies  
- Lazy-loaded infrastructure layers
- Batch-optimized proximity calculations

## Current Development Status

### ✅ Recently Fixed
1. **Backend-Frontend Mismatch**: Updated infranodev2 backend to return `investment_rating` + `rating_description` instead of old `enhanced_score` + `investment_grade` system
2. **TypeScript Interface Issues**: Fixed Project interface to match new 1.0-10.0 rating system
3. **Persona Integration**: Complete persona-based scoring implementation
4. **UI Component Bloat**: Removed 20+ unused components

### ✅ Production Ready Features  
- Persona-based investment scoring (1.0-10.0 scale)
- Real-time site assessment with persona selection
- Professional map interface with region switching (UK/Ireland)
- Infrastructure data serving (6 layer types working)
- AI-powered project analysis (ready for integration)
- Batch-optimized performance for multiple site scoring

### 🔄 Active Development
1. **AI Integration**: Supabase Edge Function for `analyze-project-personas`
2. **Enhanced Chat**: Project-context awareness in AI conversations  
3. **Professional UI**: Investor-appropriate terminology and styling
4. **Advanced Analytics**: Persona comparison reports

### ⏳ Planned Features
- PDF report generation with persona-specific insights
- Advanced financial modeling with persona-weighted ROI
- Multi-region expansion beyond UK/Ireland
- Real-time infrastructure data feeds
- Collaborative workspace features

## Technical Architecture Decisions

### Why Persona-Based Scoring?
Different data center types have fundamentally different infrastructure requirements:
- **Hyperscalers** need massive power capacity and reliability above all
- **Colocation providers** balance power, connectivity, and operational efficiency
- **Edge computing** prioritizes quick deployment and low latency over capacity

Generic renewable energy scoring doesn't capture these nuanced requirements.

### Why 1.0-10.0 Display Scale?
- **User-friendly**: Intuitive rating system (like IMDb, Yelp)
- **Precise**: 0.1 increments allow nuanced differentiation
- **Professional**: Investment-grade appearance vs. academic letter grades
- **Scalable**: Easy to extend with additional personas or criteria

### Why AI Integration?
Persona-based scoring provides quantitative analysis, but investors need qualitative insights:
- **Contextual Analysis**: AI explains why a site scores well/poorly for specific personas
- **Risk Assessment**: Identifies concerns human analysts might miss
- **Opportunity Identification**: Suggests optimization strategies
- **Comparative Intelligence**: Explains trade-offs between persona approaches

## Next Development Priorities

### Critical Path (Q1 2024)
1. **Complete AI Integration**: Deploy Supabase Edge Functions for persona analysis
2. **Enhanced User Experience**: Professional styling and terminology refinement
3. **Advanced Analytics**: Comparative persona analysis and reporting
4. **Performance Optimization**: Further map rendering and data loading improvements

### Growth Phase (Q2 2024)
1. **Financial Modeling**: ROI calculations with persona-specific cost models
2. **Advanced Visualization**: Heat maps, trend analysis, market intelligence
3. **Collaboration Features**: Multi-user access, shared analysis, stakeholder reports
4. **Regional Expansion**: EU market data integration

## Environment Configuration

### Required Environment Variables
```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Mapping (Frontend)  
MAPBOX_PUBLIC_TOKEN=pk.your-mapbox-token

# API Configuration (UPDATED)
API_BASE_URL=https://infranodev2.onrender.com  # Correct backend URL

# AI Integration (NEW)
OPENAI_API_KEY=your-openai-key  # For Supabase Edge Functions
```

### Development Dependencies (Updated)
```json
{
  "mapbox-gl": "^2.15.0",
  "@supabase/supabase-js": "^2.38.0", 
  "lucide-react": "^0.263.1",
  "recharts": "^2.8.0",
  "tailwindcss": "^3.3.0",
  "react-markdown": "^9.0.0"
}
```

## API Response Format (NEW)

### Enhanced Project Response
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature", 
    "geometry": {"type": "Point", "coordinates": [-2.69, 51.25]},
    "properties": {
      "ref_id": 18491,
      "site_name": "Plas Power Estate Solar Farm",
      "technology_type": "Battery",
      "capacity_mw": 57.0,
      
      // NEW: 1.0-10.0 Rating System  
      "investment_rating": 4.2,
      "rating_description": "Below Average", 
      "color_code": "#FFCC00",
      
      // NEW: Persona-Specific Data
      "persona": "hyperscaler",
      "component_scores": {
        "capacity": 85.0,
        "development_stage": 70.0,
        "grid_infrastructure": 45.2,
        "digital_infrastructure": 25.8,
        "water_resources": 60.0
      },
      "weighted_contributions": {
        "capacity": 29.75,
        "development_stage": 17.5,
        "grid_infrastructure": 9.04
      },
      "nearest_infrastructure": {
        "substation_km": 28.7,
        "transmission_km": 78.1,
        "fiber_km": 18.2
      }
    }
  }],
  "metadata": {
    "scoring_system": "persona-based - 1.0-10.0 display scale",
    "persona": "hyperscaler",
    "algorithm_version": "2.1 - Persona-Based Infrastructure Scoring",
    "rating_distribution": {
      "excellent": 5, "very_good": 12, "good": 18,
      "above_average": 15, "average": 8
    }
  }
}
```

This documentation reflects the current production state as of September 2025, including the new persona-based scoring system, AI integration capabilities, and recent frontend optimizations.
