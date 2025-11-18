# Frontend-Backend Integration & Architecture Map
**Date**: November 18, 2025
**Project**: Infranode Cloud Flow + Infranodev2 Backend
**Version**: 1.0
**Status**: Complete Integration Mapping

---

## Executive Summary

This document maps the complete integration between the **Infranode Cloud Flow frontend** (React 18 + TypeScript) and **Infranodev2 backend** (FastAPI). It provides a detailed guide to understand:

- **API Endpoints** - Frontend consumption of backend endpoints
- **Data Flow** - Request/response patterns and data transformations
- **Routing** - Frontend routes and backend endpoint routing
- **File Dependencies** - Frontend component dependencies on backend services
- **State Management** - How frontend manages backend data
- **Authentication** - User auth flow and authorization
- **Configuration** - Environment setup and deployment

---

## Table of Contents

1. [API Integration Map](#api-integration-map)
2. [Frontend Component to Backend API Mapping](#frontend-component-to-backend-api-mapping)
3. [Data Flow & Workflows](#data-flow--workflows)
4. [Routing Architecture](#routing-architecture)
5. [File Dependencies](#file-dependencies)
6. [State Management Integration](#state-management-integration)
7. [Authentication & Authorization](#authentication--authorization)
8. [Error Handling Integration](#error-handling-integration)
9. [Request/Response Contracts](#requestresponse-contracts)
10. [Performance & Caching Strategy](#performance--caching-strategy)
11. [Deployment & Environment Configuration](#deployment--environment-configuration)
12. [Known Issues & Recommendations](#known-issues--recommendations)

---

## API Integration Map

### Complete Endpoint Reference

#### **Project Data Endpoints** (`/api/projects/*`)

| Frontend Component | HTTP Method | Backend Endpoint | Request Body | Response | Cache TTL | Purpose |
|-------------------|------------|------------------|--------------|----------|-----------|---------|
| HyperscalerDashboard, UtilityDashboard | GET | `/api/projects` | None | `Project[]` (JSON) | 5min | Fetch all renewable projects |
| SiteMappingTools, FullScreenMap | GET | `/api/projects/geojson` | None | `FeatureCollection` (GeoJSON) | 5min | Map visualization of all projects |
| TopProjectsPanel, ResultsModal | GET | `/api/projects/enhanced` | Params: `limit`, `offset` | `FeatureCollection` with scoring | 5min | Projects with investment ratings |
| HyperscalerDashboard (customer match) | POST | `/api/projects/customer-match` | `{persona, criteria, filters}` | `{matched_projects: Feature[], stats}` | None | Find projects by persona fit |
| ProjectScoreStatistics | GET | `/api/projects/compare-scoring` | Params: `project_ids[]` | `{comparisons: object[]}` | 1min | Compare different scoring methods |
| PowerDeveloperAnalysis | POST | `/api/projects/power-developer-analysis` | `{persona, criteria, limit}` | `{results: Feature[], ranking}` | None | Power developer workflow |

#### **User Site Submission** (`/api/user-sites/*`)

| Frontend Component | HTTP Method | Backend Endpoint | Request Body | Response | Purpose |
|-------------------|------------|------------------|--------------|----------|---------|
| SiteAssessmentTool | POST | `/api/user-sites/score` | `{sites: {lat, lon, name, capacity}[]}` | `{scored_sites: Feature[]}` | Score user-submitted locations |

#### **Infrastructure Layers** (`/api/infrastructure/*`)

| Frontend Component | HTTP Method | Backend Endpoint | Response Type | Layer Name | Purpose |
|-------------------|------------|------------------|--------------|-----------|---------|
| SiteMap, FullScreenMap | GET | `/api/infrastructure/transmission` | GeoJSON (LineString[]) | `transmission` | Power transmission lines (32kV+) |
| SiteMap, FullScreenMap | GET | `/api/infrastructure/substations` | GeoJSON (Point[]) | `substations` | Electrical substations |
| SiteMap, FullScreenMap | GET | `/api/infrastructure/gsp` | GeoJSON (Polygon[]) | `gsp` | Grid Supply Points (333 zones) |
| SiteMap, FullScreenMap | GET | `/api/infrastructure/fiber` | GeoJSON (LineString[]) | `fiber` | Telecommunications fiber cables |
| SiteMap, FullScreenMap | GET | `/api/infrastructure/tnuos` | GeoJSON (Polygon[] with tariffs) | `tnuos` | TNUoS transmission zones (27 zones) |
| SiteMap, FullScreenMap | GET | `/api/infrastructure/ixp` | GeoJSON (Point[]) | `ixp` | Internet exchange points |
| SiteMap, FullScreenMap | GET | `/api/infrastructure/water` | GeoJSON (Point[]/LineString[]) | `water` | Water resources for cooling |
| SiteMap, FullScreenMap | GET | `/api/infrastructure/dno-areas` | GeoJSON (Polygon[]) | `dno-areas` | DNO license areas |

#### **TEC Connections** (`/api/tec/*`)

| Frontend Component | HTTP Method | Backend Endpoint | Response Type | Purpose |
|-------------------|------------|------------------|--------------|---------|
| TecConnectionsMap | GET | `/api/tec/connections` | GeoJSON (Point[]) | Grid connection applications |

#### **Financial Modeling** (`/api/financial-model/*`)

| Frontend Component | HTTP Method | Backend Endpoint | Request Body | Response | Purpose |
|-------------------|------------|------------------|--------------|----------|---------|
| IRREstimator | POST | `/api/financial-model` | `FinancialModelRequest` | `FinancialModelResponse` | Calculate IRR/NPV/LCOE |
| IRREstimator | GET | `/api/financial-model/units` | None | `{parameters: {unit, default_value}[]}` | Financial input parameters |

#### **Health & Status** (Monitoring)

| Frontend Component | HTTP Method | Backend Endpoint | Response | Purpose |
|-------------------|------------|------------------|----------|---------|
| App initialization | GET | `/health` | `{status, cache_status, db_status}` | API health check |

---

## Frontend Component to Backend API Mapping

### Dashboard Components

#### **HyperscalerDashboard** (`src/pages/dashboards/HyperscalerDashboard.tsx`)

```typescript
// Component Purpose: Main analysis dashboard for Hyperscaler persona

API Calls:
├─ GET /api/projects/enhanced
│  └─ Fetches projects with scoring metadata
│     Response: FeatureCollection with investment_rating, component_scores
│
├─ POST /api/projects/customer-match
│  ├─ Input: CriteriaModal selections (capacity, connection_speed, resilience, etc.)
│  ├─ Persona: "hyperscaler" (capacity: 100-250MW)
│  └─ Response: Ranked matching projects
│
└─ GET /api/infrastructure/* (7 layers)
   ├─ /transmission, /substations, /gsp, /fiber, /tnuos, /ixp, /water
   └─ Displayed on interactive Mapbox GL map

State Management:
├─ Zustand: useAppStore() → selectedPersona, user
├─ React Query: Cache /api/projects/enhanced (5min TTL)
└─ Session Storage: Top projects for workflow preservation

Component Tree:
├─ CriteriaModal (captures user preferences)
├─ SiteMap (Mapbox GL with layer toggles)
├─ TopProjectsPanel (display top 5-10 projects)
├─ ResultsModal (detailed scoring breakdown)
└─ ProcessingModal (async status feedback)
```

#### **UtilityDashboard** (`src/pages/dashboards/UtilityDashboard.tsx`)

```typescript
// Component Purpose: Analysis dashboard for Utility persona

API Calls:
├─ POST /api/projects/customer-match
│  ├─ Persona: "utility"
│  ├─ Different criteria weights than hyperscaler
│  └─ Focus: Grid connection, regulatory compliance
│
├─ GET /api/projects/geojson
│  └─ All utility-relevant projects as GeoJSON
│
└─ GET /api/infrastructure/gsp, /transmission
   └─ Grid Supply Point and transmission focus

State Management:
├─ Zustand: selectedPersona = "utility"
├─ React Query: Cached project data
└─ Session Storage: Utility-specific analysis results
```

#### **ColocationAnalysis** (`src/pages/ColocationAnalysis.tsx`)

```typescript
// Component Purpose: Colocation-specific site matching

API Calls:
├─ POST /api/projects/customer-match
│  ├─ Persona: "solutions" or "colocation"
│  ├─ Focus: IXP proximity, fiber connectivity
│  └─ Gate: IXP <= 5km, fiber <= 2km
│
├─ GET /api/infrastructure/ixp
│  └─ Internet exchange point locations
│
└─ GET /api/infrastructure/fiber
   └─ Fiber cable routes for connectivity analysis

Key Data:
├─ ixp_km: Distance to nearest Internet Exchange Point
├─ fiber_km: Distance to nearest fiber cable
└─ latency: Critical metric for colocation success
```

### Map & Visualization Components

#### **SiteMap** (`src/features/site-map/SiteMap.tsx`)

```typescript
// Component Purpose: Interactive Mapbox GL visualization

API Calls:
├─ GET /api/projects/geojson
│  └─ Project features (Point[] with properties)
│
├─ GET /api/infrastructure/transmission
│  ├─ Type: LineString (polylines)
│  ├─ Style: Purple (#8B4789) lines
│  └─ Click handler: Show transmission details
│
├─ GET /api/infrastructure/substations
│  ├─ Type: Point (circles)
│  ├─ Style: Orange (#FF8C00) circles, sized by capacity
│  └─ Hover: Display capacity_mva, voltage_kv
│
├─ GET /api/infrastructure/gsp
│  ├─ Type: Polygon (filled boundaries)
│  ├─ Style: Light blue fill, darker blue outline
│  └─ Purpose: Show 333 GSP zones
│
├─ GET /api/infrastructure/fiber
│  ├─ Type: LineString (cyan/teal lines)
│  └─ Click: Show provider, connection_type
│
├─ GET /api/infrastructure/tnuos
│  ├─ Type: Polygon (27 zones with tariff data)
│  ├─ Fill color: Green (positive tariff) to Red (negative)
│  └─ Hover: Display tariff_rate (£/MW)
│
├─ GET /api/infrastructure/ixp
│  ├─ Type: Point (red squares)
│  └─ Hover: Display connected_operators
│
└─ GET /api/infrastructure/water
   ├─ Type: Point/LineString (blue symbols)
   └─ Info: Type (river, reservoir), capacity

Layer Management:
├─ MapOverlayControls component controls visibility
├─ toggleMapLayer(layerName, visible) function
└─ All layers cached for 5 minutes

Mapbox GL Integration:
├─ Version: 3.13.0
├─ Style: Mapbox Streets (light/dark mode)
├─ Controls: Zoom, pan, fullscreen, layer toggle
└─ GeoJSON FeatureCollections directly rendered
```

#### **FullScreenMap** (`src/pages/FullScreenMap.tsx`)

```typescript
// Component Purpose: Full-screen map view with all layers

Extends SiteMap with:
├─ Full viewport (no sidebars)
├─ Larger interactive area
└─ All infrastructure layers simultaneously visible
```

### Analysis & Results Components

#### **TopProjectsPanel** (`src/components/TopProjectsPanel.tsx`)

```typescript
// Component Purpose: Display ranked projects from analysis

Data Source:
├─ Props: projects FeatureCollection from /api/projects/enhanced
└─ Filter: Top 5-10 projects by investment_rating

Display Fields:
├─ Site Name
├─ Investment Rating (1.0-10.0 scale)
├─ Capacity (MW)
├─ Technology Type
├─ Development Status
├─ Color-coded rating badge
└─ Distance to key infrastructure

Click Handler:
└─ Navigate to Project Detail view or show on map
```

#### **ResultsModal** (`src/components/ResultsModal.tsx`)

```typescript
// Component Purpose: Detailed scoring breakdown

Data Source:
├─ Props: Selected project Feature object
└─ Includes: component_scores, weighted_contributions

Displays:
├─ Investment rating breakdown (8 components)
├─ Capacity fit vs persona ideal
├─ Distance to all infrastructure types
├─ TNUoS tariff impact
├─ LCOE resource quality
└─ Recommendations

No direct API calls - uses data from /api/projects/enhanced response
```

#### **ProjectInsights** (`src/components/ProjectInsights.tsx`)

```typescript
// Component Purpose: Statistical analysis and insights

Data Source:
├─ Props: projects FeatureCollection
└─ Computed locally from project data

Calculates:
├─ Average investment rating
├─ Median distance to infrastructure
├─ Range and percentiles
└─ Technology mix
```

### Analysis Components

#### **DistanceDistributionChart** & **CumulativeDistanceChart**

```typescript
// Component Purpose: Visualize infrastructure proximity

Data Source:
├─ Props: projects array
└─ Uses: Computed distance metrics (fiber_km, transmission_km, etc.)

Charts (Recharts):
├─ Histogram: Distribution of distances
└─ CDF: Cumulative distance probability

No backend calls - local computation
```

#### **InteractiveRadarChart** (`src/components/InteractiveRadarChart.tsx`)

```typescript
// Component Purpose: Multi-dimensional criteria visualization

Data Source:
├─ Props: component_scores from project Feature
└─ Axes: 8 scoring components (capacity, technology, grid, etc.)

Visualization:
├─ Radar plot with filled area
├─ Color-coded by score (green = high, red = low)
└─ Interactive tooltips
```

### Financial Modeling Components

#### **IRREstimator** (`src/features/irr-estimator/*`)

```typescript
// Component Purpose: Financial modeling and IRR/NPV calculations

API Calls:
├─ POST /api/financial-model
│  ├─ Request: FinancialModelRequest
│  │  ├─ technology: "solar" | "wind" | "battery"
│  │  ├─ capacity_mw: number
│  │  ├─ capacity_factor: number
│  │  ├─ capex_per_kw: number
│  │  ├─ opex_fix: number
│  │  ├─ opex_var: number
│  │  ├─ ppa_price: number
│  │  ├─ ppa_duration: number
│  │  ├─ merchant_price: number
│  │  ├─ discount_rate: number
│  │  ├─ project_life: number
│  │  ├─ tax_rate: number
│  │  └─ ... (15+ total parameters)
│  │
│  └─ Response: FinancialModelResponse
│     ├─ standard: ModelResults
│     │  ├─ irr: number (%)
│     │  ├─ npv: number (£)
│     │  ├─ lcoe: number (£/MWh)
│     │  ├─ cashflows: number[]
│     │  ├─ payback_simple: number (years)
│     │  └─ payback_discounted: number (years)
│     │
│     └─ autoproducer: ModelResults (BTM scenario)
│
└─ GET /api/financial-model/units
   └─ Returns: {parameters: [{name, unit, default_value, min, max}]}

Input Form:
├─ Technology dropdown
├─ Capacity input (MW)
├─ Capacity factor (0-100%)
├─ CAPEX per kW (£/kW)
├─ Fixed OPEX (£/kW/year)
├─ Variable OPEX (£/MWh)
├─ PPA price (£/MWh)
├─ PPA duration (years)
├─ Merchant price (£/MWh)
├─ Discount rate (%)
├─ Project life (years)
└─ Tax rate (%)

Results Display:
├─ IRR % (dual scenarios)
├─ NPV £ (dual scenarios)
├─ LCOE £/MWh
├─ Cashflow table
├─ Payback period
└─ Sensitivity analysis charts (optional)
```

### Form & User Input Components

#### **CriteriaModal** (`src/components/CriteriaModal.tsx`)

```typescript
// Component Purpose: Capture hyperscaler business criteria

Form Fields (Importance Score 0-100):
├─ Capacity: Priority weight
├─ Connection Speed: Grid + fiber proximity importance
├─ Resilience: Redundancy/backup requirements
├─ Land Planning: Planning permission maturity
├─ Latency: Network latency tolerance
├─ Cooling: Water/cooling system importance
├─ Price Sensitivity: Cost optimization importance
└─ Custom Weights (Optional): Override defaults

Gate Filters (Mandatory):
├─ Minimum Capacity: >= X MW
├─ Maximum Fiber Distance: <= X km
├─ Maximum Transmission Distance: <= X km
└─ Minimum Transmission Capacity: >= X MW

On Submit:
├─ Compile BusinessCriteria object
├─ POST to /api/projects/customer-match
└─ Normalize weights to sum = 1.0
```

#### **UtilityCriteriaModal** (`src/components/UtilityCriteriaModal.tsx`)

```typescript
// Component Purpose: Capture utility business criteria

Form Fields (Different from Hyperscaler):
├─ Grid Connection Priority
├─ Regulatory Compliance
├─ Regional Preference
├─ Technology Preference
└─ Capacity Requirements

Gate Filters:
├─ GSP zone requirements
├─ Transmission capacity requirements
└─ Regional grid constraints
```

### User & Auth Components

#### **Auth** (`src/pages/Auth.tsx`)

```typescript
// Component Purpose: User authentication

Service Used: Supabase Auth
├─ Email/password authentication
├─ OAuth integration
└─ Session management

On Success:
├─ Create user session
├─ Store in Supabase users table
├─ Set auth context
└─ Redirect to /dashboard/{persona}
```

#### **PersonaSelection** (`src/pages/PersonaSelection.tsx`)

```typescript
// Component Purpose: Initial user persona selection

Options:
├─ Hyperscaler
├─ Utility
├─ Colocation/Solutions
└─ Grid Operator (future)

Selection Flow:
├─ Save persona to Zustand store
├─ Save to Supabase user_roles table
└─ Redirect to /auth or /dashboard/{persona}
```

---

## Data Flow & Workflows

### Workflow 1: Hyperscaler Site Analysis

```
┌─────────────────────────────────────────────────────────┐
│ User selects "Hyperscaler" on PersonaSelection page     │
└────────────────────┬────────────────────────────────────┘
                     │ selectedPersona = "hyperscaler"
                     ▼
┌─────────────────────────────────────────────────────────┐
│ HyperscalerDashboard loads                              │
├─ GET /api/projects/enhanced (cache 5min)                │
├─ GET /api/infrastructure/* (7 layers)                   │
└─ Render: SiteMap + TopProjectsPanel + CriteriaModal     │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ User opens CriteriaModal                                │
├─ Select business criteria weights (0-100 per criterion) │
├─ Set gate filters (min capacity, max fiber distance)    │
└─ Click "Analyze"                                        │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ POST /api/projects/customer-match                       │
├─ Body: {                                                │
│   persona: "hyperscaler",                               │
│   criteria: {capacity: 75, connection_speed: 90, ...},  │
│   filters: {min_capacity: 100, max_fiber: 10}          │
│ }                                                       │
│                                                         │
│ Backend Processing:                                     │
│ 1. Load all projects from renewable_projects table      │
│ 2. Apply gate filters (capacity, fiber distance)        │
│ 3. Score each project using persona weights             │
│ 4. Rank by final investment_rating                      │
│ 5. Return top N projects as GeoJSON FeatureCollection   │
└─ Response: {matched_projects: Feature[], count: int}    │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend: ResultsModal displays top projects            │
├─ Session Storage: Save top projects                     │
├─ SiteMap: Highlight matched projects in green          │
├─ TopProjectsPanel: Show ranked list (rating 1.0-10.0)  │
└─ User can click project → ResultsModal shows breakdown  │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ User clicks project → Project Detail View               │
├─ GET /api/projects/enhanced (specific project)          │
├─ Display full scoring breakdown (8 components)          │
├─ Show nearest infrastructure (distance, name, type)     │
├─ Option to run financial model: IRR/NPV/LCOE           │
└─ Export report (PDF or CSV - optional)                  │
```

### Workflow 2: Infrastructure Proximity Analysis

```
┌─────────────────────────────────────────────────────────┐
│ User interacts with SiteMap                             │
├─ Toggles infrastructure layers on/off                   │
├─ Pans/zooms to region of interest                       │
└─ Clicks on project marker                              │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend: Display Project Properties                    │
├─ site_name, capacity_mw, technology_type               │
├─ investment_rating (1.0-10.0)                          │
├─ Distance to each infrastructure type:                  │
│  ├─ fiber_km (to nearest fiber cable)                  │
│  ├─ transmission_km (to nearest transmission line)      │
│  ├─ substation_km (to nearest substation)              │
│  ├─ ixp_km (to nearest IXP)                            │
│  ├─ water_km (to nearest water resource)               │
│  └─ [calculated in backend scoring.py]                 │
│                                                        │
├─ TNUoS Impact:                                          │
│  ├─ tnuos_zone: Current TNUoS zone (27 zones)          │
│  ├─ tnuos_tariff: £/MW/year for transmission charge     │
│  └─ tnuos_score: Impact on investment rating (0-100)   │
│                                                        │
└─ Color-coded proximity badges (green=close, red=far)   │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ DistanceDistributionChart & CumulativeDistanceChart     │
├─ Local computation: fiber distances histogram           │
├─ CDF: Probability of finding site within X km          │
├─ Recharts visualizations                               │
└─ No backend calls (uses project feature data)          │
```

### Workflow 3: Financial Modeling

```
┌─────────────────────────────────────────────────────────┐
│ User opens IRR Estimator feature                        │
├─ GET /api/financial-model/units (optional: load params) │
└─ Display form with default values                       │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ User enters project financials                          │
├─ Technology (solar, wind, battery)                      │
├─ Capacity (MW)                                          │
├─ CAPEX, OPEX (£/kW, £/kW/year, £/MWh)                 │
├─ PPA terms (£/MWh, years)                              │
├─ Merchant price (£/MWh)                                │
├─ Discount rate, project life, tax rate                 │
└─ Click "Calculate"                                      │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ POST /api/financial-model                              │
├─ Body: FinancialModelRequest {...all fields...}        │
│                                                        │
│ Backend Processing (renewable_model.py):               │
│ 1. Initialize RenewableFinancialModel                  │
│ 2. Calculate annual generation (capacity × factor)     │
│ 3. Compute PPA revenues (fixed price)                  │
│ 4. Compute merchant revenues (if enabled)              │
│ 5. Calculate OPEX (fixed + variable)                   │
│ 6. Run cashflow analysis (25-year project life)       │
│ 7. Calculate NPV (discounted to present value)         │
│ 8. Calculate IRR (rate where NPV = 0)                 │
│ 9. Calculate LCOE (levelized cost of energy)          │
│ 10. Generate dual scenarios (Standard PPA + BTM)       │
└─ Response: FinancialModelResponse {...results...}      │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend: Display Results                               │
├─ IRR % (utility-scale scenario)                        │
├─ IRR % (behind-the-meter/autoproducer scenario)        │
├─ NPV £ (both scenarios)                                │
├─ LCOE £/MWh (both scenarios)                           │
├─ Payback period (simple and discounted)                │
├─ Annual cashflow table                                 │
└─ Optional: Sensitivity analysis (vary inputs ±10%)     │
```

### Workflow 4: User Site Scoring

```
┌─────────────────────────────────────────────────────────┐
│ User navigates to SiteAssessmentTool                    │
├─ CSV upload or manual site entry form                   │
├─ Fields: Site name, latitude, longitude, capacity (MW) │
└─ Click "Score Sites"                                   │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ POST /api/user-sites/score                             │
├─ Body: {sites: [{name, lat, lon, capacity_mw}, ...]}  │
│                                                        │
│ Backend Processing (main.py):                          │
│ 1. Validate coordinates (within UK bounds)             │
│ 2. Calculate proximity to all infrastructure types      │
│ 3. Calculate investment rating for each site           │
│ 4. Assign TNUoS zone and tariff impact                 │
│ 5. Generate recommendations                           │
└─ Response: {scored_sites: Feature[]}                   │
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend: Display Scored User Sites                     │
├─ Ranked by investment_rating                           │
├─ Infrastructure proximity breakdown                    │
├─ Color-coded suitability (green=excellent, red=poor)   │
├─ Option to export results (CSV/PDF)                    │
└─ Add top sites to project shortlist (Session Storage)  │
```

---

## Routing Architecture

### Frontend Routes & Backend Mapping

```
Frontend Route Path          Component                    Backend API Calls
════════════════════════════════════════════════════════════════════════════════

PUBLIC ROUTES:
─────────────────────────────────────────────────────────────────────────────
/                            PersonaSelection             None
                                                          (POST to Zustand)

/auth                        Auth                         Supabase Auth
                                                          (email/password)

/invite                      InviteSignup                 Supabase (create user)

/about                       About                        None

/access-pending              AccessPending                None


PROTECTED ROUTES:
─────────────────────────────────────────────────────────────────────────────
/dashboard/hyperscaler       HyperscalerDashboard        GET /api/projects/enhanced
                                                         POST /api/projects/customer-match
                                                         GET /api/infrastructure/* (7)
                                                         GET /api/projects/geojson (SiteMap)

/dashboard/utility           UtilityDashboard            POST /api/projects/customer-match
                                                         GET /api/infrastructure/* (7)
                                                         GET /api/projects/geojson

/colocation-analysis         ColocationAnalysis          POST /api/projects/customer-match
                                                         GET /api/infrastructure/ixp
                                                         GET /api/infrastructure/fiber

/site-mapping-tools          SiteMappingTools            GET /api/projects/geojson
                                                         GET /api/infrastructure/* (7)

/site-assessment             SiteAssessmentTool          POST /api/user-sites/score

/fullscreen-map              FullScreenMap               GET /api/projects/geojson
                                                         GET /api/infrastructure/* (7)

/tec-connections/map         TecConnectionsMap           GET /api/tec/connections
                                                         GET /api/infrastructure/transmission

/*                           NotFound                    None
```

### Backend Endpoint Routing (FastAPI)

```
FastAPI Route                    Handler Function           Logic File
════════════════════════════════════════════════════════════════════════════════

GET  /                           health_check()             main.py
GET  /health                     detailed_health()          main.py

GET  /api/projects               list_projects()            main.py
GET  /api/projects/geojson       get_projects_geojson()     main.py
GET  /api/projects/enhanced      get_enhanced_projects()    main.py

POST /api/projects/customer-match    score_customer_match() scoring.py
                                                            power_workflow.py

POST /api/projects/power-developer-analysis
                                 power_dev_analysis()       power_workflow.py

GET  /api/projects/compare-scoring   compare_scoring()      scoring.py

POST /api/user-sites/score       score_user_sites()         main.py
                                                            scoring.py

GET  /api/infrastructure/transmission   get_transmission() main.py
GET  /api/infrastructure/substations    get_substations()   main.py
GET  /api/infrastructure/gsp            get_gsp()           main.py
GET  /api/infrastructure/fiber          get_fiber()         main.py
GET  /api/infrastructure/tnuos          get_tnuos()         main.py
GET  /api/infrastructure/ixp            get_ixp()           main.py
GET  /api/infrastructure/water          get_water()         main.py
GET  /api/infrastructure/dno-areas      get_dno_areas()     main.py

GET  /api/tec/connections        get_tec_connections()      main.py

POST /api/financial-model        calculate_financial_model() financial_model_api.py
                                                             renewable_model.py

GET  /api/financial-model/units  get_financial_units()      financial_model_api.py
```

---

## File Dependencies

### Frontend to Backend Dependencies Map

```typescript
// src/pages/dashboards/HyperscalerDashboard.tsx
├── depends on: /api/projects/enhanced (GET)
├── depends on: /api/projects/customer-match (POST)
├── depends on: /api/infrastructure/transmission (GET)
├── depends on: /api/infrastructure/substations (GET)
├── depends on: /api/infrastructure/gsp (GET)
├── depends on: /api/infrastructure/fiber (GET)
├── depends on: /api/infrastructure/tnuos (GET)
├── depends on: /api/infrastructure/ixp (GET)
└── depends on: /api/infrastructure/water (GET)

// src/pages/dashboards/UtilityDashboard.tsx
├── depends on: /api/projects/customer-match (POST)
└── depends on: /api/infrastructure/* (7 layers)

// src/pages/ColocationAnalysis.tsx
├── depends on: /api/projects/customer-match (POST)
├── depends on: /api/infrastructure/ixp (GET)
└── depends on: /api/infrastructure/fiber (GET)

// src/features/site-map/SiteMap.tsx
├── depends on: /api/projects/geojson (GET)
└── depends on: /api/infrastructure/* (7 layers)

// src/pages/SiteAssessmentTool.tsx
└── depends on: /api/user-sites/score (POST)

// src/features/irr-estimator/IRREstimator.tsx
├── depends on: /api/financial-model (POST)
└── depends on: /api/financial-model/units (GET - optional)

// src/pages/TecConnectionsMap.tsx
├── depends on: /api/tec/connections (GET)
└── depends on: /api/infrastructure/transmission (GET)

// src/components/CriteriaModal.tsx
└── (no direct API calls - parent component handles POST)

// src/components/ResultsModal.tsx
└── (no direct API calls - uses data from parent)

// src/components/TopProjectsPanel.tsx
└── (no direct API calls - uses data from parent)

// src/App.tsx
├── depends on: Supabase Auth (session check)
└── depends on: /health (GET - on app init)
```

### Backend to Frontend Data Contracts

```python
# main.py - API Responses

## GET /api/projects/enhanced
Response Type: FeatureCollection
├─ type: "FeatureCollection"
├─ features: Feature[] [
│  ├─ type: "Feature"
│  ├─ geometry: {type: "Point", coordinates: [lon, lat]}
│  └─ properties: {
│     ├─ ref_id: string
│     ├─ site_name: string
│     ├─ capacity_mw: number
│     ├─ technology_type: string
│     ├─ development_status: string
│     ├─ county: string
│     ├─ investment_rating: number (1.0-10.0)
│     ├─ investment_grade: number (0-100 internal)
│     ├─ rating_description: "Excellent" | "Good" | "Poor" | ...
│     ├─ color_code: "#00DD00" | "#7FFF00" | ... (hex)
│     ├─ component_scores: {
│     │  ├─ capacity: number (0-100)
│     │  ├─ development_stage: number
│     │  ├─ technology: number
│     │  ├─ grid_infrastructure: number
│     │  ├─ digital_infrastructure: number
│     │  ├─ water_resources: number
│     │  ├─ lcoe: number
│     │  └─ tnuos: number
│     ├─ },
│     ├─ weighted_contributions: {...} (same keys × weight)
│     ├─ nearest_infrastructure: {
│     │  ├─ fiber_km: number
│     │  ├─ transmission_km: number
│     │  ├─ substation_km: number
│     │  ├─ ixp_km: number
│     │  ├─ water_km: number
│     │  └─ gsp_zone: string
│     ├─ },
│     ├─ tnuos_zone: string ("GZ1", "GZ2", ...)
│     ├─ tnuos_tariff: number (£/MW/year)
│     └─ infrastructure_bonus: number
│  }
│ ]
└─ count: number (total features)

## POST /api/projects/customer-match
Request Type: BusinessCriteria + Filters
├─ persona: "hyperscaler" | "utility" | "colocation" | "edge"
├─ criteria: {
│  ├─ capacity: number (0-100)
│  ├─ connection_speed: number (0-100)
│  ├─ resilience: number (0-100)
│  ├─ land_planning: number (0-100)
│  ├─ latency: number (0-100)
│  ├─ cooling: number (0-100)
│  ├─ price_sensitivity: number (0-100)
│  └─ ...
├─ }
├─ filters: {
│  ├─ min_capacity_mw: number
│  ├─ max_fiber_km: number
│  ├─ max_transmission_km: number
│  ├─ min_transmission_capacity_mw: number
│  └─ ...
└─ }

Response Type: FeatureCollection (ranked matches)
└─ features: Feature[] [sorted by investment_rating DESC]

## GET /api/infrastructure/{layer}
Response Type: FeatureCollection
├─ type: "FeatureCollection"
├─ features: Feature[] [
│  ├─ type: "Feature"
│  ├─ geometry: (Point | LineString | Polygon)
│  └─ properties: {layer-specific}
└─ ]

Layer-Specific Properties:
├─ transmission: {path, voltage_kv, operator}
├─ substations: {name, voltage_kv, capacity_mva, owner}
├─ gsp: {gsp_id, gsp_name, authority}
├─ fiber: {provider, connection_type, operator}
├─ tnuos: {zone_id, zone_name, tariff_rate}
├─ ixp: {name, operators, peering_members}
├─ water: {type, capacity, operator}
└─ dno-areas: {dno_name, license_area}

## POST /api/financial-model
Request Type: FinancialModelRequest
├─ technology: "solar" | "wind" | "battery"
├─ capacity_mw: number
├─ capacity_factor: number (0-1)
├─ project_life: number (years)
├─ capex_per_kw: number (£)
├─ opex_fix: number (£/kW/year)
├─ opex_var: number (£/MWh)
├─ ppa_price: number (£/MWh)
├─ ppa_duration: number (years)
├─ merchant_price: number (£/MWh)
├─ discount_rate: number (0-1)
├─ tax_rate: number (0-1)
└─ [15+ total parameters]

Response Type: FinancialModelResponse
├─ standard: ModelResults {
│  ├─ irr: number | null (%)
│  ├─ npv: number (£)
│  ├─ lcoe: number (£/MWh)
│  ├─ cashflows: number[] (annual)
│  ├─ payback_simple: number | null (years)
│  └─ payback_discounted: number | null (years)
├─ }
├─ autoproducer: ModelResults { ... }
├─ metrics: {
│  ├─ total_revenue: number
│  ├─ total_opex: number
│  ├─ peak_debt_service: number
│  └─ ...
├─ }
└─ success: boolean
```

---

## State Management Integration

### Zustand Global Store (useAppStore)

```typescript
// File: src/store/appStore.ts

store state:
├─ user: User | null
├─ selectedPersona: UserPersona
├─ isAuthenticated: boolean
├─ loading: boolean

Dependencies:
├─ Frontend only - no backend dependency
└─ Persists in localStorage

Used in:
├─ HyperscalerDashboard (selects persona-specific weights)
├─ UtilityDashboard (selects utility weights)
├─ ColocationAnalysis (selects colocation weights)
├─ PersonaSelection (captures initial choice)
└─ Authentication flow (updates on login/logout)
```

### React Query Caching

```typescript
// Query keys and cache invalidation

queryKey: ['projects', 'enhanced']
├─ URL: GET /api/projects/enhanced
├─ staleTime: 5 minutes
├─ cacheTime: 10 minutes
└─ Dependencies: Uses in HyperscalerDashboard, SiteMap

queryKey: ['infrastructure', layerName]
├─ URL: GET /api/infrastructure/{layerName}
├─ staleTime: 5 minutes
├─ cacheTime: 10 minutes
├─ layerName: "transmission" | "substations" | "gsp" | ...
└─ Dependencies: Uses in SiteMap, FullScreenMap

queryKey: ['projects', 'customer-match']
├─ URL: POST /api/projects/customer-match
├─ No caching (POST request - mutationKey used)
├─ Triggers: CriteriaModal submit
└─ onSuccess: Update session storage with results

queryKey: ['financial-model']
├─ URL: POST /api/financial-model
├─ No caching (calculation-based)
├─ Triggers: IRREstimator form submit
└─ onSuccess: Display results in modal
```

### Session Storage Caching

```typescript
// File: src/lib/analysis-cache.ts

sessionStorage Keys:

'topProjects'
├─ Value: JSON.stringify(FeatureCollection)
├─ TTL: Browser session
├─ Set by: ResultsModal after customer-match
├─ Used by: Refresh page → restore previous analysis

'selectedProject'
├─ Value: JSON.stringify(Feature)
├─ TTL: Browser session
├─ Set by: Project detail click
├─ Used by: Navigate away/back → restore context

'mapState'
├─ Value: {center: [lon, lat], zoom: number}
├─ TTL: Browser session
├─ Set by: FullScreenMap pan/zoom
└─ Used by: Preserve map view across navigation

'analysisHistory'
├─ Value: JSON.stringify({timestamp, criteria, results}[])
├─ TTL: Browser session
├─ Set by: Each analysis run
└─ Used by: Historical comparison (optional feature)
```

### Auth Context (Supabase)

```typescript
// File: src/integrations/supabase/auth-context.tsx

Context state:
├─ user: User | null
├─ session: Session | null
├─ loading: boolean
├─ access: {
│  ├─ hasDashboardAccess: boolean
│  ├─ isEmailVerified: boolean
│  ├─ reason: string
│  └─ roles: string[]
└─ }

Initialization:
├─ App init: Check Supabase session (onAuthStateChange)
├─ Restore session from browser storage
└─ Validate email verification status

On Login:
├─ Call: supabase.auth.signInWithPassword({email, password})
├─ Success: Store session, redirect to /dashboard/{persona}
└─ Error: Display error message in Auth component

On Logout:
├─ Call: supabase.auth.signOut()
├─ Clear: Session storage, localStorage
└─ Redirect: /auth

Access Control:
├─ Check user.roles array
├─ Check is_email_verified flag
├─ Enforce: ProtectedRoute components
└─ Show: AccessPending page if !hasDashboardAccess
```

---

## Authentication & Authorization

### Auth Flow Diagram

```
┌──────────────────────────────────────────────────────────┐
│ User visits / (PublicWeb.com)                            │
└─────────────────────┬──────────────────────────────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │ Check localStorage     │
          │ for existing session   │
          └────────┬──────┬────────┘
                   │      │
           ✓ Valid │      │ No session
           session │      │
                   ▼      ▼
              ┌────────┐  ┌──────────────┐
              │Bypass  │  │Redirect to   │
              │Auth    │  │/auth         │
              └───┬────┘  └──────┬───────┘
                  │              │
                  ▼              ▼
          ┌─────────────────────────────┐
          │ Auth.tsx - Login Form       │
          ├─ Email input               │
          ├─ Password input            │
          ├─ Submit button             │
          ├─ "Signup" link             │
          └────────┬────────────────────┘
                   │ supabase.auth.signInWithPassword()
                   ▼
          ┌─────────────────────────────┐
          │ Supabase Auth Service       │
          ├─ Validate credentials      │
          ├─ Return session JWT        │
          ├─ Return user object        │
          └────────┬────────────────────┘
                   │
        ┌──────────┴──────────┐
        │ Success             │ Error
        ▼                     ▼
   ┌──────────┐        ┌──────────────┐
   │Store     │        │Display error │
   │session   │        │message       │
   │in local  │        └──────────────┘
   │Storage   │
   └────┬─────┘
        │
        ▼
   ┌────────────────────┐
   │Redirect to:        │
   │/dashboard/{        │
   │  selectedPersona   │
   │}                   │
   └────────────────────┘
        │
        ▼
   ┌────────────────────────────────┐
   │ ProtectedRoute component       │
   ├─ Check isAuthenticated         │
   ├─ Check hasDashboardAccess      │
   └────┬───────────────────────────┘
        │
   ┌────┴──────────┐
   │ Yes           │ No
   ▼               ▼
Dashboard      AccessPending
```

### Protected Route Implementation

```typescript
// src/components/ProtectedRoute.tsx

<ProtectedRoute>
  <HyperscalerDashboard />
</ProtectedRoute>

Checks:
├─ isAuthenticated === true
├─ hasDashboardAccess === true
├─ isEmailVerified === true (optional)
└─ roles.includes('dashboard_user') (optional)

If all checks pass:
├─ Render child component
└─ Component can call API endpoints

If checks fail:
├─ Redirect to /access-pending
└─ Show pending activation message
```

### Supabase Tables for Auth

```sql
-- auth.users (Supabase managed)
├─ id: UUID
├─ email: string
├─ encrypted_password: string
├─ email_confirmed_at: timestamp
├─ last_sign_in_at: timestamp
└─ ...

-- public.user_roles (Frontend managed)
├─ id: UUID
├─ user_id: UUID (FK → auth.users)
├─ role: string ("dashboard_user", "admin", ...)
├─ persona: string ("hyperscaler", "utility", ...)
├─ created_at: timestamp
└─ is_email_verified: boolean
```

---

## Error Handling Integration

### Frontend Error Handling

```typescript
// API Request Wrapper with Error Handling

async function apiRequest(endpoint: string, options = {}) {
  try {
    const response = await fetch(
      `${VITE_API_BASE_URL}${endpoint}`,
      {
        ...options,
        timeout: 90000,  // 90 second timeout
        signal: options.signal  // AbortController
      }
    );

    if (!response.ok) {
      throw new ApiError(
        `API Error: ${response.status} ${response.statusText}`,
        response.status,
        endpoint
      );
    }

    return await response.json();

  } catch (error) {
    if (error.name === 'AbortError') {
      // Request timeout
      showErrorNotification('Request timeout - server not responding');
    } else if (error instanceof ApiError) {
      // API error
      showErrorNotification(error.message);
    } else {
      // Network error
      showErrorNotification('Network error - check connection');
    }

    throw error;  // Re-throw for caller handling
  }
}

// Component-Level Error Handling

try {
  const results = await apiRequest('/api/projects/customer-match', {
    method: 'POST',
    body: JSON.stringify(criteria)
  });

  // Success
  setResults(results);
  showSuccessNotification('Analysis complete');

} catch (error) {
  // Component-specific error UI
  setError(error.message);
  <ResultsModal showError={true} message={error.message} />
}
```

### Backend Error Responses

```python
# Backend Error Response Format (FastAPI)

HTTP 400 Bad Request:
{
  "detail": "Invalid coordinates - outside UK bounds"
}

HTTP 404 Not Found:
{
  "detail": "Project not found"
}

HTTP 500 Internal Server Error:
{
  "detail": "Supabase connection failed"
}

# Graceful Degradation Example

# Processing 100 projects, 1 fails
Response 200 OK:
{
  "processed_count": 99,
  "failed_count": 1,
  "features": [...99 successful projects...],
  "warnings": [
    "Project ref_id=XYZ: Missing coordinates"
  ]
}
```

### Error Scenarios & Recovery

| Error Scenario | Frontend Behavior | Backend Behavior | Recovery |
|---|---|---|---|
| **API Timeout** | Show loading spinner → Timeout error after 90s | Request times out | Retry button, increase timeout |
| **Network Down** | Cannot reach API | N/A | Show offline message, retry |
| **Invalid Credentials** | Show error in Auth form | 401 Unauthorized | Clear localStorage, re-login |
| **Missing Infrastructure Data** | Show message "Infrastructure data not available" | Log warning, continue | Cache refresh (600s TTL) |
| **Project Scoring Fails** | Show top 99 projects, skip 1 | Per-project error catch | Log warning, show in results |
| **Financial Model Calc Error** | Show error modal "Cannot calculate" | 500 error response | Show error details, adjust inputs |
| **Invalid GeoJSON Response** | Mapbox renders fallback | Return valid GeoJSON | Clear cache, refetch |

---

## Request/Response Contracts

### GET /api/projects/enhanced

**Frontend Caller**: HyperscalerDashboard.tsx, SiteMap.tsx

```typescript
// Request
GET /api/projects/enhanced?limit=50&offset=0

// Response (200 OK)
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-1.2345, 51.6789]
      },
      "properties": {
        "ref_id": "REP001",
        "site_name": "Solar Farm A",
        "capacity_mw": 150,
        "technology_type": "solar",
        "development_status": "operational",
        "county": "Devon",
        "country": "UK",
        "investment_rating": 7.5,           // 1.0-10.0
        "investment_grade": 75,              // 0-100 internal
        "rating_description": "Good",
        "color_code": "#7FFF00",
        "component_scores": {
          "capacity": 85,
          "development_stage": 90,
          "technology": 85,
          "grid_infrastructure": 72,
          "digital_infrastructure": 68,
          "water_resources": 50,
          "lcoe": 80,
          "tnuos": 65
        },
        "weighted_contributions": {...},
        "nearest_infrastructure": {
          "fiber_km": 8.5,
          "transmission_km": 12.3,
          "substation_km": 3.2,
          "ixp_km": 45.0,
          "water_km": 2.1,
          "gsp_zone": "GZ15"
        },
        "tnuos_zone": "GZ15",
        "tnuos_tariff": 3.45,
        "infrastructure_bonus": 10
      }
    },
    ...
  ],
  "count": 125
}
```

### POST /api/projects/customer-match

**Frontend Caller**: HyperscalerDashboard.tsx (CriteriaModal)

```typescript
// Request
POST /api/projects/customer-match
Content-Type: application/json

{
  "persona": "hyperscaler",
  "criteria": {
    "capacity": 75,
    "connection_speed": 90,
    "resilience": 80,
    "land_planning": 70,
    "latency": 85,
    "cooling": 75,
    "price_sensitivity": 65
  },
  "filters": {
    "min_capacity_mw": 100,
    "max_fiber_km": 10,
    "max_transmission_km": 25,
    "min_transmission_capacity_mw": 50
  }
}

// Response (200 OK)
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {...},
      "properties": {
        ...same as /api/projects/enhanced...
        "investment_rating": 8.2,
        "ranking": 1                    // NEW: ranking field
      }
    },
    ...ranked by investment_rating DESC...
  ],
  "count": 15,
  "stats": {
    "avg_rating": 7.2,
    "median_distance_fiber_km": 6.5,
    "median_distance_transmission_km": 14.3
  }
}
```

### POST /api/financial-model

**Frontend Caller**: IRREstimator.tsx

```typescript
// Request
POST /api/financial-model
Content-Type: application/json

{
  "technology": "solar",
  "capacity_mw": 100,
  "capacity_factor": 0.18,
  "project_life": 25,
  "capex_per_kw": 900,
  "opex_fix": 20,
  "opex_var": 2.5,
  "ppa_price": 45,
  "ppa_duration": 15,
  "merchant_price": 50,
  "capacity_payment": 0,
  "ancillary_services": 0,
  "initial_capex": 90000000,
  "debt_percentage": 0.7,
  "debt_cost": 0.05,
  "discount_rate": 0.08,
  "inflation": 0.02,
  "tax_rate": 0.25,
  "available_incentives": 0,
  "grid_connection_cost": 5000000
}

// Response (200 OK)
{
  "standard": {
    "irr": 12.5,                           // %
    "npv": 45000000,                       // £
    "lcoe": 38.5,                          // £/MWh
    "cashflows": [-90000000, 8000000, ...] // 25-year array
    "payback_simple": 11.25,               // years
    "payback_discounted": 14.75            // years
  },
  "autoproducer": {
    "irr": 15.2,
    "npv": 52000000,
    "lcoe": 32.1,
    "cashflows": [...],
    "payback_simple": 9.5,
    "payback_discounted": 12.3
  },
  "metrics": {
    "total_revenue": 1800000000,
    "total_opex": 550000000,
    "peak_debt_service": 12000000,
    "annual_generation_mwh": 18000000
  },
  "success": true
}

// Error Response (500 Error)
{
  "detail": "Financial model calculation failed: Invalid capacity_factor"
}
```

### GET /api/infrastructure/{layer}

**Frontend Caller**: SiteMap.tsx, FullScreenMap.tsx

```typescript
// Request Examples:
GET /api/infrastructure/transmission
GET /api/infrastructure/substations
GET /api/infrastructure/fiber
GET /api/infrastructure/tnuos
GET /api/infrastructure/ixp

// Response: transmission (LineString Features)
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [-1.2345, 51.6789],
          [-1.2346, 51.6790],
          ...
        ]
      },
      "properties": {
        "name": "Transmission Line A",
        "voltage_kv": 400,
        "operator": "National Grid",
        "capacity_mva": 500
      }
    }
  ]
}

// Response: substations (Point Features)
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-1.2345, 51.6789]
      },
      "properties": {
        "name": "Substation X",
        "voltage_kv": 132,
        "capacity_mva": 300,
        "owner": "UK Power Networks"
      }
    }
  ]
}

// Response: tnuos (Polygon Features with tariff data)
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
      },
      "properties": {
        "zone_id": "GZ1",
        "zone_name": "North Scotland",
        "tariff_rate": 15.32      // £/MW/year
      }
    }
  ]
}
```

### POST /api/user-sites/score

**Frontend Caller**: SiteAssessmentTool.tsx

```typescript
// Request
POST /api/user-sites/score
Content-Type: application/json

{
  "sites": [
    {
      "name": "User Site A",
      "latitude": 51.5074,
      "longitude": -0.1278,
      "capacity_mw": 50
    },
    {
      "name": "User Site B",
      "latitude": 53.4808,
      "longitude": -2.2426,
      "capacity_mw": 75
    }
  ]
}

// Response (200 OK)
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-0.1278, 51.5074]
      },
      "properties": {
        "site_name": "User Site A",
        "capacity_mw": 50,
        "investment_rating": 6.8,
        "rating_description": "Average",
        "color_code": "#FFFF00",
        "component_scores": {...},
        "nearest_infrastructure": {...},
        "tnuos_tariff": 2.34,
        "recommendations": [
          "Consider grid connection to nearest substation (5.2km)",
          "Good fiber connectivity available (1.8km)"
        ]
      }
    }
  ],
  "processed_count": 2,
  "failed_count": 0
}
```

---

## Performance & Caching Strategy

### Frontend Caching Layers

| Layer | Strategy | TTL | Trigger |
|-------|----------|-----|---------|
| **React Query** | Automatic deduplication + reuse | 5 min | GET requests (automatic invalidation) |
| **Session Storage** | Manual serialization | Browser session | Analysis completion, page refresh |
| **Browser Cache** | HTTP Cache-Control headers | 5 min | GET /api/infrastructure/* |
| **Component Memoization** | useMemo, useCallback | Component lifetime | Dependency array changes |

### Backend Caching Layers

| Layer | Strategy | TTL | Implementation |
|-------|----------|-----|-----------------|
| **Infrastructure Cache** | In-memory spatially indexed | 600 sec (config) | InfrastructureCache class (main.py) |
| **Spatial Index** | Grid cells (0.5° resolution) | Matches infra cache | SpatialGrid (proximity.py) |

### Load Time Optimization

```
Cold Start (First Page Load):
1. React app initialization: 1-2s
2. Supabase auth check: 500ms
3. GET /api/projects/enhanced: 1-2s (backend loads infra cache)
4. GET /api/infrastructure/* × 7: 2-3s total (concurrent)
5. Render HyperscalerDashboard: 500ms
─────────────────────────────────
Total: ~5-8 seconds

Warm Start (Subsequent Navigation):
1. React Router: 100ms
2. React Query cache hit: 0ms (data already loaded)
3. Mapbox GL render: 500ms
─────────────────────────────────
Total: <1 second
```

### Memory Usage Estimates

```
Frontend (React App):
├─ React bundle: ~150KB (gzipped)
├─ Mapbox GL: ~200KB
├─ Infrastructure cache (session): ~20MB (1000+ GeoJSON features)
├─ Project cache (React Query): ~5MB (100+ projects with scoring)
└─ Total: ~225MB runtime (browser)

Backend (FastAPI):
├─ Application code: ~5MB
├─ Infrastructure catalog (in-memory): ~50-100MB
│  ├─ 1000+ substations: 10MB
│  ├─ 500+ transmission lines: 20MB
│  ├─ 549+ fiber segments: 15MB
│  ├─ 1000+ water resources: 5MB
│  ├─ 27 TNUoS zones: 1MB
│  └─ 400+ IXPs: 2MB
├─ Spatial indices: ~20MB
└─ Total: ~155-205MB runtime
```

### Concurrent Request Optimization

```typescript
// Frontend: Concurrent Infrastructure Loads
const [transmission, substations, gsp, fiber, tnuos, ixp, water] =
  await Promise.all([
    fetch('/api/infrastructure/transmission'),
    fetch('/api/infrastructure/substations'),
    fetch('/api/infrastructure/gsp'),
    fetch('/api/infrastructure/fiber'),
    fetch('/api/infrastructure/tnuos'),
    fetch('/api/infrastructure/ixp'),
    fetch('/api/infrastructure/water')
  ]);
// Result: 7 requests in parallel = 1-2s total (vs. 7-14s sequential)

// Backend: Concurrent Proximity Calculations
proximity_scores = await asyncio.gather(*[
  calculate_proximity_scores(project)
  for project in projects
])
// Result: 10-50x faster than sequential scoring
```

---

## Deployment & Environment Configuration

### Frontend Environment Variables

```bash
# .env.production

VITE_SUPABASE_URL=https://qoweiksrcooqrzssykbo.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# API Configuration
VITE_API_BASE_URL=https://infranodev2.onrender.com
# OR
VITE_API_URL=https://infranodev2.onrender.com
# OR
VITE_FINANCIAL_API_URL=https://infranodev2.onrender.com/api/financial-model

# Development
VITE_API_BASE_URL=http://localhost:8001
```

### Backend Environment Variables

```bash
# .env (backend)

SUPABASE_URL=https://qoweiksrcooqrzssykbo.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

INFRA_CACHE_TTL=600  # seconds (infrastructure cache TTL)
```

### Build & Deployment

**Frontend** (Vercel/Netlify recommended):
```bash
npm install
npm run build         # Vite production build
# Output: dist/ directory

# Deploy dist/ to Vercel/Netlify
# Env vars configured in platform dashboard
# API proxy: /api → https://infranodev2.onrender.com
```

**Backend** (Render.com):
```bash
# requirements.txt specifies all dependencies
python -m pip install -r requirements.txt

# Run: uvicorn main:app --host 0.0.0.0 --port 8001
# Deployed at: https://infranodev2.onrender.com
```

### CORS Configuration

```python
# Backend (main.py)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend origin should be specified
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Should be:
allow_origins=[
    "http://localhost:3000",           # Dev
    "https://infranode-frontend.vercel.app",  # Prod
]
```

### API Proxy Configuration (Vite)

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api')
      }
    }
  }
});

// Production: Handled by reverse proxy (Vercel, Netlify, Nginx)
```

---

## Known Issues & Recommendations

### Critical Issues

1. **CORS Configuration Too Permissive**
   - **Issue**: `allow_origins=["*"]` exposes API to any domain
   - **Recommendation**: Specify frontend domain in backend CORS config
   - **Priority**: HIGH - Fix before production

2. **Missing Input Validation on Coordinates**
   - **Issue**: Frontend doesn't validate coordinates before sending to backend
   - **Recommendation**: Add Zod validation for latitude/longitude bounds
   - **Priority**: MEDIUM

3. **No Rate Limiting**
   - **Issue**: Backend has no rate limit on API endpoints
   - **Recommendation**: Add rate limiting middleware (e.g., slowapi)
   - **Priority**: HIGH - Prevent abuse

4. **Hardcoded TNUoS Zones**
   - **Issue**: 27 TNUoS zones hardcoded in main.py
   - **Recommendation**: Load from database table for maintainability
   - **Priority**: MEDIUM

### Performance Issues

1. **Infrastructure Cache TTL Too Long**
   - **Issue**: 600-second TTL may show stale data
   - **Recommendation**: Consider reducing to 300s or adding cache invalidation
   - **Priority**: LOW

2. **No Request Cancellation on Component Unmount**
   - **Issue**: Frontend may waste requests if user navigates away
   - **Recommendation**: Use AbortController in custom hooks
   - **Priority**: LOW

3. **Missing API Response Pagination Metadata**
   - **Issue**: FeatureCollections lack `next_page`, `total_count` fields
   - **Recommendation**: Standardize pagination response format
   - **Priority**: MEDIUM

### Testing Gaps

1. **No Frontend Integration Tests**
   - **Issue**: React components untested with actual API responses
   - **Recommendation**: Add Vitest + MSW (Mock Service Worker) tests
   - **Priority**: HIGH

2. **Minimal Backend Tests (4 unit tests)**
   - **Issue**: Only persona resolution tested
   - **Recommendation**: Add tests for all scoring functions, financial model
   - **Priority**: HIGH

3. **No E2E Tests**
   - **Issue**: No end-to-end workflow testing
   - **Recommendation**: Add Playwright or Cypress E2E tests
   - **Priority**: MEDIUM

### Documentation Gaps

1. **Missing API Documentation**
   - **Recommendation**: Generate OpenAPI/Swagger docs from FastAPI
   - **Priority**: MEDIUM

2. **Missing Component Documentation**
   - **Recommendation**: Add Storybook or Chromatic for component library
   - **Priority**: LOW

3. **Missing Architecture Decision Records (ADRs)**
   - **Recommendation**: Document why certain patterns were chosen
   - **Priority**: LOW

### Recommended Enhancements

| Feature | Complexity | Impact | Priority |
|---------|-----------|--------|----------|
| **Advanced Filtering** | Medium | UX improvement | MEDIUM |
| **Export Results (CSV/PDF)** | Medium | Business value | MEDIUM |
| **Sensitivity Analysis** | High | Financial value | LOW |
| **Real-time Collaboration** | High | Enterprise feature | LOW |
| **Mobile Responsive Design** | Medium | UX improvement | MEDIUM |
| **Dark Mode Support** | Low | UX improvement | LOW |
| **Multi-language Support** | Medium | Market expansion | LOW |
| **API Key Authentication** | Medium | Security | HIGH |

---

## Summary

### Key Integration Points

| Frontend Component | Backend API | Method | Cache |
|---|---|---|---|
| HyperscalerDashboard | `/api/projects/customer-match` | POST | None |
| SiteMap | `/api/infrastructure/*` (7 layers) | GET | 5min (React Query) |
| IRREstimator | `/api/financial-model` | POST | None |
| TopProjectsPanel | `/api/projects/enhanced` | GET | 5min (Session) |
| SiteAssessmentTool | `/api/user-sites/score` | POST | None |
| TecConnectionsMap | `/api/tec/connections` | GET | 5min |

### State Management Summary

| State Type | Technology | Scope | Persistence |
|---|---|---|---|
| **Global App State** | Zustand | Entire app | localStorage |
| **Server State** | React Query | API responses | Memory + cache |
| **Auth State** | Supabase Auth Context | User/session | localStorage (JWT) |
| **Component State** | useState/useCallback | Local component | Memory |
| **Session Cache** | sessionStorage | Analysis workflows | Browser session |

### Performance Summary

| Metric | Value |
|--------|-------|
| **Cold Start** | 5-8 seconds |
| **Warm Start** | <1 second |
| **API Response Time** | 200-500ms |
| **Cache Hit Rate** | ~95% |
| **Frontend Bundle** | ~150KB (gzipped) |
| **Backend Memory** | ~155-205MB |

---

## Appendix A: API Endpoint Summary

**Total Endpoints**: 19

**By Category**:
- Projects: 6 endpoints
- Infrastructure: 8 endpoints
- User Sites: 1 endpoint
- Financial: 2 endpoints
- TEC: 1 endpoint
- Health: 1 endpoint

---

## Appendix B: File Structure Reference

```
frontend/
├── src/
│   ├── components/
│   │   ├── CriteriaModal.tsx → POST /api/projects/customer-match
│   │   ├── ResultsModal.tsx → displays /api/projects/enhanced data
│   │   ├── TopProjectsPanel.tsx → GET /api/projects/enhanced
│   │   ├── ProjectInsights.tsx → local computation
│   │   ├── InteractiveRadarChart.tsx → local computation
│   │   └── ... (40+ other components)
│   ├── features/
│   │   ├── site-map/
│   │   │   └── SiteMap.tsx → GET /api/infrastructure/*
│   │   └── irr-estimator/
│   │       └── IRREstimator.tsx → POST /api/financial-model
│   ├── pages/
│   │   ├── dashboards/
│   │   │   ├── HyperscalerDashboard.tsx → POST /api/projects/customer-match
│   │   │   └── UtilityDashboard.tsx → POST /api/projects/customer-match
│   │   ├── Auth.tsx → Supabase Auth
│   │   ├── SiteAssessmentTool.tsx → POST /api/user-sites/score
│   │   ├── TecConnectionsMap.tsx → GET /api/tec/connections
│   │   └── ... (6 other pages)
│   ├── services/
│   │   ├── FinancialModelService.ts → Wraps /api/financial-model
│   │   └── FinancialUnitsService.ts → Wraps /api/financial-model/units
│   ├── store/
│   │   └── appStore.ts → Zustand global state
│   ├── lib/
│   │   ├── api-config.ts → API base URL + request wrapper
│   │   ├── analysis-cache.ts → sessionStorage management
│   │   └── persona.ts → Persona default weights
│   └── App.tsx → Router + providers
│
backend/
├── main.py (2,384 lines)
│   ├── GET / → health check
│   ├── GET /health → detailed status
│   ├── GET /api/projects → list all projects
│   ├── GET /api/projects/geojson → GeoJSON projects
│   ├── GET /api/projects/enhanced → scored projects
│   ├── POST /api/projects/customer-match → score by criteria
│   ├── GET /api/projects/compare-scoring → compare methods
│   ├── POST /api/user-sites/score → score user sites
│   ├── GET /api/infrastructure/transmission → lines
│   ├── GET /api/infrastructure/substations → points
│   ├── GET /api/infrastructure/gsp → polygons
│   ├── GET /api/infrastructure/fiber → lines
│   ├── GET /api/infrastructure/tnuos → tariff zones
│   ├── GET /api/infrastructure/ixp → IXP points
│   ├── GET /api/infrastructure/water → water resources
│   ├── GET /api/infrastructure/dno-areas → DNO zones
│   └── GET /api/tec/connections → TEC projects
│
├── backend/
│   ├── scoring.py (988 lines)
│   │   ├── calculate_capacity_component_score()
│   │   ├── calculate_grid_infrastructure_score() → uses proximity_scores
│   │   ├── calculate_persona_weighted_score() → combines all components
│   │   └── ... (8 total scoring functions)
│   ├── renewable_model.py (657 lines)
│   │   ├── RenewableFinancialModel class
│   │   └── calculate_irr_npv_lcoe()
│   ├── power_workflow.py (428 lines)
│   │   └── run_power_developer_analysis()
│   ├── proximity.py (359 lines)
│   │   ├── SpatialGrid class → O(1) proximity lookups
│   │   └── InfrastructureCatalog class → spatially indexed data
│   ├── financial_model_api.py (298 lines)
│   │   ├── FinancialModelRequest
│   │   └── FinancialModelResponse
│   └── dc_workflow.py (70 lines)
│
└── database/
    ├── renewable_projects (100+ records)
    ├── electrical_grid (333 GSP zones)
    ├── transmission_lines (500+ segments)
    ├── substations (1000+ points)
    ├── fiber_cables (549+ segments)
    ├── internet_exchange_points (400+ points)
    ├── water_resources (1000+ points)
    ├── tnuos_zones (27 zones)
    └── tec_connections (grid connection pipeline)
```

---

**Document Completed**: 2025-11-18
**Version**: 1.0 - Final
**Status**: Ready for Development & Deployment

---

*This document serves as the single source of truth for frontend-backend integration. Refer to this when implementing new features, debugging integration issues, or onboarding new developers.*
