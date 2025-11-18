# InfraNode Backend API Documentation for Frontend

**Last Updated:** 2025-11-18
**API Version:** 2.1.0
**Framework:** FastAPI (Python)
**Deployment:** Render (https://infranodev2.onrender.com)
**Development:** http://localhost:8001

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Security](#authentication--security)
3. [API Endpoints](#api-endpoints)
4. [Data Models & Schemas](#data-models--schemas)
5. [Scoring Algorithms](#scoring-algorithms)
6. [Infrastructure Data](#infrastructure-data)
7. [Financial Model](#financial-model)
8. [Database & Supabase](#database--supabase)
9. [Performance & Caching](#performance--caching)
10. [Error Handling](#error-handling)
11. [Configuration](#configuration)
12. [Technology Stack](#technology-stack)

---

## Overview

The InfraNode backend is a Python FastAPI application that provides comprehensive scoring, analysis, and data retrieval for renewable energy projects and data center site selection. It integrates with Supabase for infrastructure data, implements sophisticated multi-persona scoring algorithms, and provides financial modeling capabilities.

### Key Responsibilities

- **Project Scoring:** Evaluates renewable energy projects using multiple personas (data center vs. power developer vs. custom criteria)
- **Infrastructure Proximity:** Calculates distances to transmission lines, fiber cables, substations, water resources, and IXP locations
- **Financial Modeling:** Calculates NPV, IRR, LCOE, and cashflows for solar, wind, battery, and hybrid projects
- **Data Access:** Provides GeoJSON-formatted project and infrastructure data via REST API
- **Batch Processing:** Efficiently scores hundreds or thousands of projects simultaneously

---

## Authentication & Security

### Current Status: **OPEN (NO AUTHENTICATION)**

- **All API endpoints are publicly accessible** - no authentication tokens required
- **CORS:** Enabled for all origins (`allow_origins=["*"]`)
- **Rate Limiting:** Not implemented
- **HTTPS:** Required in production (enforced by Render), optional in development

### Important

- The frontend does **NOT** send authentication tokens to the backend
- Supabase authentication is **frontend-only** via Supabase Anon Key
- Backend Supabase queries use backend credentials (service role key) stored in environment variables
- The frontend and backend operate independently from an authentication perspective

---

## API Endpoints

### 1. Health & System

#### `GET /`
**Description:** Homepage/status endpoint

**Response:**
```json
{
  "message": "InfraNode Cloud Flow API v2.1.0",
  "status": "operational",
  "timestamp": "2025-11-18T10:30:00Z"
}
```

#### `GET /health`
**Description:** Database connectivity check

**Response (Healthy):**
```json
{
  "status": "healthy",
  "database": "connected",
  "projects": 5000
}
```

**Response (Degraded):**
```json
{
  "status": "degraded",
  "database": "disconnected",
  "error": "Connection timeout"
}
```

---

### 2. Project Endpoints

#### `GET /api/projects`
**Description:** Retrieve raw project data with computed investment ratings

**Query Parameters:**
- `limit` (int, default: 5000) - Maximum number of projects to return
- `technology` (str, optional) - Filter by technology type (e.g., "solar", "wind")
- `country` (str, optional) - Filter by country (e.g., "GB", "IE")
- `persona` (str, optional) - Scoring persona: `hyperscaler`, `colocation`, `edge_computing`

**Response:**
```json
[
  {
    "ref_id": "REPD_12345",
    "site_name": "Example Solar Farm",
    "technology_type": "Solar PV",
    "capacity_mw": 50.0,
    "operator": "Green Energy Ltd",
    "latitude": 51.5,
    "longitude": -0.1,
    "county": "Greater London",
    "country": "GB",
    "investment_rating": 7.5,
    "rating_description": "Good",
    "color_code": "#7FFF00",
    "component_scores": {
      "capacity": 85.0,
      "connection_speed": 72.0,
      "resilience": 78.0,
      "land_planning": 65.0,
      "latency": 55.0,
      "cooling": 70.0,
      "price_sensitivity": 62.0
    },
    "weighted_contributions": {
      "capacity": 20.7,
      "connection_speed": 12.0,
      "resilience": 10.4,
      "land_planning": 13.0,
      "latency": 3.1,
      "cooling": 10.1,
      "price_sensitivity": 3.5
    },
    "persona": "hyperscaler",
    "base_score": 7.5,
    "infrastructure_bonus": 0.8
  }
]
```

**Performance:** 200-500ms for 5000 projects

---

#### `GET /api/projects/geojson`
**Description:** Retrieve projects as GeoJSON FeatureCollection

**Query Parameters:**
- `persona` (str, optional) - Scoring persona

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-0.1, 51.5]
      },
      "properties": {
        "ref_id": "REPD_12345",
        "site_name": "Example Solar Farm",
        "technology_type": "Solar PV",
        "capacity_mw": 50.0,
        "operator": "Green Energy Ltd",
        "county": "Greater London",
        "country": "GB",
        "investment_rating": 7.5,
        "rating_description": "Good",
        "color_code": "#7FFF00",
        "component_scores": { /* ... */ },
        "weighted_contributions": { /* ... */ },
        "persona": "hyperscaler",
        "base_score": 7.5,
        "infrastructure_bonus": 0.8
      }
    }
  ]
}
```

**Performance:** 300-800ms for 500 projects

---

#### `GET /api/projects/enhanced`
**Description:** Main endpoint for filtered, scored, and analyzed projects with advanced options

**Query Parameters:**
- `limit` (int, default: 5000) - Maximum projects to process
- `persona` (str, optional) - One of: `hyperscaler`, `colocation`, `edge_computing`
- `apply_capacity_filter` (bool, default: true) - Apply persona capacity thresholds
- `custom_weights` (str, optional) - JSON object with 7 criteria weights (will normalize)
- `scoring_method` (str, default: "weighted_sum") - One of: `weighted_sum`, `topsis`
- `dc_demand_mw` (float, optional) - Facility demand for capacity gating
- `source_table` (str, default: "renewable_projects") - Database table to query
- `user_max_price_mwh` (float, optional) - Max acceptable power price (£/MWh)
- `user_ideal_mw` (float, optional) - Preferred capacity (sets Gaussian peak)

**Example Custom Weights:**
```
custom_weights={"capacity":0.2,"connection_speed":0.15,"resilience":0.15,"land_planning":0.2,"latency":0.15,"cooling":0.1,"price_sensitivity":0.05}
```

**Response:** GeoJSON FeatureCollection with enhanced metadata
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { /* ... */ },
      "properties": {
        "ref_id": "REPD_12345",
        "site_name": "Example Solar Farm",
        "technology_type": "Solar PV",
        "capacity_mw": 50.0,
        "development_status_short": "in planning",
        "county": "Greater London",
        "country": "GB",
        "investment_rating": 7.5,
        "rating_description": "Good",
        "color_code": "#7FFF00",
        "component_scores": { /* 7 components */ },
        "weighted_contributions": { /* 7 components */ },
        "persona": "hyperscaler",
        "persona_weights": { /* 7 weights */ },
        "nearest_infrastructure": {
          "substation_km": 3.2,
          "transmission_km": 8.5,
          "fiber_km": 1.2,
          "ixp_km": 12.0,
          "water_km": 45.0,
          "gsp_km": 5.5,
          "dno_area": "Eastern"
        },
        "internal_total_score": 75.0,
        "scoring_methodology": "Persona weighted sum scoring (1.0-10.0 display scale)"
      }
    }
  ],
  "metadata": {
    "total_projects_processed": 5000,
    "projects_returned": 342,
    "scoring_system": "hyperscaler - 1.0-10.0 Investment Rating Scale",
    "persona": "hyperscaler",
    "processing_time_seconds": 3.45,
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
```

**TOPSIS Response (when `scoring_method=topsis`):**
Includes additional metrics in properties:
```json
"topsis_metrics": {
  "distance_to_ideal": 0.45,
  "distance_to_anti_ideal": 0.78,
  "closeness_coefficient": 0.634,
  "weighted_normalized_scores": { /* 7 components */ },
  "normalized_scores": { /* 7 components */ }
}
```

**Performance:** 2-5 seconds for 5000 projects (depending on proximity calculation)

---

#### `GET /api/projects/compare-scoring`
**Description:** Compare a single project using multiple personas

**Query Parameters:**
- `ref_id` (str, required) - Project reference ID
- `limit` (int, default: 1) - Not typically used

**Response:**
```json
{
  "project": {
    "ref_id": "REPD_12345",
    "site_name": "Example Solar Farm",
    "capacity_mw": 50.0,
    "latitude": 51.5,
    "longitude": -0.1
  },
  "scores": {
    "hyperscaler": {
      "investment_rating": 7.5,
      "rating_description": "Good",
      "component_scores": { /* ... */ },
      "weighted_contributions": { /* ... */ },
      "color_code": "#7FFF00"
    },
    "colocation": {
      "investment_rating": 6.2,
      "rating_description": "Above Average",
      "component_scores": { /* ... */ },
      "weighted_contributions": { /* ... */ },
      "color_code": "#CCFF00"
    },
    "edge_computing": {
      "investment_rating": 5.8,
      "rating_description": "Average",
      "component_scores": { /* ... */ },
      "weighted_contributions": { /* ... */ },
      "color_code": "#FFFF00"
    }
  },
  "best_fit_persona": "hyperscaler",
  "comparison_metadata": {
    "processing_time_seconds": 0.45
  }
}
```

**Performance:** 400-600ms per project

---

#### `GET /api/projects/customer-match`
**Description:** Find best-matching renewable projects for a specific site

**Query Parameters:**
- `latitude` (float, required) - Target latitude
- `longitude` (float, required) - Target longitude
- `persona` (str, optional) - Filter by persona
- `limit` (int, default: 5) - Number of matches to return

**Response:**
```json
{
  "target_location": {
    "latitude": 51.5,
    "longitude": -0.1
  },
  "matches": [
    {
      "ref_id": "REPD_12345",
      "site_name": "Example Solar Farm",
      "capacity_mw": 50.0,
      "latitude": 51.52,
      "longitude": -0.08,
      "investment_rating": 7.5,
      "distance_km": 3.2,
      "similarity_score": 0.92,
      "matched_criteria": {
        "capacity_match": true,
        "geography_match": true,
        "development_stage_match": true
      }
    }
  ],
  "metadata": {
    "total_matches_found": 12,
    "matches_returned": 5,
    "search_radius_km": 50.0
  }
}
```

**Performance:** 800ms-2s depending on search radius

---

#### `POST /api/projects/power-developer-analysis`
**Description:** Analyze projects as power developer (supply-side perspective)

**Request Body:**
```json
{
  "projects": [
    {
      "ref_id": "REPD_12345",
      "site_name": "Example Solar Farm",
      "capacity_mw": 50.0,
      "latitude": 51.5,
      "longitude": -0.1,
      "technology_type": "Solar PV",
      "development_status_short": "in planning"
    }
  ],
  "persona": "greenfield",
  "grid_capacity_mw": 100.0,
  "region": "East Anglia"
}
```

**Response:**
```json
{
  "persona_assigned": "greenfield",
  "capacity_category": "large",
  "analysis_results": [
    {
      "ref_id": "REPD_12345",
      "site_name": "Example Solar Farm",
      "capacity_mw": 50.0,
      "investment_rating": 7.8,
      "rating_description": "Good",
      "development_stage_score": 55.0,
      "power_developer_perspective": {
        "grid_connection_feasibility": 0.85,
        "revenue_potential": 0.78,
        "development_risk": 0.6,
        "timeline_months": 24
      }
    }
  ]
}
```

**Supported Power Developer Personas:**
- `greenfield` - New sites, typical 24-36 month development
- `repower` - Existing sites, faster timeline 12-18 months
- `stranded` - Partially developed sites, 6-12 months

**Performance:** 1-3 seconds depending on project count

---

### 3. User Site Scoring

#### `POST /api/user-sites/score`
**Description:** Score user-submitted sites with infrastructure proximity analysis

**Request Body:**
```json
{
  "sites": [
    {
      "site_name": "My Proposed Solar Farm",
      "technology_type": "Solar PV",
      "capacity_mw": 45.0,
      "latitude": 51.5,
      "longitude": -0.1,
      "commissioning_year": 2027,
      "is_btm": false,
      "capacity_factor": 0.14,
      "development_status_short": "planning"
    }
  ],
  "persona": "hyperscaler"
}
```

**Query Parameters:**
- `persona` (str, optional) - Scoring persona

**Request Validation:**
- Coordinates must be within UK bounds: 49.8°N-60.9°N, -10.8°W-2.0°E
- Capacity: 5-500 MW
- Commissioning year: 2025-2035

**Response:**
```json
{
  "sites": [
    {
      "site_name": "My Proposed Solar Farm",
      "technology_type": "Solar PV",
      "capacity_mw": 45.0,
      "commissioning_year": 2027,
      "is_btm": false,
      "coordinates": [-0.1, 51.5],
      "investment_rating": 7.2,
      "rating_description": "Good",
      "color_code": "#7FFF00",
      "component_scores": { /* 7 components */ },
      "weighted_contributions": { /* 7 components */ },
      "persona": "hyperscaler",
      "base_score": 7.2,
      "infrastructure_bonus": 0.5,
      "nearest_infrastructure": {
        "substation_km": 3.2,
        "transmission_km": 8.5,
        "fiber_km": 1.2,
        "ixp_km": 12.0,
        "water_km": 45.0,
        "gsp_km": 5.5,
        "dno_area": "Eastern"
      },
      "methodology": "persona-based scoring system"
    }
  ],
  "metadata": {
    "scoring_system": "persona-based - 1.0-10.0 Investment Rating Scale",
    "persona": "hyperscaler",
    "processing_time_seconds": 0.82,
    "algorithm_version": "2.1 - Persona-Based Infrastructure Proximity Enhanced",
    "rating_scale": { /* ... */ }
  }
}
```

**Error Responses:**
```json
{
  "detail": "Site 1: Coordinates outside UK bounds"
}
```

**Performance:** 500ms-2s for 10 sites

---

### 4. Infrastructure Endpoints

All infrastructure endpoints return GeoJSON FeatureCollections of point or line geometries.

#### `GET /api/infrastructure/substations`
**Description:** Retrieve electrical substations (point features)

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-0.1, 51.5]
      },
      "properties": {
        "name": "Example Substation",
        "voltage_kv": 275,
        "operator": "National Grid",
        "region": "South East",
        "capacity_mva": 500
      }
    }
  ]
}
```

**Properties Available:**
- `name` - Substation name
- `voltage_kv` - Voltage level (e.g., 132, 275, 400)
- `operator` - Network operator
- `region` - Geographic region
- `capacity_mva` - Transmission capacity

**Performance:** 200-400ms, ~4000 features

---

#### `GET /api/infrastructure/transmission`
**Description:** Retrieve transmission line data (line features)

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[-0.1, 51.5], [-0.15, 51.52], [-0.2, 51.55]]
      },
      "properties": {
        "name": "Example Transmission Line",
        "voltage_kv": 400,
        "operator": "National Grid",
        "length_km": 45.2,
        "capacity_mw": 2000,
        "status": "operational"
      }
    }
  ]
}
```

**Properties Available:**
- `name` - Line identifier
- `voltage_kv` - Voltage level
- `operator` - Network operator
- `length_km` - Line length
- `capacity_mw` - Transmission capacity
- `status` - operational, planned, decommissioned

**Performance:** 300-500ms, ~500 features

---

#### `GET /api/infrastructure/fiber`
**Description:** Retrieve fiber optic cable routes (line features)

**Limitations:** Limited to top 200 routes (sorted by importance)

**Response:** GeoJSON LineString features with properties:
- `route_name` - Cable identifier
- `operator` - Operator name
- `bandwidth_tbps` - Total bandwidth
- `path_type` - onshore, submarine, mixed
- `operational_date` - Commission date

**Performance:** 200-350ms, ~200 features (capped)

---

#### `GET /api/infrastructure/ixp`
**Description:** Retrieve Internet Exchange Point locations (point features)

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-0.08, 51.52]
      },
      "properties": {
        "name": "LINX LoNAP",
        "operator": "LINX",
        "city": "London",
        "peering_count": 850,
        "capacity_gbps": 20000
      }
    }
  ]
}
```

**Performance:** 150-300ms, ~40-50 features

---

#### `GET /api/infrastructure/water`
**Description:** Retrieve water resource locations (point features)

**Response:** GeoJSON Point features with properties:
- `name` - Water resource name
- `type` - river, reservoir, groundwater, tidal
- `region` - Geographic region
- `capacity_m3` - Water volume capacity
- `abstraction_license` - License status

**Performance:** 200-350ms, ~1500 features

---

#### `GET /api/infrastructure/gsp`
**Description:** Retrieve Grid Supply Point boundaries (polygon features)

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-0.1, 51.5], [-0.05, 51.5], [-0.05, 51.55], [-0.1, 51.55], [-0.1, 51.5]]]
      },
      "properties": {
        "gsp_code": "GSP001",
        "gsp_name": "Example GSP",
        "region": "South East",
        "dno": "SEEL"
      }
    }
  ]
}
```

**Properties Available:**
- `gsp_code` - GSP identifier
- `gsp_name` - GSP name
- `region` - Geographic region
- `dno` - Distribution Network Operator

**Performance:** 250-400ms, ~370 features

---

#### `GET /api/infrastructure/tnuos`
**Description:** Retrieve TNUoS (Transmission Network Use of System) zones

**Response:** GeoJSON Polygon features with 27 hardcoded zones

**Properties Returned:**
- `zone_id` - GZ1-GZ27
- `zone_name` - Zone name (e.g., "North Scotland")
- `generation_tariff_pounds_per_kw` - Annual tariff
- `tariff_type` - "positive" or "negative" (negative = payment to generator)

**TNUoS Zone Details (Sample):**
| Zone | Name | Tariff (£/kW/year) |
|------|------|-------------------|
| GZ1  | North Scotland | +15.32 |
| GZ8  | Central Belt | +8.92 |
| GZ21 | South West England | -0.12 |
| GZ23 | London | -0.78 |

**Performance:** <50ms (hardcoded)

---

#### `GET /api/infrastructure/dno-areas`
**Description:** Retrieve DNO (Distribution Network Operator) area boundaries

**Response:** GeoJSON Polygon features

**Properties Available:**
- `dno_code` - Operator code
- `dno_name` - Full operator name
- `region` - Geographic region
- `customer_count` - Number of customers

**Performance:** 200-350ms, ~14 features

---

### 5. TEC Connections

#### `GET /api/tec/connections`
**Description:** Retrieve TEC (Transmission Entry Capacity) connections for projects

**Query Parameters:**
- `ref_id` (str, optional) - Filter by project reference
- `status` (str, optional) - Filter by status (active, pending, completed)
- `limit` (int, default: 1000) - Maximum records to return

**Response:**
```json
{
  "connections": [
    {
      "ref_id": "REPD_12345",
      "connection_id": "TEC_001",
      "site_name": "Example Solar Farm",
      "connection_type": "Transmission",
      "capacity_mw": 50.0,
      "entry_point": "Example Substation",
      "status": "active",
      "queue_position": 5,
      "estimated_connection_date": "2027-06-30",
      "application_date": "2024-01-15",
      "capacity_location": "GSP001"
    }
  ],
  "metadata": {
    "total_connections": 1,
    "request_parameters": {
      "ref_id": "REPD_12345"
    }
  }
}
```

**Performance:** 400-800ms for typical queries

---

### 6. Financial Model

#### `POST /api/financial-model`
**Description:** Calculate financial metrics (NPV, IRR, LCOE, cashflows)

**Request Body:**
```json
{
  "technology": "Solar PV",
  "capacity_mw": 50.0,
  "capacity_factor": 0.14,
  "project_life": 25,
  "degradation": 0.5,
  "capex_per_kw": 800.0,
  "devex_abs": 500000.0,
  "devex_pct": 0.0,
  "opex_fix_per_mw_year": 12000.0,
  "opex_var_per_mwh": 1.5,
  "tnd_costs_per_year": 50000.0,
  "ppa_price": 65.0,
  "ppa_escalation": 2.5,
  "ppa_duration": 15,
  "merchant_price": 75.0,
  "capacity_market_per_mw_year": 5000.0,
  "ancillary_per_mw_year": 2000.0,
  "discount_rate": 8.0,
  "inflation_rate": 2.0,
  "tax_rate": 0.19,
  "grid_savings_factor": 0.0,
  "battery_capacity_mwh": null,
  "battery_capex_per_mwh": null,
  "battery_cycles_per_year": null
}
```

**Field Descriptions:**

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| technology | str | - | Solar PV, Wind Onshore, Wind Offshore, Battery, Hybrid |
| capacity_mw | float | MW | Project capacity |
| capacity_factor | float | - | 0.0-1.0 (14% for solar, 35-45% for wind) |
| project_life | int | years | Typically 25-30 |
| degradation | float | % per year | Annual performance loss |
| capex_per_kw | float | £/kW | Capital expenditure |
| devex_abs | float | £ | Development costs (absolute) |
| devex_pct | float | % of capex | Development costs (percentage) |
| opex_fix_per_mw_year | float | £/MW/year | Fixed operating costs |
| opex_var_per_mwh | float | £/MWh | Variable operating costs |
| tnd_costs_per_year | float | £/year | Transmission & distribution costs |
| ppa_price | float | £/MWh | Power purchase agreement price |
| ppa_escalation | float | % per year | PPA price escalation |
| ppa_duration | int | years | PPA contract duration |
| merchant_price | float | £/MWh | Merchant power price (post-PPA) |
| capacity_market_per_mw_year | float | £/MW/year | Capacity market revenue (if eligible) |
| ancillary_per_mw_year | float | £/MW/year | Grid services/ancillary revenue |
| discount_rate | float | % per year | Financial discount rate (WACC) |
| inflation_rate | float | % per year | General inflation rate |
| tax_rate | float | - | 0-1.0 (typically 0.19 for 19%) |
| grid_savings_factor | float | - | 0-1.0 for grid connection savings |
| battery_capacity_mwh | float | MWh | Optional battery storage capacity |
| battery_capex_per_mwh | float | £/MWh | Battery capital cost |
| battery_cycles_per_year | int | cycles | Battery cycling rate |

**Response:**
```json
{
  "standard": {
    "irr": 12.5,
    "npv": 8500000.0,
    "cashflows": [
      -52000000.0,
      4200000.0,
      4312000.0,
      4428320.0,
      ...
    ],
    "breakdown": {
      "energyRev": 52500000.0,
      "capacityRev": 6250000.0,
      "ancillaryRev": 2500000.0,
      "gridSavings": 0.0,
      "opexTotal": 11850000.0
    },
    "lcoe": 48.5,
    "payback_simple": 9.8,
    "payback_discounted": 11.2
  },
  "autoproducer": {
    "irr": 14.2,
    "npv": 9200000.0,
    "cashflows": [
      -52000000.0,
      4650000.0,
      4761500.0,
      4879145.0,
      ...
    ],
    "breakdown": {
      "energyRev": 58500000.0,
      "capacityRev": 6250000.0,
      "ancillaryRev": 2500000.0,
      "gridSavings": 1200000.0,
      "opexTotal": 10500000.0
    },
    "lcoe": 45.2,
    "payback_simple": 8.9,
    "payback_discounted": 10.1
  },
  "metrics": {
    "profitability_index": 1.18,
    "equity_irr": 18.5,
    "debt_service_coverage_ratio": 1.45
  },
  "success": true,
  "message": "Financial model calculated successfully"
}
```

**Response Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| irr | float | Internal Rate of Return (%) |
| npv | float | Net Present Value (£) |
| cashflows | list[float] | Year-by-year cashflows |
| lcoe | float | Levelized Cost of Energy (£/MWh) |
| payback_simple | float | Simple payback period (years) |
| payback_discounted | float | Discounted payback period (years) |
| breakdown.energyRev | float | Total energy revenue (£) |
| breakdown.capacityRev | float | Capacity market revenue (£) |
| breakdown.ancillaryRev | float | Grid services revenue (£) |
| breakdown.gridSavings | float | Grid connection savings (£) |
| breakdown.opexTotal | float | Total operating expenses (£) |

**Scenarios:**
- **Standard:** Utility-scale scenario with PPA revenue
- **Autoproducer:** Behind-the-meter scenario with grid savings and self-consumption

**Supported Technologies:**
- Solar PV (capacity factor: 10-18%)
- Wind Onshore (capacity factor: 30-45%)
- Wind Offshore (capacity factor: 40-55%)
- Battery Storage (4-6 hour duration)
- Hybrid (Solar + Wind)

**Performance:** 100-200ms per calculation

---

#### `GET /api/financial-model/units`
**Description:** Retrieve default units and parameter ranges for financial modeling

**Response:**
```json
{
  "technologies": ["Solar PV", "Wind Onshore", "Wind Offshore", "Battery", "Hybrid"],
  "parameters": {
    "capacity_mw": {
      "unit": "MW",
      "min": 0.1,
      "max": 1000.0,
      "default": 50.0
    },
    "capacity_factor": {
      "unit": "-",
      "min": 0.0,
      "max": 1.0,
      "default": 0.14
    },
    "project_life": {
      "unit": "years",
      "min": 5,
      "max": 50,
      "default": 25
    },
    "capex_per_kw": {
      "unit": "£/kW",
      "min": 200.0,
      "max": 5000.0,
      "default": 800.0
    },
    "discount_rate": {
      "unit": "%",
      "min": 3.0,
      "max": 20.0,
      "default": 8.0
    },
    "ppa_price": {
      "unit": "£/MWh",
      "min": 20.0,
      "max": 150.0,
      "default": 65.0
    }
  }
}
```

**Performance:** <50ms

---

## Data Models & Schemas

### Core Data Models

#### UserSite (Request Model)
```python
class UserSite(BaseModel):
    site_name: str                          # Required: Site identifier
    technology_type: str                    # Required: Solar PV, Wind, Battery, etc.
    capacity_mw: float                      # Required: 5-500 MW
    latitude: float                         # Required: 49.8-60.9
    longitude: float                        # Required: -10.8 to 2.0
    commissioning_year: int                 # Required: 2025-2035
    is_btm: bool                           # Required: Behind-the-meter flag
    capacity_factor: Optional[float] = None # Annual capacity factor 0-1.0
    development_status_short: Optional[str] = "planning"  # Planning status
```

#### FinancialModelRequest
```python
class FinancialModelRequest(BaseModel):
    technology: str                         # Technology type
    capacity_mw: float                      # Project capacity (MW)
    capacity_factor: float                  # Annual capacity factor (0-1)
    project_life: int                       # Project life (years)
    degradation: float                      # Annual degradation (%)
    capex_per_kw: float                     # Capital cost (£/kW)
    devex_abs: float                        # Development cost (£)
    devex_pct: float                        # Dev as % of capex
    opex_fix_per_mw_year: float            # Fixed opex (£/MW/year)
    opex_var_per_mwh: float                # Variable opex (£/MWh)
    tnd_costs_per_year: float              # T&D costs (£/year)
    ppa_price: float                        # PPA price (£/MWh)
    ppa_escalation: float                   # PPA escalation (%)
    ppa_duration: int                       # PPA duration (years)
    merchant_price: float                   # Merchant price (£/MWh)
    capacity_market_per_mw_year: float     # Capacity market (£/MW/year)
    ancillary_per_mw_year: float           # Ancillary services (£/MW/year)
    discount_rate: float                    # WACC (%)
    inflation_rate: float                   # Inflation rate (%)
    tax_rate: float = 0.19                 # Tax rate (default 19%)
    grid_savings_factor: float              # Grid savings factor (0-1)
    battery_capacity_mwh: Optional[float]  # Battery size (MWh)
    battery_capex_per_mwh: Optional[float] # Battery cost (£/MWh)
    battery_cycles_per_year: Optional[int] # Battery cycles/year
```

### Project Base Model
```python
# From Supabase renewable_projects table:
{
    "ref_id": str,                  # Unique identifier
    "site_name": str,               # Project name
    "technology_type": str,         # Solar PV, Wind, Hydro, etc.
    "capacity_mw": float,           # Installed capacity
    "latitude": float,              # Geographic location
    "longitude": float,
    "operator": str,                # Project operator
    "county": str,                  # County/region
    "country": str,                 # Country code
    "development_status_short": str, # Planning status
    "commissioning_year": int,      # Expected commission year
    "capacity_factor": Optional[float],  # Annual capacity factor
    "grid_connection_status": str,  # Grid connection status
    "connection_point": Optional[str], # GSP or substation
    "is_btm": bool                  # Behind-the-meter indicator
}
```

---

## Scoring Algorithms

### Overview

The backend implements three distinct scoring systems:

1. **Renewable Energy Scoring** - Default system for renewable projects
2. **Data Center Persona Scoring** - Three personas: hyperscaler, colocation, edge_computing
3. **Power Developer Scoring** - Supply-side perspective: greenfield, repower, stranded

### Rating Scale

**Display Scale:** 1.0 - 10.0 (shown to frontend)
**Internal Scale:** 0 - 100 (used internally)
**Conversion:** display = internal / 10

| Display | Internal | Description |
|---------|----------|-------------|
| 9.0-10.0 | 90-100 | Excellent - Premium opportunity |
| 8.0-8.9 | 80-89 | Very Good - Strong potential |
| 7.0-7.9 | 70-79 | Good - Solid opportunity |
| 6.0-6.9 | 60-69 | Above Average - Moderate potential |
| 5.0-5.9 | 50-59 | Average - Standard opportunity |
| 4.0-4.9 | 40-49 | Below Average - Limited appeal |
| 3.0-3.9 | 30-39 | Poor - Challenges |
| 2.0-2.9 | 20-29 | Very Poor - High risk |
| 1.0-1.9 | 10-19 | Bad - Unfavorable |

### Data Center Persona Scoring

#### Personas

**1. Hyperscaler**
- **Typical Facilities:** 30-250 MW
- **Target Use Cases:** Large cloud data centers, AI training clusters
- **Weighting:**
  - Capacity: 24.4%
  - Connection Speed: 16.7%
  - Resilience: 13.3%
  - Land Planning: 20.0%
  - Latency: 5.6%
  - Cooling: 14.4%
  - Price Sensitivity: 5.6%

**2. Colocation**
- **Typical Facilities:** 5-30 MW
- **Target Use Cases:** Shared data centers, edge colocation
- **Weighting:**
  - Capacity: 14.1%
  - Connection Speed: 16.3%
  - Resilience: 19.6%
  - Land Planning: 16.3%
  - Latency: 21.7% (highest)
  - Cooling: 8.7%
  - Price Sensitivity: 3.3%

**3. Edge Computing**
- **Typical Facilities:** 0.4-5 MW
- **Target Use Cases:** Distributed edge compute, telecom centers
- **Weighting:**
  - Capacity: 9.7% (lowest)
  - Connection Speed: 12.9%
  - Resilience: 10.8%
  - Land Planning: 28.0% (highest)
  - Latency: 24.7% (highest)
  - Cooling: 5.4%
  - Price Sensitivity: 8.6%

#### Seven Scoring Components

##### 1. Capacity Component
**Scoring Function:** Gaussian distribution centered on ideal capacity

**Formula:**
```
capacity_score = 100 * exp(-((capacity_mw - ideal_mw)² / (2 * tolerance²)))
```

**Parameters by Persona:**

| Persona | Min (MW) | Ideal (MW) | Max (MW) | Tolerance |
|---------|----------|-----------|---------|-----------|
| hyperscaler | 20 | 50 | 200 | 20 (tolerance_factor=0.4) |
| colocation | 4 | 12 | 25 | 6 (tolerance_factor=0.5) |
| edge_computing | 0.3 | 2 | 5 | 1.4 (tolerance_factor=0.7) |

**Characteristics:**
- Projects at ideal_mw score 100
- Score drops as capacity moves away from ideal
- Steepness controlled by tolerance_factor
- User can override ideal_mw with `user_ideal_mw` parameter

**Example:**
```
Hyperscaler ideal = 50 MW, tolerance = 20 MW
- 50 MW project: score = 100
- 40 MW project: score = 97.5
- 30 MW project: score = 90
- 100 MW project: score = 61
```

**Capacity Gating:**
If `apply_capacity_filter=true`, projects outside persona capacity range are filtered out pre-scoring:
- Hyperscaler: < 30 MW filtered
- Colocation: < 5 MW filtered
- Edge Computing: < 0.4 MW filtered

---

##### 2. Connection Speed Component
**Scoring Function:** Composite of development stage, substation proximity, and transmission proximity

**Formula:**
```
connection_score = (0.50 * dev_stage_score) + (0.30 * substation_score) + (0.20 * transmission_score)
```

**Sub-components:**

**a) Development Stage Score (0-100)**
Maps planning status to scores:

| Status | Score | Notes |
|--------|-------|-------|
| Operational | 10 | Already built (poor for new capacity) |
| Consented | 70 | Planning approved |
| Application Submitted | 100 | Active application |
| In Planning | 55 | Under review |
| No Application Made | 45 | Pre-planning stage |
| Application Refused | 30 | Rejected previously |

**b) Substation Score (0-100)**
Based on distance to nearest substation:

**Formula:**
```
substation_score = 100 * exp(-distance_km / half_distance_km)
substation_half_distance = 35 km
```

**Distance to Score Mapping:**
```
0 km:   100.0 (at substation)
5 km:   87.3
10 km:  75.9
35 km:  36.8 (half-score point)
50 km:  20.0
100 km: 1.4
```

**c) Transmission Score (0-100)**
Based on distance to nearest transmission line:

**Formula:**
```
transmission_score = 100 * exp(-distance_km / half_distance_km)
transmission_half_distance = 50 km
```

**Distance to Score Mapping:**
```
0 km:   100.0
10 km:  81.9
50 km:  36.8 (half-score point)
100 km: 13.5
```

---

##### 3. Resilience Component
**Scoring Function:** Discrete scoring based on count of nearby infrastructure points

**Definition:** Count of each infrastructure type within threshold distances:

| Infrastructure | Threshold (km) | Weight |
|---------------|---|--------|
| Substations | 50 | 40% |
| Transmission nodes | 100 | 30% |
| Fiber junction points | 30 | 20% |
| IXP presence | 100 km | 10% |

**Score Mapping:**
```
0-5 points:    Score = points * 15  (0-75)
6-8 points:    Score = 75 + (points - 5) * 5  (75-90)
9+ points:     Score = 100
```

**Interpretation:**
- Few infrastructure points nearby = poor resilience
- Multiple redundant infrastructure = high resilience

---

##### 4. Land Planning Component
**Scoring Function:** Direct mapping from development status

**Formula:**
```
land_planning_score = calculate_development_stage_score(status, perspective="demand")
```

**Values:**
- Consented/Granted/In Planning/No Application: 55-100
- Application Refused/Withdrawn: 30-35
- Operational: 10 (existing assets, not greenfield)
- Decommissioned: 0

---

##### 5. Latency/Digital Infrastructure Component
**Scoring Function:** Proximity to fiber and IXP (internet exchange points)

**Formula:**
```
latency_score = (0.65 * fiber_score) + (0.35 * ixp_score)
```

**Fiber Score (0-100):**
```
fiber_score = 100 * exp(-distance_km / 40_km)
```

**IXP Score (0-100):**
```
ixp_score = 100 * exp(-distance_km / 70_km)
```

**Distance Impact:**
```
Fiber (40km half-distance):
- 0 km: 100.0
- 10 km: 77.9
- 40 km: 36.8 (half)
- 80 km: 13.5

IXP (70km half-distance):
- 0 km: 100.0
- 10 km: 87.1
- 70 km: 36.8 (half)
- 140 km: 13.5
```

**Importance by Persona:**
- Colocation: 21.7% weight (highest)
- Edge Computing: 24.7% weight (highest)
- Hyperscaler: 5.6% weight (lowest)

---

##### 6. Cooling/Water Resources Component
**Scoring Function:** Exponential decay based on water proximity

**Formula:**
```
water_score = 100 * exp(-distance_km / 15_km)
```

**Distance to Score Mapping:**
```
0 km:    100.0 (at water)
5 km:    71.7
10 km:   51.3
15 km:   36.8 (half-score point)
30 km:   13.5
60 km:   1.8
```

**Water Half-Distance:** 15 km (shortest of all infrastructure)

**Importance by Persona:**
- Hyperscaler: 14.4% weight (critical for cooling)
- Colocation: 8.7% weight
- Edge Computing: 5.4% weight

---

##### 7. Price Sensitivity Component
**Scoring Function:** Compares project LCOE vs. user budget/market price

**Formula:**
```
if user_max_price_mwh is provided:
    budget = user_max_price_mwh
else:
    budget = MERCHANT_POWER_PRICE_DEFAULT (£75/MWh)

lcoe_score = 100 * (1 - (lcoe - min_lcoe) / (max_lcoe - min_lcoe))
lcoe_score = max(0, min(100, lcoe_score))

if lcoe <= budget:
    price_score = lcoe_score * 0.8 + 20  (boost if within budget)
else:
    price_score = lcoe_score * (1 - (lcoe - budget) / (2 * budget))
```

**Default LCOE Configuration:**
```
baseline: £60/MWh
min_lcoe: £45/MWh
max_lcoe: £100/MWh
```

---

#### Scoring Method: Weighted Sum (Default)

**Algorithm:**
```
weighted_score = sum(component_score * weight for each component)
final_rating = weighted_score / 10.0  (convert to 1.0-10.0 scale)
```

**Example: Hyperscaler Scoring**
```
Inputs:
- Capacity: 45 MW → score 94.0, weight 24.4% → contribution 22.9
- Connection Speed: (dev_stage 90 + substation 78 + transmission 65) weighted → score 80, weight 16.7% → contribution 13.4
- Resilience: 5 infrastructure points → score 75, weight 13.3% → contribution 10.0
- Land Planning: 70, weight 20.0% → contribution 14.0
- Latency: 65, weight 5.6% → contribution 3.6
- Cooling: 72, weight 14.4% → contribution 10.4
- Price Sensitivity: 58, weight 5.6% → contribution 3.2

Weighted Score = 22.9 + 13.4 + 10.0 + 14.0 + 3.6 + 10.4 + 3.2 = 77.5
Final Rating = 77.5 / 10 = 7.75 ("Good")
```

---

#### Scoring Method: TOPSIS (Multi-Criteria Decision Analysis)

**Triggered by:** `scoring_method=topsis` parameter

**Algorithm Steps:**
1. Normalize each component score (0-100) to unit vector
2. Apply persona weights to normalized scores
3. Calculate ideal solution (best possible for each component)
4. Calculate anti-ideal solution (worst possible for each component)
5. Calculate Euclidean distance from each option to ideal
6. Calculate Euclidean distance from each option to anti-ideal
7. Closeness coefficient = distance_to_anti_ideal / (distance_to_ideal + distance_to_anti_ideal)
8. Scale closeness to 0-100: `score_100 = 10 + closeness * 90`
9. Convert to display rating: `rating = score_100 / 10`

**Response Includes:**
```json
"topsis_metrics": {
  "distance_to_ideal": 0.45,
  "distance_to_anti_ideal": 0.78,
  "closeness_coefficient": 0.634,
  "normalized_scores": { /* 7 components */ },
  "weighted_normalized_scores": { /* 7 components */ }
}
```

**TOPSIS Advantages:**
- Ranks options by distance to ideals
- Better handling of conflicting criteria
- Produces slightly different rankings than weighted sum
- Useful for comparing alternatives

---

### Power Developer Scoring

**Perspectives:** Supply-side (developer) vs. Demand-side (user site)

**Available Personas:**
- `greenfield` - New development sites
- `repower` - Existing site upgrades
- `stranded` - Partially developed sites

**Key Differences from Data Center Scoring:**
- Development stage weighted higher (future revenue visibility)
- Grid connection feasibility assessed (transmission vs. substation)
- Market revenue potential evaluated (PPA, merchant, capacity market)
- Timeline acceleration for repower/stranded scenarios

---

### Infrastructure Proximity Calculations

All distances calculated using great-circle distance (Haversine formula):

```python
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c
```

**Spatial Indexing:** Uses 0.5° grid cells for O(1) lookup
- Grid resolution: ~55 km cells at UK latitude
- Reduces nearest-neighbor search from O(n) to O(1) on average

---

## Infrastructure Data

### Data Sources & Update Frequency

| Infrastructure | Source | Update Frequency | Coverage |
|---|---|---|---|
| Substations | National Grid & DNOs | Quarterly | 100% UK |
| Transmission | National Grid | Quarterly | 100% GB |
| Fiber | InfraWatch / ISPGenius | Semi-annual | ~95% urban |
| IXPs | LINX, DE-CIX, Equinix | Monthly | Major cities |
| Water Resources | Environment Agency | Annual | 100% England/Wales |
| GSP Boundaries | DNO/ESO | Annual | 100% GB |
| DNO Areas | UKPN / SEEL / etc. | Static | 100% GB |
| TNUoS Zones | ESO | Annual | 27 zones, 100% GB |

### TNUoS Zones (27 Hardcoded)

**High Tariff Zones (Scotland):**
```
GZ1: North Scotland, +15.32 £/kW
GZ2: South Scotland, +14.87 £/kW
GZ3: Borders, +13.45 £/kW
GZ4: Central Scotland, +12.98 £/kW
```

**Neutral Zones (Midlands):**
```
GZ15: East Midlands, +2.95 £/kW
GZ16: West Midlands, +2.34 £/kW
GZ17: East England, +1.87 £/kW
```

**Negative Tariff Zones (South/Southeast):**
```
GZ21: South West England, -0.12 £/kW (generators paid)
GZ22: Cornwall, -0.45 £/kW
GZ23: London, -0.78 £/kW
GZ25: Kent, -1.56 £/kW
GZ27: Solent, -2.34 £/kW
```

**TNUoS Impact on Scoring:**
- Tariff converted to 0-100 score: `score = 100 * (1 - (tariff - min_tariff) / (max_tariff - min_tariff))`
- Min tariff: -3.0 £/kW (score 100)
- Max tariff: +16.0 £/kW (score 0)
- Southern zone negative tariffs score 100 (generators rewarded)
- Northern zone positive tariffs score 0-50 (generators penalized)

**Enrichment:** TNUoS score integrated into final rating when enriching with `/api/projects/enhanced`

---

### Caching Strategy

**Cache TTL:** 600 seconds (10 minutes, configurable via `INFRA_CACHE_TTL` env var)

**Cached Endpoints:**
```
substations
transmission_lines
fiber_cables
internet_exchange_points (IXPs)
water_resources
```

**Supabase Queries (Batched):**
```python
await asyncio.gather(
    query_supabase("substations?select=*"),
    query_supabase("transmission_lines?select=*"),
    query_supabase("fiber_cables?select=*", limit=200),  # Limited
    query_supabase("internet_exchange_points?select=*"),
    query_supabase("water_resources?select=*"),
)
```

**Cache Loading:**
- First request triggers load from Supabase
- Subsequent requests within TTL use in-memory cache
- Lock prevents multiple simultaneous loads
- Cache refresh logged to console

---

## Financial Model

### Technologies & Default Parameters

#### Solar PV
```python
{
    "capacity_factor": 0.14,        # 14% typical
    "degradation": 0.5,             # 0.5% per year
    "capex_per_kw": 800,            # £800/kW
    "opex_fix_per_mw_year": 12000,  # £12k/MW/year
    "project_life": 25              # 25 years
}
```

#### Wind Onshore
```python
{
    "capacity_factor": 0.35,        # 35% typical (range 30-45%)
    "degradation": 0.4,             # 0.4% per year
    "capex_per_kw": 1200,           # £1200/kW
    "opex_fix_per_mw_year": 45000,  # £45k/MW/year
    "project_life": 25
}
```

#### Wind Offshore
```python
{
    "capacity_factor": 0.45,        # 45% typical (range 40-55%)
    "degradation": 0.3,             # 0.3% per year
    "capex_per_kw": 2500,           # £2500/kW (much higher)
    "opex_fix_per_mw_year": 75000,  # £75k/MW/year
    "project_life": 25
}
```

#### Battery Storage
```python
{
    "capacity_factor": 0.5,         # 50% utilization assumption
    "degradation": 2.0,             # 2% per year
    "capex_per_kwh": 300,           # £300/kWh
    "project_life": 10,             # 10 years (shorter than solar/wind)
}
```

#### Hybrid (Solar + Wind)
```python
{
    "capacity_factor": 0.25,        # Blended (60% solar, 40% wind)
    "degradation": 0.45,            # Blended
    "capex_per_kw": 1000,           # Blended
}
```

### Calculation Methodology

#### Annual Energy Output
```
year_y_energy = capacity_mw * capacity_factor * 8760 * (1 - degradation/100)^y
```

#### Revenue Streams (Year Y)

**1. PPA Revenue (first ppa_duration years):**
```
ppa_revenue_y = year_y_energy * ppa_price * (1 + ppa_escalation/100)^y
```

**2. Merchant Revenue (after PPA ends):**
```
merchant_revenue_y = year_y_energy * merchant_price * (1 + inflation/100)^y
```

**3. Capacity Market (if eligible):**
```
capacity_market_y = capacity_mw * capacity_market_per_mw_year * (1 + inflation/100)^y
```

**4. Ancillary Services:**
```
ancillary_y = capacity_mw * ancillary_per_mw_year * (1 + inflation/100)^y
```

**5. Grid Connection Savings (autoproducer only):**
```
grid_savings_y = year_y_energy * grid_savings_factor * merchant_price
```

#### Total Revenue
```
total_revenue_y = ppa_revenue + merchant_revenue + capacity_market + ancillary + grid_savings
```

#### Operating Costs
```
opex_y = (opex_fix_per_mw_year * capacity_mw + opex_var_per_mwh * year_y_energy) * (1 + inflation/100)^y
t_and_d_costs_y = tnd_costs_per_year * (1 + inflation/100)^y
```

#### Tax
```
taxable_income = revenue - opex - t_and_d - depreciation
tax_y = max(0, taxable_income * tax_rate)
```

#### Cashflow
```
year_0: -capex - devex
year_y (y > 0): total_revenue_y - opex_y - t_and_d_y - tax_y
```

#### NPV & IRR
```
NPV = sum(cashflow_y / (1 + discount_rate)^y for y in 0..project_life)
IRR = discount_rate where NPV = 0 (solved iteratively)
```

#### LCOE (Levelized Cost of Energy)
```
LCOE = sum(cost_y / (1 + discount_rate)^y) / sum(energy_y / (1 + discount_rate)^y)
cost = capex + opex + taxes
```

#### Payback Period
```
simple_payback: Year where cumulative cashflow >= 0
discounted_payback: Year where discounted cumulative cashflow >= 0
```

### Two Scenarios

**Standard (Utility-Scale):**
- Large PPA (typically 12-20 years)
- Full capacity market participation
- Lower grid savings (grid connected)
- Typical for large solar/wind farms

**Autoproducer (Behind-the-Meter):**
- Shorter or no PPA
- Self-consumption discount
- Grid connection savings applied
- Typical for rooftop solar, microgrids

---

## Database & Supabase

### Supabase Configuration

**URL Environment Variable:** `SUPABASE_URL`
**API Key (Anon):** `SUPABASE_ANON_KEY` (frontend only)
**Service Role Key:** Stored in backend environment (not exposed)

### Tables Used by Backend

#### 1. `renewable_projects` (Primary)
Main project data source. Contains ~5000 renewable energy projects.

**Columns:**
```
ref_id (text, PK)
site_name (text)
technology_type (text)
capacity_mw (float)
operator (text)
latitude (float)
longitude (float)
county (text)
country (text)
development_status_short (text)
commissioning_year (int)
capacity_factor (float, nullable)
grid_connection_status (text, nullable)
connection_point (text, nullable)
is_btm (boolean)
created_at (timestamp)
updated_at (timestamp)
```

**Indexes:**
- `renewable_projects_pkey` on `ref_id`
- `renewable_projects_coordinates` on `(latitude, longitude)` (spatial)
- `renewable_projects_technology` on `technology_type`

---

#### 2. `substations`
Electrical substation locations.

**Columns:**
```
id (uuid, PK)
name (text)
voltage_kv (integer)
operator (text)
latitude (float)
longitude (float)
region (text)
capacity_mva (float)
created_at (timestamp)
```

**Features:** ~4000 substations across UK

---

#### 3. `transmission_lines`
High-voltage transmission routes.

**Columns:**
```
id (uuid, PK)
name (text)
voltage_kv (integer)
operator (text)
length_km (float)
capacity_mw (float)
status (text)
geometry (geometry, LineString)
created_at (timestamp)
```

**Features:** ~500 transmission line segments

---

#### 4. `fiber_cables`
Fiber optic route data (limited to ~200 top routes).

**Columns:**
```
id (uuid, PK)
route_name (text)
operator (text)
bandwidth_tbps (float)
path_type (text)  -- onshore, submarine, mixed
geometry (geometry, LineString)
operational_date (date)
created_at (timestamp)
```

**Query Limit:** `limit=200` (top routes only)

---

#### 5. `internet_exchange_points`
IXP locations for peering connectivity.

**Columns:**
```
id (uuid, PK)
name (text)
operator (text)
city (text)
peering_count (integer)
capacity_gbps (float)
latitude (float)
longitude (float)
created_at (timestamp)
```

**Features:** ~40-50 IXPs in UK

---

#### 6. `water_resources`
Water sources for cooling.

**Columns:**
```
id (uuid, PK)
name (text)
type (text)  -- river, reservoir, groundwater, tidal
region (text)
capacity_m3 (float)
abstraction_license (text)
latitude (float)
longitude (float)
created_at (timestamp)
```

**Features:** ~1500 water resources

---

#### 7. `gsp_boundaries`
Grid Supply Point polygons.

**Columns:**
```
id (uuid, PK)
gsp_code (text, unique)
gsp_name (text)
region (text)
dno (text)
geometry (geometry, Polygon)
created_at (timestamp)
```

**Features:** ~370 GSP boundaries covering entire GB

---

#### 8. `dno_areas`
Distribution Network Operator area boundaries.

**Columns:**
```
id (uuid, PK)
dno_code (text, unique)
dno_name (text)
region (text)
customer_count (integer)
geometry (geometry, Polygon)
created_at (timestamp)
```

**Features:** 14 DNO operators

---

#### 9. `tec_connections` (Optional)
TEC (Transmission Entry Capacity) connections.

**Columns:**
```
id (uuid, PK)
ref_id (text, FK to renewable_projects)
connection_id (text)
site_name (text)
connection_type (text)
capacity_mw (float)
entry_point (text)
status (text)
queue_position (integer)
estimated_connection_date (date)
application_date (date)
capacity_location (text)
created_at (timestamp)
```

---

#### 10. `demand_sites` (Future)
Data center and facility locations (not yet used in current version).

**Planned Columns:**
```
id (uuid, PK)
name (text)
demand_mw (float)
latitude (float)
longitude (float)
operator (text)
facility_type (text)  -- hyperscaler, colocation, edge
created_at (timestamp)
```

---

### Query Strategy

**Pagination:** Uses offset/limit with async batching
```python
async with httpx.AsyncClient() as client:
    while offset < limit:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/{endpoint}&offset={offset}&limit={page_size}",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        )
        results.extend(response.json())
        offset += page_size
```

**Performance:** Single queries return ~200-400ms, batched queries ~1-2s

---

## Performance & Caching

### Response Time Targets

| Endpoint | Typical | Peak | Conditions |
|----------|---------|------|------------|
| `/api/projects` | 200-500ms | 1s | 5000 projects, no proximity |
| `/api/projects/geojson` | 300-800ms | 2s | 500 projects, no proximity |
| `/api/projects/enhanced` | 2-5s | 10s | 5000 projects, WITH proximity |
| `/api/user-sites/score` | 500ms-2s | 5s | 10 sites |
| `/api/projects/compare-scoring` | 400-600ms | 1.5s | Single project |
| Infrastructure endpoints | 150-500ms | 1s | Cached or small datasets |
| `/api/financial-model` | 100-200ms | 500ms | Single calculation |

### Batch Processing

**Proximity Calculation Optimization:**
```python
async def calculate_proximity_scores_batch(projects: List[Dict]) -> List[Dict]:
    catalog = await infrastructure_cache.get_catalog()

    # Spatial grid: O(1) average lookup instead of O(n)
    scores_batch = []
    for project in projects:
        # Quick index lookup via 0.5° grid cells
        nearest = catalog.find_nearest([
            'substations', 'transmission', 'fiber', 'ixps', 'water'
        ], lat=project['latitude'], lon=project['longitude'])

        scores_batch.append(calculate_scores(nearest))

    return scores_batch
```

**Grid Cell Resolution:** 0.5° ≈ 55 km at UK latitude
- ~500 grid cells total covering UK
- Average 8-10 projects per cell
- Reduces nearest-neighbor from O(5000) to O(10)

### Memory Usage

**Infrastructure Cache:**
- Substations: ~4000 features × 50 bytes ≈ 200 KB
- Transmission: ~500 features × 100 bytes ≈ 50 KB
- Fiber: ~200 features × 150 bytes ≈ 30 KB
- IXPs: ~50 features × 50 bytes ≈ 2.5 KB
- Water: ~1500 features × 50 bytes ≈ 75 KB
- **Total:** ~360 KB per cache instance

**Project Data in Memory:**
- 5000 projects × 1.5 KB ≈ 7.5 MB
- Typically kept in Supabase, not cached in backend

---

## Error Handling

### Error Response Format

**Standard HTTP Error Response:**
```json
{
  "detail": "Error message here",
  "status_code": 400
}
```

**FastAPI Standard (HTTPException):**
```python
raise HTTPException(
    status_code=400,
    detail="Validation failed"
)
```

### Common Error Cases

#### 1. Coordinate Validation (User Sites)
```json
{
  "detail": "Site 1: Coordinates outside UK bounds",
  "status_code": 400
}
```

**Bounds Check:**
```python
if not (49.8 <= latitude <= 60.9) or not (-10.8 <= longitude <= 2.0):
    raise HTTPException(400, f"Site {i}: Coordinates outside UK bounds")
```

#### 2. Capacity Validation
```json
{
  "detail": "Site 1: Capacity must be between 5-500 MW",
  "status_code": 400
}
```

#### 3. Commissioning Year Validation
```json
{
  "detail": "Site 1: Commissioning year must be between 2025-2035",
  "status_code": 400
}
```

#### 4. Empty Sites List
```json
{
  "detail": "No sites provided",
  "status_code": 400
}
```

#### 5. Database Connection Error
```json
{
  "detail": "Database error: 500",
  "status_code": 500
}
```

#### 6. Missing Required Parameters
```json
{
  "detail": "Missing required query parameter: ref_id",
  "status_code": 422
}
```

### Logging

**Console Logging:**
All requests and errors logged to stdout with timestamps and emojis:
```
🔄 Scoring 10 user-submitted sites with PERSONA-BASED SCORING system...
✓ Enriched 100/342 projects
✅ User sites scored with PERSONA-BASED SYSTEM in 0.82s
❌ Database error: Connection timeout
⚠️  Error processing project: Invalid geometry
```

**No External Error Tracking:** (Sentry, Rollbar, etc. not configured)

---

## Configuration

### Environment Variables

**Supabase (Frontend Integration):**
```
SUPABASE_URL=https://[project-id].supabase.co
SUPABASE_ANON_KEY=[anon-key]
```

**Backend Operation:**
```
INFRA_CACHE_TTL=600              # Infrastructure cache TTL in seconds
DATABASE_URL=postgresql://...    # Optional: direct DB connection
LOG_LEVEL=INFO                   # Logging level
PORT=8001                         # API port
```

**Optional:**
```
SENTRY_DSN=                       # Error tracking (not configured)
REDIS_URL=                        # Redis caching (not configured)
```

### FastAPI Configuration

**CORS Settings:**
```python
CORSMiddleware(
    app,
    allow_origins=["*"],          # All origins
    allow_methods=["*"],          # All HTTP methods
    allow_headers=["*"],          # All headers
)
```

**Request Timeouts:**
- HTTP Client: 30 seconds (Supabase queries)
- FastAPI: Default 60 seconds per request

---

## Technology Stack

### Backend Framework
- **FastAPI** 0.100+ (async Python web framework)
- **Python** 3.9+
- **Uvicorn** (ASGI server)

### Key Dependencies
```
fastapi==0.104.1
httpx==0.25.0          # Async HTTP client (Supabase queries)
pydantic==2.4.0        # Data validation
python-dotenv==1.0.0   # Environment variables
uvicorn==0.24.0        # ASGI server
```

### Deployment
- **Platform:** Render (https://infranodev2.onrender.com)
- **Server:** Uvicorn with 4 workers
- **Type:** Cloud-deployed Python app
- **HTTPS:** Enforced in production
- **Development:** `python main.py` runs at http://localhost:8001

### Database
- **Supabase** (PostgreSQL with PostGIS for geometry)
- **Geometry Support:** PostGIS for spatial queries
- **No ORM:** Direct REST API calls to Supabase (no SQLAlchemy)

### Spatial Libraries
- **Shapely** (geometry operations, optional)
- **Haversine** formula (custom implementation) for distance calculations

### Frontend Integration
- **API Type:** REST JSON
- **Data Format:** GeoJSON for geographic data
- **Response Format:** JSON
- **Content-Type:** application/json

---

## Development & Debugging

### Local Development

**Setup:**
```bash
# Clone repository
git clone [repo-url]
cd infranodev2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
SUPABASE_URL=https://[project-id].supabase.co
SUPABASE_ANON_KEY=[anon-key]
INFRA_CACHE_TTL=600
EOF

# Run backend
python main.py
```

**Access:**
- API: http://localhost:8001
- Health check: http://localhost:8001/health
- Swagger UI: http://localhost:8001/docs

### Debug Endpoints

**Health Check:**
```bash
curl http://localhost:8001/health
```

**Sample Project Query:**
```bash
curl "http://localhost:8001/api/projects?limit=10"
```

**Enhanced Scoring with Custom Weights:**
```bash
curl "http://localhost:8001/api/projects/enhanced?limit=100&scoring_method=topsis&custom_weights={%22capacity%22:0.2,%22connection_speed%22:0.15,%22resilience%22:0.15,%22land_planning%22:0.2,%22latency%22:0.15,%22cooling%22:0.1,%22price_sensitivity%22:0.05}"
```

### Testing

**Test Coverage:** Unit tests for scoring algorithms in `backend/tests/`

**Running Tests:**
```bash
pytest backend/tests/ -v
```

---

## Migration Notes for Frontend

### Key Takeaways

1. **No Authentication Required** - API is fully public, no token handling needed
2. **Personas Matter** - Same project scores differently for hyperscaler vs. edge computing
3. **Infrastructure Proximity** - Major factor in scoring, included in `/enhanced` endpoint
4. **Financial Model Separated** - Different endpoint, different request body
5. **TOPSIS Alternative** - Available for multi-criteria decision analysis
6. **TNUoS Zones** - Geographic tariff influences southern sites significantly
7. **Batch Processing** - Scores ~5000 projects in 2-5 seconds with proximity
8. **Display Scale** - 1.0-10.0 (internal is 0-100, divide by 10)
9. **Color Codes** - 10-point gradient from green to red based on score
10. **Supabase is Separate** - Frontend uses Supabase for auth, backend uses it for data only

---

## Support & Documentation

### Endpoints Summary
```
GET  /health
GET  /api/projects
GET  /api/projects/geojson
GET  /api/projects/enhanced
GET  /api/projects/compare-scoring
GET  /api/projects/customer-match
POST /api/projects/power-developer-analysis
POST /api/user-sites/score
GET  /api/infrastructure/substations
GET  /api/infrastructure/transmission
GET  /api/infrastructure/fiber
GET  /api/infrastructure/ixp
GET  /api/infrastructure/water
GET  /api/infrastructure/gsp
GET  /api/infrastructure/tnuos
GET  /api/infrastructure/dno-areas
GET  /api/tec/connections
POST /api/financial-model
GET  /api/financial-model/units
```

### Production URL
```
https://infranodev2.onrender.com
```

### Development URL
```
http://localhost:8001
```

### Key Files
- **Main API:** `/home/user/infranodev2/main.py` (2400 lines)
- **Scoring Logic:** `/home/user/infranodev2/backend/scoring.py`
- **Power Developer Logic:** `/home/user/infranodev2/backend/power_workflow.py`
- **Proximity Calculations:** `/home/user/infranodev2/backend/proximity.py`
- **Financial Model:** `/home/user/infranodev2/backend/renewable_model.py`

---

**End of Backend API Documentation**

Generated: 2025-11-18 for InfraNode Frontend Team
