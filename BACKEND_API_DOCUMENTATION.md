# InfraNode Cloud Flow - Backend API Documentation

**Date:** 2025-11-17
**Version:** 2.1 - Persona-Based Infrastructure Scoring
**Framework:** FastAPI 0.104.1
**Production URL:** https://infranodev2.onrender.com
**Development URL:** http://localhost:8001

---

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [API Endpoints](#2-api-endpoints)
3. [Database Schema & Models](#3-database-schema--models)
4. [Business Logic & Algorithms](#4-business-logic--algorithms)
5. [External Data Sources](#5-external-data-sources)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Configuration & Environment](#7-configuration--environment)
8. [Performance & Caching](#8-performance--caching)
9. [Background Jobs](#9-background-jobs--scheduled-tasks)
10. [Error Handling](#10-error-handling--validation)
11. [Specific Data Structures](#11-specific-data-structures)
12. [Color Coding](#12-color-coding-for-visualization)
13. [Known Issues](#13-known-issues--notes)

---

## 1. Technology Stack

### Backend Framework
- **Framework:** FastAPI 0.104.1
- **Python Version:** 3.x
- **Server:** Uvicorn 0.24.0
- **Architecture:** Monolithic FastAPI application

### Key Dependencies
```
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.2          # HTTP client for Supabase
python-dotenv==1.0.0   # Environment variables
numpy==1.24.3          # Financial calculations
pandas==2.0.3          # Cashflow modeling
pydantic               # Data validation (via FastAPI)
```

### Database
- **Type:** PostgreSQL via Supabase
- **Access Method:** REST API (httpx, not direct SQL)
- **URL:** https://qoweiksrcooqrzssykbo.supabase.co
- **Authentication:** Anon key (read-only public access)

### Entry Point
`/home/user/infranodev2/main.py` (2384 lines)

---

## 2. API Endpoints

### 2.1 Core Endpoints

#### **GET /**
Root endpoint.

**Response:**
```json
{
  "message": "Infranodal API v2.1 with Persona-Based Scoring",
  "status": "active"
}
```

---

#### **GET /health**
Health check with database connectivity test.

**Response:**
```json
{
  "status": "healthy" | "degraded",
  "database": "connected" | "disconnected",
  "projects": 1234,
  "error": "error message if degraded"
}
```

---

### 2.2 Project Endpoints

#### **GET /api/projects**

Basic project listing with optional filters.

**Query Parameters:**
- `limit` (int, default: 5000): Number of projects to return
- `technology` (string, optional): Filter by technology type (partial, case-insensitive match)
- `country` (string, optional): Filter by country (partial, case-insensitive match)
- `persona` (PersonaType, optional): One of `hyperscaler`, `colocation`, `edge_computing`

**Response:** Array of project objects

**Notes:**
- Calculates investment ratings WITHOUT infrastructure proximity
- Uses dummy proximity scores for basic scoring

---

#### **GET /api/projects/geojson**

Get projects as GeoJSON FeatureCollection with basic scoring.

**Query Parameters:**
- `persona` (PersonaType, optional): `hyperscaler`, `colocation`, or `edge_computing`

**Limit:** Fixed at 500 projects

**Response:** GeoJSON FeatureCollection

**Properties included:**
- `ref_id`, `site_name`, `technology_type`, `operator`
- `capacity_mw`, `county`, `country`
- `investment_rating` (1.0-10.0 scale)
- `rating_description` (e.g., "Excellent", "Good")
- `color_code` (hex color for visualization)
- `component_scores` (object with individual criterion scores)
- `weighted_contributions` (weighted component scores)
- `persona` (if persona-based scoring used)
- `base_score`, `infrastructure_bonus`

---

#### **GET /api/projects/enhanced** ⭐ PRIMARY ENDPOINT

The most comprehensive project endpoint with full infrastructure proximity analysis.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 5000 | Number of projects to process |
| `persona` | PersonaType | null | `hyperscaler`, `colocation`, or `edge_computing` |
| `apply_capacity_filter` | bool | true | Filter by persona capacity requirements |
| `custom_weights` | JSON string | null | Custom criterion weights (overrides persona) |
| `scoring_method` | literal | "weighted_sum" | `weighted_sum` or `topsis` |
| `dc_demand_mw` | float | null | DC facility demand for capacity gating |
| `source_table` | string | "renewable_projects" | Source table name |
| `user_max_price_mwh` | float | null | User's maximum acceptable power price (£/MWh) |
| `user_ideal_mw` | float | null | User's preferred capacity (overrides persona default) |

**Features:**
- ✅ Batch proximity calculation for all valid projects
- ✅ Infrastructure caching with TTL (default 600 seconds)
- ✅ Capacity filtering by persona ranges
- ✅ Capacity gating based on minimum thresholds
- ✅ TNUoS enrichment for top projects
- ✅ TOPSIS scoring support as alternative

**Response Schema:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-1.234, 52.456]
      },
      "properties": {
        "ref_id": "abc123",
        "site_name": "Example Solar Farm",
        "technology_type": "solar",
        "operator": "Example Operator",
        "capacity_mw": 50.0,
        "development_status_short": "consented",
        "county": "Yorkshire",
        "country": "England",

        "investment_rating": 8.5,
        "rating_description": "Very Good",
        "color_code": "#33FF33",

        "component_scores": {
          "capacity": 85.2,
          "connection_speed": 78.3,
          "resilience": 65.0,
          "land_planning": 70.0,
          "latency": 82.5,
          "cooling": 91.2,
          "price_sensitivity": 88.0
        },

        "weighted_contributions": {
          "capacity": 20.8,
          "connection_speed": 13.1,
          "resilience": 8.6,
          "land_planning": 14.0,
          "latency": 4.6,
          "cooling": 13.1,
          "price_sensitivity": 4.9
        },

        "nearest_infrastructure": {
          "substation_km": 5.2,
          "transmission_km": 12.3,
          "fiber_km": 8.5,
          "ixp_km": 45.2,
          "water_km": 3.1
        },

        "persona": "hyperscaler",
        "persona_weights": {
          "capacity": 0.244,
          "connection_speed": 0.167,
          "resilience": 0.133,
          "land_planning": 0.200,
          "latency": 0.056,
          "cooling": 0.144,
          "price_sensitivity": 0.056
        },

        "base_score": 7.9,
        "infrastructure_bonus": 1.2,
        "internal_total_score": 85.0,

        "tnuos_zone_id": "GZ14",
        "tnuos_zone_name": "Yorkshire",
        "tnuos_tariff_pounds_per_kw": 2.45,
        "tnuos_score": 72.0,
        "tnuos_enriched": true,
        "rating_change": 0.3
      }
    }
  ],
  "metadata": {
    "scoring_system": "Hyperscaler Infrastructure Scoring",
    "scoring_method": "weighted_sum",
    "persona": "hyperscaler",
    "processing_time_seconds": 8.234,
    "projects_processed": 5000,
    "algorithm_version": "2.1 - Persona-Based Infrastructure Scoring",
    "performance_optimization": "Cached infrastructure + batch proximity scoring",
    "rating_distribution": {
      "excellent": 45,
      "very_good": 123,
      "good": 234,
      "above_average": 456,
      "average": 567,
      "below_average": 234,
      "poor": 123,
      "very_poor": 45,
      "bad": 23
    },
    "rating_scale_guide": {
      "excellent": "9.0-10.0",
      "very_good": "8.0-8.9",
      "good": "7.0-7.9",
      "above_average": "6.0-6.9",
      "average": "5.0-5.9",
      "below_average": "4.0-4.9",
      "poor": "3.0-3.9",
      "very_poor": "2.0-2.9",
      "bad": "0.0-1.9"
    }
  }
}
```

---

#### **POST /api/user-sites/score**

Score user-uploaded sites with full infrastructure proximity analysis.

**Request Body:** Array of UserSite objects
```json
[
  {
    "site_name": "My Solar Farm",
    "technology_type": "solar",
    "capacity_mw": 50.0,
    "latitude": 52.456,
    "longitude": -1.234,
    "commissioning_year": 2026,
    "is_btm": false,
    "capacity_factor": 0.12,
    "development_status_short": "planning"
  }
]
```

**Query Parameters:**
- `persona` (PersonaType, optional): Scoring persona

**Validation:**
- Coordinates must be within UK bounds (lat: 49.8-60.9, lon: -10.8 to 2.0)
- Capacity: 5-500 MW
- Commissioning year: 2025-2035

**Response:** Scored sites with full proximity data

---

#### **GET /api/projects/compare-scoring**

Compare renewable energy scoring vs persona-based scoring.

**Query Parameters:**
- `limit` (int, default: 10): Projects to compare
- `persona` (PersonaType, default: "hyperscaler"): Persona for comparison

**Response:** Comparison object with both scoring methodologies

---

#### **POST /api/projects/power-developer-analysis**

Analyze projects for power developers (greenfield, repower, stranded assets).

**Request Body:**
```json
{
  "criteria": {
    "capacity": 15,
    "connection_speed": 40,
    "resilience": 5,
    "land_planning": 10,
    "latency": 5,
    "cooling": 5,
    "price_sensitivity": 20
  },
  "site_location": {
    "latitude": 52.456,
    "longitude": -1.234
  }
}
```

**Query Parameters:**
- `target_persona` (string, optional): `greenfield`, `repower`, or `stranded`
- `limit` (int, default: 5000)
- `source_table` (string, default: "tec_connections"): Can also be "renewable_projects"

**Power Developer Personas:**

| Criterion | Greenfield | Repower | Stranded |
|-----------|------------|---------|----------|
| Capacity | 15% | 15% | 5% |
| Connection Speed | **40%** | 20% | 25% |
| Resilience | 5% | 12% | 10% |
| Land/Planning | 10% | 15% | 5% |
| Latency | 5% | 5% | 5% |
| Cooling | 5% | 3% | 5% |
| Price Sensitivity | 20% | 15% | **25%** |

**Response:** GeoJSON FeatureCollection with power developer scoring

---

#### **GET /api/projects/customer-match**

Find best customer matches for renewable projects.

**Query Parameters:**
- `target_customer` (PersonaType, default: "hyperscaler"): Target customer type
- `limit` (int, default: 5000)

**Logic:**
1. Filters projects by persona capacity range
2. Scores each project against all three personas (hyperscaler, colocation, edge_computing)
3. Returns `best_customer_match`, `customer_match_scores`, and `suitable_customers` (score >= 6.0)

**Response:** Projects with customer matching analysis

---

### 2.3 Infrastructure Endpoints

All infrastructure endpoints return GeoJSON FeatureCollections.

#### **GET /api/infrastructure/transmission**

Get transmission lines.

**Response:** FeatureCollection with LineString geometries

**Properties:**
- `name` (line_name)
- `voltage_kv`
- `operator`
- `type`: "transmission_line"

**Data Source:** `transmission_lines` table

---

#### **GET /api/infrastructure/substations**

Get substations.

**Response:** FeatureCollection with Point geometries

**Properties:**
- `name` / `substation_name`
- `operator`
- `primary_voltage_kv` / `voltage_kv`
- `capacity_mva`
- `constraint_status`
- `type`: "substation"

**Data Source:** `substations` table

---

#### **GET /api/infrastructure/gsp**

Get Grid Supply Point (GSP) boundaries.

**Response:** FeatureCollection with Polygon/MultiPolygon geometries

**Properties:**
- `name`
- `operator` (default: "NESO")
- `type`: "gsp_boundary"

**Data Source:** `electrical_grid` table where `type=gsp_boundary`

---

#### **GET /api/infrastructure/fiber**

Get fiber optic cable routes.

**Response:** FeatureCollection with LineString geometries

**Properties:**
- `name` (cable_name)
- `operator`
- `cable_type`
- `type`: "fiber_cable"

**Data Source:** `fiber_cables` table

**Note:** Cache limited to 200 records for performance

---

#### **GET /api/infrastructure/ixp**

Get Internet Exchange Points.

**Response:** FeatureCollection with Point geometries

**Properties:**
- `name` (ixp_name)
- `operator`
- `city`
- `networks` (connected_networks)
- `capacity_gbps`
- `type`: "ixp"

**Data Source:** `internet_exchange_points` table

---

#### **GET /api/infrastructure/water**

Get water resources.

**Response:** FeatureCollection with mixed geometries (Point or LineString)

**Properties:**
- `name` (resource_name)
- `resource_type`
- `water_quality`
- `flow_rate` (liters/sec)
- `capacity` (million liters)
- `type`: "water_resource"

**Data Source:** `water_resources` table

---

#### **GET /api/infrastructure/tnuos**

Get TNUoS (Transmission Network Use of System) zones.

**Response:** FeatureCollection with Polygon geometries

**Properties:**
- `zone_id` (GZ1-GZ27)
- `zone_name`
- `tariff_pounds_per_kw` (-3.0 to 16.0)
- `tariff_year` (e.g., "2024-25")
- `effective_from`
- `type`: "tnuos_zone"

**Data Source:** `tnuos_zones` table filtered by `tariff_year=2024-25`

**Note:** Also has hard-coded 27 zones with bounding boxes in main.py

---

#### **GET /api/infrastructure/dno-areas**

Get Distribution Network Operator (DNO) license areas.

**Response:** FeatureCollection with Polygon geometries

**Properties:**
- `id`
- `name` / `dno_name`
- `license_area`
- `company`
- `region`
- `type`: "dno_area"

**Data Source:** `dno_license_areas` table

---

### 2.4 TEC Connections Endpoint

#### **GET /api/tec/connections**

Get Transmission Entry Capacity (TEC) connections.

**Query Parameters:**
- `limit` (int, default: 1000, range: 1-5000)
- `search` (string, optional): Search in project_name (case-insensitive)
- `status` (string, optional): Filter by development_status
- `plant_type` (string, optional): Filter by technology_type

**Response Schema:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "123",
      "geometry": {
        "type": "Point",
        "coordinates": [-1.234, 52.456]
      },
      "properties": {
        "id": 123,
        "project_name": "Example Wind Farm",
        "operator": "National Grid",
        "customer_name": "Example Energy Ltd",
        "capacity_mw": 100.0,
        "mw_delta": 10.0,
        "technology_type": "wind",
        "plant_type": "Onshore Wind",
        "project_status": "Energised",
        "latitude": 52.456,
        "longitude": -1.234,
        "connection_site": "Example Substation",
        "substation_name": "Example 400kV",
        "voltage": 400.0,
        "constraint_status": "Constrained",
        "created_at": "2024-01-15T10:30:00Z",
        "agreement_type": "Connection Agreement",
        "effective_from": "2024-02-01T00:00:00Z"
      }
    }
  ],
  "count": 123
}
```

**Data Source:** `tec_connections` table

---

### 2.5 Financial Model Endpoint

#### **POST /api/financial-model**

Calculate financial models for renewable energy projects.

**Returns:** Both utility-scale and behind-the-meter (autoproducer) scenarios

**Request Schema:**
```json
{
  "technology": "solar_pv|wind|battery|solar_battery|wind_battery",
  "capacity_mw": 50.0,
  "capacity_factor": 0.12,
  "project_life": 25,
  "degradation": 0.005,

  "capex_per_kw": 800.0,
  "devex_abs": 50000.0,
  "devex_pct": 0.05,
  "opex_fix_per_mw_year": 25000.0,
  "opex_var_per_mwh": 2.5,
  "tnd_costs_per_year": 10000.0,

  "ppa_price": 55.0,
  "ppa_escalation": 0.025,
  "ppa_duration": 15,
  "merchant_price": 50.0,
  "capacity_market_per_mw_year": 15000.0,
  "ancillary_per_mw_year": 5000.0,

  "discount_rate": 0.08,
  "inflation_rate": 0.02,
  "tax_rate": 0.19,
  "grid_savings_factor": 0.3,

  "battery_capacity_mwh": 100.0,
  "battery_capex_per_mwh": 300000.0,
  "battery_cycles_per_year": 365
}
```

**Response Schema:**
```json
{
  "standard": {
    "irr": 12.5,
    "npv": 5234567.89,
    "cashflows": [
      -40000000,
      3456789,
      3567890,
      ...
    ],
    "breakdown": {
      "energyRev": 12345678.0,
      "capacityRev": 750000.0,
      "ancillaryRev": 250000.0,
      "gridSavings": 0.0,
      "opexTotal": 1500000.0
    },
    "lcoe": 48.5,
    "payback_simple": 11.5,
    "payback_discounted": 14.2
  },
  "autoproducer": {
    "irr": 15.2,
    "npv": 7890123.45,
    "cashflows": [...],
    "breakdown": {...},
    "lcoe": 42.3,
    "payback_simple": 9.8,
    "payback_discounted": 12.1
  },
  "metrics": {
    "total_capex": 42000000.0,
    "capex_per_mw": 840000.0,
    "irr_uplift": 2.7,
    "npv_delta": 2655555.56,
    "annual_generation": 52560.0
  },
  "success": true,
  "message": "Financial analysis completed successfully"
}
```

**Financial Model Details:**

**Standard Model (Utility-Scale):**
- PPA revenues (70% of generation under PPA contract)
- Merchant revenues (30% at wholesale prices)
- Capacity market payments
- Ancillary services revenues
- Battery arbitrage (if applicable)

**Autoproducer Model (Behind-the-Meter):**
- Retail electricity price savings
- Grid charges avoided
- Demand charge savings
- Export revenues at ~90% of wholesale price

**Calculation Methodology:**
- Annual generation with degradation: `generation × (1 - degradation)^(year - 1)`
- NPV calculated with discount rate
- IRR calculated using numpy's IRR or Newton-Raphson method
- LCOE = Present Value of Costs / Present Value of Generation
- Tax rate: 19% (UK corporation tax)
- Depreciation: Straight-line over project life

**Typical Capacity Factors:**
- Solar PV: 11-12% (UK)
- Onshore Wind: 30% (UK)
- Offshore Wind: 40-45%

---

#### **GET /api/financial-model/units**

Get units documentation for financial model fields.

**Response:**
```json
{
  "units": {
    "capacity_mw": "MW (Megawatts)",
    "capex_per_kw": "£/kW",
    "opex_fix_per_mw_year": "£/MW/year",
    "ppa_price": "£/MWh",
    "discount_rate": "decimal (e.g., 0.08 = 8%)",
    "irr": "percentage (as decimal)",
    "npv": "£ (British Pounds)",
    "lcoe": "£/MWh",
    ...
  }
}
```

---

### 2.6 Diagnostics Endpoint

#### **GET /api/diagnostics/site-scoring-log**

Get site scoring diagnostic logs.

**Query Parameters:** (not specified in code)

**Response:** Diagnostic logging information

**Note:** Limited implementation details available

---

## 3. Database Schema & Models

### 3.1 Database Configuration

**Type:** PostgreSQL via Supabase
**URL:** https://qoweiksrcooqrzssykbo.supabase.co
**Authentication:** Anon key (Bearer token)
**Access Method:** REST API via httpx (not direct SQL)

**Supabase Query Function:**
```python
async def query_supabase(
    endpoint: str,
    *,
    limit: Optional[int] = None,
    page_size: int = 1000
)
```

Features:
- Offset-limit pagination for large requests (page_size: 1000 records)
- Automatic pagination for limits > page_size
- 30-second timeout
- Bearer token authentication

---

### 3.2 Tables & Schema

#### **renewable_projects**

Primary table for renewable energy projects.

| Column | Type | Description |
|--------|------|-------------|
| `ref_id` | string | Unique identifier |
| `site_name` | string | Project site name |
| `project_name` | string | Official project name |
| `technology_type` | string | solar, wind, battery, hybrid, ccgt, etc. |
| `capacity_mw` | float | Generation capacity in MW |
| `latitude` | float | Latitude coordinate |
| `longitude` | float | Longitude coordinate |
| `county` | string | County location |
| `country` | string | Country (England, Scotland, Wales) |
| `operator` | string | Project operator/developer |
| `development_status_short` | string | operational, planning, consented, etc. |
| `development_status` | string | Full status description |
| `commissioning_year` | int | Expected/actual commissioning year |
| `capacity_factor` | float | Optional capacity factor (0-1) |
| `is_btm` | boolean | Behind-the-meter flag |

**Indexes:** Likely on lat/lon, technology_type, country

---

#### **tec_connections**

TEC (Transmission Entry Capacity) connection applications.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `project_name` | string | Project name |
| `operator` | string | Network operator |
| `customer_name` | string | Customer/developer name |
| `capacity_mw` | float | Connection capacity (MW) |
| `technology_type` | string | Technology type |
| `development_status` | string | Connection status |
| `constraint_status` | string | Constraint status |
| `connection_site` | string | Connection site name |
| `substation_name` | string | Substation name |
| `voltage` | float | Connection voltage (kV) |
| `latitude` | float | Latitude (or nested in location/coordinates) |
| `longitude` | float | Longitude (or nested in location/coordinates) |
| `created_at` | timestamp | Record creation date |
| `agreement_type` | string | Agreement type |
| `effective_from` | timestamp | Agreement effective date |

**Note:** Flexible coordinate field extraction via `extract_coordinates()` function

---

#### **substations**

Electrical substations.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `substation_name` / `name` | string | Substation name |
| `latitude` / `lat` / `Lat` | float | Latitude |
| `longitude` / `lon` / `Long` | float | Longitude |
| `operator` / `COMPANY` | string | Operating company |
| `primary_voltage_kv` / `voltage_kv` | float | Primary voltage (kV) |
| `capacity_mva` | float | Capacity (MVA) |
| `constraint_status` | string | Constraint status |

**Note:** Multiple column name variants supported

---

#### **transmission_lines**

High-voltage transmission lines.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `line_name` | string | Line name |
| `voltage_kv` | float | Voltage level (kV) |
| `operator` | string | Operating company |
| `path_coordinates` | JSON array | LineString coordinates: `[[lon, lat], ...]` |

---

#### **fiber_cables**

Fiber optic cable routes.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `cable_name` | string | Cable name |
| `operator` | string | Operating company |
| `cable_type` | string | Cable type |
| `route_coordinates` | JSON array | LineString coordinates |

**Cache Limit:** 200 records in infrastructure cache

---

#### **internet_exchange_points**

Internet Exchange Points (IXPs).

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `ixp_name` | string | IXP name |
| `operator` | string | Operating company |
| `city` | string | City location |
| `latitude` | float | Latitude |
| `longitude` | float | Longitude |
| `connected_networks` | int/array | Number of connected networks |
| `capacity_gbps` | float | Capacity (Gbps) |

---

#### **water_resources**

Water sources for cooling.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `resource_name` | string | Resource name |
| `resource_type` | string | river, reservoir, lake, etc. |
| `water_quality` | string | Water quality |
| `flow_rate_liters_sec` | float | Flow rate (L/s) |
| `capacity_million_liters` | float | Capacity (ML) |
| `coordinates` | JSON | Point `[lon, lat]` OR LineString `[[lon, lat], ...]` |

**Note:** Geometry can be Point or LineString

---

#### **tnuos_zones**

TNUoS (Transmission Network Use of System) tariff zones.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `zone_id` | string | Zone ID (GZ1, GZ2, ..., GZ27) |
| `zone_name` | string | Zone name (e.g., "North Scotland", "London") |
| `generation_tariff_pounds_per_kw` | float | Tariff (£/kW/year), range: -3.0 to 16.0 |
| `tariff_year` | string | Tariff year (e.g., "2024-25") |
| `effective_from` | date | Effective date |
| `geometry` | GeoJSON | Polygon geometry |

**Hard-coded zones:** 27 zones (GZ1-GZ27) also available in main.py with bounding boxes

---

#### **electrical_grid**

Electrical grid features (GSP boundaries).

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `name` | string | Feature name |
| `operator` | string | Operating company |
| `type` | string | Feature type (e.g., "gsp_boundary") |
| `geometry` | GeoJSON | Polygon/MultiPolygon geometry |

---

#### **dno_license_areas**

Distribution Network Operator (DNO) license areas.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `dno_name` | string | DNO name |
| `license_area` | string | License area name |
| `company` | string | Company name |
| `region` | string | Region |
| `geometry` | GeoJSON | Polygon geometry |

---

### 3.3 Pydantic Models

#### **UserSite**
```python
class UserSite(BaseModel):
    site_name: str
    technology_type: str
    capacity_mw: float  # Validated: 5-500 MW
    latitude: float  # Validated: 49.8-60.9
    longitude: float  # Validated: -10.8 to 2.0
    commissioning_year: int  # Validated: 2025-2035
    is_btm: bool
    capacity_factor: Optional[float] = None
    development_status_short: Optional[str] = "planning"
```

#### **FinancialModelRequest**
See Financial Model Endpoint section for complete schema.

#### **TecConnectionProperties**
See TEC Connections Endpoint section for complete schema.

---

## 4. Business Logic & Algorithms

### 4.1 Investment Rating Calculation (0-10 Scale)

**Internal Score:** 0-100 points
**Display Rating:** Internal Score / 10 → **0.0 to 10.0**

---

### 4.2 Two Scoring Systems

#### **A. Renewable Energy Scoring** (Default, no persona)

```
Base Score (0-85 points) = Weighted sum of:
  - Capacity (25%)
  - Development Stage (28%)
  - Technology (17%)
  - LCOE/Resource Quality (15%)
  - TNUoS Transmission Costs (15%)

Infrastructure Bonus (0-25 points) = Weighted sum of:
  - Grid Infrastructure (45%)
  - Digital Infrastructure (35%)
  - Water Resources (20%)

Total = min(100, Base Score + Infrastructure Bonus)
Display Rating = Total / 10
```

---

#### **B. Persona-Based Scoring** (With persona parameter)

```
Component Scores (each 0-100):
  1. Capacity
  2. Connection Speed
  3. Resilience
  4. Land/Planning
  5. Latency
  6. Cooling
  7. Price Sensitivity

Weighted Score = Σ(Component Score × Persona Weight)
Display Rating = Weighted Score / 10
```

---

### 4.3 Persona Weights

| Criterion | Hyperscaler | Colocation | Edge Computing |
|-----------|-------------|------------|----------------|
| Capacity | **24.4%** | 14.1% | 9.7% |
| Connection Speed | 16.7% | 16.3% | 12.9% |
| Resilience | 13.3% | **19.6%** | 10.8% |
| Land/Planning | 20.0% | 16.3% | **28.0%** |
| Latency | 5.6% | **21.7%** | **24.7%** |
| Cooling | **14.4%** | 8.7% | 5.4% |
| Price Sensitivity | 5.6% | 3.3% | 8.6% |
| **TOTAL** | 100% | 100% | 100% |

**Key Insights:**
- **Hyperscaler:** Prioritizes capacity (24.4%), land/planning (20%), cooling (14.4%)
- **Colocation:** Prioritizes latency (21.7%), resilience (19.6%)
- **Edge Computing:** Prioritizes land/planning (28%), latency (24.7%)

---

### 4.4 Component Score Calculations

#### **1. Capacity Score**

**Gaussian distribution centered on persona ideal capacity:**

```python
ideal_mw = persona_ideal_capacity  # e.g., 50 MW for hyperscaler
tolerance = ideal_mw × tolerance_factor  # 0.4-0.7 depending on persona

score = 100 × exp(-((capacity_mw - ideal_mw)² / (2 × tolerance²)))
```

**Persona Capacity Ranges:**
- **Edge Computing:** 0.4-5 MW (ideal: 2 MW, tolerance factor: 0.5)
- **Colocation:** 5-30 MW (ideal: 12 MW, tolerance factor: 0.6)
- **Hyperscaler:** 30-250 MW (ideal: 50 MW, tolerance factor: 0.7)

**Example:**
- 50 MW project for hyperscaler → score ≈ 100
- 30 MW project for hyperscaler → score ≈ 82
- 100 MW project for hyperscaler → score ≈ 50

---

#### **2. Connection Speed Score**

```python
stage_score = Development Stage Score (normalized to 15-100)
substation_score = 100 × exp(-distance_km / 30)
transmission_score = 100 × exp(-distance_km / 50)

final_score = 0.50 × stage_score + 0.30 × substation_score + 0.20 × transmission_score
```

**Components:**
- 50%: Development stage readiness
- 30%: Proximity to substation
- 20%: Proximity to transmission lines

---

#### **3. Resilience Score**

```python
backup_count = 0

if substation_km < 15:
    backup_count += 4
elif substation_km < 30:
    backup_count += 3

if transmission_km < 30:
    backup_count += 2

if technology in ['battery', 'BESS']:
    backup_count += 1

if 'hybrid' in technology:
    backup_count += 3

score = (backup_count / 10) × 100
```

**Maximum Score:** 100 (backup_count = 10)

---

#### **4. Land/Planning Score (Development Stage)**

**Lookup table:**

| Development Status | Score |
|--------------------|-------|
| No application required | 100 |
| Application submitted | 100 |
| Revised | 90 |
| Secretary of State granted | 80 |
| Consented | 70 |
| Granted | 70 |
| Planning expired | 70 |
| In planning | 55 |
| Appeal submitted | 45 |
| Awaiting construction | 40 |
| Under construction | 30 |
| Operational | 10 |
| Decommissioned | 0 |

---

#### **5. Latency Score (Digital Infrastructure)**

```python
fiber_score = 100 × exp(-fiber_km / 40)
ixp_score = 100 × exp(-ixp_km / 70)

final_score = 0.5 × (fiber_score + ixp_score)
```

**Half-distance values:**
- Fiber: 40 km
- IXP: 70 km

---

#### **6. Cooling Score (Water Resources)**

```python
score = 100 × exp(-water_km / 15)
```

**Half-distance:** 15 km

**Score examples:**
- 0 km: 100
- 10 km: 51
- 20 km: 26
- 30 km: 13

---

#### **7. Price Sensitivity Score**

**Estimated LCOE calculation:**

```python
# Base LCOE by technology (£/MWh)
base_lcoe = {
    'solar': 52,
    'wind': 68,
    'battery': 85,
    'hybrid': 60
}

# Adjust for capacity factor
reference_CF = 0.12  # Solar reference
adjusted_lcoe = base_lcoe × (reference_CF / actual_CF)

# Add TNUoS impact
tnuos_mwh_impact = (|tnuos_tariff| × 1000) / annual_capacity_hours
total_cost = adjusted_lcoe ± tnuos_mwh_impact

# Score calculation
if user_max_price_mwh provided:
    threshold = user_max_price_mwh × 0.9
    if total_cost <= threshold:
        score = 100
    elif total_cost <= user_max_price_mwh:
        score = 90
    else:
        overage_pct = (total_cost - user_max_price_mwh) / user_max_price_mwh
        score = max(0, 90 - overage_pct × 200)
else:
    # Normalize to 40-100 £/MWh range
    score = 100 × (1 - (total_cost - 40) / 60)
    score = max(0, min(100, score))
```

---

### 4.5 TNUoS Scoring

**TNUoS Tariff Range:** -3.0 to +16.0 £/kW/year
**Number of Zones:** 27 (GZ1-GZ27)
**Coverage:** North Scotland to Southern England

**Score Calculation:**
```python
if tariff <= -3.0:
    score = 100  # Best (subsidy)
elif tariff >= 16.0:
    score = 0    # Worst (high cost)
else:
    # Linear interpolation
    score = 100 × (1 - (tariff - (-3.0)) / (16.0 - (-3.0)))
```

**TNUoS Zone Examples:**
- **GZ1 (North Scotland):** ~-2.34 £/kW/year → score ≈ 100
- **GZ27 (London):** ~15.32 £/kW/year → score ≈ 3

**TNUoS Enrichment Process:**
1. Sort features by `investment_rating` (descending)
2. For each feature:
   - Find TNUoS zone by lat/lon (bounding box check)
   - Calculate TNUoS score from tariff
   - Add TNUoS score to `component_scores`
   - Recalculate weighted score with updated weights (normalize to sum to 1.0)
   - Update `investment_rating`
   - Track `rating_change`
3. Re-sort by new ratings

**Weight Adjustment:**
```python
# Add tnuos weight (e.g., 5% = 0.05)
total_weight = sum(persona_weights.values()) + 0.05
normalized_weights = {k: v / total_weight for k, v in persona_weights.items()}
normalized_weights['tnuos'] = 0.05 / total_weight
```

---

### 4.6 Infrastructure Distance Calculations

**Method:** Haversine formula (great-circle distance)
**Units:** Kilometers
**Calculation:** On-demand via spatial grid index

**Haversine Formula:**
```python
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    φ1 = radians(lat1)
    φ2 = radians(lat2)
    Δφ = radians(lat2 - lat1)
    Δλ = radians(lon2 - lon1)

    a = sin(Δφ/2)² + cos(φ1) × cos(φ2) × sin(Δλ/2)²
    c = 2 × atan2(sqrt(a), sqrt(1-a))

    return R × c
```

**Exponential Decay Scoring:**
```python
score = 100 × exp(-distance_km / half_distance_km)

if distance_km >= 200:
    score = 0  # Too far
```

**Half-Distance Values (km):**
- Substation: 35 km
- Transmission: 50 km
- Fiber: 40 km
- IXP: 70 km
- Water: 15 km

**At half-distance, score ≈ 37 (e^-1 × 100)**

---

### 4.7 Spatial Grid Index

**Cell Size:** 0.5 degrees (~55 km at UK latitudes)

**Index Structure:**
```python
grid_index = {
    (cell_lat, cell_lon): [infrastructure_points_in_cell]
}
```

**Query Strategy:**
1. Calculate cell coordinates for project location
2. Start with immediate cell (0-cell expansion)
3. If no infrastructure found, expand to neighboring cells
4. Adaptive expansion up to search radius
5. Early termination when match found

**Point-to-Line Distance:**
For transmission lines and fiber cables:
1. Iterate through line segments
2. Calculate perpendicular distance to each segment
3. Return minimum distance

---

### 4.8 TOPSIS Scoring (Alternative Method)

**TOPSIS:** Technique for Order of Preference by Similarity to Ideal Solution

**Steps:**
1. **Normalize** component scores (vector normalization):
   ```
   normalized_score = score / sqrt(Σ(score²))
   ```

2. **Apply weights** to normalized scores:
   ```
   weighted_score = normalized_score × weight
   ```

3. **Identify ideal solution** (max of each weighted component):
   ```
   ideal = {criterion: max(weighted_scores)}
   ```

4. **Identify anti-ideal solution** (min of each weighted component):
   ```
   anti_ideal = {criterion: min(weighted_scores)}
   ```

5. **Calculate Euclidean distance** to ideal and anti-ideal:
   ```
   distance_ideal = sqrt(Σ((weighted_score - ideal)²))
   distance_anti_ideal = sqrt(Σ((weighted_score - anti_ideal)²))
   ```

6. **Calculate closeness coefficient**:
   ```
   closeness = distance_anti_ideal / (distance_ideal + distance_anti_ideal)
   ```

7. **Scale to 1-10**:
   ```
   rating = 1 + closeness × 9
   ```

**Advantages of TOPSIS:**
- Considers distance from both ideal and anti-ideal solutions
- More nuanced than simple weighted sum
- Better discrimination between similar projects

---

### 4.9 Customer Matching Algorithm

**For `/api/projects/customer-match`:**

**Algorithm:**
1. Filter projects by target persona capacity range
2. For each project:
   - Score against **hyperscaler**, **colocation**, and **edge_computing** personas
   - If capacity outside persona range: assign score = 2.0 (penalty)
3. Select `best_customer_match` = persona with highest score
4. Identify `suitable_customers` = all personas with score >= 6.0

**Response fields added:**
- `best_customer_match`: "hyperscaler" | "colocation" | "edge_computing"
- `customer_match_scores`: {hyperscaler: 8.5, colocation: 7.2, edge_computing: 4.1}
- `suitable_customers`: ["hyperscaler", "colocation"]

---

## 5. External Data Sources

### 5.1 Infrastructure Data Sources

| Data Type | Source |
|-----------|--------|
| Transmission Lines | National Grid ESO / NESO |
| Substations | Distribution Network Operators (DNOs) |
| Fiber Cables | Telecoms infrastructure data |
| Internet Exchange Points (IXPs) | PeeringDB / industry sources |
| Water Resources | Environment Agency (EA) / SEPA |
| TNUoS Zones | National Grid ESO tariff data |
| DNO License Areas | Ofgem |

---

### 5.2 Project Data Sources

| Data Type | Source |
|-----------|--------|
| Renewable Projects | REPD (Renewable Energy Planning Database) |
| TEC Connections | National Grid ESO TEC register |

---

### 5.3 Financial Data Sources

| Data Type | Source |
|-----------|--------|
| Electricity Prices | Market data / user input |
| Capacity Market Prices | UK Government capacity market auctions |
| Retail Prices | User-configurable |
| TNUoS Tariffs | National Grid ESO |

---

### 5.4 Update Frequencies

| Component | Update Frequency |
|-----------|------------------|
| Infrastructure Cache | 600 seconds (10 minutes) - configurable via `INFRA_CACHE_TTL` |
| Database Updates | Manual/periodic (not specified in code) |

**Note:** No automated background jobs for data updates found in codebase.

---

## 6. Authentication & Authorization

### 6.1 REST API Authentication

❌ **NO AUTHENTICATION REQUIRED**

All `/api/*` endpoints are **publicly accessible** with no authentication.

---

### 6.2 CORS Policy

```python
allow_origins=["*"]
allow_methods=["*"]
allow_headers=["*"]
```

**All origins, methods, and headers allowed.**

---

### 6.3 Supabase Integration

**Backend Supabase Access:**
- Uses Supabase **anon key** (public, read-only access)
- **No user-specific authentication** in backend
- Frontend may handle user auth separately via Supabase client SDK

**Supabase is NOT used for backend authentication**, only for data storage.

---

### 6.4 Rate Limiting

❌ **Not implemented** in backend

---

### 6.5 Request Validation

✅ **Validation implemented:**
- Pydantic models for request bodies
- Query parameter type validation via FastAPI
- Geographic bounds checking (UK coordinates for user sites)
- Capacity and year range validation

**UserSite Validation:**
- Latitude: 49.8-60.9
- Longitude: -10.8 to 2.0
- Capacity: 5-500 MW
- Commissioning year: 2025-2035

---

## 7. Configuration & Environment

### 7.1 Environment Variables

**Required:**
```bash
SUPABASE_URL=https://qoweiksrcooqrzssykbo.supabase.co
SUPABASE_ANON_KEY=<anon_key>
```

**Optional:**
```bash
INFRA_CACHE_TTL=600  # Infrastructure cache TTL in seconds (default: 600)
```

---

### 7.2 Configuration Files

- **`.env`** - Environment variables (loaded via python-dotenv)
- **`requirements.txt`** - Python dependencies
- **`runtime.txt`** - Python version for deployment

---

### 7.3 Deployment

**Platform:** Render.com (inferred from production URL)

**URLs:**
- **Production:** https://infranodev2.onrender.com
- **Development:** http://localhost:8001

**Startup Scripts:**
- `start_backend.py` (for financial model API)
- `main.py` (main FastAPI app)

**Startup Command:**
```bash
python main.py
# OR
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Instances/Workers:** Not specified in code (likely single instance)

---

## 8. Performance & Caching

### 8.1 Caching Strategy

**InfrastructureCache Class:**
- **Type:** In-memory (asyncio lock-protected)
- **TTL:** `INFRASTRUCTURE_CACHE_TTL_SECONDS` (default: 600s / 10 minutes)

**Data Cached:**
- Substations (all records)
- Transmission lines (all records)
- Fiber cables (**limited to 200 records**)
- IXPs (all records)
- Water resources (all records)

**Cache Refresh:**
- Automatic on first request after TTL expiration
- Parallel loading via `asyncio.gather()`
- Spatial indices rebuilt on each refresh

**Spatial Index Performance:**
- Grid-based indexing (0.5° cell size)
- O(1) cell lookup
- Adaptive query expansion
- Early termination on match found

---

### 8.2 Database Optimization

**Pagination:**
- Supabase queries use offset-limit pagination
- Page size: 1000 records per request
- Automatic pagination for large datasets

**Indexes:**
- Not explicitly defined in code
- Likely indexes on lat/lon, technology_type, country in Supabase

**Materialized Views:**
- ❌ Not found in code

**Pre-aggregation:**
- ❌ Not found in code

---

### 8.3 Performance Characteristics

**Typical Response Times:**

| Endpoint | Response Time | Notes |
|----------|---------------|-------|
| `/health` | < 100ms | With DB check |
| `/api/projects/geojson` | ~500-1000ms | 500 projects, no proximity |
| `/api/projects/enhanced` | 5-15 seconds | 5000 projects with full proximity + TNUoS |
| `/api/user-sites/score` | 1-3 seconds | Depends on number of sites |
| Infrastructure endpoints | < 1 second | Cached data |

**Largest Datasets:**
- Renewable projects: ~5000-10000 records
- TEC connections: ~1000-5000 records
- Substations: ~1000 records
- Transmission lines: ~500 records

**Pagination:**
- `/api/projects/enhanced`: Configurable limit (default: 5000, max: not specified)
- `/api/tec/connections`: Configurable limit (default: 1000, max: 5000)

---

### 8.4 Performance Optimizations

1. **Batch proximity calculation:** Single pass through infrastructure catalog
2. **Spatial grid indexing:** Reduces distance calculation overhead
3. **Infrastructure caching:** Avoids repeated DB queries
4. **Capacity gating:** Filters projects before expensive proximity calculations
5. **Top-N TNUoS enrichment:** Only enriches top-rated projects
6. **Fiber cable limit:** Cache limited to 200 records (performance trade-off)

---

## 9. Background Jobs & Scheduled Tasks

### 9.1 Status

❌ **Not implemented in current codebase**

**No evidence of:**
- Celery / RQ / APScheduler
- Scheduled data updates
- Cache warming jobs
- Batch processing queues

---

### 9.2 Manual Data Update Scripts

**Likely separate scripts for data updates:**
- `fetch_network_data.py`
- `fetch_fiber_data`
- `fetch_tnuos_data.py`
- `import_projects.py`

**These are NOT integrated into the main API application.**

---

## 10. Error Handling & Validation

### 10.1 Standard Error Response Format

**FastAPI Default:**
```json
{
  "detail": "<error_message>"
}
```

**Custom Format (Financial Model):**
```json
{
  "success": false,
  "message": "<error_description>",
  "error_type": "<exception_class_name>"
}
```

---

### 10.2 HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (validation errors) |
| 500 | Internal Server Error (database errors, financial model errors) |

---

### 10.3 Input Validation

**Pydantic Models:**
- Automatic type validation
- Custom constraints via FastAPI Query parameters
- Optional/required field enforcement

**Validation Constraints:**

| Field | Constraint |
|-------|------------|
| User site latitude | 49.8-60.9 |
| User site longitude | -10.8 to 2.0 |
| User site capacity | 5-500 MW |
| User site commissioning year | 2025-2035 |
| TEC connections limit | 1-5000 |

---

### 10.4 Error Logging

**Current Implementation:**
- Print statements for diagnostic logging (not structured logging)
- Traceback printing on financial model errors
- Pragma comments: `# pragma: no cover` for exception handlers

**Error Tracking Tools:**
❌ No integration with Sentry, Rollbar, or similar tools found

---

## 11. Specific Data Structures

### 11.1 Enhanced Projects GeoJSON Response (Complete Schema)

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-1.234, 52.456]
      },
      "properties": {
        // ==================== BASIC PROJECT INFO ====================
        "ref_id": "abc123",
        "site_name": "Example Solar Farm",
        "technology_type": "solar",
        "operator": "Example Operator",
        "capacity_mw": 50.0,
        "development_status_short": "consented",
        "county": "Yorkshire",
        "country": "England",

        // ==================== INVESTMENT RATING ====================
        "investment_rating": 8.5,               // 0.0-10.0 scale
        "rating_description": "Very Good",      // Text description
        "color_code": "#33FF33",                // Hex color for map

        // ==================== COMPONENT SCORES (0-100 each) ====================
        "component_scores": {
          // Persona-based scoring components:
          "capacity": 85.2,
          "connection_speed": 78.3,
          "resilience": 65.0,
          "land_planning": 70.0,
          "latency": 82.5,
          "cooling": 91.2,
          "price_sensitivity": 88.0,

          // Renewable energy scoring components (if no persona):
          "development_stage": 70.0,
          "technology": 85.0,
          "lcoe_resource_quality": 80.0,
          "tnuos_transmission_costs": 72.0,
          "grid_infrastructure": 75.0,
          "digital_infrastructure": 82.5,
          "water_resources": 91.2
        },

        // ==================== WEIGHTED CONTRIBUTIONS ====================
        "weighted_contributions": {
          "capacity": 20.8,           // component_score × weight
          "connection_speed": 13.1,
          "resilience": 8.6,
          "land_planning": 14.0,
          "latency": 4.6,
          "cooling": 13.1,
          "price_sensitivity": 4.9
        },

        // ==================== INFRASTRUCTURE DISTANCES ====================
        "nearest_infrastructure": {
          "substation_km": 5.2,
          "transmission_km": 12.3,
          "fiber_km": 8.5,
          "ixp_km": 45.2,
          "water_km": 3.1
        },

        // ==================== PERSONA INFO ====================
        "persona": "hyperscaler",   // or "colocation", "edge_computing", null
        "persona_weights": {
          "capacity": 0.244,
          "connection_speed": 0.167,
          "resilience": 0.133,
          "land_planning": 0.200,
          "latency": 0.056,
          "cooling": 0.144,
          "price_sensitivity": 0.056
        },

        // Optional: Bayesian posterior weights (if adaptive weighting used)
        "posterior_persona_weights": {
          "capacity": 0.250,
          "connection_speed": 0.160,
          // ...
        },

        // ==================== SCORING BREAKDOWN ====================
        "base_score": 7.9,              // 1.0-10.0 (before infrastructure bonus)
        "infrastructure_bonus": 1.2,    // 0.0-2.5 (proximity bonus)
        "internal_total_score": 85.0,   // 0-100 (internal calculation)

        // ==================== TNUOS DATA (if enriched) ====================
        "tnuos_zone_id": "GZ14",
        "tnuos_zone_name": "Yorkshire",
        "tnuos_tariff_pounds_per_kw": 2.45,
        "tnuos_score": 72.0,            // 0-100
        "tnuos_enriched": true,
        "rating_change": 0.3,           // Change after TNUoS enrichment

        // ==================== TOPSIS METRICS (if scoring_method=topsis) ====================
        "topsis_metrics": {
          "distance_to_ideal": 0.234,
          "distance_to_anti_ideal": 0.876,
          "closeness_coefficient": 0.789,
          "weighted_normalized_scores": {
            "capacity": 0.123,
            "connection_speed": 0.098,
            // ...
          },
          "normalized_scores": {
            "capacity": 0.234,
            "connection_speed": 0.198,
            // ...
          }
        },
        "scoring_methodology": "TOPSIS with hyperscaler persona"
      }
    }
  ],

  // ==================== METADATA ====================
  "metadata": {
    "scoring_system": "Hyperscaler Infrastructure Scoring",
    "scoring_method": "weighted_sum",   // or "topsis"
    "persona": "hyperscaler",           // or null
    "processing_time_seconds": 8.234,
    "projects_processed": 5000,
    "algorithm_version": "2.1 - Persona-Based Infrastructure Scoring",
    "performance_optimization": "Cached infrastructure + batch proximity scoring",

    // Rating distribution
    "rating_distribution": {
      "excellent": 45,        // 9.0-10.0
      "very_good": 123,       // 8.0-8.9
      "good": 234,            // 7.0-7.9
      "above_average": 456,   // 6.0-6.9
      "average": 567,         // 5.0-5.9
      "below_average": 234,   // 4.0-4.9
      "poor": 123,            // 3.0-3.9
      "very_poor": 45,        // 2.0-2.9
      "bad": 23               // 0.0-1.9
    },

    // Rating scale guide
    "rating_scale_guide": {
      "excellent": "9.0-10.0",
      "very_good": "8.0-8.9",
      "good": "7.0-7.9",
      "above_average": "6.0-6.9",
      "average": "5.0-5.9",
      "below_average": "4.0-4.9",
      "poor": "3.0-3.9",
      "very_poor": "2.0-2.9",
      "bad": "0.0-1.9"
    },

    // TOPSIS-specific (if applicable)
    "topsis_ideal_solution": {
      "capacity": 100.0,
      "connection_speed": 100.0,
      // ...
    },
    "topsis_anti_ideal_solution": {
      "capacity": 0.0,
      "connection_speed": 0.0,
      // ...
    },
    "topsis_persona_reference": "hyperscaler"
  }
}
```

---

### 11.2 Financial Model Complete Schema

**Request Schema:**
```json
{
  // ==================== BASIC PROJECT INFO ====================
  "technology": "solar_pv|wind|battery|solar_battery|wind_battery",
  "capacity_mw": 50.0,
  "capacity_factor": 0.12,        // 0-1
  "project_life": 25,             // years
  "degradation": 0.005,           // annual degradation rate (0.5%)

  // ==================== COST INFORMATION ====================
  "capex_per_kw": 800.0,          // £/kW
  "devex_abs": 50000.0,           // £ absolute development costs
  "devex_pct": 0.05,              // % of capex for development costs
  "opex_fix_per_mw_year": 25000.0,   // £/MW/year
  "opex_var_per_mwh": 2.5,        // £/MWh
  "tnd_costs_per_year": 10000.0,  // £/year (TNUoS, DUoS, etc.)

  // ==================== REVENUE INFORMATION ====================
  "ppa_price": 55.0,              // £/MWh
  "ppa_escalation": 0.025,        // 2.5% annual escalation
  "ppa_duration": 15,             // years
  "merchant_price": 50.0,         // £/MWh
  "capacity_market_per_mw_year": 15000.0,  // £/MW/year
  "ancillary_per_mw_year": 5000.0,         // £/MW/year

  // ==================== FINANCIAL ASSUMPTIONS ====================
  "discount_rate": 0.08,          // 8% WACC
  "inflation_rate": 0.02,         // 2% annual inflation
  "tax_rate": 0.19,               // 19% (UK corporation tax)
  "grid_savings_factor": 0.3,     // 30% of retail price for grid savings

  // ==================== BATTERY INFO (optional) ====================
  "battery_capacity_mwh": 100.0,
  "battery_capex_per_mwh": 300000.0,  // £/MWh
  "battery_cycles_per_year": 365
}
```

**Response Schema:**
```json
{
  // ==================== STANDARD MODEL (Utility-Scale) ====================
  "standard": {
    "irr": 12.5,                  // % (as float, e.g., 12.5 = 12.5%)
    "npv": 5234567.89,            // £
    "cashflows": [
      -40000000,                  // Year 0 (CAPEX)
      3456789,                    // Year 1
      3567890,                    // Year 2
      // ... (project_life + 1 elements)
    ],
    "breakdown": {
      "energyRev": 12345678.0,    // £ (lifetime PPA + merchant)
      "capacityRev": 750000.0,    // £ (lifetime capacity market)
      "ancillaryRev": 250000.0,   // £ (lifetime ancillary services)
      "gridSavings": 0.0,         // £ (not applicable for standard)
      "opexTotal": 1500000.0      // £ (lifetime opex)
    },
    "lcoe": 48.5,                 // £/MWh
    "payback_simple": 11.5,       // years (nominal cashflows)
    "payback_discounted": 14.2    // years (discounted cashflows)
  },

  // ==================== AUTOPRODUCER MODEL (Behind-the-Meter) ====================
  "autoproducer": {
    "irr": 15.2,
    "npv": 7890123.45,
    "cashflows": [...],
    "breakdown": {
      "energyRev": 0.0,           // Not applicable
      "capacityRev": 0.0,         // Not applicable
      "ancillaryRev": 0.0,        // Not applicable
      "gridSavings": 15678900.0,  // £ (retail price savings)
      "opexTotal": 1200000.0      // £ (lower opex)
    },
    "lcoe": 42.3,
    "payback_simple": 9.8,
    "payback_discounted": 12.1
  },

  // ==================== COMPARISON METRICS ====================
  "metrics": {
    "total_capex": 42000000.0,    // £
    "capex_per_mw": 840000.0,     // £/MW
    "irr_uplift": 2.7,            // percentage points (autoproducer - standard)
    "npv_delta": 2655555.56,      // £ (autoproducer - standard)
    "annual_generation": 52560.0  // MWh/year
  },

  "success": true,
  "message": "Financial analysis completed successfully"
}
```

**Units Reference:**

| Field | Unit |
|-------|------|
| `capacity_mw` | MW (Megawatts) |
| `capacity_factor` | Decimal (0-1) |
| `capex_per_kw` | £/kW |
| `opex_fix_per_mw_year` | £/MW/year |
| `opex_var_per_mwh` | £/MWh |
| `ppa_price` | £/MWh |
| `merchant_price` | £/MWh |
| `capacity_market_per_mw_year` | £/MW/year |
| `discount_rate` | Decimal (e.g., 0.08 = 8%) |
| `irr` | Percentage as float (e.g., 12.5 = 12.5%) |
| `npv` | £ (British Pounds) |
| `lcoe` | £/MWh |
| `payback_simple` | Years |
| `payback_discounted` | Years |

**Default Values:**

| Parameter | Default |
|-----------|---------|
| PPA percentage | 70% |
| PPA duration | 15 years |
| Capacity derating | 1.0 |
| Tax rate | 19% (UK) |
| Inflation | 2% |
| Discount rate | 8% (user-configurable) |
| Solar degradation | 0.5% annually |
| Battery degradation | 2% annually |
| Battery efficiency | 90% round-trip |

**Revenue Formulas:**

```python
# PPA Revenue
ppa_revenue = generation × 0.70 × ppa_price × (1 + ppa_escalation)^(year-1)

# Merchant Revenue
merchant_revenue = generation × 0.30 × power_price × (1 + escalation)^(year-1)

# Capacity Revenue
capacity_revenue = capacity_mw × derating × capacity_payment × 1000

# Battery Arbitrage
battery_arbitrage = throughput × price_spread × efficiency

# BTM Energy Savings
btm_savings = generation × retail_price × (1 + retail_escalation)^(year-1)

# BTM Grid Savings
grid_savings = generation × grid_charges
```

**OPEX Formulas:**

```python
# Fixed O&M
fixed_om = capacity_mw × opex_per_mw_year × (1 + inflation)^(year-1)

# Insurance
insurance = capex_total × 0.01 × (1 + inflation)^(year-1)

# Land Lease (utility only)
land_lease = capacity_mw × 1000 × (1 + inflation)^(year-1)

# Battery Overhaul (every 10 years)
battery_overhaul = capacity_mwh × capex_per_mwh × 0.3
```

**Key Metrics:**

```python
# IRR: Newton-Raphson method or numpy.irr
irr = solve for r: Σ(cashflow_t / (1+r)^t) = 0

# NPV
npv = Σ(cashflow_t / (1 + discount_rate)^t)

# LCOE
lcoe = PV(costs) / PV(generation)

# Payback
payback_simple = years until Σ(nominal_cashflows) > 0
payback_discounted = years until Σ(discounted_cashflows) > 0
```

---

### 11.3 Business Criteria Schema

**Frontend sends:**
```typescript
{
  capacity: 24.4,              // 0-100 weight (as percentage)
  connection_speed: 16.7,
  resilience: 13.3,
  land_planning: 20.0,
  latency: 5.6,
  cooling: 14.4,
  price_sensitivity: 5.6
}
```

**Backend converts to:**
```python
{
  "capacity": 0.244,           # Decimal weights (sum = 1.0)
  "connection_speed": 0.167,
  "resilience": 0.133,
  "land_planning": 0.200,
  "latency": 0.056,
  "cooling": 0.144,
  "price_sensitivity": 0.056
}
```

**Application in scoring:**
```python
weighted_score = Σ(component_score[criterion] × weight[criterion])
investment_rating = weighted_score / 10
```

**Validation:**
- Sum of weights must equal 100 (when expressed as percentages)
- Sum of weights must equal 1.0 (when expressed as decimals)

---

## 12. Color Coding for Visualization

### 12.1 Rating → Color Mapping

| Rating Range | Color Code | Color Name | Description |
|--------------|------------|------------|-------------|
| 9.0-10.0 | `#00DD00` | Bright Green | Excellent |
| 8.0-8.9 | `#33FF33` | Light Green | Very Good |
| 7.0-7.9 | `#7FFF00` | Chartreuse | Good |
| 6.0-6.9 | `#CCFF00` | Yellow-Green | Above Average |
| 5.0-5.9 | `#FFFF00` | Yellow | Average |
| 4.0-4.9 | `#FFCC00` | Orange-Yellow | Below Average |
| 3.0-3.9 | `#FF9900` | Orange | Poor |
| 2.0-2.9 | `#FF6600` | Red-Orange | Very Poor |
| 1.0-1.9 | `#FF3300` | Red | Bad |
| 0.0-0.9 | `#CC0000` | Dark Red | Very Bad |

**Color Gradient:** Green (best) → Yellow → Orange → Red (worst)

---

## 13. Known Issues / Notes

### 13.1 Potential Bugs

1. **Function naming discrepancy:**
   - Code calls `enrich_and_rescore_top_25_with_tnuos()`
   - Function defined as `enrich_and_rescore_with_tnuos()`
   - Likely works due to Python aliasing or there's a wrapper function

---

### 13.2 Limitations

1. **No authentication:** All endpoints publicly accessible
2. **No rate limiting:** Potential for abuse
3. **Fiber cable limit:** Hard-coded to 200 records in cache (line 557 of main.py)
4. **No background jobs:** Data updates require manual script execution
5. **No structured logging:** Uses print statements instead of logging framework
6. **No error tracking:** No Sentry/Rollbar integration

---

### 13.3 Design Notes

1. **TNUoS enrichment:** Despite function name, processes ALL features (not just top 25)
2. **Power developer personas:** Separate from DC personas; weights must sum to 1.0
3. **Financial model:** Separate import; availability checked via `FINANCIAL_MODEL_AVAILABLE` flag
4. **Capacity filtering:** Applied before proximity calculation for performance
5. **TOPSIS scoring:** Optional alternative to weighted sum; provides more nuanced ranking

---

### 13.4 Future Improvements

1. Add authentication and rate limiting
2. Implement structured logging (e.g., Python logging module)
3. Add error tracking (Sentry integration)
4. Implement background jobs for data updates (Celery/APScheduler)
5. Add API versioning (/api/v1/, /api/v2/)
6. Implement database connection pooling
7. Add request caching (Redis)
8. Implement pagination for all large datasets
9. Add OpenAPI/Swagger documentation generation
10. Add unit tests and integration tests

---

## Appendix A: Persona Comparison

### Capacity Preferences

| Persona | Min MW | Max MW | Ideal MW | Tolerance Factor |
|---------|--------|--------|----------|------------------|
| Edge Computing | 0.4 | 5 | 2 | 0.5 |
| Colocation | 5 | 30 | 12 | 0.6 |
| Hyperscaler | 30 | 250 | 50 | 0.7 |

### Criterion Priorities (Ranked)

**Hyperscaler:**
1. Capacity (24.4%) ⭐
2. Land/Planning (20.0%)
3. Connection Speed (16.7%)
4. Cooling (14.4%)
5. Resilience (13.3%)
6. Latency (5.6%)
7. Price Sensitivity (5.6%)

**Colocation:**
1. Latency (21.7%) ⭐
2. Resilience (19.6%) ⭐
3. Connection Speed (16.3%)
4. Land/Planning (16.3%)
5. Capacity (14.1%)
6. Cooling (8.7%)
7. Price Sensitivity (3.3%)

**Edge Computing:**
1. Land/Planning (28.0%) ⭐
2. Latency (24.7%) ⭐
3. Connection Speed (12.9%)
4. Resilience (10.8%)
5. Capacity (9.7%)
6. Price Sensitivity (8.6%)
7. Cooling (5.4%)

---

## Appendix B: TNUoS Zone Reference

**27 TNUoS Zones (GZ1-GZ27):**

| Zone ID | Zone Name | Approx Tariff (£/kW/year) |
|---------|-----------|---------------------------|
| GZ1 | North Scotland | -2.34 |
| GZ2 | East Aberdeenshire | -1.56 |
| ... | ... | ... |
| GZ14 | Yorkshire | 2.45 |
| ... | ... | ... |
| GZ27 | London | 15.32 |

**Tariff Range:** -3.0 (subsidy) to +16.0 (charge)

**Geographic Coverage:** North Scotland (cheapest) to London/Southeast (most expensive)

---

## Appendix C: Technology Type Reference

**Common Technology Types:**
- `solar` / `solar_pv`
- `wind` / `onshore_wind` / `offshore_wind`
- `battery` / `BESS`
- `hybrid` / `solar_battery` / `wind_battery`
- `ccgt` (Combined Cycle Gas Turbine)
- `hydro`
- `biomass`
- `nuclear`

---

## Appendix D: Development Status Reference

**Development Status (Short):**
- `operational`
- `under_construction`
- `awaiting_construction`
- `consented`
- `granted`
- `planning`
- `in_planning`
- `application_submitted`
- `revised`
- `appeal_submitted`
- `planning_expired`
- `decommissioned`

---

## Appendix E: API Endpoint Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Root/status |
| `/health` | GET | Health check |
| `/api/projects` | GET | Basic project list |
| `/api/projects/geojson` | GET | Projects as GeoJSON (basic) |
| `/api/projects/enhanced` | GET | Projects with full analysis ⭐ |
| `/api/user-sites/score` | POST | Score user sites |
| `/api/projects/compare-scoring` | GET | Compare scoring methods |
| `/api/projects/power-developer-analysis` | POST | Power developer analysis |
| `/api/projects/customer-match` | GET | Customer matching |
| `/api/infrastructure/transmission` | GET | Transmission lines |
| `/api/infrastructure/substations` | GET | Substations |
| `/api/infrastructure/gsp` | GET | GSP boundaries |
| `/api/infrastructure/fiber` | GET | Fiber cables |
| `/api/infrastructure/ixp` | GET | Internet exchange points |
| `/api/infrastructure/water` | GET | Water resources |
| `/api/infrastructure/tnuos` | GET | TNUoS zones |
| `/api/infrastructure/dno-areas` | GET | DNO license areas |
| `/api/tec/connections` | GET | TEC connections |
| `/api/financial-model` | POST | Financial analysis |
| `/api/financial-model/units` | GET | Units documentation |
| `/api/diagnostics/site-scoring-log` | GET | Diagnostics |

---

**End of Documentation**

**Version:** 2.1
**Last Updated:** 2025-11-17
**Generated by:** Claude Code Backend Exploration Agent
