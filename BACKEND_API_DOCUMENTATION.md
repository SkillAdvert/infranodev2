# Backend API Documentation - InfraNode Cloud Flow

**Version:** 2.1.0
**Backend Framework:** FastAPI
**Database:** Supabase (PostgreSQL)
**Production URL:** `https://infranodev2.onrender.com`
**Development URL:** `http://localhost:8001`

---

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [API Endpoints](#2-api-endpoints)
3. [Database Schema](#3-database-schema)
4. [Business Logic & Algorithms](#4-business-logic--algorithms)
5. [External Data Sources](#5-external-data-sources)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Configuration & Environment](#7-configuration--environment)
8. [Performance & Caching](#8-performance--caching)
9. [Error Handling](#9-error-handling)
10. [Development Setup](#10-development-setup)

---

## 1. Technology Stack

### 1.1 Backend Framework
- **FastAPI** version 0.104.1
- **Uvicorn** version 0.24.0 (ASGI server)
- Python 3.x

### 1.2 Key Dependencies

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.2              # Async HTTP client for Supabase queries
python-dotenv==1.0.0       # Environment variable management
numpy==1.24.3              # Numerical calculations
pandas==2.0.3              # Financial model data processing
```

### 1.3 Architecture Pattern
- **Monolithic architecture** with modular code organization
- **Async/await** pattern for all I/O operations
- **In-memory caching** for infrastructure data (600 second TTL)
- **Spatial indexing** using custom grid-based system for proximity calculations

---

## 2. API Endpoints

### 2.1 Health & Status Endpoints

#### `GET /`
**Description:** Root endpoint providing API status
**Authentication:** None
**Query Parameters:** None

**Response:**
```json
{
  "message": "Infranodal API v2.1 with Persona-Based Scoring",
  "status": "active"
}
```

---

#### `GET /health`
**Description:** Health check endpoint with database connectivity test
**Authentication:** None
**Query Parameters:** None

**Response (Healthy):**
```json
{
  "status": "healthy",
  "database": "connected",
  "projects": 5247
}
```

**Response (Degraded):**
```json
{
  "status": "degraded",
  "database": "disconnected",
  "error": "Database connection error message"
}
```

---

### 2.2 Project Endpoints

#### `GET /api/projects`
**Description:** Retrieve projects with optional filtering and persona-based scoring
**Authentication:** None
**Rate Limiting:** None

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 5000 | Number of projects to return (max: 5000) |
| `technology` | string | No | null | Filter by technology type (case-insensitive partial match) |
| `country` | string | No | null | Filter by country (case-insensitive partial match) |
| `persona` | string | No | null | Data center persona for scoring: `hyperscaler`, `colocation`, `edge_computing` |

**Response:** Array of project objects

**Example Response:**
```json
[
  {
    "ref_id": "proj_12345",
    "site_name": "Sunnydale Solar Farm",
    "technology_type": "Solar Photovoltaics",
    "operator": "Green Energy Ltd",
    "capacity_mw": 50.0,
    "latitude": 51.5074,
    "longitude": -0.1278,
    "county": "Greater London",
    "country": "England",
    "development_status_short": "consented",
    "investment_rating": 7.8,
    "rating_description": "Good",
    "color_code": "#7FFF00",
    "component_scores": {
      "capacity": 85.3,
      "connection_speed": 72.1,
      "resilience": 65.4,
      "land_planning": 85.0,
      "latency": 45.2,
      "cooling": 32.1,
      "price_sensitivity": 78.9
    },
    "weighted_contributions": {
      "capacity": 20.8,
      "connection_speed": 12.0,
      "resilience": 8.7,
      "land_planning": 17.0,
      "latency": 2.5,
      "cooling": 4.6,
      "price_sensitivity": 4.4
    },
    "persona": "hyperscaler",
    "base_score": 7.8,
    "infrastructure_bonus": 0.0
  }
]
```

---

#### `GET /api/projects/geojson`
**Description:** Retrieve projects as GeoJSON FeatureCollection (simplified, limited to 500 projects)
**Authentication:** None

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `persona` | string | No | null | Data center persona: `hyperscaler`, `colocation`, `edge_computing` |

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
        "ref_id": "proj_12345",
        "site_name": "Sunnydale Solar Farm",
        "technology_type": "Solar Photovoltaics",
        "operator": "Green Energy Ltd",
        "capacity_mw": 50.0,
        "county": "Greater London",
        "country": "England",
        "investment_rating": 7.8,
        "rating_description": "Good",
        "color_code": "#7FFF00",
        "component_scores": { /* ... */ },
        "weighted_contributions": { /* ... */ },
        "persona": "hyperscaler",
        "base_score": 7.8,
        "infrastructure_bonus": 0.0
      }
    }
  ]
}
```

---

#### `GET /api/projects/enhanced`
**Description:** **MAIN ENDPOINT** - Enhanced projects with full proximity scoring, infrastructure distances, and advanced filtering
**Authentication:** None
**Performance:** Includes batch proximity calculations (~2-5 seconds for 5000 projects)

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 5000 | Number of projects to process |
| `persona` | string | No | null | Persona: `hyperscaler`, `colocation`, `edge_computing` |
| `apply_capacity_filter` | boolean | No | true | Filter projects by persona capacity requirements |
| `custom_weights` | string (JSON) | No | null | Custom weights as JSON string (overrides persona) |
| `scoring_method` | string | No | `weighted_sum` | Scoring method: `weighted_sum` or `topsis` |
| `dc_demand_mw` | float | No | null | DC facility demand in MW for capacity gating |
| `source_table` | string | No | `renewable_projects` | Source table name |
| `user_max_price_mwh` | float | No | null | User's maximum acceptable power price (£/MWh) |
| `user_ideal_mw` | float | No | null | User's preferred capacity in MW (overrides persona default) |

**Custom Weights Format:**
```json
{
  "capacity": 0.25,
  "connection_speed": 0.20,
  "resilience": 0.15,
  "land_planning": 0.15,
  "latency": 0.10,
  "cooling": 0.10,
  "price_sensitivity": 0.05
}
```
*Note: Weights must sum to 1.0 (will be normalized if not)*

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
        "ref_id": "proj_12345",
        "site_name": "Sunnydale Solar Farm",
        "technology_type": "Solar Photovoltaics",
        "operator": "Green Energy Ltd",
        "capacity_mw": 50.0,
        "development_status_short": "consented",
        "county": "Greater London",
        "country": "England",
        "investment_rating": 7.8,
        "rating_description": "Good",
        "color_code": "#7FFF00",
        "component_scores": {
          "capacity": 85.3,
          "connection_speed": 72.1,
          "resilience": 65.4,
          "land_planning": 85.0,
          "latency": 45.2,
          "cooling": 32.1,
          "price_sensitivity": 78.9
        },
        "weighted_contributions": {
          "capacity": 20.8,
          "connection_speed": 12.0,
          "resilience": 8.7,
          "land_planning": 17.0,
          "latency": 2.5,
          "cooling": 4.6,
          "price_sensitivity": 4.4
        },
        "nearest_infrastructure": {
          "fiber_km": 2.3,
          "transmission_km": 5.7,
          "water_km": 12.4,
          "substation_km": 3.8,
          "ixp_km": 45.2,
          "gsp_km": 15.3
        },
        "persona": "hyperscaler",
        "persona_weights": {
          "capacity": 0.244,
          "connection_speed": 0.167,
          "resilience": 0.133,
          "land_planning": 0.2,
          "latency": 0.056,
          "cooling": 0.144,
          "price_sensitivity": 0.056
        },
        "base_score": 7.8,
        "infrastructure_bonus": 0.0,
        "internal_total_score": 78.0
      }
    }
  ],
  "metadata": {
    "total_projects": 1234,
    "persona": "hyperscaler",
    "scoring_method": "weighted_sum"
  }
}
```

**TOPSIS Scoring Response (when `scoring_method=topsis`):**
Additional fields in properties:
```json
{
  "topsis_metrics": {
    "distance_to_ideal": 0.234,
    "distance_to_anti_ideal": 0.789,
    "closeness_coefficient": 0.771,
    "weighted_normalized_scores": { /* ... */ },
    "normalized_scores": { /* ... */ }
  },
  "scoring_methodology": "Persona TOPSIS scoring (closeness scaled to 1-10)"
}
```

---

#### `GET /api/projects/compare-scoring`
**Description:** Compare different scoring methodologies on the same dataset
**Authentication:** None

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 100 | Number of projects to analyze |
| `persona` | string | No | `hyperscaler` | Persona for comparison |

**Response:**
```json
{
  "persona": "hyperscaler",
  "projects_analyzed": 100,
  "scoring_comparison": [
    {
      "site_name": "Project A",
      "capacity_mw": 50,
      "weighted_sum_score": 7.8,
      "topsis_score": 7.6,
      "score_delta": 0.2,
      "nearest_infrastructure": { /* ... */ }
    }
  ],
  "summary_statistics": {
    "weighted_sum_avg": 6.5,
    "topsis_avg": 6.3,
    "correlation": 0.92
  }
}
```

---

#### `GET /api/projects/customer-match`
**Description:** Find best customer persona matches for each project based on capacity and scoring
**Authentication:** None

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 500 | Number of projects to analyze |

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
        "site_name": "Project A",
        "capacity_mw": 50.0,
        "best_customer_match": "hyperscaler",
        "customer_match_scores": {
          "hyperscaler": 8.2,
          "colocation": 6.5,
          "edge_computing": 2.0
        },
        "best_match_score": 8.2,
        "suitable_customers": ["hyperscaler", "colocation"]
      }
    }
  ]
}
```

---

#### `POST /api/projects/power-developer-analysis`
**Description:** Analyze TEC connection opportunities for power developers
**Authentication:** None

**Request Body:**
```json
{
  "persona": "greenfield",
  "limit": 1000
}
```

**Personas:** `greenfield`, `repower`, `stranded`

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
        "project_name": "Grid Connection A",
        "capacity_mw": 100.0,
        "connection_site": "Substation X",
        "investment_rating": 7.5,
        "persona": "greenfield",
        "component_scores": { /* ... */ }
      }
    }
  ],
  "metadata": {
    "persona": "greenfield",
    "projects_analyzed": 234,
    "average_score": 6.8
  }
}
```

---

#### `POST /api/user-sites/score`
**Description:** Score user-uploaded site locations against infrastructure and market conditions
**Authentication:** None
**Validation:** Coordinates must be within UK bounds (49.8-60.9°N, -10.8-2.0°E), capacity 5-500 MW

**Request Body:**
```json
{
  "sites": [
    {
      "site_name": "My Proposed Data Center",
      "technology_type": "Solar Photovoltaics",
      "capacity_mw": 50.0,
      "latitude": 51.5074,
      "longitude": -0.1278,
      "commissioning_year": 2026,
      "is_btm": false,
      "capacity_factor": 12.0,
      "development_status_short": "planning"
    }
  ],
  "persona": "hyperscaler"
}
```

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `persona` | string | No | null | Scoring persona |

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
        "site_name": "My Proposed Data Center",
        "technology_type": "Solar Photovoltaics",
        "capacity_mw": 50.0,
        "investment_rating": 7.8,
        "rating_description": "Good",
        "color_code": "#7FFF00",
        "component_scores": { /* ... */ },
        "nearest_infrastructure": {
          "fiber_km": 2.3,
          "transmission_km": 5.7,
          "water_km": 12.4,
          "substation_km": 3.8,
          "ixp_km": 45.2
        },
        "tnuos_zone": "GZ23",
        "tnuos_zone_name": "London",
        "tnuos_tariff_pounds_per_kw": -0.78,
        "tnuos_score": 95.2
      }
    }
  ],
  "scoring_summary": {
    "total_sites": 1,
    "average_rating": 7.8,
    "persona": "hyperscaler",
    "processing_time_seconds": 1.23
  }
}
```

---

### 2.3 Infrastructure Endpoints

All infrastructure endpoints return GeoJSON FeatureCollections. These are **READ-ONLY** endpoints serving pre-loaded infrastructure data.

#### `GET /api/infrastructure/transmission`
**Description:** Transmission line geometries
**Response:** GeoJSON FeatureCollection with LineString features

**Feature Properties:**
- `name`: Line name
- `voltage_kv`: Voltage level
- `operator`: Network operator
- `path_coordinates`: Array of [lng, lat] coordinates

---

#### `GET /api/infrastructure/substations`
**Description:** Electrical substation locations
**Response:** GeoJSON FeatureCollection with Point features

**Feature Properties:**
- `name`: Substation name
- `voltage_kv`: Voltage level
- `operator`: Network operator
- `Lat`, `Long`: Coordinates

---

#### `GET /api/infrastructure/gsp`
**Description:** Grid Supply Point (GSP) boundaries
**Response:** GeoJSON FeatureCollection with Polygon features

**Feature Properties:**
- `gsp_name`: GSP name
- `gsp_id`: Unique identifier
- `region`: Regional network

---

#### `GET /api/infrastructure/fiber`
**Description:** Fiber optic cable routes
**Response:** GeoJSON FeatureCollection with LineString features

**Feature Properties:**
- `operator`: Cable operator
- `cable_name`: Cable system name
- `route_coordinates`: Array of [lng, lat] coordinates

---

#### `GET /api/infrastructure/ixp`
**Description:** Internet Exchange Point (IXP) locations
**Response:** GeoJSON FeatureCollection with Point features

**Feature Properties:**
- `name`: IXP name
- `city`: City location
- `operators`: Connected operators

---

#### `GET /api/infrastructure/water`
**Description:** Water resource locations (rivers, lakes, reservoirs)
**Response:** GeoJSON FeatureCollection with Point and LineString features

**Feature Properties:**
- `name`: Water body name
- `type`: `river`, `lake`, `reservoir`
- `coordinates`: Point or LineString geometry

---

#### `GET /api/infrastructure/tnuos`
**Description:** TNUoS (Transmission Network Use of System) charging zones
**Response:** GeoJSON FeatureCollection with Polygon features

**Feature Properties:**
```json
{
  "zone_id": "GZ23",
  "zone_name": "London",
  "generation_tariff_pounds_per_kw": -0.78,
  "demand_tariff_pounds_per_kw": 23.45,
  "bounds": {
    "min_lat": 51.2,
    "max_lat": 51.8,
    "min_lng": -0.5,
    "max_lng": 0.5
  }
}
```

**TNUoS Zones:** 27 zones from GZ1 (North Scotland, £15.32/kW) to GZ27 (Solent, £-2.34/kW)

---

#### `GET /api/infrastructure/dno-areas`
**Description:** Distribution Network Operator (DNO) license areas
**Response:** GeoJSON FeatureCollection with Polygon features

**Feature Properties:**
- `dno_name`: DNO company name
- `license_area`: License area name
- `region`: Geographic region

---

### 2.4 TEC Connections Endpoint

#### `GET /api/tec/connections`
**Description:** Transmission Entry Capacity (TEC) connection queue data
**Authentication:** None

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 1000 | Max records (1-5000) |
| `search` | string | No | null | Search project_name (case-insensitive) |
| `status` | string | No | null | Filter by development_status |
| `plant_type` | string | No | null | Filter by technology_type |

**Response:**
```json
{
  "type": "FeatureCollection",
  "count": 234,
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-0.1278, 51.5074]
      },
      "properties": {
        "id": 12345,
        "project_name": "Solar Farm A",
        "operator": "Green Energy Ltd",
        "customer_name": "Energy Buyer Co",
        "capacity_mw": 50.0,
        "mw_delta": 10.0,
        "technology_type": "Solar",
        "plant_type": "Generation",
        "project_status": "Active",
        "connection_site": "Substation X",
        "substation_name": "Substation X 400kV",
        "voltage": 400.0,
        "constraint_status": "Unconstrained",
        "agreement_type": "BELLA",
        "effective_from": "2024-01-15",
        "created_at": "2023-12-01T10:30:00Z"
      }
    }
  ]
}
```

---

### 2.5 Financial Model Endpoint

#### `POST /api/financial-model`
**Description:** Calculate comprehensive financial analysis for renewable energy projects
**Authentication:** None
**Performance:** ~200-500ms per calculation

**Request Body:**
```json
{
  "technology": "solar",
  "capacity_mw": 50.0,
  "capacity_factor": 12.0,
  "project_life": 25,
  "degradation": 0.005,

  "capex_per_kw": 800.0,
  "devex_abs": 500000.0,
  "devex_pct": 0.05,
  "opex_fix_per_mw_year": 15000.0,
  "opex_var_per_mwh": 2.0,
  "tnd_costs_per_year": 50000.0,

  "ppa_price": 65.0,
  "ppa_escalation": 0.025,
  "ppa_duration": 15,
  "merchant_price": 55.0,
  "capacity_market_per_mw_year": 10000.0,
  "ancillary_per_mw_year": 5000.0,

  "discount_rate": 0.08,
  "inflation_rate": 0.02,
  "tax_rate": 0.19,
  "grid_savings_factor": 0.8,

  "battery_capacity_mwh": null,
  "battery_capex_per_mwh": null,
  "battery_cycles_per_year": null
}
```

**Technology Types:** `solar`, `solar_pv`, `wind`, `battery`, `solar_battery`, `solar_bess`, `wind_battery`

**Response:**
```json
{
  "success": true,
  "message": "Financial analysis completed successfully",
  "standard": {
    "irr": 8.5,
    "npv": 5234567.89,
    "lcoe": 52.3,
    "payback_simple": 10.2,
    "payback_discounted": 14.5,
    "cashflows": [-40000000, 3200000, 3250000, ...],
    "breakdown": {
      "energyRev": 123456789.0,
      "capacityRev": 3750000.0,
      "ancillaryRev": 1875000.0,
      "gridSavings": 0.0,
      "opexTotal": 18750000.0
    }
  },
  "autoproducer": {
    "irr": 12.3,
    "npv": 8345678.90,
    "lcoe": 48.7,
    "payback_simple": 8.5,
    "payback_discounted": 11.2,
    "cashflows": [-40000000, 4100000, 4150000, ...],
    "breakdown": {
      "energyRev": 145678901.0,
      "capacityRev": 0.0,
      "ancillaryRev": 0.0,
      "gridSavings": 12500000.0,
      "opexTotal": 18750000.0
    }
  },
  "metrics": {
    "total_capex": 40000000.0,
    "capex_per_mw": 800000.0,
    "irr_uplift": 3.8,
    "npv_delta": 3111111.01,
    "annual_generation": 52560.0
  }
}
```

**Error Response (500):**
```json
{
  "detail": {
    "success": false,
    "message": "Financial model calculation failed: Invalid capacity factor",
    "error_type": "ValueError"
  }
}
```

---

## 3. Database Schema

### 3.1 Database Technology
- **Type:** PostgreSQL (via Supabase)
- **Connection:** REST API (PostgREST) via HTTPS
- **Authentication:** API Key-based (Supabase anon key)

### 3.2 Main Tables

#### `renewable_projects`
**Description:** Core renewable energy projects table
**Primary Key:** `ref_id`

**Columns:**
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `ref_id` | text | No | Unique project identifier |
| `site_name` | text | Yes | Project/site name |
| `technology_type` | text | Yes | Technology: "Solar Photovoltaics", "Wind", "Battery", "Hybrid" |
| `operator` | text | Yes | Project operator/developer |
| `capacity_mw` | float | Yes | Installed capacity in MW |
| `latitude` | float | Yes | Latitude (WGS84) |
| `longitude` | float | Yes | Longitude (WGS84) |
| `county` | text | Yes | County/region |
| `country` | text | Yes | Country (England, Scotland, Wales, Northern Ireland) |
| `development_status_short` | text | Yes | Status: "operational", "under construction", "consented", "in planning", etc. |
| `commissioning_year` | integer | Yes | Expected/actual commissioning year |
| `created_at` | timestamp | No | Record creation timestamp |

**Indexes:** Recommended on `latitude`, `longitude`, `capacity_mw`, `technology_type`

---

#### `substations`
**Description:** Electrical substation point locations

**Columns:**
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | No | Primary key |
| `name` | text | Yes | Substation name |
| `Lat` / `latitude` | float | Yes | Latitude |
| `Long` / `longitude` | float | Yes | Longitude |
| `voltage_kv` | float | Yes | Voltage level (kV) |
| `operator` | text | Yes | Network operator |

---

#### `transmission_lines`
**Description:** Transmission line polyline geometries

**Columns:**
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | No | Primary key |
| `name` | text | Yes | Line name |
| `voltage_kv` | float | Yes | Voltage level |
| `operator` | text | Yes | Network operator |
| `path_coordinates` | jsonb | Yes | Array of [lng, lat] coordinates |

---

#### `fiber_cables`
**Description:** Fiber optic cable routes

**Columns:**
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | No | Primary key |
| `operator` | text | Yes | Cable operator |
| `cable_name` | text | Yes | Cable system name |
| `route_coordinates` | jsonb | Yes | Array of [lng, lat] coordinates |

---

#### `internet_exchange_points`
**Description:** IXP locations

**Columns:**
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | No | Primary key |
| `name` | text | Yes | IXP name |
| `latitude` | float | Yes | Latitude |
| `longitude` | float | Yes | Longitude |
| `city` | text | Yes | City location |
| `operators` | text[] | Yes | Connected operators |

---

#### `water_resources`
**Description:** Water bodies (point or line geometries)

**Columns:**
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | No | Primary key |
| `name` | text | Yes | Water body name |
| `type` | text | Yes | Type: "river", "lake", "reservoir" |
| `coordinates` | jsonb | Yes | Point [lng, lat] or array of coordinates |

---

#### `tec_connections`
**Description:** TEC connection queue data

**Columns:**
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | No | Primary key |
| `project_name` | text | Yes | Project name |
| `operator` | text | Yes | Operator/developer |
| `customer_name` | text | Yes | Customer/offtaker |
| `capacity_mw` | float | Yes | Connection capacity MW |
| `mw_delta` | float | Yes | MW change |
| `technology_type` | text | Yes | Technology type |
| `plant_type` | text | Yes | Plant type |
| `project_status` | text | Yes | Connection status |
| `latitude` | float | Yes | Latitude |
| `longitude` | float | Yes | Longitude |
| `connection_site` | text | Yes | Connection substation |
| `substation_name` | text | Yes | Substation name |
| `voltage` | float | Yes | Connection voltage (kV) |
| `constraint_status` | text | Yes | Constraint status |
| `agreement_type` | text | Yes | Agreement type (BELLA, etc.) |
| `effective_from` | date | Yes | Effective date |
| `created_at` | timestamp | No | Record creation |

---

### 3.3 Data Relationships

**No explicit foreign keys** are used in the current schema. Relationships are implicit:

- **Projects → Infrastructure:** Calculated via spatial proximity (haversine distance)
- **Projects → TEC Connections:** No direct link; matched by location/name if needed
- **No user data tables:** User authentication is frontend-only (Supabase Auth)

---

## 4. Business Logic & Algorithms

### 4.1 Investment Rating Calculation

The backend uses **three scoring systems**:

1. **Traditional Renewable Energy Scoring** (no persona)
2. **Persona-Based Weighted Sum Scoring** (DC demand personas)
3. **TOPSIS Multi-Criteria Decision Analysis** (advanced)

---

### 4.2 Persona-Based Scoring Algorithm

**File:** `backend/scoring.py`

**Supported DC Personas:**
- `hyperscaler` (30-250 MW range)
- `colocation` (5-30 MW range)
- `edge_computing` (0.4-5 MW range)

**Supported Power Developer Personas:**
- `greenfield` (new grid connections)
- `repower` (existing site upgrades)
- `stranded` (stranded assets/grid capacity)

**Component Scores (0-100 scale):**

1. **Capacity Score** - Gaussian curve centered on ideal MW for persona
   ```python
   score = 100 * exp(-((capacity_mw - ideal_mw)^2) / (2 * tolerance^2))
   ```

2. **Connection Speed Score** - Development stage + grid proximity
   ```python
   score = (stage_score * 0.5) + (substation_score * 0.3) + (transmission_score * 0.2)
   ```

3. **Resilience Score** - Backup infrastructure availability
   ```python
   backup_count = 0
   if substation_km < 15: backup_count += 4
   if transmission_km < 30: backup_count += 2
   if tech_type == "battery": backup_count += 1
   score = (backup_count / 10.0) * 100
   ```

4. **Land Planning Score** - Development status scoring
   - `no application required`: 100
   - `application submitted`: 100
   - `consented`: 70
   - `in planning`: 55
   - `operational`: 10 (demand perspective)

5. **Latency Score** - Digital infrastructure proximity
   ```python
   fiber_score = 100 * exp(-fiber_km / 40)
   ixp_score = 100 * exp(-ixp_km / 70)
   score = 50 * (fiber_score + ixp_score)
   ```

6. **Cooling Score** - Water resource proximity
   ```python
   score = 100 * exp(-water_km / 15)
   ```

7. **Price Sensitivity Score** - LCOE + TNUoS calculation
   ```python
   adjusted_lcoe = base_lcoe * (reference_cf / capacity_factor)
   tnuos_mwh_impact = (tariff * 1000) / capacity_hours
   total_cost_mwh = adjusted_lcoe + tnuos_mwh_impact

   if total_cost_mwh <= user_max_price:
       score = 100
   else:
       overage_pct = (total_cost - threshold) / threshold
       score = 100 - (overage_pct based decay)
   ```

**Final Score Calculation (Weighted Sum):**
```python
weighted_sum = sum(normalized_scores[key] * weights[key] for key in scores)
logistic_value = 1 / (1 + exp(-steepness * (weighted_sum - midpoint)))
final_score = logistic_value * 100  # 0-100 scale
display_rating = final_score / 10   # 1-10 scale for frontend
```

**Persona Weights:**

```python
PERSONA_WEIGHTS = {
    "hyperscaler": {
        "capacity": 0.244,
        "connection_speed": 0.167,
        "resilience": 0.133,
        "land_planning": 0.2,
        "latency": 0.056,
        "cooling": 0.144,
        "price_sensitivity": 0.056,
    },
    "colocation": {
        "capacity": 0.141,
        "connection_speed": 0.163,
        "resilience": 0.196,
        "land_planning": 0.163,
        "latency": 0.217,
        "cooling": 0.087,
        "price_sensitivity": 0.033,
    },
    "edge_computing": {
        "capacity": 0.097,
        "connection_speed": 0.129,
        "resilience": 0.108,
        "land_planning": 0.28,
        "latency": 0.247,
        "cooling": 0.054,
        "price_sensitivity": 0.086,
    },
}
```

---

### 4.3 TOPSIS Scoring Algorithm

**TOPSIS** (Technique for Order of Preference by Similarity to Ideal Solution)

**Steps:**
1. Normalize component scores using vector normalization
2. Apply persona weights to normalized scores
3. Identify ideal solution (max weighted normalized score per criterion)
4. Identify anti-ideal solution (min weighted normalized score per criterion)
5. Calculate Euclidean distance to ideal and anti-ideal
6. Calculate closeness coefficient: `C = D- / (D+ + D-)` where D+ is distance to ideal, D- is distance to anti-ideal
7. Scale closeness (0-1) to rating (1-10)

**Output:** Projects ranked by closeness to ideal solution

---

### 4.4 Infrastructure Distance Calculations

**Method:** Haversine formula for great-circle distance

```python
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)^2 + cos(lat1) * cos(lat2) * sin(dlon/2)^2
    c = 2 * asin(sqrt(a))
    return R * c
```

**Spatial Indexing:** Custom grid-based system with 0.5° cells (~55km at UK latitudes)

**Search Radius:**
```python
INFRASTRUCTURE_SEARCH_RADIUS_KM = {
    "substation": 150.0,
    "transmission": 200.0,
    "fiber": 200.0,
    "ixp": 300.0,
    "water": 100.0,
}
```

**Half-Distance (exponential decay):**
```python
INFRASTRUCTURE_HALF_DISTANCE_KM = {
    "substation": 35.0,
    "transmission": 50.0,
    "fiber": 40.0,
    "ixp": 70.0,
    "water": 15.0,
}
```

**Proximity Score:**
```python
score = 100 * exp(-distance_km / half_distance_km)
```

---

### 4.5 TNUoS Zone Matching

**Method:** Bounding box lookup (27 hardcoded zones)

**Algorithm:**
```python
def find_tnuos_zone(lat, lng):
    for zone_id, zone_data in TNUOS_ZONES:
        if (zone.min_lat <= lat <= zone.max_lat and
            zone.min_lng <= lng <= zone.max_lng):
            return zone
    return None
```

**TNUoS Score:**
```python
min_tariff = -3.0  # Most favorable (south)
max_tariff = 16.0  # Least favorable (north)
normalized = (tariff - min_tariff) / (max_tariff - min_tariff)
score = 100 * (1 - normalized)  # Invert: lower tariff = higher score
```

---

### 4.6 Capacity Factor Estimation

**Technology-specific defaults:**
```python
def estimate_capacity_factor(tech_type, latitude):
    if "solar" in tech:
        base_cf = 12.0 - ((lat - 50.0) / 8.0) * 2.0  # 9-13% range
    elif "wind" in tech:
        if "offshore" in tech:
            return 45.0
        base_cf = 28.0 + ((lat - 50.0) / 8.0) * 7.0  # 25-38% range
    elif "battery" in tech:
        return 20.0
    elif "gas" in tech or "ccgt" in tech:
        return 70.0
    else:
        return 30.0
```

---

### 4.7 Financial Model Calculations

**File:** `backend/renewable_model.py`

**Key Metrics:**

1. **IRR (Internal Rate of Return):**
   ```python
   NPV = sum(cashflow[t] / (1 + IRR)^t) = 0
   # Solved iteratively using numpy.irr
   ```

2. **NPV (Net Present Value):**
   ```python
   NPV = sum(cashflow[t] / (1 + discount_rate)^t)
   ```

3. **LCOE (Levelized Cost of Energy):**
   ```python
   LCOE = sum(costs[t] / (1 + r)^t) / sum(generation[t] / (1 + r)^t)
   ```

4. **Payback Periods:**
   - Simple: Year when cumulative cashflow > 0
   - Discounted: Year when cumulative NPV > 0

**Revenue Streams:**
- PPA revenue (70% of generation at contracted rate)
- Merchant revenue (30% of generation at market rate)
- Capacity market payments (£/kW/year)
- Ancillary services (frequency response, reserve)
- Grid charge savings (behind-the-meter only)

**Cost Structure:**
- CAPEX (£/kW) including battery CAPEX if hybrid
- DEVEX (development costs, absolute + percentage)
- Fixed OPEX (£/MW/year)
- Variable OPEX (£/MWh)
- TND costs (transmission/distribution)

**Degradation:**
- Solar: 0.5%/year default
- Wind: 0.5%/year default
- Battery: 2%/year default

---

## 5. External Data Sources

### 5.1 Infrastructure Data Sources

**All infrastructure data is pre-loaded into Supabase.** The backend does **NOT** make real-time external API calls.

**Data Sources (for reference):**
- **Transmission lines:** National Grid ESO data
- **Substations:** Ofgem/DNO published data
- **Fiber cables:** Publicly available fiber route data
- **IXPs:** PeeringDB, industry databases
- **Water resources:** OS Open Rivers, Environment Agency
- **TNUoS zones:** National Grid charging methodology

**Update Frequency:** Manual updates (not automated)

---

### 5.2 Project Data Source

**Source:** UK Renewable Energy Planning Database (REPD) + planning applications

**Update Frequency:** Manual updates

---

### 5.3 TEC Data Source

**Source:** National Grid ESO TEC Register

**Update Frequency:** Manual updates

---

## 6. Authentication & Authorization

### 6.1 API Authentication

**All REST API endpoints (`/api/*`) are PUBLICLY ACCESSIBLE with NO authentication required.**

- No API keys needed
- No JWT tokens
- No OAuth
- No rate limiting (currently)

**Rationale:** This is a read-only analytical API for public infrastructure data.

---

### 6.2 Supabase Integration

**Backend → Supabase:**
- Uses Supabase **anon key** for database queries
- Read-only access to public tables
- No user context passed to backend

**Frontend → Supabase:**
- Direct Supabase Auth integration for user management
- User roles stored in `user_roles` table (frontend-only)
- Backend is **NOT aware of user roles**

---

### 6.3 CORS Configuration

**Allowed Origins:** `*` (all origins)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 7. Configuration & Environment

### 7.1 Environment Variables

**Required:**
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

**Optional:**
```bash
INFRA_CACHE_TTL=600  # Infrastructure cache TTL in seconds (default: 600)
```

---

### 7.2 Deployment Configuration

**Production:**
- **Platform:** Render.com
- **URL:** `https://infranodev2.onrender.com`
- **Workers:** Uvicorn (async workers)
- **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Development:**
- **URL:** `http://localhost:8001`
- **Start command:** `python start_backend.py` or `uvicorn main:app --reload --port 8001`

---

### 7.3 Feature Flags

**None currently implemented.**

---

## 8. Performance & Caching

### 8.1 Infrastructure Caching

**Strategy:** In-memory cache with time-based expiration

```python
class InfrastructureCache:
    _catalog: Optional[InfrastructureCatalog] = None
    _last_loaded: float = 0.0
    TTL: int = 600  # 10 minutes
```

**Cached Data:**
- Substations (~2000 points)
- Transmission lines (~500 polylines)
- Fiber cables (~200 polylines, limited)
- IXPs (~50 points)
- Water resources (~1000 points + lines)

**Cache Warming:** On first request after server start or TTL expiration

**Cache Size:** ~5-10 MB in memory

---

### 8.2 Spatial Indexing

**Grid-based spatial index** for fast proximity lookups:
- Cell size: 0.5° (~55km at UK latitudes)
- Index type: Hash map of (lat_idx, lon_idx) → features
- Lookup: O(1) cell access, O(n) feature scan within nearby cells

**Performance:**
- Single proximity calculation: ~1-2ms
- Batch 5000 projects: ~2-5 seconds

---

### 8.3 Database Query Optimization

**Pagination:** Automatic offset-based pagination for large queries
```python
# For queries >1000 records, fetches in chunks of 1000
# Example: limit=5000 → 5 sequential queries with offset
```

**No database indexes** are defined in the code (managed by Supabase)

**Recommended indexes:**
- `renewable_projects(latitude, longitude)`
- `renewable_projects(capacity_mw)`
- `renewable_projects(technology_type)`
- `tec_connections(latitude, longitude)`

---

### 8.4 Response Time Characteristics

**Typical response times:**

| Endpoint | Response Time | Notes |
|----------|---------------|-------|
| `GET /health` | 100-300ms | Includes DB query |
| `GET /api/projects` | 500ms-2s | 5000 projects |
| `GET /api/projects/geojson` | 300-800ms | 500 projects |
| `GET /api/projects/enhanced` | 3-8s | 5000 projects with proximity |
| `POST /api/user-sites/score` | 1-3s | Depends on site count |
| `GET /api/infrastructure/*` | 100-500ms | Cached data |
| `POST /api/financial-model` | 200-500ms | Single calculation |

---

## 9. Error Handling

### 9.1 Standard Error Response Format

**HTTP 400 (Bad Request):**
```json
{
  "detail": "Site 1: Coordinates outside UK bounds"
}
```

**HTTP 500 (Internal Server Error):**
```json
{
  "detail": "Database connection failed"
}
```

**HTTP 500 (Financial Model Error):**
```json
{
  "detail": {
    "success": false,
    "message": "Financial model calculation failed: Invalid capacity factor",
    "error_type": "ValueError"
  }
}
```

---

### 9.2 Input Validation

**User Site Scoring Validation:**
```python
# Coordinate bounds
49.8 <= latitude <= 60.9
-10.8 <= longitude <= 2.0

# Capacity bounds
5 <= capacity_mw <= 500

# Year bounds
2025 <= commissioning_year <= 2035
```

**Pydantic Models:** Used for request validation on all POST endpoints

---

### 9.3 Error Logging

**Console logging only** - no external error tracking

```python
print(f"❌ Database error: {exc}")
print(f"⚠️ Skipped {count} rows (missing coords)")
```

**No Sentry, Rollbar, or other error tracking services configured.**

---

## 10. Development Setup

### 10.1 Local Development

**Prerequisites:**
- Python 3.9+
- pip

**Setup:**
```bash
# Clone repository
git clone <repo-url>
cd infranodev2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
INFRA_CACHE_TTL=600
EOF

# Run backend
python start_backend.py
# OR
uvicorn main:app --reload --port 8001
```

**Backend will start on:** `http://localhost:8001`

---

### 10.2 Testing

**Current test coverage:** Limited

**Test files:**
- `backend/tests/test_power_developer_persona.py`

**Run tests:**
```bash
pytest backend/tests/
```

**No integration tests for API endpoints currently exist.**

---

### 10.3 Debug Endpoints

**No dedicated debug endpoints.**

**Diagnostics available via:**
- `GET /health` - Database connectivity check
- Console logs for all operations

---

## 11. API Versioning & Changelog

### 11.1 Versioning Strategy

**No explicit API versioning** (no `/api/v1/`, `/api/v2/`)

**Breaking changes** are deployed directly to production endpoints.

**Recommendation:** Implement versioning before making breaking changes.

---

### 11.2 Recent Changes (v2.1.0)

- Added `user_ideal_mw` parameter to `/api/projects/enhanced`
- Added `user_max_price_mwh` parameter for price sensitivity scoring
- Added TOPSIS scoring method support
- Added power developer personas (`greenfield`, `repower`, `stranded`)
- Enhanced TNUoS integration with hardcoded zones

---

## 12. Data Structure Reference

### 12.1 Enhanced Projects Response (Complete Schema)

```typescript
{
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [longitude, latitude]  // Note: GeoJSON is [lng, lat]
      },
      properties: {
        // Project Identity
        ref_id: string,
        site_name: string,
        operator: string | null,

        // Technical Specifications
        technology_type: string,  // "Solar Photovoltaics", "Wind", "Battery Storage", "Hybrid"
        capacity_mw: number,
        development_status_short: string,  // "operational", "under construction", "consented", "in planning", etc.
        commissioning_year: number | null,

        // Location
        county: string | null,
        country: string,  // "England", "Scotland", "Wales", "Northern Ireland"

        // Investment Rating (1.0 - 10.0 scale)
        investment_rating: number,
        rating_description: string,  // "Excellent", "Very Good", "Good", "Above Average", "Average", "Below Average", "Poor", etc.
        color_code: string,  // Hex color for map visualization

        // Component Scores (0-100 scale)
        component_scores: {
          capacity: number,
          connection_speed: number,
          resilience: number,
          land_planning: number,
          latency: number,
          cooling: number,
          price_sensitivity: number
        },

        // Weighted Contributions (component_score * weight)
        weighted_contributions: {
          capacity: number,
          connection_speed: number,
          resilience: number,
          land_planning: number,
          latency: number,
          cooling: number,
          price_sensitivity: number
        },

        // Infrastructure Distances (km)
        nearest_infrastructure: {
          fiber_km: number,
          transmission_km: number,
          water_km: number,
          substation_km: number,
          ixp_km: number,
          gsp_km?: number  // Not always present
        },

        // Scoring Metadata
        persona: string,  // "hyperscaler", "colocation", "edge_computing", "custom"
        persona_weights: {
          capacity: number,
          connection_speed: number,
          resilience: number,
          land_planning: number,
          latency: number,
          cooling: number,
          price_sensitivity: number
        },
        base_score: number,
        infrastructure_bonus: number,
        internal_total_score: number,  // 0-100 scale (backend internal)

        // TOPSIS-specific (only if scoring_method=topsis)
        topsis_metrics?: {
          distance_to_ideal: number,
          distance_to_anti_ideal: number,
          closeness_coefficient: number,
          weighted_normalized_scores: { /* ... */ },
          normalized_scores: { /* ... */ }
        },
        scoring_methodology?: string
      }
    }
  ]
}
```

---

### 12.2 Rating Description Mapping

```python
Rating (0-10 scale) → Description
≥ 9.0 → "Excellent"
≥ 8.0 → "Very Good"
≥ 7.0 → "Good"
≥ 6.0 → "Above Average"
≥ 5.0 → "Average"
≥ 4.0 → "Below Average"
≥ 3.0 → "Poor"
≥ 2.0 → "Very Poor"
≥ 1.0 → "Bad"
< 1.0 → "Very Bad"
```

---

### 12.3 Color Code Mapping

```python
Rating (0-10 scale) → Color (Hex)
≥ 9.0 → "#00DD00" (bright green)
≥ 8.0 → "#33FF33"
≥ 7.0 → "#7FFF00"
≥ 6.0 → "#CCFF00"
≥ 5.0 → "#FFFF00" (yellow)
≥ 4.0 → "#FFCC00"
≥ 3.0 → "#FF9900"
≥ 2.0 → "#FF6600"
≥ 1.0 → "#FF3300"
< 1.0 → "#CC0000" (red)
```

---

## 13. Known Issues & Technical Debt

### 13.1 Current Limitations

1. **No API authentication** - All endpoints are public
2. **No rate limiting** - Potential for abuse
3. **No API versioning** - Breaking changes affect all clients
4. **Manual data updates** - Infrastructure and project data require manual refresh
5. **Limited test coverage** - Few automated tests
6. **No error tracking service** - Errors only logged to console
7. **Fiber cable limit** - Only 200 fiber cables loaded (performance optimization)
8. **No pagination on enhanced endpoint** - Can return very large payloads

---

### 13.2 Future Improvements

**Recommended:**
- Implement API key authentication
- Add rate limiting (e.g., 100 requests/minute per IP)
- Add API versioning (`/api/v2/`)
- Implement automated data refresh pipelines
- Add comprehensive test suite
- Integrate Sentry or similar for error tracking
- Add request/response compression (gzip)
- Implement GraphQL endpoint for flexible queries
- Add OpenAPI/Swagger documentation UI
- Add database indexes for faster queries

---

## 14. API Usage Examples

### 14.1 Get Enhanced Projects for Hyperscaler

```bash
curl -X GET "https://infranodev2.onrender.com/api/projects/enhanced?persona=hyperscaler&limit=1000&apply_capacity_filter=true"
```

---

### 14.2 Score User Site

```bash
curl -X POST "https://infranodev2.onrender.com/api/user-sites/score?persona=colocation" \
  -H "Content-Type: application/json" \
  -d '{
    "sites": [
      {
        "site_name": "My Data Center",
        "technology_type": "Solar Photovoltaics",
        "capacity_mw": 10.0,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "commissioning_year": 2026,
        "is_btm": false,
        "capacity_factor": 12.0,
        "development_status_short": "planning"
      }
    ]
  }'
```

---

### 14.3 Get TOPSIS Scoring

```bash
curl -X GET "https://infranodev2.onrender.com/api/projects/enhanced?persona=hyperscaler&scoring_method=topsis&limit=500"
```

---

### 14.4 Custom Weights

```bash
curl -X GET 'https://infranodev2.onrender.com/api/projects/enhanced?limit=100&custom_weights=%7B%22capacity%22%3A0.3%2C%22connection_speed%22%3A0.25%2C%22resilience%22%3A0.15%2C%22land_planning%22%3A0.1%2C%22latency%22%3A0.1%2C%22cooling%22%3A0.05%2C%22price_sensitivity%22%3A0.05%7D'

# URL-decoded custom_weights:
# {"capacity":0.3,"connection_speed":0.25,"resilience":0.15,"land_planning":0.1,"latency":0.1,"cooling":0.05,"price_sensitivity":0.05}
```

---

### 14.5 Financial Model Calculation

```bash
curl -X POST "https://infranodev2.onrender.com/api/financial-model" \
  -H "Content-Type: application/json" \
  -d '{
    "technology": "solar",
    "capacity_mw": 50.0,
    "capacity_factor": 12.0,
    "project_life": 25,
    "degradation": 0.005,
    "capex_per_kw": 800.0,
    "devex_abs": 500000.0,
    "devex_pct": 0.05,
    "opex_fix_per_mw_year": 15000.0,
    "opex_var_per_mwh": 2.0,
    "tnd_costs_per_year": 50000.0,
    "ppa_price": 65.0,
    "ppa_escalation": 0.025,
    "ppa_duration": 15,
    "merchant_price": 55.0,
    "capacity_market_per_mw_year": 10000.0,
    "ancillary_per_mw_year": 5000.0,
    "discount_rate": 0.08,
    "inflation_rate": 0.02,
    "tax_rate": 0.19,
    "grid_savings_factor": 0.8
  }'
```

---

## 15. Support & Documentation

### 15.1 Source Code Locations

**Main Files:**
- `/main.py` - API endpoints (2385 lines)
- `/backend/scoring.py` - Scoring algorithms (988 lines)
- `/backend/proximity.py` - Spatial calculations (360 lines)
- `/backend/power_workflow.py` - Power developer personas
- `/backend/renewable_model.py` - Financial model
- `/backend/financial_model_api.py` - Financial API wrapper

---

### 15.2 Contact

For backend issues, contact the development team or open an issue on GitHub.

---

## Appendix A: Persona Capacity Ranges

```python
PERSONA_CAPACITY_RANGES = {
    "edge_computing": {"min": 0.4, "max": 5},     # MW
    "colocation": {"min": 5, "max": 30},          # MW
    "hyperscaler": {"min": 30, "max": 250},       # MW
}

POWER_DEVELOPER_CAPACITY_RANGES = {
    "greenfield": {"min": 1, "max": 1000},        # MW
    "repower": {"min": 1, "max": 1000},           # MW
    "stranded": {"min": 1, "max": 1000},          # MW
}
```

---

## Appendix B: TNUoS Zone Reference

**27 TNUoS Zones** (GZ1 - GZ27):

| Zone | Name | Tariff (£/kW) | Region |
|------|------|---------------|--------|
| GZ1 | North Scotland | 15.32 | Scotland |
| GZ2 | South Scotland | 14.87 | Scotland |
| GZ3 | Borders | 13.45 | Scotland |
| ... | ... | ... | ... |
| GZ23 | London | -0.78 | England |
| GZ24 | South East England | -1.23 | England |
| GZ25 | Kent | -1.56 | England |
| GZ26 | Southern England | -1.89 | England |
| GZ27 | Solent | -2.34 | England |

**Note:** Negative tariffs indicate generation credit (favorable), positive tariffs indicate charges.

---

**END OF DOCUMENTATION**
