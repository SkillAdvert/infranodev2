# INFRANODEV2 - Quick Reference Guide

## Project at a Glance

**Type:** Full-stack renewable energy & data center infrastructure assessment platform  
**Backend:** Python 3.11 FastAPI (2,384 lines, 19 endpoints)  
**Frontend:** React 18 + TypeScript (minimal, 1 component)  
**Database:** Supabase PostgreSQL + PostGIS  
**Deployment:** Render.com (https://infranodev2.onrender.com)

---

## File Organization

```
infranodev2/
├── main.py                 (2,384 lines) - ALL API ENDPOINTS
├── backend/
│   ├── scoring.py         (988 lines) - Scoring algorithms
│   ├── renewable_model.py  (657 lines) - Financial models
│   ├── power_workflow.py   (428 lines) - Power dev workflows
│   ├── proximity.py        (359 lines) - Spatial indexing
│   ├── financial_model_api.py (298 lines) - API wrapper
│   ├── dc_workflow.py      (70 lines) - DC orchestration
│   └── tests/
├── frontend/
│   └── src/components/
│       └── criteriamodal.tsx - Modal component
├── Data ETL Scripts:
│   ├── fetch_network_data.py
│   ├── fetch_tnuos_data.py
│   ├── import_projects.py
│   └── fetch_fiber_data
└── Config:
    ├── .env (Supabase credentials)
    ├── requirements.txt (dependencies)
    └── runtime.txt (Python 3.11.9)
```

---

## Core Modules

### 1. main.py - THE HUB
- **Role:** FastAPI application with all 19 REST endpoints
- **Key Functions:**
  - Project scoring (persona-based)
  - Infrastructure data serving
  - Financial model calculations
  - User site analysis
- **Infrastructure:** Hard-coded TNUoS zones, batch processing

### 2. scoring.py - THE ENGINE
- **Role:** All scoring algorithms
- **Key Algorithms:**
  - 8-component scoring framework
  - Weighted scoring (persona-specific)
  - TOPSIS multi-criteria decision
  - Component normalization
- **Personas:** hyperscaler, colocation, edge_computing

### 3. proximity.py - THE SPATIAL INDEX
- **Role:** Geospatial calculations
- **Key Classes:**
  - `SpatialGrid` - O(1) proximity lookups
  - `PointFeature` - Point infrastructure
  - `LineFeature` - Line infrastructure
  - `InfrastructureCatalog` - Unified repository

### 4. renewable_model.py - THE FINANCIAL ENGINE
- **Role:** Professional financial modeling for renewables
- **Key Features:**
  - 5 technology types (solar, wind, battery, hybrid)
  - 2 project types (utility-scale, behind-the-meter)
  - 2 regions (UK, Ireland)
  - Comprehensive metrics (IRR, NPV, LCOE, payback)

### 5. power_workflow.py - POWER DEV ORCHESTRATION
- **Role:** Workflow for renewable energy projects
- **Personas:** greenfield, repower, stranded
- **Key Functions:**
  - Persona resolution & normalization
  - Investment scoring
  - TEC data transformation

---

## The 8-Component Scoring Framework

| # | Component | Purpose | Impact |
|---|-----------|---------|--------|
| 1 | Capacity | Project size suitability | MW matching |
| 2 | Development Stage | Deployment readiness | Timeline |
| 3 | Technology | Technology appropriateness | Tech type fit |
| 4 | Grid Infrastructure | Power proximity | Substation, transmission |
| 5 | Digital Infrastructure | Connectivity | Fiber, IXP |
| 6 | Water Resources | Cooling availability | Water proximity |
| 7 | TNUoS Costs | Transmission charges | Annual £ impact |
| 8 | LCOE Quality | Generation cost | MW production |

---

## 19 API Endpoints

### Project Data (5)
- GET `/api/projects` - List all projects
- GET `/api/projects/geojson` - GeoJSON format
- GET `/api/projects/enhanced` - With persona scoring
- GET `/api/projects/compare-scoring` - Algorithm comparison
- POST `/api/user-sites/score` - Score user sites

### Power Developer (2)
- POST `/api/projects/power-developer-analysis` - Analyze projects
- GET `/api/projects/customer-match` - Find customer matches

### Infrastructure (8)
- GET `/api/infrastructure/transmission` - Transmission lines
- GET `/api/infrastructure/substations` - Electrical substations
- GET `/api/infrastructure/gsp` - Grid Supply Points
- GET `/api/infrastructure/fiber` - Fiber cables
- GET `/api/infrastructure/tnuos` - TNUoS zones
- GET `/api/infrastructure/ixp` - Internet exchanges
- GET `/api/infrastructure/water` - Water resources
- GET `/api/infrastructure/dno-areas` - DNO areas

### Financial Modeling (1)
- POST `/api/financial-model` - Calculate financial metrics

### TEC Integration (1)
- GET `/api/tec/connections` - Grid connections

### Health (2)
- GET `/` - Root endpoint
- GET `/health` - Health check

---

## Database Tables

### Project Data
- `renewable_projects` (100+) - UK renewable projects
- `electrical_grid` (333) - GSP boundaries

### Infrastructure
- `transmission_lines` - High-voltage network
- `substations` - Electrical infrastructure
- `fiber_cables` (549+) - Telecom networks
- `internet_exchange_points` - Data centers
- `water_resources` - Water sources

### Transmission & Connections
- `tnuos_zones` (27) - Transmission charging zones
- `tec_connections` - Grid capacity applications

---

## Key Architectural Patterns

1. **Layered Architecture**
   - FastAPI REST → Business Logic → Supabase

2. **Persona-Based Scoring**
   - Different stakeholders, different priorities
   - Weighted component framework
   - 1.0-10.0 rating scale

3. **Spatial Indexing**
   - O(1) proximity lookups via grid cells
   - Batch processing (10-50x faster)
   - TTL-based infrastructure caching

4. **Async/Non-blocking**
   - Async httpx for Supabase queries
   - FastAPI native async/await
   - Efficient batch operations

5. **Financial Modeling**
   - Technology + Market + Financial Assumptions
   - Year-by-year cashflow projection
   - Dual-mode analysis (utility vs behind-the-meter)

6. **Stateless REST**
   - No server-side sessions
   - Computed on-demand
   - GeoJSON output standard

7. **Type Safety**
   - Python type hints throughout
   - Pydantic models for validation
   - TypeScript on frontend

---

## Configuration

### Environment Variables (.env)
```
SUPABASE_URL=https://...         # Database connection
SUPABASE_ANON_KEY=eyJ...         # JWT token
INFRA_CACHE_TTL=600              # Cache lifetime (seconds)
```

### Dependencies
- FastAPI 0.104.1
- Uvicorn 0.24.0
- Pydantic 2.5.0
- httpx 0.25.2
- pandas 2.0.3
- numpy 1.24.3

---

## Key Files by Purpose

### To Understand Scoring
→ `backend/scoring.py` (line 18 for persona weights, line 222 for component functions)

### To Add API Endpoint
→ `main.py` (line 1015 onwards for @app decorator patterns)

### To Modify Financial Modeling
→ `backend/renewable_model.py` (classes: TechnologyType, MarketPrices, RenewableFinancialModel)

### To Change Spatial Logic
→ `backend/proximity.py` (classes: SpatialGrid, PointFeature, LineFeature)

### To Debug Power Developer
→ `backend/power_workflow.py` (functions: resolve_power_developer_persona, run_power_developer_analysis)

### To Understand Development Status
→ `claude.md` (sections: "Development Stage Scoring Issue", "Immediate Next Steps")

---

## Data Flow

```
User Request → FastAPI (main.py)
              ↓
          ┌───┴───┬─────────┬──────────┐
          ↓       ↓         ↓          ↓
      Scoring  Proximity Financial  Infrastructure
        ↓       ↓         ↓          ↓
      ┌─────────┴─────────┴──────────┘
      ↓
  Supabase PostgreSQL + PostGIS
      ↓
  GeoJSON + Metadata → User Browser
```

---

## Common Tasks

### Run Locally
```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
python start_backend.py  # Runs on localhost:8001
```

### Test Backend
```bash
pytest backend/tests/
```

### Add Scoring Component
1. Add function to `backend/scoring.py`
2. Call from appropriate persona weighting in `main.py`
3. Add to component_scores dictionary in response

### Add Infrastructure Layer
1. Create new Supabase table
2. Add `fetch_*` script to data ETL
3. Add GET endpoint in `main.py`
4. Return GeoJSON FeatureCollection

### Deploy to Render.com
- Push to main branch
- Render auto-deploys using `main.py` as entry point
- Python 3.11.9 from `runtime.txt`

---

## Development Guidelines

From AGENTS.md:
- Match surrounding code style
- Functions < 40 lines
- Type hints required
- Async/await for I/O
- Pydantic models for APIs
- Test before committing
- Descriptive commit messages

---

## Performance Notes

- **Batch Processing:** 10-50x faster than individual queries
- **Infrastructure Cache:** 600s TTL (configurable)
- **Spatial Grid:** O(1) point lookups, 0.5° cell size
- **Async I/O:** Non-blocking Supabase API calls
- **Memory:** Infrastructure catalog loaded once, cached

---

## Known Issues/TODOs

From claude.md:
1. Development Stage Scoring - Too conservative
2. Capacity Scoring - Too restrictive for hyperscaler range (5.2-8.6 instead of 1.0-10.0)
3. TNUoS Integration - Spatial queries not fully integrated
4. Frontend - Minimal React components, needs expansion

---

## Contact & Documentation

- **Architecture:** See ARCHITECTURE.md (comprehensive)
- **Guidelines:** See AGENTS.md (development standards)
- **Status:** See claude.md (project roadmap)
- **Tests:** `backend/tests/test_power_developer_persona.py`

