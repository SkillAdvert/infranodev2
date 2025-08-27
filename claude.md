# Infranodal - Renewable Energy Site Assessment Platform

## Project Overview
Interactive web application that allows power developers to assess renewable energy sites and receive investment scores based on infrastructure proximity. Users can either upload CSV data or use an interactive site builder with map-based placement and real-time scoring.

## Current Architecture

### Backend
- **Framework**: FastAPI with Python
- **Database**: Supabase PostgreSQL
- **Deployment**: Render.com at `https://infranodev2.onrender.com`
- **Key Tables**: 
  - `renewable_projects` - Existing project database
  - `substations`, `transmission_lines`, `fiber_cables`, `internet_exchange_points`, `water_resources` - Infrastructure data

### Frontend
- **Framework**: React + TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **Mapping**: Mapbox GL JS
- **State Management**: React hooks (useState, useRef)

### API Endpoints
- `GET /api/projects/enhanced` - Enhanced project scoring (existing projects)
- `POST /api/user-sites/score` - User site scoring (new functionality)
- `GET /api/infrastructure/{type}` - Infrastructure layer data (substations, transmission, fiber, ixp, water)

## Investment Scoring Algorithm

### Base Scoring (0-100 points)
- **Capacity**: 100MW+ = 40pts, 50-100MW = 30pts, 20-50MW = 20pts, <20MW = 10pts
- **Development Status**: Operational = 40pts, Construction = 35pts, Granted = 30pts, Submitted = 20pts, Planning = 10pts
- **Technology**: Solar = 20pts, Battery = 18pts, Other = 15pts

### Proximity Scoring (0-95 points)
- **Substations**: Up to 50pts (exponential decay from distance)
- **Transmission Lines**: Up to 50pts (point-to-line distance calculation)
- **Fiber Networks**: Up to 20pts
- **Internet Exchanges**: Up to 10pts
- **Water Resources**: Up to 15pts

### Enhanced Score
- **Total Range**: 0-195 points
- **Grading**: A++ (170+), A+ (150+), A (130+), B+ (110+), B (90+), C+ (70+), C (50+), D (<50)

## Key Components

### DataUploadPanel.tsx
- Interactive site builder form
- Two-site comparison capability
- Form validation (5-500MW capacity, UK coordinates, required fields)
- Map integration for coordinate placement
- Real-time scoring via API calls
- Results display with scoring breakdown

### DynamicSiteMap.tsx  
- Mapbox integration with UK bounds (49.8-60.9 lat, -10.8-2.0 lng)
- Placement mode for click-to-place site coordinates
- Project visualization with investment grade colors
- Infrastructure layer toggles (when working)
- Popup information for projects

### main.py (FastAPI Backend)
- User site scoring endpoint with validation
- Batch proximity calculation algorithm (10-50x faster than individual processing)
- Infrastructure data serving
- Enhanced project scoring for existing database

## Current Status

### Working Features
- User site form entry with validation
- Map-based coordinate placement
- Investment scoring algorithm with proximity calculations
- Two-site comparison
- Results display with infrastructure distances
- API integration between frontend and backend
- UK bounds validation and coordinate handling

### Known Issues
- Infrastructure layer visualization removed due to compilation issues
- PDF export shows placeholder toast only
- Missing data center type recommendations

### In Progress
- Infrastructure layer controls (temporarily disabled)

### Not Implemented
- PDF export functionality
- Data center provider recommendations (HPC, Compute, Inference, ML Training)
- Enhanced financial modeling integration
- Site data persistence (currently client-side only)

## Technical Specifications

### Validation Rules
- **Capacity**: 5-500 MW range
- **Coordinates**: UK bounds only
- **Commissioning Year**: 2025-2035
- **Required Fields**: Site name, technology type, capacity, commissioning year, coordinates

### Data Formats
```javascript
// User Site Input Format
{
  site_name: string,
  technology_type: "Solar" | "Wind" | "Battery" | "Hybrid", 
  capacity_mw: number (5-500),
  latitude: number (49.8-60.9),
  longitude: number (-10.8-2.0),
  commissioning_year: number (2025-2035),
  is_btm: boolean
}

// API Response Format
{
  site_name: string,
  investment_grade: "A++" | "A+" | "A" | "B+" | "B" | "C+" | "C" | "D",
  enhanced_score: number (0-195),
  base_score: number (0-100),
  proximity_bonus: number (0-95),
  color_code: string,
  nearest_infrastructure: {
    substation_km?: number,
    transmission_km?: number,
    fiber_km?: number,
    ixp_km?: number,
    water_km?: number
  }
}
```

## Development History

### Completed Phases
1. **Algorithm Development** - Proximity-based scoring with infrastructure distance calculations
2. **API Implementation** - FastAPI endpoints with Supabase integration
3. **Frontend Core** - React components for site entry and map integration
4. **Scoring Integration** - End-to-end workflow from form to results

### Architectural Decisions
- **Batch Processing**: Load all infrastructure once, score multiple sites for performance
- **UK Focus**: Bounded coordinate validation for target market
- **No Session Storage**: Pure client-side state management
- **Exponential Distance Scoring**: Closer infrastructure gets exponentially higher scores
- **Two-Site Limit**: MVP constraint for comparison functionality

## Next Development Priorities

### High Priority (MVP Completion)
1. **Infrastructure Layer Visualization** - Fix compilation issues and restore infrastructure toggles
2. **Data Center Recommendations** - AI-generated suggestions based on scoring (HPC for high scores, Edge for lower scores)
3. **PDF Export** - Professional reports with site details, scores, and map snapshots

### Medium Priority (Enhancement)
1. **Enhanced Results Analysis** - Comparative insights between sites
2. **Financial Modeling Integration** - ROI calculations based on proximity scores
3. **Constraint Validation** - Real-time feedback on planning restrictions

### Low Priority (Future Features)
1. **Multi-region Support** - Beyond UK boundaries
2. **Advanced Infrastructure** - Gas pipelines, rail connections
3. **Collaborative Features** - Share results with stakeholders

## Environment & Dependencies

### Key Environment Variables
- `SUPABASE_URL` - Database connection
- `SUPABASE_ANON_KEY` - Database authentication
- `MAPBOX_PUBLIC_TOKEN` - Map rendering

### Critical Dependencies
- `mapbox-gl` - Map rendering and interactions
- `@supabase/supabase-js` - Database client
- `lucide-react` - UI icons
- `tailwindcss` - Styling framework

## Testing & Validation

### Known Working Workflow
1. User fills site form with valid data
2. User clicks map to set coordinates
3. Form validates all required fields
4. API call to `/api/user-sites/score` with proper payload
5. Results display with investment grade and infrastructure distances

### Common Issues
- Mapbox token configuration required for map display
- CORS handling between frontend and deployed API
- Infrastructure data loading performance (17+ seconds for full dataset)

## File Structure
```
project/
├── claude.md (this file)
├── main.py (FastAPI backend)
├── src/components/
│   ├── DataUploadPanel.tsx (site builder)
│   └── DynamicSiteMap.tsx (map integration)
└── README.md
```
