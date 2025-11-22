/**
 * MSW Request Handlers
 *
 * Mock handlers for all API endpoints used by the frontend.
 * Based on the backend API specification in BACKEND_INTEGRATION_REFERENCE.md
 */

import { http, HttpResponse, delay } from 'msw';

const API_BASE = 'https://infranodev2.onrender.com';

// Mock data
const mockProjects = [
  {
    id: 'proj-001',
    name: 'Sunrise Solar Farm',
    capacity_mw: 150,
    latitude: 52.4862,
    longitude: -1.8904,
    technology: 'Solar',
    status: 'active',
    total_score: 85,
    component_scores: {
      grid_proximity: 90,
      land_availability: 80,
      fiber_connectivity: 85,
      transmission_access: 88,
      water_access: 75,
      planning_status: 82,
      environmental: 90,
      financial_viability: 88,
    },
    match_reasons: ['High grid proximity', 'Excellent fiber connectivity'],
  },
  {
    id: 'proj-002',
    name: 'Highland Wind Complex',
    capacity_mw: 250,
    latitude: 56.8198,
    longitude: -5.1052,
    technology: 'Wind',
    status: 'active',
    total_score: 78,
    component_scores: {
      grid_proximity: 72,
      land_availability: 95,
      fiber_connectivity: 60,
      transmission_access: 75,
      water_access: 90,
      planning_status: 80,
      environmental: 70,
      financial_viability: 82,
    },
    match_reasons: ['Large land availability', 'Strong wind resource'],
  },
  {
    id: 'proj-003',
    name: 'Thames BESS',
    capacity_mw: 100,
    latitude: 51.5074,
    longitude: -0.1278,
    technology: 'Battery',
    status: 'development',
    total_score: 92,
    component_scores: {
      grid_proximity: 95,
      land_availability: 70,
      fiber_connectivity: 98,
      transmission_access: 92,
      water_access: 85,
      planning_status: 90,
      environmental: 95,
      financial_viability: 95,
    },
    match_reasons: ['Prime location', 'Excellent grid access'],
  },
];

const mockGeoJSON = {
  type: 'FeatureCollection' as const,
  features: mockProjects.map((project) => ({
    type: 'Feature' as const,
    properties: {
      id: project.id,
      name: project.name,
      capacity_mw: project.capacity_mw,
      technology: project.technology,
      status: project.status,
      total_score: project.total_score,
    },
    geometry: {
      type: 'Point' as const,
      coordinates: [project.longitude, project.latitude],
    },
  })),
};

const mockInfrastructure = {
  transmission: {
    type: 'FeatureCollection' as const,
    features: [
      {
        type: 'Feature' as const,
        properties: { id: 'trans-001', name: '400kV Line A', voltage: 400 },
        geometry: {
          type: 'LineString' as const,
          coordinates: [
            [-2.0, 52.0],
            [-1.5, 52.5],
            [-1.0, 53.0],
          ],
        },
      },
    ],
  },
  substations: {
    type: 'FeatureCollection' as const,
    features: [
      {
        type: 'Feature' as const,
        properties: { id: 'sub-001', name: 'Birmingham Grid', capacity_mva: 500 },
        geometry: { type: 'Point' as const, coordinates: [-1.8904, 52.4862] },
      },
    ],
  },
  gsp: {
    type: 'FeatureCollection' as const,
    features: [
      {
        type: 'Feature' as const,
        properties: { id: 'gsp-001', name: 'GSP Alpha', capacity_mw: 200 },
        geometry: { type: 'Point' as const, coordinates: [-1.5, 52.0] },
      },
    ],
  },
  fiber: {
    type: 'FeatureCollection' as const,
    features: [
      {
        type: 'Feature' as const,
        properties: { id: 'fiber-001', name: 'Fiber Backbone', provider: 'BT' },
        geometry: {
          type: 'LineString' as const,
          coordinates: [
            [-2.5, 51.5],
            [-1.5, 52.5],
          ],
        },
      },
    ],
  },
  ixp: {
    type: 'FeatureCollection' as const,
    features: [
      {
        type: 'Feature' as const,
        properties: { id: 'ixp-001', name: 'London Internet Exchange' },
        geometry: { type: 'Point' as const, coordinates: [-0.1278, 51.5074] },
      },
    ],
  },
  water: {
    type: 'FeatureCollection' as const,
    features: [
      {
        type: 'Feature' as const,
        properties: { id: 'water-001', name: 'River Thames' },
        geometry: {
          type: 'LineString' as const,
          coordinates: [
            [-0.5, 51.5],
            [0.5, 51.4],
          ],
        },
      },
    ],
  },
  tnuos: {
    type: 'FeatureCollection' as const,
    features: [
      {
        type: 'Feature' as const,
        properties: { id: 'tnuos-001', zone: 'Zone A', tariff: 25.5 },
        geometry: {
          type: 'Polygon' as const,
          coordinates: [
            [
              [-2.0, 51.0],
              [-1.0, 51.0],
              [-1.0, 52.0],
              [-2.0, 52.0],
              [-2.0, 51.0],
            ],
          ],
        },
      },
    ],
  },
  dnoAreas: {
    type: 'FeatureCollection' as const,
    features: [
      {
        type: 'Feature' as const,
        properties: { id: 'dno-001', name: 'Western Power Distribution' },
        geometry: {
          type: 'Polygon' as const,
          coordinates: [
            [
              [-3.0, 51.0],
              [-2.0, 51.0],
              [-2.0, 53.0],
              [-3.0, 53.0],
              [-3.0, 51.0],
            ],
          ],
        },
      },
    ],
  },
};

const mockTecConnections = [
  {
    id: 'tec-001',
    project_name: 'Solar Farm Alpha',
    capacity_mw: 100,
    connection_date: '2025-06-01',
    status: 'approved',
    latitude: 52.0,
    longitude: -1.5,
  },
  {
    id: 'tec-002',
    project_name: 'Wind Farm Beta',
    capacity_mw: 200,
    connection_date: '2025-09-15',
    status: 'pending',
    latitude: 53.0,
    longitude: -2.0,
  },
];

// Request handlers
export const handlers = [
  // Health check
  http.get(`${API_BASE}/`, () => {
    return HttpResponse.json({ status: 'ok', message: 'InfraNode API v2' });
  }),

  http.get(`${API_BASE}/health`, () => {
    return HttpResponse.json({ status: 'healthy', uptime: 3600 });
  }),

  // Projects endpoints
  http.get(`${API_BASE}/api/projects`, async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const persona = url.searchParams.get('persona');

    return HttpResponse.json({
      success: true,
      data: mockProjects,
      persona: persona || 'greenfield',
      count: mockProjects.length,
    });
  }),

  http.get(`${API_BASE}/api/projects/geojson`, async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const persona = url.searchParams.get('persona');

    return HttpResponse.json({
      ...mockGeoJSON,
      metadata: { persona: persona || 'greenfield', count: mockGeoJSON.features.length },
    });
  }),

  http.get(`${API_BASE}/api/projects/enhanced`, async ({ request }) => {
    await delay(150);
    const url = new URL(request.url);
    const persona = url.searchParams.get('persona');
    const limit = parseInt(url.searchParams.get('limit') || '50', 10);

    const projects = mockProjects.slice(0, limit);

    return HttpResponse.json({
      success: true,
      data: projects,
      persona: persona || 'greenfield',
      count: projects.length,
    });
  }),

  http.post(`${API_BASE}/api/projects/customer-match`, async ({ request }) => {
    await delay(200);
    const body = await request.json() as Record<string, unknown>;
    const criteria = body.criteria as Record<string, unknown> || {};
    const persona = body.persona as string || 'greenfield';

    // Filter based on criteria (simplified)
    let filtered = [...mockProjects];
    if (criteria.min_capacity_mw) {
      filtered = filtered.filter((p) => p.capacity_mw >= (criteria.min_capacity_mw as number));
    }

    return HttpResponse.json({
      success: true,
      matched_projects: filtered,
      persona,
      match_count: filtered.length,
    });
  }),

  http.post(`${API_BASE}/api/projects/compare-scoring`, async ({ request }) => {
    await delay(150);
    const body = await request.json() as Record<string, unknown>;
    const projectIds = body.project_ids as string[] || [];

    const compared = mockProjects.filter((p) => projectIds.includes(p.id));

    return HttpResponse.json({
      success: true,
      comparison: compared,
      statistics: {
        average_score: 85,
        max_score: 92,
        min_score: 78,
      },
    });
  }),

  http.post(`${API_BASE}/api/projects/power-developer-analysis`, async () => {
    await delay(300);

    return HttpResponse.json({
      success: true,
      analysis: {
        top_projects: mockProjects.slice(0, 2),
        market_insights: {
          total_capacity_gw: 0.5,
          average_score: 85,
          technology_distribution: { Solar: 1, Wind: 1, Battery: 1 },
        },
      },
    });
  }),

  // Infrastructure endpoints
  http.get(`${API_BASE}/api/infrastructure/transmission`, async () => {
    await delay(100);
    return HttpResponse.json(mockInfrastructure.transmission);
  }),

  http.get(`${API_BASE}/api/infrastructure/substations`, async () => {
    await delay(100);
    return HttpResponse.json(mockInfrastructure.substations);
  }),

  http.get(`${API_BASE}/api/infrastructure/gsp`, async () => {
    await delay(100);
    return HttpResponse.json(mockInfrastructure.gsp);
  }),

  http.get(`${API_BASE}/api/infrastructure/fiber`, async () => {
    await delay(100);
    return HttpResponse.json(mockInfrastructure.fiber);
  }),

  http.get(`${API_BASE}/api/infrastructure/tnuos`, async () => {
    await delay(100);
    return HttpResponse.json(mockInfrastructure.tnuos);
  }),

  http.get(`${API_BASE}/api/infrastructure/ixp`, async () => {
    await delay(100);
    return HttpResponse.json(mockInfrastructure.ixp);
  }),

  http.get(`${API_BASE}/api/infrastructure/water`, async () => {
    await delay(100);
    return HttpResponse.json(mockInfrastructure.water);
  }),

  http.get(`${API_BASE}/api/infrastructure/dno-areas`, async () => {
    await delay(100);
    return HttpResponse.json(mockInfrastructure.dnoAreas);
  }),

  // TEC Connections
  http.get(`${API_BASE}/api/tec/connections`, async () => {
    await delay(150);
    return HttpResponse.json({
      success: true,
      connections: mockTecConnections,
      count: mockTecConnections.length,
    });
  }),

  // User Sites
  http.post(`${API_BASE}/api/user-sites/score`, async ({ request }) => {
    await delay(500);
    const body = await request.json() as Record<string, unknown>;
    const sites = body.sites as Array<Record<string, unknown>> || [];

    const scoredSites = sites.map((site, index) => ({
      ...site,
      id: `user-site-${index}`,
      total_score: 70 + Math.random() * 25,
      component_scores: {
        grid_proximity: 70 + Math.random() * 30,
        land_availability: 70 + Math.random() * 30,
        fiber_connectivity: 70 + Math.random() * 30,
        transmission_access: 70 + Math.random() * 30,
        water_access: 70 + Math.random() * 30,
        planning_status: 70 + Math.random() * 30,
        environmental: 70 + Math.random() * 30,
        financial_viability: 70 + Math.random() * 30,
      },
      nearest_infrastructure: {
        transmission_km: 5 + Math.random() * 20,
        substation_km: 3 + Math.random() * 15,
        fiber_km: 1 + Math.random() * 10,
      },
    }));

    return HttpResponse.json({
      success: true,
      scored_sites: scoredSites,
      count: scoredSites.length,
    });
  }),

  // Financial Model
  http.post(`${API_BASE}/api/financial-model`, async ({ request }) => {
    await delay(800);
    const body = await request.json() as Record<string, unknown>;
    const capacityMw = (body.capacity_mw as number) || 100;

    return HttpResponse.json({
      success: true,
      standard: {
        npv: capacityMw * 50000,
        irr: 0.12,
        lcoe: 42.5,
        payback_years: 7.5,
        annual_revenue: capacityMw * 150000,
        cashflows: Array.from({ length: 25 }, (_, i) => ({
          year: i + 1,
          revenue: capacityMw * 150000 * (1 + i * 0.01),
          opex: capacityMw * 30000,
          net_cashflow: capacityMw * 120000,
        })),
      },
      autoproducer: {
        npv: capacityMw * 65000,
        irr: 0.15,
        lcoe: 38.5,
        payback_years: 6.2,
        annual_revenue: capacityMw * 180000,
        uplift_percent: 25,
      },
      metrics: {
        capacity_factor: 0.25,
        annual_generation_mwh: capacityMw * 8760 * 0.25,
        discount_rate: 0.08,
      },
    });
  }),
];

// Error response handlers (for testing error states)
export const errorHandlers = {
  serverError: http.get(`${API_BASE}/api/projects`, () => {
    return HttpResponse.json(
      { success: false, error_type: 'ServerError', message: 'Internal server error' },
      { status: 500 }
    );
  }),

  notFound: http.get(`${API_BASE}/api/projects/:id`, () => {
    return HttpResponse.json(
      { success: false, error_type: 'NotFound', message: 'Project not found' },
      { status: 404 }
    );
  }),

  validationError: http.post(`${API_BASE}/api/user-sites/score`, () => {
    return HttpResponse.json(
      {
        detail: [
          {
            type: 'value_error',
            loc: ['body', 'latitude'],
            msg: 'Latitude outside UK bounds',
            input: 65.0,
          },
        ],
      },
      { status: 422 }
    );
  }),

  timeout: http.get(`${API_BASE}/api/projects`, async () => {
    await delay(100000); // Simulate timeout
    return HttpResponse.json({ success: true, data: [] });
  }),
};
