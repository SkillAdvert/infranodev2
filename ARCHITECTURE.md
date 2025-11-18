# INFRANODEV2 - Comprehensive Codebase Architecture Analysis

## Executive Summary

**Infranodev2** is a full-stack renewable energy and data center infrastructure assessment platform built with Python FastAPI backend and React TypeScript frontend. The system uses Supabase PostgreSQL with PostGIS extensions for spatial data, deployed on Render.com.

**Project Purpose:** Interactive web application enabling renewable energy investors and data center developers to assess site viability through AI-powered infrastructure scoring, combining project databases with real-time infrastructure analysis.

**Current Status:** Production-ready backend (version 2.1.0), React frontend with TypeScript components, deployed at https://infranodev2.onrender.com

---

## 1. DIRECTORY STRUCTURE AND ORGANIZATION

```
infranodev2/
├── backend/                          # Backend services and algorithms
│   ├── dc_workflow.py               # Data center workflow orchestration
│   ├── financial_model_api.py        # Financial modeling REST API wrapper
│   ├── power_workflow.py             # Renewable power developer workflows
│   ├── proximity.py                  # Spatial indexing and proximity calculations
│   ├── renewable_model.py            # Financial modeling engine for renewables
│   ├── scoring.py                    # Core scoring algorithms (988 lines)
│   ├── requirements.txt              # Backend dependencies
│   └── tests/
│       └── test_power_developer_persona.py  # Power developer persona tests
│
├── frontend/                         # React TypeScript frontend
│   └── src/
│       └── components/
│           └── criteriamodal.tsx     # Modal for capacity criteria input
│
├── main.py                           # Primary FastAPI application (2384 lines)
├── start_backend.py                  # Backend startup script
├── requirements.txt                  # Root dependencies
├── runtime.txt                       # Python version specification (3.11.9)
├── .env                              # Environment variables (Supabase credentials)
│
├── Data Ingestion Scripts:
├── fetch_network_data.py             # Telecom infrastructure data fetching
├── fetch_tnuos_data.py               # TNUoS transmission zones fetching
├── fetch_fiber_data                  # Fiber cable network data
├── import_projects.py                # Renewable projects CSV importer
│
├── Data Files:
├── tnuosgenzones_geojs.geojson       # TNUoS transmission zones (46KB GeoJSON)
│
├── Documentation:
├── claude.md                         # Comprehensive architectural documentation (38KB)
├── AGENTS.md                         # Development guidelines and standards
│
└── Git Repository (.git/)

Total Files: 12 Python files, 1 TypeScript file, 5 Script files, 3 Config files, 2 Docs
Total Size: ~400KB (excluding .git)
```

---

## 2. MAIN APPLICATION FILES AND THEIR PURPOSES

### Core Application Files

#### `main.py` (2,384 lines) - PRIMARY API GATEWAY
**Role:** Main FastAPI application serving all REST endpoints
**Key Responsibilities:**
- FastAPI setup with CORS middleware
- 19 API endpoint definitions (GET/POST)
- Persona-based project scoring orchestration
- Infrastructure data serving
- Financial model calculations
- User site scoring and analysis

**Key Features:**
- Supabase PostgreSQL integration
- Hard-coded TNUoS zones (27 UK transmission zones)
- Batch processing optimization (10-50x faster)
- Proximity score caching with TTL
- Infrastructure catalog loading and indexing
- Financial model wrapper for renewable projects

#### `backend/scoring.py` (988 lines) - SCORING ENGINE
**Role:** Core algorithms for infrastructure scoring
**Contains:**
- Persona definitions (hyperscaler, colocation, edge_computing)
- Component scoring functions (capacity, development stage, technology, grid, digital, water, TNUoS, LCOE)
- Weighted scoring calculations
- TOPSIS (multi-criteria decision) algorithm
- Color coding and rating descriptions
- Utility functions for score normalization

**Key Functions:**
```python
- calculate_capacity_component_score()
- calculate_development_stage_score()
- calculate_persona_weighted_score()
- calculate_persona_topsis_score()
- build_persona_component_scores()
- get_color_from_score()
- get_rating_description()
```

#### `backend/proximity.py` (359 lines) - SPATIAL INDEXING
**Role:** Geospatial algorithms and spatial indexing
**Provides:**
- Lightweight spatial grid indexing for proximity lookups
- Point and line feature dataclasses (PointFeature, LineFeature)
- InfrastructureCatalog aggregation
- SpatialGrid class for efficient proximity queries
- Batch proximity scoring for multiple projects

**Key Components:**
- `SpatialGrid`: O(1) lookup spatial index using grid cells
- `PointFeature`: Point-based infrastructure (substations, IXPs, water)
- `LineFeature`: Line-based infrastructure (transmission, fiber, water)
- `InfrastructureCatalog`: Unified infrastructure repository

#### `backend/power_workflow.py` (428 lines) - RENEWABLE POWER ANALYSIS
**Role:** Workflow orchestration for renewable energy projects
**Personas Supported:**
- greenfield (new development)
- repower (existing site upgrades)
- stranded (limited grid access)

**Key Capabilities:**
- Power developer persona normalization
- Coordinate extraction from various formats
- Investment scoring for power projects
- TEC (Transmission Entry Capacity) data transformation
- Power developer analysis orchestration

#### `backend/renewable_model.py` (657 lines) - FINANCIAL MODELING ENGINE
**Role:** Professional-grade financial modeling for renewable projects
**Supports:**
- Technologies: Solar PV, Wind, Battery, Hybrid systems
- Markets: Utility-scale and Behind-the-Meter
- Regions: UK and Ireland
- Revenue streams: PPA, capacity market, ancillary services, grid savings
- Comprehensive financial metrics: IRR, NPV, LCOE, payback periods

**Key Classes:**
```python
- TechnologyType enum (SOLAR_PV, WIND, BATTERY, SOLAR_BATTERY, WIND_BATTERY)
- ProjectType enum (UTILITY_SCALE, BEHIND_THE_METER)
- MarketRegion enum (UK, IRELAND)
- TechnologyParams: Capacity, CAPEX, OPEX, degradation, battery specs
- MarketPrices: Energy prices, PPA terms, capacity payments, ancillary services
- FinancialAssumptions: Discount rate, inflation, tax
- RenewableFinancialModel: Main calculation engine
```

#### `backend/financial_model_api.py` (298 lines) - FINANCIAL API WRAPPER
**Role:** FastAPI wrapper for financial model calculations
**Exposes:**
- `/api/financial-model` POST endpoint
- Request/response Pydantic models
- Utility-scale and Behind-the-Meter analysis
- Revenue breakdown calculations
- Metrics aggregation

#### `backend/dc_workflow.py` (70 lines) - DATA CENTER ORCHESTRATION
**Role:** Data center workflow entry points
**Delegates:**
- All scoring logic to scoring.py
- Maintains backward compatibility
- Re-exports scoring functions for DC consumers

### Supporting Scripts

#### `fetch_network_data.py` (9.3 KB)
**Purpose:** ETL script for telecom infrastructure
**Fetches:**
- Fiber cable networks from OpenStreetMap
- Internet exchange points (IXPs)
- UK Power Networks substations and transmission lines
**API:** UK Power Networks OpenData Soft API

#### `fetch_tnuos_data.py` (6.2 KB)
**Purpose:** TNUoS (Transmission Network Use of System) zone data
**Fetches:** Transmission charging zones with tariff rates
**Source:** External power system data feeds
**Output:** Geographic boundaries and cost data

#### `import_projects.py` (2.3 KB)
**Purpose:** CSV data import for renewable projects
**Process:**
- Parses "Project List.csv" with OSGB coordinates
- Converts OSGB grid to WGS84 lat/lon
- Batch uploads to Supabase (100-project batches)
- ~100+ renewable projects imported

#### `start_backend.py` (879 bytes)
**Purpose:** Local development server launcher
**Function:** Starts uvicorn FastAPI server on localhost:8001 with hot-reload

---

## 3. FILE TYPES AND THEIR LOCATIONS

### Python Files (12 total)
```
Backend Core (6 files, 3.2KB):
  - main.py (91KB) - Primary API application
  - backend/scoring.py (32KB) - Scoring algorithms
  - backend/power_workflow.py (15KB) - Power workflows
  - backend/proximity.py (11KB) - Spatial algorithms
  - backend/renewable_model.py (28KB) - Financial modeling
  - backend/financial_model_api.py (10KB) - API wrapper

Backend Support (2 files, 70 bytes):
  - backend/dc_workflow.py (2.2KB) - DC orchestration
  - backend/tests/test_power_developer_persona.py (1.5KB) - Unit tests

Data Processing (4 files, ~22KB):
  - fetch_network_data.py (9.3KB) - Network data ingestion
  - fetch_tnuos_data.py (6.2KB) - TNUoS data fetching
  - import_projects.py (2.3KB) - CSV project import
  - start_backend.py (879 bytes) - Development launcher
```

### TypeScript/React Files (1 total)
```
Frontend:
  - frontend/src/components/criteriamodal.tsx (2.3KB) - Modal component
```

### Configuration Files
```
YAML/Text:
  - runtime.txt (14 bytes) - Python version specification
  - .env (281 bytes) - Environment variables (Supabase credentials)
  - requirements.txt (224 bytes) - Root dependencies
  - backend/requirements.txt (189 bytes) - Backend dependencies

Markdown:
  - AGENTS.md (4.7KB) - Development guidelines
  - claude.md (38KB) - Architectural documentation
```

### Data Files
```
GeoJSON:
  - tnuosgenzones_geojs.geojson (46KB) - TNUoS zone boundaries

CSV (External):
  - Project List.csv (not in repo) - Renewable projects source data
```

---

## 4. KEY ENTRY POINTS AND MAIN MODULES

### Application Entry Point
**`main.py`** - Primary FastAPI application
```python
if __name__ == "__main__":
    # Run with: python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### FastAPI Application Initialization
```python
app = FastAPI(title="Infranodal API", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```

### Core Module Imports Chain
```
main.py
├── backend.power_workflow (power developer personas, analysis)
├── backend.scoring (scoring algorithms, 8-component framework)
├── backend.proximity (spatial indexing, proximity calculations)
├── backend.renewable_model (financial modeling engine)
└── Supabase PostgreSQL client (via httpx async client)
```

### Database Connection
- **Type:** Supabase PostgreSQL with PostGIS
- **Connection:** SUPABASE_URL + SUPABASE_ANON_KEY from .env
- **Query Method:** Async httpx client to REST API

### Deployment Entry
**Render.com** - https://infranodev2.onrender.com
- Uses `main.py` as ASGI entry point
- Python 3.11.9 runtime (from runtime.txt)
- Dependencies from requirements.txt

---

## 5. API ENDPOINTS AND REST INTERFACE

### Root & Health Endpoints
```
GET  /                           - Root info endpoint
GET  /health                     - Health check with infrastructure metrics
```

### Project Data Endpoints
```
GET  /api/projects                       - List all renewable projects
GET  /api/projects/geojson              - GeoJSON format projects
GET  /api/projects/enhanced             - Enhanced scoring with persona weighting
GET  /api/projects/compare-scoring      - Algorithm comparison view
GET  /api/projects/customer-match       - Power developer customer matching
POST /api/user-sites/score              - Score user-supplied sites
```

### Power Developer Endpoints
```
POST /api/projects/power-developer-analysis  - Analyze for power developers
GET  /api/projects/customer-match            - Find matching projects for power devs
```

### Infrastructure Visualization Endpoints
```
GET  /api/infrastructure/transmission   - Transmission lines (GeoJSON)
GET  /api/infrastructure/substations    - Electrical substations (GeoJSON)
GET  /api/infrastructure/gsp            - Grid Supply Points (GeoJSON)
GET  /api/infrastructure/fiber          - Fiber cables (GeoJSON)
GET  /api/infrastructure/tnuos          - TNUoS charging zones (GeoJSON)
GET  /api/infrastructure/ixp            - Internet exchange points (GeoJSON)
GET  /api/infrastructure/water          - Water resources (GeoJSON)
GET  /api/infrastructure/dno-areas      - Distribution network operator areas
```

### Financial Modeling Endpoint
```
POST /api/financial-model  - Calculate renewable project financial metrics
     Input: Technology, capacity, costs, revenue assumptions
     Output: IRR, NPV, cashflows, LCOE, payback periods (utility & BTM)
```

### TEC Integration Endpoint
```
GET  /api/tec/connections  - Transmission Entry Capacity connections
     Output: GeoJSON FeatureCollection of pending/approved grid connections
```

---

## 6. DATABASE/STORAGE FILES

### Supabase PostgreSQL Tables

**Core Project Data:**
- `renewable_projects` - 100+ UK renewable energy projects
  - Fields: ref_id, site_name, operator, technology_type, capacity_mw, development_status, coordinates
  
- `electrical_grid` - GSP (Grid Supply Point) boundaries (333 features)
  - PostGIS geometry for spatial queries

**Infrastructure Assets:**
- `transmission_lines` - High-voltage transmission network
- `substations` - Electrical substations with capacity data
- `fiber_cables` - Telecommunications fiber networks (549+ segments)
- `internet_exchange_points` - Data center connectivity hubs
- `water_resources` - Water sources for cooling/operations

**Transmission & Charging:**
- `tnuos_zones` - 27 UK transmission charging zones
  - Fields: zone_id, name, tariff_rate_£/MWh, geographic_bounds

**Grid Connections (TEC):**
- `tec_connections` - Transmission Entry Capacity applications
  - Fields: project_name, operator, capacity_mw, status, coordinates, voltage

### Local Data Files

**Hardcoded Spatial Data:**
- `tnuosgenzones_geojs.geojson` (46KB) - All 27 TNUoS zones with GeoJSON geometry

**Caching:**
- Infrastructure catalog cached in memory with TTL (configurable, default 600s)
- Cache key: INFRA_CACHE_TTL environment variable

---

## 7. CONFIGURATION FILES AND THEIR PURPOSES

### `.env` (Environment Variables)
```
SUPABASE_URL=https://qoweiksrcooqrzssykbo.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...  # JWT token for Supabase API access
INFRA_CACHE_TTL=600            # Infrastructure cache lifetime (seconds)
```

### `requirements.txt` (Root Level)
**Dependencies:**
```
fastapi==0.104.1               # Web framework
uvicorn[standard]==0.24.0      # ASGI server
httpx==0.25.2                  # Async HTTP client
python-dotenv==1.0.0           # Environment variable loading
numpy==1.24.3                  # Numerical computing
pandas==2.0.3                  # Data manipulation
```

### `backend/requirements.txt`
**Additional Backend Dependencies:**
```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0                # Data validation
numpy==1.24.3
pandas==2.0.3
python-multipart==0.0.6        # Form data parsing
```

### `runtime.txt`
```
python-3.11.9                  # Python version for Render.com deployment
```

### `.gitignore` (Not Shown)
- Typically excludes: __pycache__, *.pyc, venv/, .env (credentials)

---

## 8. DOCUMENTATION FILES

### `claude.md` (38 KB) - COMPREHENSIVE ARCHITECTURE DOCUMENTATION
**Contains:**
- Project overview and mission statement
- Current architecture status (December 2024)
- Backend framework stack (FastAPI, Supabase, Render.com)
- Frontend technology (React 18, TypeScript, Tailwind, Mapbox)
- Database schema overview
- Persona-based investment scoring algorithm (v2.3)
- 8-component scoring framework
- Persona weighting matrices
- Investment rating scale (1.0-10.0)
- Implementation status checklist
- Development state and known issues
- Immediate next steps and priorities
- API response format specifications
- Component architecture breakdown
- Technical decision rationale

### `AGENTS.md` (4.7 KB) - DEVELOPMENT GUIDELINES
**Contains:**
- Repository overview and scope
- Collaboration workflow (gather context, plan deliberately, focused diffs)
- Development tooling standards
  - Python dependency management
  - Node package management (npm only)
  - Testing requirements (pytest, linting)
  - Frontend build procedures
- Coding standards
  - Python: 3.9+, type hints, Pydantic models, FastAPI patterns
  - Data/ETL: idempotent scripts, config via args/env vars
  - Frontend: functional components, TypeScript, utility composition
- Documentation expectations
- Git & PR process requirements

---

## 9. ARCHITECTURAL PATTERNS OBSERVED

### 1. **Layered Architecture**
```
┌─────────────────────────────────┐
│   FastAPI REST API Layer        │  main.py (19 endpoints)
├─────────────────────────────────┤
│   Business Logic Layer          │  backend/ modules
│  ├─ Scoring Engine              │  scoring.py (988 lines)
│  ├─ Workflows                   │  power_workflow.py, dc_workflow.py
│  ├─ Proximity/Spatial           │  proximity.py
│  └─ Financial Modeling          │  renewable_model.py
├─────────────────────────────────┤
│   Data Access Layer             │  Supabase PostgreSQL
│                                 │  + PostGIS extensions
└─────────────────────────────────┘
```

### 2. **Multi-Persona Scoring Framework**
**Data Center Personas:**
- Hyperscaler (large-scale capacity)
- Colocation (reliability, connectivity)
- Edge Computing (latency, deployment speed)

**Power Developer Personas:**
- Greenfield (new development)
- Repower (upgrades)
- Stranded (limited grid access)

**Scoring Components (8-part framework):**
1. Capacity Score - Project size suitability
2. Development Stage Score - Deployment readiness
3. Technology Score - Technology appropriateness
4. Grid Infrastructure Score - Power infrastructure proximity
5. Digital Infrastructure Score - Fiber/IXP connectivity
6. Water Resources Score - Cooling availability
7. TNUoS Transmission Costs Score - Annual transmission charges
8. LCOE Resource Quality Score - Generation cost efficiency

### 3. **Spatial Indexing Pattern**
```python
SpatialGrid Class:
- Grid cell index (0.5° default cell size)
- O(1) point lookup via 2D index
- Bounding box queries for line features
- Efficient batch proximity scoring

InfrastructureCatalog:
- Unified repository of 6 infrastructure types
- Pre-indexed with SpatialGrid instances
- Stateless design for easy caching/invalidation
```

### 4. **Asynchronous Processing**
```python
- Async/await for I/O-bound Supabase queries
- Batch processing optimization (10-50x improvement)
- Infrastructure cache with TTL-based invalidation
- Progressive data loading for frontend
```

### 5. **Financial Modeling Pattern**
```python
RenewableFinancialModel:
┌─────────────────────────┐
│ Technology Params       │ (capacity, costs, degradation)
│ Market Prices          │ (PPA, merchant, capacity payments)
│ Financial Assumptions  │ (discount rate, tax, inflation)
└─────────────────────────┘
         │
         ▼
   Cashflow Projection (year-by-year)
         │
         ▼
   Financial Metrics (IRR, NPV, LCOE, payback)
```

### 6. **Stateless REST Design**
- No server-side sessions
- All scoring computed on-demand
- Infrastructure cache managed independently
- Client-side state management in React

### 7. **GeoJSON StandardCompliance**
- All spatial endpoints return RFC 7946 GeoJSON
- FeatureCollection structure for multiple features
- Properties contain persona-specific scoring metadata
- Coordinates in [longitude, latitude] order

### 8. **Type Safety**
**Python:**
- Type hints throughout (from __future__ import annotations)
- Pydantic models for request/response validation
- Literal types for personas and enums

**TypeScript:**
- React functional components with explicit Props types
- No `any` types without justification
- Component-level type definitions

### 9. **Modular Workflow Orchestration**
```
Power Developer Workflow:
- resolve_power_developer_persona() - Normalize input
- extract_coordinates() - Parse geometry
- run_power_developer_analysis() - Score projects
- transform_tec_to_project_schema() - Normalize data

Data Center Workflow:
- Delegates to shared scoring.py algorithms
- Maintains backward compatibility
- Re-exports for different consumers
```

### 10. **Dual-Mode Financial Analysis**
```
For Each Renewable Project:
├─ Utility-Scale Model
│  └─ Grid-connected, wholesale energy prices
└─ Behind-the-Meter Model
   └─ Self-consumption, retail electricity savings

Comparison Metrics:
- IRR uplift (BTM vs Utility)
- NPV delta analysis
- Payback period comparison
- LCOE differential
```

---

## 10. DEPLOYMENT & OPERATIONAL PATTERNS

### Production Deployment
- **Host:** Render.com
- **URL:** https://infranodev2.onrender.com
- **Runtime:** Python 3.11.9
- **ASGI Server:** Uvicorn
- **Database:** Supabase PostgreSQL with PostGIS

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Load environment
source .env

# Start backend
python start_backend.py  # Runs on localhost:8001 with hot-reload

# Start frontend (when available)
# npm run dev             # React dev server
```

### Performance Optimizations
1. **Batch Processing:** 10-50x faster for multiple projects
2. **Spatial Indexing:** O(1) proximity lookups via grid
3. **Infrastructure Caching:** TTL-based cache with default 600s
4. **Async I/O:** Non-blocking Supabase queries
5. **Incremental Loading:** Frontend loads data progressively

---

## 11. TECHNOLOGY STACK SUMMARY

### Backend Stack
| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | FastAPI | 0.104.1 | REST API, async routing |
| Server | Uvicorn | 0.24.0 | ASGI production server |
| Database | Supabase PostgreSQL | - | Primary data store |
| ORM | None (REST client) | httpx 0.25.2 | Direct SQL via Supabase API |
| Spatial | PostGIS | (Supabase) | Geographic queries |
| Data Processing | Pandas | 2.0.3 | CSV/tabular data |
| Numerical | NumPy | 1.24.3 | Matrix operations |
| Validation | Pydantic | 2.5.0 | Request/response schemas |
| HTTP Client | httpx | 0.25.2 | Async Supabase API calls |
| Config | python-dotenv | 1.0.0 | Environment variables |

### Frontend Stack
| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | React 18 | UI components |
| Language | TypeScript | Type-safe scripting |
| Styling | Tailwind CSS | Utility-first CSS |
| UI Components | shadcn/ui | Pre-built components |
| Mapping | Mapbox GL JS | Map visualization |
| State | React hooks | Component state management |
| Build | Vite/CRA | Module bundling |

---

## 12. CODE METRICS

| Metric | Value | File |
|--------|-------|------|
| Primary API | 2,384 lines | main.py |
| Scoring Engine | 988 lines | backend/scoring.py |
| Financial Model | 657 lines | backend/renewable_model.py |
| Power Workflow | 428 lines | backend/power_workflow.py |
| Proximity/Spatial | 359 lines | backend/proximity.py |
| Financial API | 298 lines | backend/financial_model_api.py |
| DC Workflow | 70 lines | backend/dc_workflow.py |
| **Total Backend Python** | **5,184 lines** | |
| API Endpoints | 19 | main.py |
| Data Personas (DC) | 3 | scoring.py |
| Data Personas (Power) | 3 | power_workflow.py |
| Scoring Components | 8 | main.py config |
| TNUoS Zones | 27 | Hardcoded + GeoJSON |
| Test Coverage | Basic | test_power_developer_persona.py |

---

## 13. KEY ARCHITECTURAL DECISIONS & RATIONALE

### Why Supabase?
- PostgreSQL with PostGIS for spatial queries
- Built-in REST API (no ORM needed)
- Real-time subscriptions support
- Row-level security for multi-tenant scenarios
- Scalability without infrastructure management

### Why FastAPI?
- Native async/await support
- Automatic OpenAPI documentation
- Type-safe request/response validation via Pydantic
- Superior performance vs Flask/Django
- Dependency injection framework

### Why Persona-Based Scoring?
- Different stakeholder types have fundamentally different priorities
  - Hyperscalers prioritize capacity & grid reliability
  - Colocation needs redundancy & connectivity
  - Edge computing needs latency & rapid deployment
- Weighted component scoring allows flexible ranking
- Enables "best match" functionality for decision support

### Why Dual-Mode Financial Analysis?
- Renewable projects can operate in two distinct markets:
  1. Utility-scale (grid-connected, wholesale prices)
  2. Behind-the-Meter (self-consumption, retail savings)
- Each has different economics, risk profiles, and stakeholders
- Side-by-side comparison enables investment strategy evaluation

### Why GeoJSON for All Spatial Endpoints?
- RFC 7946 standard widely supported by web mapping libraries
- Can encode both geometry and rich properties
- Natural fit for Mapbox GL JS visualization
- JSON serialization eliminates format translation overhead

---

## 14. DATA FLOW SUMMARY

```
┌─────────────────┐
│  User Browser   │
│   (React UI)    │
└────────┬────────┘
         │ HTTP/JSON
         ▼
┌──────────────────────────────────┐
│     FastAPI (main.py)            │
│  ├─ Route to appropriate handler │
│  └─ Validate input (Pydantic)    │
└────────┬─────────────────────────┘
         │
    ┌────┴────┬──────────────┬─────────────┐
    │          │              │             │
    ▼          ▼              ▼             ▼
  Scoring   Proximity    Financial      Infrastructure
  Engine    Queries      Modeling       Serving
    │          │              │             │
    └────┬─────┴──────────────┴─────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Supabase PostgreSQL + PostGIS   │
│  ├─ renewable_projects           │
│  ├─ electrical_grid              │
│  ├─ transmission_lines           │
│  ├─ substations                  │
│  ├─ fiber_cables                 │
│  ├─ internet_exchange_points     │
│  ├─ water_resources              │
│  ├─ tnuos_zones                  │
│  └─ tec_connections              │
└──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Response (GeoJSON + Metadata)   │
│  Cached infrastructure (600s TTL)│
└────────┬─────────────────────────┘
         │ HTTP/JSON
         ▼
┌─────────────────┐
│  User Browser   │
│  (Render Map)   │
└─────────────────┘
```

---

## 15. SECURITY CONSIDERATIONS

### Authentication & Authorization
- Supabase anonymous key used (publicly shareable)
- Row-level security can be implemented at DB level
- CORS enabled for all origins ("*") - suitable for public API
- No private keys stored in version control

### Data Protection
- Credentials stored in .env (not in git)
- HTTPS enforced on Render.com deployment
- Supabase JWT tokens handle session management

### Input Validation
- Pydantic models validate all POST/PUT request bodies
- Query parameters validated with FastAPI Query dependencies
- Type hints enforce expected data types

---

## 16. DEVELOPMENT WORKFLOW

### Adding New Features
1. **Create issue/feature branch**
   - Name pattern: `feature/description` or `fix/description`

2. **Implement following AGENTS.md standards**
   - Match surrounding code style
   - Extract testable functions < 40 lines
   - Use descriptive names
   - Include type hints

3. **Test locally**
   - `pytest backend/tests/` for backend
   - Manual API testing via curl/Postman
   - Visual testing in React dev server

4. **Commit with descriptive messages**
   - Format: "[Feature/Fix] Brief description"
   - Reference issue numbers if applicable

5. **Submit PR with test results**
   - Highlight functional changes
   - List checks performed
   - Note any follow-up work needed

---

## CONCLUSION

**Infranodev2** demonstrates a modern, production-ready architecture for spatial decision support systems. The modular design allows independent scaling of:
- Scoring algorithms (via backend/scoring.py)
- Data access patterns (Supabase integration)
- Financial modeling (renewable_model.py)
- Spatial capabilities (proximity.py + PostGIS)
- API endpoints (main.py)

The persona-based framework provides flexibility for serving multiple stakeholder types with different priorities, while the stateless REST design enables horizontal scaling and easy frontend/backend decoupling.

