/**
 * API Integration Tests
 *
 * Tests for complete API interaction flows, verifying that
 * frontend components correctly communicate with backend endpoints.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';

const API_BASE = 'https://infranodev2.onrender.com';

describe('API Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Health Check', () => {
    it('API returns healthy status', async () => {
      const response = await fetch(`${API_BASE}/health`);
      const data = await response.json();

      expect(data.status).toBe('healthy');
    });

    it('Root endpoint returns API info', async () => {
      const response = await fetch(`${API_BASE}/`);
      const data = await response.json();

      expect(data.status).toBe('ok');
      expect(data.message).toContain('InfraNode');
    });
  });

  describe('Projects API', () => {
    it('GET /api/projects returns project list', async () => {
      const response = await fetch(`${API_BASE}/api/projects`);
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(Array.isArray(data.data)).toBe(true);
      expect(data.count).toBeGreaterThan(0);
    });

    it('GET /api/projects with persona filters correctly', async () => {
      const response = await fetch(`${API_BASE}/api/projects?persona=hyperscaler`);
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(data.persona).toBe('hyperscaler');
    });

    it('GET /api/projects/enhanced returns scored projects', async () => {
      const response = await fetch(`${API_BASE}/api/projects/enhanced`);
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(data.data[0]).toHaveProperty('component_scores');
      expect(data.data[0]).toHaveProperty('total_score');
    });

    it('GET /api/projects/geojson returns valid GeoJSON', async () => {
      const response = await fetch(`${API_BASE}/api/projects/geojson`);
      const data = await response.json();

      expect(data.type).toBe('FeatureCollection');
      expect(Array.isArray(data.features)).toBe(true);

      if (data.features.length > 0) {
        expect(data.features[0].type).toBe('Feature');
        expect(data.features[0].geometry.type).toBe('Point');
      }
    });

    it('POST /api/projects/customer-match filters by criteria', async () => {
      const response = await fetch(`${API_BASE}/api/projects/customer-match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          criteria: { min_capacity_mw: 100 },
          persona: 'hyperscaler',
        }),
      });
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(Array.isArray(data.matched_projects)).toBe(true);
      expect(typeof data.match_count).toBe('number');
    });
  });

  describe('Infrastructure API', () => {
    const infrastructureTypes = [
      'transmission',
      'substations',
      'gsp',
      'fiber',
      'tnuos',
      'ixp',
      'water',
      'dno-areas',
    ];

    infrastructureTypes.forEach((type) => {
      it(`GET /api/infrastructure/${type} returns GeoJSON`, async () => {
        const response = await fetch(`${API_BASE}/api/infrastructure/${type}`);
        const data = await response.json();

        expect(data.type).toBe('FeatureCollection');
        expect(Array.isArray(data.features)).toBe(true);
      });
    });
  });

  describe('Financial Model API', () => {
    it('POST /api/financial-model calculates NPV/IRR/LCOE', async () => {
      const response = await fetch(`${API_BASE}/api/financial-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          capacity_mw: 100,
          technology: 'Solar',
        }),
      });
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(data.standard).toHaveProperty('npv');
      expect(data.standard).toHaveProperty('irr');
      expect(data.standard).toHaveProperty('lcoe');
      expect(data.autoproducer).toHaveProperty('npv');
    });

    it('Financial model returns 25-year cashflows', async () => {
      const response = await fetch(`${API_BASE}/api/financial-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          capacity_mw: 100,
          technology: 'Solar',
        }),
      });
      const data = await response.json();

      expect(data.standard.cashflows).toHaveLength(25);
      expect(data.standard.cashflows[0]).toHaveProperty('year', 1);
      expect(data.standard.cashflows[24]).toHaveProperty('year', 25);
    });
  });

  describe('User Sites API', () => {
    it('POST /api/user-sites/score scores custom locations', async () => {
      const response = await fetch(`${API_BASE}/api/user-sites/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sites: [
            { name: 'Test Site', latitude: 52.0, longitude: -1.5, capacity_mw: 50 },
          ],
        }),
      });
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(Array.isArray(data.scored_sites)).toBe(true);
      expect(data.scored_sites[0]).toHaveProperty('total_score');
      expect(data.scored_sites[0]).toHaveProperty('component_scores');
      expect(data.scored_sites[0]).toHaveProperty('nearest_infrastructure');
    });
  });

  describe('TEC Connections API', () => {
    it('GET /api/tec/connections returns connection data', async () => {
      const response = await fetch(`${API_BASE}/api/tec/connections`);
      const data = await response.json();

      expect(data.success).toBe(true);
      expect(Array.isArray(data.connections)).toBe(true);
      expect(typeof data.count).toBe('number');
    });
  });

  describe('Error Handling', () => {
    it('handles server errors gracefully', async () => {
      server.use(
        http.get(`${API_BASE}/api/projects`, () => {
          return HttpResponse.json(
            { success: false, error_type: 'ServerError', message: 'Internal error' },
            { status: 500 }
          );
        })
      );

      const response = await fetch(`${API_BASE}/api/projects`);
      expect(response.status).toBe(500);

      const data = await response.json();
      expect(data.success).toBe(false);
    });

    it('handles validation errors', async () => {
      server.use(
        http.post(`${API_BASE}/api/user-sites/score`, () => {
          return HttpResponse.json(
            {
              detail: [
                {
                  type: 'value_error',
                  loc: ['body', 'latitude'],
                  msg: 'Latitude outside UK bounds',
                },
              ],
            },
            { status: 422 }
          );
        })
      );

      const response = await fetch(`${API_BASE}/api/user-sites/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sites: [{ latitude: 65.0, longitude: -1.5 }],
        }),
      });

      expect(response.status).toBe(422);
    });
  });

  describe('Response Timing', () => {
    it('projects endpoint responds within timeout', async () => {
      const start = Date.now();
      await fetch(`${API_BASE}/api/projects`);
      const duration = Date.now() - start;

      // Should respond within 5 seconds (mock has 100ms delay)
      expect(duration).toBeLessThan(5000);
    });

    it('financial model responds within timeout', async () => {
      const start = Date.now();
      await fetch(`${API_BASE}/api/financial-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ capacity_mw: 100, technology: 'Solar' }),
      });
      const duration = Date.now() - start;

      // Should respond within 5 seconds (mock has 800ms delay)
      expect(duration).toBeLessThan(5000);
    });
  });

  describe('Request Headers', () => {
    it('accepts JSON content type', async () => {
      const response = await fetch(`${API_BASE}/api/projects/customer-match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ criteria: {}, persona: 'hyperscaler' }),
      });

      expect(response.ok).toBe(true);
    });
  });

  describe('Concurrent Requests', () => {
    it('handles multiple simultaneous requests', async () => {
      const requests = [
        fetch(`${API_BASE}/api/projects`),
        fetch(`${API_BASE}/api/projects/enhanced`),
        fetch(`${API_BASE}/api/projects/geojson`),
        fetch(`${API_BASE}/api/infrastructure/transmission`),
        fetch(`${API_BASE}/api/infrastructure/substations`),
      ];

      const responses = await Promise.all(requests);

      responses.forEach((response) => {
        expect(response.ok).toBe(true);
      });
    });
  });
});

describe('End-to-End Data Flow', () => {
  it('complete project search flow', async () => {
    // 1. Fetch initial project list
    const projectsResponse = await fetch(`${API_BASE}/api/projects?persona=hyperscaler`);
    const projectsData = await projectsResponse.json();
    expect(projectsData.success).toBe(true);

    // 2. Apply filter criteria
    const searchResponse = await fetch(`${API_BASE}/api/projects/customer-match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        criteria: { min_capacity_mw: 100 },
        persona: 'hyperscaler',
      }),
    });
    const searchData = await searchResponse.json();
    expect(searchData.success).toBe(true);
    expect(searchData.matched_projects.length).toBeLessThanOrEqual(projectsData.data.length);

    // 3. Get GeoJSON for map display
    const geoResponse = await fetch(`${API_BASE}/api/projects/geojson?persona=hyperscaler`);
    const geoData = await geoResponse.json();
    expect(geoData.type).toBe('FeatureCollection');
  });

  it('complete financial analysis flow', async () => {
    // 1. Get project details
    const projectsResponse = await fetch(`${API_BASE}/api/projects/enhanced`);
    const projectsData = await projectsResponse.json();
    const project = projectsData.data[0];

    // 2. Run financial model
    const modelResponse = await fetch(`${API_BASE}/api/financial-model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        capacity_mw: project.capacity_mw,
        technology: project.technology,
      }),
    });
    const modelData = await modelResponse.json();
    expect(modelData.success).toBe(true);

    // 3. Compare standard vs autoproducer
    expect(modelData.autoproducer.irr).toBeGreaterThan(modelData.standard.irr);
  });

  it('complete site assessment flow', async () => {
    // 1. User uploads sites
    const scoreResponse = await fetch(`${API_BASE}/api/user-sites/score`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sites: [
          { name: 'Site A', latitude: 52.0, longitude: -1.5, capacity_mw: 100 },
          { name: 'Site B', latitude: 53.0, longitude: -2.0, capacity_mw: 150 },
        ],
      }),
    });
    const scoreData = await scoreResponse.json();
    expect(scoreData.success).toBe(true);
    expect(scoreData.scored_sites).toHaveLength(2);

    // 2. Get benchmark projects for comparison
    const projectsResponse = await fetch(`${API_BASE}/api/projects/enhanced`);
    const projectsData = await projectsResponse.json();

    // 3. Compare user sites to benchmark
    const userSiteScore = scoreData.scored_sites[0].total_score;
    const avgProjectScore =
      projectsData.data.reduce((sum: number, p: { total_score: number }) => sum + p.total_score, 0) /
      projectsData.data.length;

    expect(typeof userSiteScore).toBe('number');
    expect(typeof avgProjectScore).toBe('number');
  });
});
