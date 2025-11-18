# INFRANODEV2 - Frontend-Backend Integration Guide
**Date:** 2025-11-18
**Version:** 1.0
**Status:** Production Integration Documentation

---

## Table of Contents
1. [Frontend Architecture Overview](#frontend-architecture-overview)
2. [Frontend File Structure](#frontend-file-structure)
3. [API Integration Layer](#api-integration-layer)
4. [REST API Endpoints Reference](#rest-api-endpoints-reference)
5. [Request/Response Models](#requestresponse-models)
6. [Data Flow Patterns](#data-flow-patterns)
7. [Frontend Dependencies](#frontend-dependencies)
8. [Routing & Navigation](#routing--navigation)
9. [Component-Backend Mapping](#component-backend-mapping)
10. [Error Handling & Status Codes](#error-handling--status-codes)
11. [State Management](#state-management)
12. [Performance Considerations](#performance-considerations)
13. [Development Workflow](#development-workflow)
14. [Deployment Integration](#deployment-integration)

---

## Frontend Architecture Overview

The Infranodev2 frontend is a **React 18 + TypeScript** single-page application that integrates with a FastAPI backend (main.py) for renewable energy and data center infrastructure assessment.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              React SPA (frontend/)                          │
│  ├─ Components (React 18 + TypeScript)                     │
│  ├─ State Management (React Hooks)                         │
│  ├─ Styling (Tailwind CSS)                                 │
│  └─ Maps (Mapbox GL JS)                                    │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST/JSON
                     │ CORS-enabled (all origins)
                     │ Base URL: /api/
┌────────────────────▼────────────────────────────────────────┐
│           FastAPI Backend (main.py)                         │
│  ├─ 19 REST Endpoints                                       │
│  ├─ Business Logic (scoring.py, renewable_model.py)        │
│  ├─ Spatial Algorithms (proximity.py)                       │
│  └─ Financial Modeling (financial_model_api.py)            │
└────────────────────┬────────────────────────────────────────┘
                     │ PostGIS Queries / SQL
                     │ REST API via httpx
┌────────────────────▼────────────────────────────────────────┐
│       Supabase PostgreSQL + PostGIS                         │
│  ├─ renewable_projects                                      │
│  ├─ electrical_grid / transmission_lines / substations      │
│  ├─ fiber_cables / internet_exchange_points                │
│  ├─ water_resources / tnuos_zones / tec_connections        │
└─────────────────────────────────────────────────────────────┘
```

---

## Frontend File Structure

### Current React Implementation

```
frontend/
└── src/
    └── components/
        └── criteriamodal.tsx          # Modal component for capacity criteria input
```

### Expected Frontend Organization (Recommended)

```
frontend/
├── src/
│   ├── components/                    # Reusable UI components
│   │   ├── criteriamodal.tsx         # Capacity criteria modal
│   │   ├── MapView.tsx               # Mapbox GL map container
│   │   ├── ProjectCard.tsx           # Individual project display
│   │   ├── ScoringPanel.tsx          # Scoring results panel
│   │   ├── FinancialChart.tsx        # IRR/NPV visualization
│   │   ├── InfrastructureOverlay.tsx # Layer control for maps
│   │   └── ...
│   │
│   ├── pages/                         # Page-level components
│   │   ├── Dashboard.tsx              # Main landing/dashboard
│   │   ├── ProjectAnalysis.tsx        # Detailed project view
│   │   ├── SiteAssessment.tsx         # User site scoring
│   │   ├── FinancialModeling.tsx      # Financial analysis
│   │   └── ...
│   │
│   ├── services/                      # API integration layer
│   │   ├── api.ts                    # REST client (main export)
│   │   ├── endpoints.ts              # Endpoint definitions
│   │   ├── types.ts                  # TypeScript interfaces
│   │   └── ...
│   │
│   ├── hooks/                         # Custom React hooks
│   │   ├── useProjects.ts            # Project fetching hook
│   │   ├── useInfrastructure.ts      # Infrastructure data hook
│   │   ├── useFinancialModel.ts      # Financial calculation hook
│   │   └── ...
│   │
│   ├── context/                       # React Context for state
│   │   ├── MapContext.tsx            # Map state
│   │   ├── FilterContext.tsx         # Filter selections
│   │   └── ...
│   │
│   ├── utils/                         # Utility functions
│   │   ├── geojson.ts               # GeoJSON helpers
│   │   ├── formatting.ts            # Data formatting
│   │   ├── scoring.ts               # Score calculations
│   │   └── ...
│   │
│   ├── types/                         # Global type definitions
│   │   ├── api.ts                    # API response types
│   │   ├── domain.ts                 # Business domain types
│   │   └── ...
│   │
│   ├── App.tsx                        # Root component
│   ├── index.tsx                      # Entry point
│   └── styles/                        # Global CSS
│       └── globals.css
│
├── public/                            # Static assets
├── package.json                       # Node dependencies
├── tsconfig.json                      # TypeScript config
├── vite.config.ts or craco.config.js # Build config
└── .env                               # Frontend environment variables
```

---

## API Integration Layer

### Base Configuration

**Base URL:** `/api/` (relative to deployment domain)

**Full URL Example:**
```
https://infranodev2.onrender.com/api/projects
```

### HTTP Client Setup

```typescript
// services/api.ts
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

export class ApiClient {
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(`${API_BASE_URL}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, String(value));
      });
    }
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    return response.json();
  }

  async post<T>(endpoint: string, body: any): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    return response.json();
  }
}

export const apiClient = new ApiClient();
```

### CORS Configuration

**Backend CORS Settings (main.py):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # All origins allowed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Frontend Environment:**
```bash
# .env (frontend)
REACT_APP_API_URL=http://localhost:8001/api    # Development
REACT_APP_API_URL=https://infranodev2.onrender.com/api  # Production
```

---

## REST API Endpoints Reference

### 1. Health & Status

#### GET `/health`
Returns backend service status and infrastructure metrics.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "infrastructure_metrics": {
    "projects_count": 150,
    "transmission_lines": 1200,
    "substations": 500,
    "fiber_segments": 549
  }
}
```

**Frontend Usage:**
```typescript
const checkBackendHealth = async () => {
  const health = await apiClient.get('/health');
  setBackendAvailable(health.status === 'healthy');
};
```

---

### 2. Project Data Endpoints

#### GET `/projects`
Retrieve all renewable energy projects in database.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 100 | Max results to return |
| `offset` | integer | 0 | Pagination offset |
| `technology` | string | - | Filter by technology type |

**Response:**
```json
{
  "projects": [
    {
      "ref_id": "REF001",
      "site_name": "Windfield Alpha",
      "operator": "GreenPower Ltd",
      "technology_type": "wind",
      "capacity_mw": 50.0,
      "development_status": "operational",
      "coordinates": [51.5074, -0.1278],
      "created_at": "2024-01-15"
    }
  ],
  "total": 150,
  "page": 0
}
```

**Frontend Hook:**
```typescript
function useProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get('/projects?limit=100')
      .then(data => setProjects(data.projects))
      .catch(err => console.error('Failed to fetch projects:', err))
      .finally(() => setLoading(false));
  }, []);

  return { projects, loading };
}
```

---

#### GET `/projects/geojson`
Retrieve projects as GeoJSON FeatureCollection for map visualization.

**Response:**
```json
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
        "ref_id": "REF001",
        "site_name": "Windfield Alpha",
        "capacity_mw": 50.0,
        "technology_type": "wind"
      }
    }
  ]
}
```

**Frontend Usage (Mapbox GL):**
```typescript
function MapView() {
  const [projects, setProjects] = useState(null);

  useEffect(() => {
    apiClient.get('/projects/geojson').then(setProjects);
  }, []);

  useEffect(() => {
    if (map && projects) {
      map.addSource('projects', {
        type: 'geojson',
        data: projects
      });
      map.addLayer({
        id: 'projects-layer',
        type: 'circle',
        source: 'projects',
        paint: {
          'circle-radius': 6,
          'circle-color': '#00B4D8'
        }
      });
    }
  }, [map, projects]);

  return <div id="map" />;
}
```

---

#### GET `/projects/enhanced`
Retrieve projects with persona-specific scoring (data center personas).

**Query Parameters:**
| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `persona` | string | - | Yes | `hyperscaler`, `colocation`, or `edge_computing` |

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {...},
      "properties": {
        "ref_id": "REF001",
        "site_name": "Windfield Alpha",
        "capacity_mw": 50.0,
        "scores": {
          "overall_score": 7.5,
          "capacity_score": 8.2,
          "development_stage_score": 6.9,
          "technology_score": 7.8,
          "grid_infrastructure_score": 7.0,
          "digital_infrastructure_score": 6.5,
          "water_resources_score": 7.2,
          "tnuos_transmission_costs_score": 6.8,
          "lcoe_resource_quality_score": 8.1
        },
        "rating": "High Potential"
      }
    }
  ]
}
```

**Frontend Integration:**
```typescript
const fetchEnhancedProjects = async (persona: 'hyperscaler' | 'colocation' | 'edge_computing') => {
  const data = await apiClient.get(`/projects/enhanced?persona=${persona}`);
  updateMapWithScores(data);
};
```

---

#### GET `/projects/compare-scoring`
Compare scoring algorithms (TOPSIS vs weighted approach).

**Response:**
```json
{
  "algorithms": {
    "topsis": {
      "method": "Multi-criteria Decision Making",
      "weights_normalized": {...}
    },
    "weighted": {
      "method": "Component-weighted summation",
      "weights_normalized": {...}
    }
  },
  "comparison": [
    {
      "ref_id": "REF001",
      "topsis_score": 7.4,
      "weighted_score": 7.5,
      "rank_diff": 0
    }
  ]
}
```

---

#### GET `/projects/customer-match`
Find projects matching power developer criteria (customer matching).

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `persona` | string | `greenfield`, `repower`, `stranded` |
| `technology` | string | `solar`, `wind`, `battery`, etc. |

**Response:**
```json
{
  "matches": [
    {
      "ref_id": "REF001",
      "site_name": "Windfield Alpha",
      "match_score": 8.7,
      "match_reason": "Perfect grid capacity match",
      "coordinates": [51.5074, -0.1278]
    }
  ],
  "total_matches": 12
}
```

---

#### POST `/user-sites/score`
Score a user-supplied site for renewable or data center viability.

**Request Body:**
```typescript
interface UserSiteRequest {
  coordinates: {
    latitude: number;
    longitude: number;
  };
  capacity_mw: number;
  technology_type: 'solar' | 'wind' | 'battery' | 'hybrid';
  development_status: string;
  persona_type: 'hyperscaler' | 'colocation' | 'edge_computing' | 'greenfield' | 'repower';
}
```

**Request Example:**
```json
{
  "coordinates": {
    "latitude": 51.5074,
    "longitude": -0.1278
  },
  "capacity_mw": 100.0,
  "technology_type": "wind",
  "development_status": "planning",
  "persona_type": "hyperscaler"
}
```

**Response:**
```json
{
  "site_id": "USER_SITE_001",
  "overall_score": 7.8,
  "component_scores": {
    "capacity_score": 8.5,
    "development_stage_score": 7.2,
    ...
  },
  "proximity_data": {
    "nearest_transmission_line_km": 2.1,
    "nearest_substation_km": 1.5,
    "fiber_coverage_present": true,
    "water_sources_within_5km": 3
  },
  "rating": "High Potential",
  "color": "#2ECC71"
}
```

**Frontend Modal Integration:**
```typescript
function UserSiteAssessment() {
  const [location, setLocation] = useState(null);
  const [capacity, setCapacity] = useState(100);
  const [score, setScore] = useState(null);

  const scoreUserSite = async () => {
    const result = await apiClient.post('/user-sites/score', {
      coordinates: location,
      capacity_mw: capacity,
      technology_type: 'wind',
      persona_type: 'hyperscaler'
    });
    setScore(result);
  };

  return (
    <>
      <CriteriaModal
        onLocation={setLocation}
        onCapacity={setCapacity}
        onSubmit={scoreUserSite}
      />
      {score && <ScoringResults score={score} />}
    </>
  );
}
```

---

### 3. Power Developer Endpoints

#### POST `/projects/power-developer-analysis`
Analyze projects for power developer personas (greenfield, repower, stranded).

**Request Body:**
```typescript
interface PowerDeveloperRequest {
  persona: 'greenfield' | 'repower' | 'stranded';
  coordinates?: [number, number];  // Optional: [lat, lon]
  technology_type?: string;
  capacity_mw?: number;
}
```

**Response:**
```json
{
  "persona": "greenfield",
  "analysis": {
    "suitable_projects": 45,
    "high_potential_count": 12,
    "average_score": 7.2,
    "top_opportunities": [
      {
        "ref_id": "REF001",
        "site_name": "Windfield Alpha",
        "score": 8.7,
        "reason": "Strong grid capacity and development stage"
      }
    ]
  }
}
```

---

#### GET `/projects/customer-match`
(Alternative to POST for simpler queries - see above)

---

### 4. Infrastructure Visualization Endpoints

All infrastructure endpoints return **GeoJSON FeatureCollections** optimized for Mapbox GL.

#### GET `/infrastructure/transmission`
Transmission lines network (high-voltage power distribution).

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[lon1, lat1], [lon2, lat2], ...]
      },
      "properties": {
        "line_id": "TX001",
        "voltage_kv": 275,
        "operator": "National Grid"
      }
    }
  ]
}
```

**Frontend Layer Config:**
```typescript
function addTransmissionLayer(map) {
  map.addSource('transmission', {
    type: 'geojson',
    data: '/api/infrastructure/transmission'
  });
  map.addLayer({
    id: 'transmission-layer',
    type: 'line',
    source: 'transmission',
    paint: {
      'line-color': '#8B0000',
      'line-width': 3
    }
  });
}
```

---

#### GET `/infrastructure/substations`
Electrical substations with capacity data.

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [lon, lat]
      },
      "properties": {
        "substation_id": "SUB001",
        "name": "London East Substation",
        "capacity_mva": 500
      }
    }
  ]
}
```

---

#### GET `/infrastructure/gsp`
Grid Supply Points (GSP) - primary distribution points.

**Response:** GeoJSON FeatureCollection (polygons)

---

#### GET `/infrastructure/fiber`
Fiber cable networks for telecommunications.

**Response:** GeoJSON FeatureCollection (LineStrings)

---

#### GET `/infrastructure/tnuos`
TNUoS (Transmission Network Use of System) charging zones.

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {...},
      "properties": {
        "zone_id": "ZONE_E",
        "zone_name": "East England",
        "tariff_rate_£_mwh": 12.50
      }
    }
  ]
}
```

**Frontend Implementation:**
```typescript
function addTNUoSLayer(map, selectedZone) {
  map.addSource('tnuos', {
    type: 'geojson',
    data: '/api/infrastructure/tnuos'
  });
  map.addLayer({
    id: 'tnuos-layer',
    type: 'fill',
    source: 'tnuos',
    paint: {
      'fill-color': '#FFA500',
      'fill-opacity': 0.3
    }
  });
}
```

---

#### GET `/infrastructure/ixp`
Internet Exchange Points (IXPs) - data center connectivity hubs.

**Response:** GeoJSON FeatureCollection (Points)

---

#### GET `/infrastructure/water`
Water resources for cooling and operations.

**Response:** GeoJSON FeatureCollection (Points and LineStrings)

---

#### GET `/infrastructure/dno-areas`
Distribution Network Operator areas.

**Response:** GeoJSON FeatureCollection (Polygons)

---

### 5. Financial Modeling Endpoint

#### POST `/financial-model`
Calculate comprehensive financial metrics for renewable projects.

**Request Body:**
```typescript
interface FinancialModelRequest {
  technology_type: 'SOLAR_PV' | 'WIND' | 'BATTERY' | 'SOLAR_BATTERY' | 'WIND_BATTERY';
  project_type: 'UTILITY_SCALE' | 'BEHIND_THE_METER';
  market_region: 'UK' | 'IRELAND';
  capacity_mw: number;
  capex_£_per_kw: number;
  opex_annual_£_per_kw: number;

  // Market pricing assumptions
  ppa_price_£_mwh: number;
  merchant_price_£_mwh: number;
  capacity_market_payment_£_mwh: number;
  ancillary_services_£_mwh: number;

  // BTM specific
  retail_electricity_price_£_kwh?: number;

  // Financial assumptions
  discount_rate: number;  // 0.05 for 5%
  analysis_period_years: number;  // typically 25
  inflation_rate: number;
  tax_rate: number;
}
```

**Request Example:**
```json
{
  "technology_type": "SOLAR_PV",
  "project_type": "UTILITY_SCALE",
  "market_region": "UK",
  "capacity_mw": 50,
  "capex_£_per_kw": 1500,
  "opex_annual_£_per_kw": 12,
  "ppa_price_£_mwh": 45,
  "merchant_price_£_mwh": 52,
  "capacity_market_payment_£_mwh": 8,
  "ancillary_services_£_mwh": 2,
  "discount_rate": 0.08,
  "analysis_period_years": 25,
  "inflation_rate": 0.02,
  "tax_rate": 0.19
}
```

**Response:**
```json
{
  "project_summary": {
    "technology": "SOLAR_PV",
    "capacity_mw": 50,
    "project_type": "UTILITY_SCALE"
  },
  "financial_metrics": {
    "irr": 0.0987,  // 9.87%
    "npv_£m": 12.5,
    "lcoe_£_mwh": 38.2,
    "payback_period_years": 8.3,
    "pv_of_costs_£m": 75.0,
    "pv_of_revenues_£m": 87.5
  },
  "annual_cashflow_summary": {
    "year_1": -75.0,  // Initial capex
    "year_2": 3.5,
    "year_3": 3.6,
    ...
    "year_25": 3.2
  },
  "revenue_breakdown": {
    "ppa_revenue_£m": 60.0,
    "merchant_revenue_£m": 15.2,
    "capacity_market_£m": 8.5,
    "ancillary_services_£m": 3.8
  }
}
```

**Frontend Financial Analysis Component:**
```typescript
function FinancialModeling() {
  const [params, setParams] = useState<FinancialModelRequest>({...});
  const [results, setResults] = useState(null);

  const calculateModel = async () => {
    const result = await apiClient.post('/financial-model', params);
    setResults(result);
  };

  return (
    <>
      <FinancialInputForm onChange={setParams} />
      <button onClick={calculateModel}>Calculate</button>
      {results && (
        <>
          <MetricsDisplay metrics={results.financial_metrics} />
          <CashflowChart data={results.annual_cashflow_summary} />
          <RevenueBreakdown data={results.revenue_breakdown} />
        </>
      )}
    </>
  );
}
```

---

### 6. TEC Integration Endpoint

#### GET `/api/tec/connections`
Transmission Entry Capacity connections (grid connection applications).

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [lon, lat]
      },
      "properties": {
        "project_name": "Solar Farm North",
        "operator": "GreenPower Ltd",
        "capacity_mw": 50,
        "status": "approved",
        "voltage_level": 132,
        "application_date": "2023-01-15"
      }
    }
  ]
}
```

---

## Request/Response Models

### Standard Error Response

All endpoints return error responses in this format:

```json
{
  "detail": "Descriptive error message",
  "status_code": 400
}
```

**Common HTTP Status Codes:**

| Code | Meaning | Frontend Action |
|------|---------|-----------------|
| 200 | Success | Process response normally |
| 201 | Created | Confirm creation success |
| 400 | Bad Request | Show validation error to user |
| 404 | Not Found | Show "No results found" message |
| 500 | Server Error | Show "Backend unavailable" message |
| 503 | Service Unavailable | Show maintenance message |

### Pydantic Validation

The backend validates all requests with Pydantic models. Invalid requests return:

```json
{
  "detail": [
    {
      "loc": ["body", "capacity_mw"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

---

## Data Flow Patterns

### 1. Basic GET Request Flow

```
User Action (e.g., "Load Projects")
           ↓
React Component
           ↓
useEffect() Hook triggers
           ↓
apiClient.get('/projects')
           ↓
HTTP GET Request
           ↓
main.py Route Handler
           ↓
Database Query (Supabase)
           ↓
JSON Response
           ↓
React State Update (setState)
           ↓
Component Re-render with Data
           ↓
Map Update / UI Display
```

### 2. Map-Based Workflow

```
User Interacts with Map
           ↓
Click on Project / Marker
           ↓
Get Feature ID
           ↓
Fetch Enhanced Scoring Data
           ↓
POST /user-sites/score
           ↓
Display Scoring Modal
           ↓
Highlight on Map
```

### 3. Financial Modeling Workflow

```
User Fills Financial Form
           ↓
Input Validation (Frontend)
           ↓
POST /financial-model
           ↓
Backend Calculates Cashflows
           ↓
Return IRR, NPV, LCOE
           ↓
Display Charts & Metrics
           ↓
Allow Export/Comparison
```

### 4. Infrastructure Layer Workflow

```
Map Initialization
           ↓
Load Base Layers (Projects)
           ↓
User Toggles Infrastructure Layer
           ↓
Fetch GeoJSON (e.g., /infrastructure/transmission)
           ↓
Add Source & Layer to Mapbox
           ↓
User Interacts with Features
           ↓
Display Properties Popup
```

---

## Frontend Dependencies

### Core React Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.0.0"
  }
}
```

### UI & Styling

```json
{
  "dependencies": {
    "tailwindcss": "^3.3.0",
    "shadcn/ui": "^0.5.0"
  }
}
```

### Mapping & Geospatial

```json
{
  "dependencies": {
    "mapbox-gl": "^2.15.0"
  }
}
```

### Data & State Management

```json
{
  "dependencies": {
    "axios": "^1.4.0"  // Alternative to fetch
  }
}
```

### Development Dependencies

```json
{
  "devDependencies": {
    "vite": "^4.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "tailwindcss": "^3.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

### Dependency Graph

```
App.tsx
├── pages/
│   ├── Dashboard.tsx
│   │   ├── MapView.tsx
│   │   │   └── mapbox-gl
│   │   ├── ProjectList.tsx
│   │   │   └── useProjects() hook
│   │   └── FilterPanel.tsx
│   │       └── useFilters() hook
│   │
│   ├── ProjectAnalysis.tsx
│   │   ├── ProjectCard.tsx
│   │   └── ScoringPanel.tsx
│   │
│   └── FinancialModeling.tsx
│       ├── FinancialForm.tsx
│       ├── FinancialChart.tsx
│       └── useFinancialModel() hook
│
├── services/
│   └── api.ts (fetch client)
│
├── utils/
│   ├── geojson.ts
│   └── formatting.ts
│
└── styles/
    └── globals.css (Tailwind)
```

---

## Routing & Navigation

### URL Structure

```
/                           # Home/Dashboard
/projects                   # All projects
/projects/:id              # Project detail
/sites                     # User site assessment
/financial                 # Financial modeling
/analysis                  # Advanced analysis
/about                     # About/Help
```

### React Router Implementation

```typescript
// App.tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<ProjectList />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/sites" element={<UserSiteAssessment />} />
        <Route path="/financial" element={<FinancialModeling />} />
        <Route path="/analysis" element={<AdvancedAnalysis />} />
      </Routes>
    </Router>
  );
}
```

### Link Integration

```typescript
// Navigation between pages
import { Link } from 'react-router-dom';

<Link to={`/projects/${projectId}`}>View Details</Link>
<Link to="/financial">Financial Modeling</Link>
```

---

## Component-Backend Mapping

### Component Dependencies Table

| Component | API Endpoint(s) | HTTP Method | Data Updated |
|-----------|-----------------|------------|--------------|
| `MapView` | `/projects/geojson`, `/infrastructure/*` | GET | Map layers & features |
| `ProjectList` | `/projects` | GET | Project cards & list |
| `ProjectCard` | `/projects/enhanced` | GET | Scores & ratings |
| `CriteriaModal` | `/user-sites/score` | POST | User site scoring |
| `ScoringPanel` | `/projects/compare-scoring` | GET | Algorithm comparison |
| `FinancialChart` | `/financial-model` | POST | Financial metrics |
| `InfrastructureOverlay` | `/infrastructure/*` (all) | GET | Layer visibility |
| `FilterPanel` | `/projects` | GET | Filter options |

---

## Error Handling & Status Codes

### Frontend Error Strategy

```typescript
// services/api.ts
export class ApiClient {
  async get<T>(endpoint: string): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`);

      if (!response.ok) {
        const error = await response.json();
        throw new ApiError(
          error.detail || 'Unknown error',
          response.status
        );
      }
      return response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        // Handle API errors
        console.error(`API Error ${error.statusCode}: ${error.message}`);
      } else {
        // Handle network errors
        console.error('Network error:', error);
      }
      throw error;
    }
  }
}

class ApiError extends Error {
  constructor(public message: string, public statusCode: number) {
    super(message);
  }
}
```

### User-Facing Error Messages

```typescript
function ProjectList() {
  const [error, setError] = useState(null);

  const loadProjects = async () => {
    try {
      const data = await apiClient.get('/projects');
      setProjects(data.projects);
    } catch (err) {
      if (err instanceof ApiError) {
        switch (err.statusCode) {
          case 400:
            setError('Invalid request. Please check your inputs.');
            break;
          case 404:
            setError('Projects not found.');
            break;
          case 500:
          case 503:
            setError('Backend service unavailable. Please try again later.');
            break;
          default:
            setError('An unexpected error occurred.');
        }
      }
    }
  };

  return (
    <>
      {error && <ErrorAlert message={error} />}
      {/* ... rest of component */}
    </>
  );
}
```

---

## State Management

### React Hooks Pattern (Recommended)

```typescript
// hooks/useProjects.ts
import { useState, useEffect } from 'react';
import { apiClient } from '../services/api';

interface Project {
  ref_id: string;
  site_name: string;
  capacity_mw: number;
  // ...
}

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get('/projects');
        setProjects(response.projects);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch');
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  return { projects, loading, error };
}

// Usage in component
function ProjectList() {
  const { projects, loading, error } = useProjects();

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;

  return (
    <div>
      {projects.map(p => (
        <ProjectCard key={p.ref_id} project={p} />
      ))}
    </div>
  );
}
```

### Context for Global State

```typescript
// context/MapContext.tsx
import { createContext, useState, ReactNode } from 'react';

interface MapState {
  selectedProject: string | null;
  visibleLayers: Set<string>;
  filterPersona: string;
}

export const MapContext = createContext<{
  state: MapState;
  setState: (state: MapState) => void;
}>(null!);

export function MapProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<MapState>({
    selectedProject: null,
    visibleLayers: new Set(['projects']),
    filterPersona: 'hyperscaler'
  });

  return (
    <MapContext.Provider value={{ state, setState }}>
      {children}
    </MapContext.Provider>
  );
}

// Usage
function MapView() {
  const { state, setState } = useContext(MapContext);

  const toggleLayer = (layerId: string) => {
    const newLayers = new Set(state.visibleLayers);
    if (newLayers.has(layerId)) {
      newLayers.delete(layerId);
    } else {
      newLayers.add(layerId);
    }
    setState({ ...state, visibleLayers: newLayers });
  };
}
```

---

## Performance Considerations

### 1. Data Fetching Optimization

```typescript
// Implement caching
const cache = new Map<string, { data: any; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

async function getCachedData(endpoint: string) {
  const cached = cache.get(endpoint);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }

  const data = await apiClient.get(endpoint);
  cache.set(endpoint, { data, timestamp: Date.now() });
  return data;
}
```

### 2. Lazy Loading

```typescript
// Lazy load heavy components
import { lazy, Suspense } from 'react';

const FinancialModeling = lazy(() => import('./pages/FinancialModeling'));
const AdvancedAnalysis = lazy(() => import('./pages/AdvancedAnalysis'));

function App() {
  return (
    <Routes>
      <Route
        path="/financial"
        element={
          <Suspense fallback={<Loading />}>
            <FinancialModeling />
          </Suspense>
        }
      />
    </Routes>
  );
}
```

### 3. Map Layer Optimization

```typescript
// Only render visible features
function MapView() {
  const [visibleLayers, setVisibleLayers] = useState(new Set(['projects']));

  useEffect(() => {
    if (visibleLayers.has('transmission')) {
      fetchAndAddLayer('transmission');
    }
  }, [visibleLayers]);

  // Only fetch when toggled, not on mount
}
```

### 4. Batch Requests

```typescript
// Fetch multiple data sources in parallel
async function loadDashboard() {
  const [projects, infrastructure, health] = await Promise.all([
    apiClient.get('/projects'),
    apiClient.get('/infrastructure/transmission'),
    apiClient.get('/health')
  ]);
  // Process all data at once
}
```

---

## Development Workflow

### Local Development Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd infranodev2

# 2. Install dependencies
npm install

# 3. Create .env for frontend
echo "REACT_APP_API_URL=http://localhost:8001/api" > frontend/.env

# 4. Start backend (separate terminal)
cd backend
python start_backend.py  # Runs on localhost:8001

# 5. Start frontend (separate terminal)
cd frontend
npm run dev  # Runs on localhost:3000 (Vite) or 5173
```

### API Testing

```bash
# Test endpoints with curl
curl http://localhost:8001/health
curl http://localhost:8001/api/projects
curl -X POST http://localhost:8001/api/user-sites/score \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Frontend Development Best Practices

1. **Component Structure**
   - Keep components small (<300 lines)
   - One responsibility per component
   - Extract logic to hooks

2. **Type Safety**
   - Always use TypeScript interfaces
   - Define API response types

3. **Error Handling**
   - Wrap API calls in try/catch
   - Show user-friendly messages
   - Log errors for debugging

4. **Performance**
   - Use React.memo for expensive components
   - Implement debouncing for search/filter
   - Profile with React DevTools

---

## Deployment Integration

### Frontend Deployment (Render.com)

```yaml
# render.yaml or build configuration
env:
  - name: REACT_APP_API_URL
    value: https://infranodev2.onrender.com/api
```

### Build & Deploy

```bash
# Build for production
npm run build

# This creates an optimized bundle in frontend/dist/
# Render automatically serves this as static files
```

### CORS & Deployment

Frontend deployed at: `https://infranodev2.onrender.com`
Backend deployed at: `https://infranodev2.onrender.com/api`

Both served from same origin, so no CORS issues in production.

### Environment Variables

```bash
# .env (development)
REACT_APP_API_URL=http://localhost:8001/api

# Render deployment (automatic)
REACT_APP_API_URL=https://infranodev2.onrender.com/api
```

---

## Summary: Frontend-Backend Contract

### Key Integration Points

| Aspect | Frontend | Backend |
|--------|----------|---------|
| **API Base URL** | `/api/` | FastAPI routes |
| **Data Format** | JSON | Pydantic models |
| **Authentication** | None (public) | CORS enabled |
| **Error Handling** | Try/catch + user alerts | Pydantic validation |
| **Spatial Data** | Mapbox GL + GeoJSON | PostGIS + GeoJSON |
| **Financial Calc** | Form input | Python models |
| **Caching** | React state + local cache | Backend TTL (600s) |

### Critical Files for Integration

**Frontend:**
- `frontend/src/services/api.ts` - API client implementation
- `frontend/src/components/MapView.tsx` - Map integration
- `frontend/src/pages/*.tsx` - Feature pages

**Backend:**
- `main.py` - API endpoint definitions
- `backend/scoring.py` - Scoring algorithms
- `backend/proximity.py` - Spatial queries
- `backend/renewable_model.py` - Financial calculations

---

**Document Version:** 1.0
**Last Updated:** 2025-11-18
**Prepared for:** Frontend Development Team
**Author:** Infranodev2 Architecture Review
