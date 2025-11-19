# Frontend-Backend Integration Mapping
## Infranode Cloud Flow Complete System Architecture

**Date:** November 18, 2025  
**Frontend Repo:** infranode-cloud-flow (React 18 + TypeScript)  
**Backend Repo:** infranodev2 (FastAPI 0.104.1 + Python 3.9+)  
**Integration Type:** REST API via HTTPS  
**Deployment:** Render.com (Backend), Vercel/Build System (Frontend)

---

## Architecture Overview

### System Topology

```
┌──────────────────────────────────────────┐
│         Browser / User Client            │
│  (React SPA + Mapbox GL + TypeScript)   │
└────────────────────┬─────────────────────┘
                     │ HTTPS
                     │ REST API
                     │
        ┌────────────▼────────────┐
        │   API Gateway / CORS    │
        │  (allow_origins=["*"])  │
        └────────────┬────────────┘
                     │
        ┌────────────▼─────────────────┐
        │  FastAPI Server (main.py)    │
        │  - 19 REST Endpoints         │
        │  - Persona-based Scoring     │
        │  - Financial Modeling        │
        │  - Infrastructure Caching    │
        └────────────┬─────────────────┘
                     │
        ┌────────────┴─────────────┐
        │                          │
        ▼                          ▼
   ┌─────────────┐        ┌──────────────┐
   │ Supabase    │        │ External     │
   │ PostgreSQL  │        │ APIs / Data  │
   │ + PostGIS   │        │ Sources      │
   │ + Auth      │        │              │
   └─────────────┘        └──────────────┘
```

### Core Integration Points

| Component | Frontend | Backend | Purpose |
|-----------|----------|---------|---------|
| **Project Scoring** | HyperscalerDashboard, UtilityDashboard | scoring.py, main.py | Calculate investment ratings |
| **Infrastructure Display** | SiteMap, MapOverlayControls | proximity.py, main.py | Render spatial data on maps |
| **Financial Modeling** | IRREstimator | renewable_model.py, financial_model_api.py | NPV/IRR/LCOE calculations |
| **Project Search** | FilterBar, ProjectLineList | /api/projects/customer-match | Find projects by criteria |
| **User Site Scoring** | SiteAssessmentTool, DataUploadPanel | /api/user-sites/score | Score custom locations |
| **Authentication** | ProtectedRoute, useAuth | Supabase Auth (via API) | Session management |
| **TEC Connections** | TecConnectionsMap | /api/tec/connections | Grid connection applications |

---

## API Endpoints Summary

| Method | Path | Frontend Component | Response |
|--------|------|-------------------|----------|
| GET | `/` | App.tsx | JSON |
| GET | `/health` | monitoring | JSON |
| GET | `/api/projects` | ProjectLineList | JSON |
| GET | `/api/projects/geojson` | SiteMap, FullScreenMap | GeoJSON |
| GET | `/api/projects/enhanced` | HyperscalerDashboard, TopProjectsPanel | JSON |
| POST | `/api/projects/customer-match` | FilterBar | JSON |
| POST | `/api/projects/compare-scoring` | ProjectScoreStatistics | JSON |
| POST | `/api/projects/power-developer-analysis` | DealSourcingDashboard | JSON |
| GET | `/api/infrastructure/transmission` | SiteMap | GeoJSON |
| GET | `/api/infrastructure/substations` | SiteMap | GeoJSON |
| GET | `/api/infrastructure/gsp` | SiteMap | GeoJSON |
| GET | `/api/infrastructure/fiber` | SiteMap | GeoJSON |
| GET | `/api/infrastructure/tnuos` | SiteMap | GeoJSON |
| GET | `/api/infrastructure/ixp` | SiteMap | GeoJSON |
| GET | `/api/infrastructure/water` | SiteMap | GeoJSON |
| GET | `/api/infrastructure/dno-areas` | SiteMap | GeoJSON |
| GET | `/api/tec/connections` | TecConnectionsMap | JSON |
| POST | `/api/user-sites/score` | SiteAssessmentTool | JSON |
| POST | `/api/financial-model` | IRREstimator | JSON |

---

## Frontend Configuration

**File:** `src/lib/api-config.ts`

```typescript
const API_BASE = process.env.VITE_API_BASE_URL || 'https://infranodev2.onrender.com';
const API_TIMEOUT = 90000; // 90 seconds
const DEFAULT_CACHE_TTL = 5 * 60 * 1000; // 5 minutes
```

**Environment Variables:**

```bash
VITE_SUPABASE_URL=https://qoweiksrcooqrzssykbo.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
VITE_API_BASE_URL=https://infranodev2.onrender.com
```

---

## Backend Configuration

**File:** `main.py`

```python
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
CORS_ORIGINS = ["*"]
INFRA_CACHE_TTL = 600  # seconds
```

**Environment Variables:**

```bash
SUPABASE_URL=https://qoweiksrcooqrzssykbo.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
INFRA_CACHE_TTL=600
```

---

## Key Data Flows

### Flow 1: User Selects Persona and Views Dashboard

1. User selects persona (e.g., 'hyperscaler')
2. `appStore.setPersona('hyperscaler')` stored in Zustand
3. HyperscalerDashboard component mounts
4. useEffect triggers three API calls:
   - `GET /api/projects/enhanced?persona=hyperscaler`
   - `GET /api/projects/geojson?persona=hyperscaler`
   - `GET /api/infrastructure/*` (transmission, substations, etc.)
5. Backend loads InfrastructureCache (600s TTL)
6. For each project, calculates 8 component scores
7. Applies hyperscaler persona weights
8. Returns ranked results
9. React Query caches responses (5 min TTL)
10. Components render with data

### Flow 2: User Applies Filter Criteria

1. User inputs criteria in CriteriaModal (capacity, fiber distance, etc.)
2. Frontend calls `POST /api/projects/customer-match`
3. Backend: power_workflow.py validates persona and gates
4. Filters projects by criteria (SQL WHERE clauses)
5. Applies persona weights to results
6. Returns matched_projects with match_score and match_reasons
7. ProjectLineList re-renders filtered results
8. User can inspect or compare projects

### Flow 3: User Uploads Site CSV and Scores

1. DataUploadPanel parses CSV: site_name, lat, lon, technology, capacity
2. Frontend validates UK bounds (49.8-60.9°N, -8.0-2.0°E)
3. Calls `POST /api/user-sites/score` with sites array
4. Backend validates locations and loads InfrastructureCache
5. For each site: queries SpatialGrid, calculates 8 component scores
6. Applies persona weights and criteria gates (optional)
7. Returns scored_sites with nearest_infrastructure details
8. ResultsModal displays scored sites in table
9. User can compare with benchmark projects

### Flow 4: Financial Modeling Calculation

1. User inputs 20+ financial parameters in IRREstimator
2. Calls `POST /api/financial-model` with full model request
3. Backend: RenewableFinancialModel calculates:
   - Annual generation = capacity_mw × capacity_factor × 8760 × loss_factor
   - 25-year cashflows (revenue - opex - taxes)
   - NPV at discount rate
   - IRR via Newton-Raphson method
   - LCOE = (Capex + PV Opex) / PV Generation
4. Repeats for Autoproducer scenario (higher merchant %)
5. Returns standard + autoproducer results with metrics and cashflows
6. UI displays results, uplift comparison, and sensitivity analysis

---

## File Dependencies Map

### Frontend Pages → Backend

**HyperscalerDashboard.tsx**
- Calls: GET /api/projects/enhanced?persona=hyperscaler
- Calls: GET /api/projects/geojson?persona=hyperscaler
- Calls: GET /api/infrastructure/* (all layers)
- Calls: POST /api/projects/customer-match (on filter)
- Depends: services/FinancialModelService.ts

**UtilityDashboard.tsx**
- Calls: GET /api/projects/enhanced?persona=utility
- Calls: POST /api/projects/power-developer-analysis
- Calls: GET /api/infrastructure/transmission
- Calls: GET /api/infrastructure/gsp

**ColocationAnalysis.tsx**
- Calls: GET /api/projects/enhanced?persona=colocation
- Calls: GET /api/infrastructure/ixp
- Calls: GET /api/infrastructure/fiber
- Calls: GET /api/infrastructure/water
- Weighted priorities: IXP distance (+15%), Fiber (+20%)

**SiteMappingTools.tsx**
- Calls: GET /api/projects/geojson
- Calls: GET /api/infrastructure/* (all 8 layers)
- Components: SiteMap, MapOverlayControls, useBaseMapbox hook
- Cache strategy: 5-minute infrastructure TTL

**SiteAssessmentTool.tsx**
- Calls: POST /api/user-sites/score
- Calls: GET /api/projects/geojson (for comparison)
- Flow: DataUploadPanel → ProcessingModal → ResultsModal

**FullScreenMap.tsx**
- Calls: GET /api/projects/geojson
- Calls: All infrastructure endpoints
- Variant of SiteMap with fullscreen styling

**TecConnectionsMap.tsx**
- Calls: GET /api/tec/connections
- Calls: GET /api/projects/geojson (for comparison)

### Frontend Components → Backend

**CriteriaModal.tsx**
- Calls: POST /api/projects/customer-match
- Sends business criteria gates (capacity, fiber, transmission, etc.)

**ProjectScoreStatistics.tsx**
- Uses data from GET /api/projects/enhanced
- Displays 8 component scores
- May call: POST /api/projects/compare-scoring

**TopProjectsPanel.tsx**
- Calls: GET /api/projects/enhanced?limit=20
- Pre-sorted top projects

**ProjectLineList.tsx**
- Calls: GET /api/projects or GET /api/projects/enhanced
- Frontend-side filtering

### Frontend Services → Backend

**FinancialModelService.ts**
- Calls: POST /api/financial-model
- Features: Request deduplication, 5-min response caching
- Error handling with fallback responses

### Backend Files → Frontend Contracts

**scoring.py**
- Exports: calculate_investment_rating, calculate_component_scores, apply_persona_weights
- Used by: main.py endpoints (customer-match, enhanced, power-developer-analysis)
- Critical: Frontend persona.ts weights must match PERSONA_WEIGHTS

**proximity.py**
- Core class: SpatialGrid with query_radius() method
- Used by: scoring.py for infrastructure distance calculations
- Performance: O(1) approximate lookups via grid cells

**renewable_model.py**
- Core class: RenewableFinancialModel
- Methods: calculate_npv, calculate_irr, calculate_lcoe, get_cashflows
- Used by: financial_model_api.py wrapper

**power_workflow.py**
- Functions: normalize_persona, query_projects, score_projects_batch
- Used by: POST /api/projects/power-developer-analysis
- Graceful degradation: Returns 'greenfield' if invalid persona

**financial_model_api.py**
- Function: post_financial_model
- Used by: POST /api/financial-model endpoint
- Returns: Standard + Autoproducer scenarios with metrics

**main.py**
- All 19 endpoint implementations
- InfrastructureCache management (600s TTL, lazy load)
- CORS: allow_origins=["*"] (development-wide open)

---

## Routing & Navigation

| Frontend Route | Component | Initial API Calls | Subsequent API Calls |
|---|---|---|---|
| `/` | PersonaSelection | None | None |
| `/auth` | Auth | None | POST /auth (Supabase) |
| `/dashboard/hyperscaler` | HyperscalerDashboard | GET /api/projects/enhanced, /geojson, /infrastructure/* | POST /api/projects/customer-match |
| `/dashboard/utility` | UtilityDashboard | GET /api/projects/enhanced (persona=utility) | POST /api/projects/power-developer-analysis |
| `/site-mapping-tools` | SiteMappingTools | GET /api/projects/geojson, ALL /infrastructure/* | Cache checks on layer toggle |
| `/site-assessment` | SiteAssessmentTool | GET /api/projects/enhanced | POST /api/user-sites/score |
| `/colocation-analysis` | ColocationAnalysis | GET /api/projects/enhanced (persona=colocation) | GET /api/infrastructure/ixp, /fiber |
| `/fullscreen-map` | FullScreenMap | GET /api/projects/geojson, /infrastructure/* | Same as SiteMappingTools |
| `/tec-connections/map` | TecConnectionsMap | GET /api/tec/connections | GET /api/projects/geojson |

---

## Caching Strategy

**Frontend (React Query):**
- Default 5-minute staleness time
- Refetch on window focus
- Manual invalidation: queryClient.invalidateQueries('projects')

**Backend (InfrastructureCache):**
- Infrastructure data: 600-second TTL
- Lazy load on first request
- Auto-refresh on TTL expiry
- Thread-safe with asyncio.Lock

**Session Storage:**
- Top projects persist across page navigation
- Map state preferences stored locally
- Selected project information cached

---

## State Synchronization Patterns

### Pattern 1: Persona Propagation

Frontend (Zustand store) → appStore.setPersona('hyperscaler')  
↓  
Subsequent API calls include ?persona=hyperscaler  
↓  
Backend routing: scoring.py uses PERSONA_WEIGHTS[persona]  
↓  
Apply weights to 8 component scores

**Key requirement:** Frontend persona.ts weights MUST match backend scoring.py PERSONA_WEIGHTS

### Pattern 2: Criteria Gates Flow

Frontend: CriteriaModal → User sets capacity, fiber distance, etc.  
↓  
Request: POST /api/projects/customer-match { criteria, persona }  
↓  
Backend: power_workflow.py parses criteria into SQL WHERE clauses  
↓  
Filter projects → Apply persona weights → Return matched_projects

### Pattern 3: Infrastructure Cache Synchronization

First request: GET /api/infrastructure/transmission  
↓  
Backend: InfrastructureCache._last_loaded = null → Async load from Supabase  
↓  
Create SpatialGrid indices → Cache for 600s → Response (1-2s delay)

Subsequent requests (within 10 minutes):  
↓  
Check cache TTL → Return cached data (instant) or reload

Frontend optimization: React Query deduplicates simultaneous requests

### Pattern 4: Session Caching

Dashboard loads → sessionStorage.setItem('topProjects', response)  
User applies filters → sessionStorage.setItem('currentProjects', filtered)  
User navigates away → sessionStorage persists data  
User returns → Dashboard re-renders from cache (no new API call)

---

## Authentication & Access Control

### Frontend Auth Flow

**Hook:** src/hooks/useAuth.tsx

```typescript
interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  access: AccessStatus;
  roles: string[];
  signOut(): Promise<void>;
}
```

Integrates with Supabase Auth API. Provides session management and user context.

### Backend Auth (Current)

- No authentication required for API endpoints
- CORS wide open: allow_origins=["*"]
- Suitable for demo/internal use only

### Backend Auth (Recommended for Production)

Verify Supabase JWT token from Authorization header:

```python
@app.post("/api/projects/customer-match")
async def search_projects(request: SearchRequest, token: str = Header()):
    user = supabaseClient.auth.get_user(token)
    if not user:
        raise HTTPException(401, "Unauthorized")
    results = power_workflow.query_projects(...)
    return results
```

### Access Control Rules

**Frontend:** src/lib/accessControl.ts

```typescript
interface AccessStatus {
  hasDashboardAccess: boolean;
  isEmailVerified: boolean;
  reason: 'none' | 'awaiting_activation' | 'unverified_email';
  roles: string[];
}
```

Protected routes check: User authenticated? Email verified? Dashboard access role?

---

## Error Handling

### Frontend Patterns

**API Request Errors:**
- Try/catch with timeout handling (90s)
- Wrap fetch in ApiError class
- Log and re-throw or return fallback

**Component-Level Errors:**
- ErrorBoundary components for graceful fallback UI
- Toast notifications via Sonner library

### Backend Patterns

**Input Validation (Pydantic):**
- Validate latitude/longitude (UK bounds: 49.8-60.9°N, -8.0-2.0°E)
- Return HTTP 422 for invalid requests

**Graceful Degradation:**
- Invalid persona defaults to 'greenfield'
- IRR calculation failure returns {success: false, irr: null}

### Error Response Format

**Success:**
```json
{ "success": true, "data": {...} }
```

**Error:**
```json
{
  "success": false,
  "error_type": "ValueError",
  "message": "User description",
  "details": "Technical details"
}
```

**Validation (HTTP 422):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "latitude"],
      "msg": "Latitude outside UK bounds",
      "input": 65.0
    }
  ]
}
```

---

## Performance Optimizations

### Frontend

| Optimization | Implementation | Impact |
|---|---|---|
| Request Deduplication | React Query deduplicates simultaneous requests | Prevents duplicate API calls |
| Response Caching | 5-minute TTL via React Query | Reduces server load |
| Session Caching | sessionStorage for page flow | Preserves UX across navigation |
| Component Memoization | useMemo, useCallback | Prevents re-renders |
| Lazy Loading | Route-based code splitting | Smaller initial JS bundle |
| GeoJSON Streaming | Mapbox incremental rendering | Maps load faster |

### Backend

| Optimization | Implementation | Impact |
|---|---|---|
| Infrastructure Cache | 600-second TTL with async load | Avoids thundering herd |
| Spatial Indexing | SpatialGrid with grid cells | O(1) approx proximity queries |
| Batch Processing | asyncio.gather() for concurrent scoring | 100 projects in 2-5s |
| Lazy Loading | Infrastructure loads on first request | 5s cold start, instant cache hits |
| Request Deduplication | Inflight request tracking | Prevents duplicate calculations |

### Bottleneck Analysis

Slowest operations:
1. Infrastructure Cache Load: 1-2s (cold start only)
2. Batch Project Scoring: 50-100ms per project
3. Financial Model Calculation: 500ms-2s (complex algorithm)

Optimization opportunities:
1. Add Redis cache for infrastructure across server restarts
2. Pre-calculate scores for all projects on startup
3. Implement async financial model with result streaming

---

## Critical Integration Points

1. **Persona Validation:** Frontend persona.ts ↔ Backend scoring.py PERSONA_WEIGHTS
2. **API Base URL:** Frontend VITE_API_BASE_URL ↔ Backend deployment URL
3. **Supabase Credentials:** Frontend & Backend must use same project
4. **Infrastructure Data:** Backend Supabase tables ↔ Frontend GeoJSON parsing
5. **Component Score Algorithms:** Frontend display ↔ Backend calculation

---

## Production Readiness Checklist

### ✅ Implemented

- 19 REST API endpoints with request/response schemas
- Persona-based scoring (6 personas)
- Infrastructure layer visualization (8 data sources)
- Financial modeling (NPV, IRR, LCOE)
- User site scoring and analysis
- TEC connections visualization
- CORS configuration (development)
- Error handling patterns (graceful degradation)
- Caching strategy (600s backend, 5min frontend)
- Session persistence
- Async batch processing

### ⚠️ Recommended for Production

- Structured logging (Python logging module)
- Rate limiting (per IP / API key)
- API authentication (Supabase JWT)
- Test coverage (unit, integration, E2E)
- OpenAPI/Swagger documentation
- Database migrations (versioning)
- Monitoring & observability (Prometheus, Sentry)
- Externalize configuration (YAML/JSON)
- Request validation (Pydantic for all endpoints)
- CI/CD pipeline (GitHub Actions)

---

**Document Generated:** November 18, 2025  
**Status:** Ready for development and deployment
