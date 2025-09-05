Infranodal - Renewable Energy Investment Analysis Platform
Project Overview
Interactive web application enabling renewable energy investors and data center developers to assess site viability through AI-powered infrastructure scoring. The platform combines existing project databases with real-time infrastructure analysis, providing investment ratings from 1.0-10.0 based on persona-specific algorithms and comprehensive proximity scoring, now enhanced with TNUoS transmission cost integration.
Current Architecture Status (December 2024)
Backend (Production Ready)

Framework: FastAPI with Python 3.9+
Database: Supabase PostgreSQL with PostGIS extensions
Deployment: Render.com at https://infranodev2.onrender.com
Performance: Batch processing optimization (10-50x faster than individual queries)
AI Integration: Ready for Claude/OpenAI integration via Supabase Edge Functions
Data Sources:

NESO GSP boundary data (333 features)
OpenStreetMap telecommunications infrastructure (549+ segments)
Manual infrastructure datasets (substations, IXPs, water resources)
TNUoS transmission cost zones (27 UK generation zones with tariff rates)



Frontend (React + TypeScript)

Framework: React 18 + TypeScript
Styling: Tailwind CSS + shadcn/ui components (optimized subset)
Mapping: Mapbox GL JS with professional infrastructure visualization
State Management: React hooks with optimized re-rendering
Build System: Vite/Create React App compatible
AI Chat: Integrated persona-aware AI chatbot for project analysis

Database Schema
sql-- Core Tables (Production)
renewable_projects (100+ records) - Existing UK renewable projects
electrical_grid - GSP boundaries and grid infrastructure  
transmission_lines - Power transmission network
substations - Electrical substations with capacity data
fiber_cables - Telecommunications fiber networks
internet_exchange_points - Data center connectivity hubs
water_resources - Water sources for cooling/operations
tnuos_zones (27 records) - UK transmission charging zones with tariff rates
Enhanced Persona-Based Investment Scoring (Algorithm 2.3)
Updated Scoring Components (8 Components)

Capacity Score: Project size suitability for persona
Development Stage Score: Deployment readiness assessment
Technology Score: Technology type appropriateness
Grid Infrastructure Score: Proximity to substations and transmission
Digital Infrastructure Score: Fiber and IXP connectivity access
Water Resources Score: Cooling infrastructure availability
TNUoS Transmission Costs Score: Annual transmission charge impact
LCOE Resource Quality Score: Energy generation cost efficiency

Current Persona Weightings (Algorithm 2.3)
File Location: main.py - 5% into file
Find: PERSONA_WEIGHTS = {
Current Configuration:
pythonPERSONA_WEIGHTS = {
    "hyperscaler": {
        "capacity": 0.25,                    # High capacity critical
        "development_stage": 0.20,           # Planning-approved preferred
        "technology": 0.08,                  # Technology flexibility
        "grid_infrastructure": 0.17,         # Reliable power essential
        "digital_infrastructure": 0.05,      # Basic connectivity needs
        "water_resources": 0.05,             # Cooling requirements
        "tnuos_transmission_costs": 0.12,    # Significant operational costs
        "lcoe_resource_quality": 0.08        # Energy cost efficiency
    },
    
    "colocation": {
        "capacity": 0.13,                    # Moderate capacity needs
        "development_stage": 0.18,           # Flexible timeline
        "technology": 0.08,                  # Technology adaptability
        "grid_infrastructure": 0.22,         # Power reliability critical
        "digital_infrastructure": 0.22,      # Connectivity is key
        "water_resources": 0.05,             # Standard cooling
        "tnuos_transmission_costs": 0.10,    # Moderate cost impact
        "lcoe_resource_quality": 0.02        # Lower priority
    },
    
    "edge_computing": {
        "capacity": 0.09,                    # Small capacity requirements
        "development_stage": 0.26,           # Quick deployment critical
        "technology": 0.14,                  # Technology flexibility
        "grid_infrastructure": 0.14,         # Modest power needs
        "digital_infrastructure": 0.23,      # Low latency critical
        "water_resources": 0.05,             # Minimal cooling
        "tnuos_transmission_costs": 0.06,    # Lower impact (smaller sites)
        "lcoe_resource_quality": 0.03        # Basic efficiency needs
    }
}
Investment Rating Scale (1.0-10.0)
Internal scoring: 10-100 points, displayed as 1.0-10.0 for user clarity
Rating Descriptions:

9.0-10.0: Excellent - Premium investment opportunity
8.0-8.9: Very Good - Strong investment potential
7.0-7.9: Good - Solid investment opportunity
6.0-6.9: Above Average - Moderate investment potential
5.0-5.9: Average - Standard investment opportunity
4.0-4.9: Below Average - Limited investment appeal
3.0-3.9: Poor - Significant investment challenges
2.0-2.9: Very Poor - High risk investment
1.0-1.9: Bad - Unfavorable investment conditions

Current Implementation Status
✅ Completed Features

Power Developer Dashboard (src/pages/UtilityDashboard.tsx):

Streamlined 60/40 map/sidebar layout
Customer-specific project matching with /api/projects/customer-match endpoint
Color-coded ratings sorted by score (highest first)
Developer information display in compact cells
Dynamic titles: "Best Hyperscale Matches" based on persona selection
Fixed scrolling issues with proper height constraints


Data Center Developer Dashboard (src/pages/HyperscalerDashboard.tsx):

5-tab navigation: Setup, Map Overview, Projects, Site Assessment, AI Insights
PersonaSelector component for persona configuration
Capacity range display and filtering
Infrastructure layer controls integration
Enhanced persona-based project scoring


Infrastructure Visualization:

TNUoS zones display as colored cost polygons
All 6 infrastructure layers working (transmission lines endpoint issues resolved)
MapOverlayControls with progressive disclosure and category grouping
Real-time infrastructure data loading with count display


API Endpoints (Production Ready):

/api/projects/enhanced - Enhanced persona-based scoring
/api/projects/customer-match - Power developer customer analysis
/api/user-sites/score - User site scoring with persona selection
/api/infrastructure/* - All infrastructure visualization endpoints
/api/projects/compare-scoring - Algorithm comparison tools



🔄 Current Development State
Development Stage Scoring Issue
File: main.py - 25% into file
Find: def calculate_development_stage_score(status: str) -> float:
Current Problem: Operational sites scoring higher than development opportunities
Lines to Replace:
pythonif 'operational' in status: return 50.0         # Possible grid headroom
elif 'construction' in status: return 70       # Near-term deployment
elif 'granted' in status: return 85          # Planning approved
elif 'submitted' in status: return 45.0         # Planning pending
elif 'planning' in status: return 30          # Early stage
TNUoS Algorithm Integration (Next Priority)
Status: Infrastructure visualization complete, algorithm integration needed
Missing: TNUoS spatial queries in scoring calculations
Required: Add TNUoS cost component to persona-weighted scoring
Hyperscaler Scoring Range Issue
Current Issue: Scores capping at 5.2-8.6 range instead of utilizing full 1.0-10.0 scale
Contributing Factors:

Conservative development stage scoring
Restrictive capacity thresholds
Limited infrastructure proximity bonuses

📋 Immediate Next Steps (Priority Order)
1. Fix Development Stage Scoring Algorithm
File: main.py - 25% into file
Find: if 'operational' in status: return 50.0
Replace with:
pythonif 'granted' in status: return 95.0            # Planning approved - prime opportunity
elif 'construction' in status: return 85.0      # Under construction - good timing
elif 'submitted' in status: return 75.0         # Planning pending - opportunity
elif 'planning' in status: return 60.0          # Early stage - potential
elif 'operational' in status: return 40.0       # Limited headroom opportunity
else: return 25.0                               # Unknown status
2. Enhance Scoring Algorithm Generosity
File: main.py - 22% into file
Find: def calculate_capacity_component_score(capacity_mw: float) -> float:
Current Issue: Capacity scoring too restrictive for hyperscaler range
Enhancement Needed: More generous scoring for 50-100MW range
3. Complete TNUoS Algorithm Integration
File: main.py - 30% into file
Find: def calculate_persona_weighted_score(
Missing Component: TNUoS cost scoring not integrated into weighted calculations
Required: Add TNUoS spatial queries and cost impact scoring
4. Data Center Developer Dashboard Optimization
File: src/pages/HyperscalerDashboard.tsx - 85% into file
Current State: Functional but needs streamlined design patterns from Power Developer Dashboard
Improvements Needed:

Apply compact project display patterns
Enhanced filtering capabilities
Investment rating threshold controls

API Response Format (Current)
Enhanced Project Response Structure
json{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature", 
    "geometry": {"type": "Point", "coordinates": [-2.69, 51.25]},
    "properties": {
      "ref_id": 18491,
      "site_name": "Plas Power Estate Solar Farm",
      "technology_type": "Battery",
      "capacity_mw": 57.0,
      "operator": "British Solar Renewables",
      
      // Current 1.0-10.0 Rating System  
      "investment_rating": 4.2,
      "rating_description": "Below Average", 
      "color_code": "#FFCC00",
      
      // Persona-Specific Data (when applicable)
      "persona": "hyperscaler",
      "component_scores": {
        "capacity": 85.0,
        "development_stage": 70.0,
        "grid_infrastructure": 45.2,
        "digital_infrastructure": 25.8,
        "water_resources": 60.0,
        "lcoe_resource_quality": 75.0
      },
      "weighted_contributions": {
        "capacity": 21.25,
        "development_stage": 14.0,
        "grid_infrastructure": 7.68
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
    "algorithm_version": "2.3 - Enhanced with TNUoS Integration",
    "processing_time_seconds": 3.2,
    "rating_distribution": {
      "excellent": 5, "very_good": 12, "good": 18
    }
  }
}
Component Architecture (Current State)
Power Developer Dashboard (COMPLETED)
File: src/pages/UtilityDashboard.tsx
Key Features:

Customer selector with real-time metrics (line 230-250)
Color-coded project ratings sorted by score (line 290-320)
Compact sidebar design with developer information (line 305-335)
Infrastructure controls commented out (line 275 - currently disabled)

Data Center Developer Dashboard (ACTIVE DEVELOPMENT)
File: src/pages/HyperscalerDashboard.tsx
Current Implementation:

5-tab navigation structure (line 150-170)
PersonaSelector integration (line 180-200)
Infrastructure layer state management (line 50-90)
Map and project list integration (line 250-300)

DynamicSiteMap Component (PRODUCTION READY)
File: src/components/DynamicSiteMap.tsx
Current State: Fully functional with TNUoS visualization
Responsibilities:

Mapbox GL integration with UK/Ireland region switching
Project visualization with 1.0-10.0 investment rating color coding
Infrastructure layer management (6 layers working)
TNUoS zones display as background cost visualization
Interactive project popups with persona-specific details

MapOverlayControls (ENHANCED)
File: src/components/MapOverlayControls.tsx
Current Features:

Progressive disclosure with category grouping (line 60-90)
Infrastructure layer toggles with loading states (line 95-130)
Icon mapping system for proper TypeScript support (line 20-45)
Count display for enabled layers (line 110-120)

PersonaSelector Component (COMPLETED)
File: src/components/PersonaSelector.tsx
Implementation:

Tabbed persona selection interface (line 80-120)
Detailed criteria breakdown with progress bars (line 180-220)
Persona characteristic explanations (line 140-170)
Weight visualization and impact analysis (line 250-290)

Technical Architecture Decisions
Why Persona-Based Scoring?
Different data center types have fundamentally different infrastructure requirements:

Hyperscalers need massive power capacity and reliability above all
Colocation providers balance power, connectivity, and operational efficiency
Edge computing prioritizes quick deployment and low latency over capacity

Generic renewable energy scoring doesn't capture these nuanced requirements.
Why 1.0-10.0 Display Scale?

User-friendly: Intuitive rating system (like IMDb, Yelp)
Precise: 0.1 increments allow nuanced differentiation
Professional: Investment-grade appearance vs. academic letter grades
Scalable: Easy to extend with additional personas or criteria

Why TNUoS Integration?
Transmission costs can vary by £800k+ annually between regions for large projects. This represents a major operational cost difference that significantly impacts investment viability, especially for hyperscale deployments.
Why Streamlined Dashboard Design?
The original tabbed navigation spread functionality too thin. The new Power Developer Dashboard design prioritizes:

Single-screen workflows: Everything visible without tab switching
Optimized information hierarchy: Most important data prominently displayed
Reduced cognitive load: Fewer decisions, clearer paths to insights
Mobile responsiveness: Works across all device sizes

Development Team Requirements
Immediate Priorities (Next 2-4 Weeks)

Backend Developer: Fix development stage scoring and enhance algorithm generosity
Full-Stack Developer: Complete TNUoS algorithm integration
Frontend Developer: Apply streamlined design patterns to Data Center Developer Dashboard
QA Engineer: Test enhanced scoring algorithms for business logic accuracy

Medium Term (1-3 Months)

Data Engineer: Optimize spatial queries and infrastructure data pipeline
UX Designer: Design advanced filtering and comparison tools
AI Engineer: Complete Supabase Edge Functions deployment for persona analysis
DevOps Engineer: Implement automated data refresh pipelines

Environment Configuration
Required Environment Variables
bash# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Mapping (Frontend)  
MAPBOX_PUBLIC_TOKEN=pk.your-mapbox-token

# API Configuration
API_BASE_URL=https://infranodev2.onrender.com

# AI Integration (Ready for deployment)
OPENAI_API_KEY=your-openai-key  # For Supabase Edge Functions
Development Dependencies (Current)
json{
  "mapbox-gl": "^2.15.0",
  "@supabase/supabase-js": "^2.38.0", 
  "lucide-react": "^0.263.1",
  "recharts": "^2.8.0",
  "tailwindcss": "^3.3.0",
  "react-markdown": "^9.0.0"
}
Code Change Instructions Format
All development instructions follow this precise format:
File: src/path/to/file.tsx
Location: X% into file
Find: [exact lines to locate]
Replace: [specific changes needed]
After: [exact lines that should follow]
This ensures reproducible code changes without ambiguity about placement or context.
Performance & Quality Assurance
Known Performance Characteristics

API Response Times: <2s for individual site scoring, <5s for batch processing
Map Rendering: <1s for 100+ projects with clustering
Infrastructure Loading: 2-17s depending on layer complexity
Database Query Performance: Optimized with spatial indexing

Verified Working Workflows

Power Developer Customer Matching: Persona selection → API query → sorted results display
Data Center Site Assessment: Persona setup → map visualization → project analysis
Infrastructure Layer Management: Toggle controls → data fetching → map overlay rendering
Investment Rating Display: Persona-weighted scoring → color coding → popup details

Next Major Development Focus
Data Center Developer Dashboard Enhancement
Target Completion: Next 2-3 weeks
Key Improvements:

Apply Power Developer Dashboard design patterns
Implement investment rating threshold filtering
Add geographic search with radius controls
Create side-by-side site comparison tools
Build investment decision support workflows

This comprehensive platform now provides the UK's most sophisticated renewable energy investment analysis, combining technical feasibility assessment with real transmission cost economics across multiple data center deployment personas. The current state represents a production-ready founda
