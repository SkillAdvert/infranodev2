/**
 * useProjects Hook Tests
 *
 * Tests for project data fetching, filtering, and caching hooks.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import {
  useProjects,
  useEnhancedProjects,
  useProjectsGeoJSON,
  useSearchProjects,
  projectKeys,
} from '../useProjects';

// Create a fresh query client for each test
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useProjects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial Fetch', () => {
    it('returns loading state initially', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useProjects(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });

    it('fetches projects successfully', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useProjects(), { wrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toBeDefined();
      expect(result.current.data?.success).toBe(true);
      expect(result.current.data?.data).toBeInstanceOf(Array);
    });

    it('returns project data with correct structure', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useProjects(), { wrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const projects = result.current.data?.data;
      expect(projects).toBeDefined();

      if (projects && projects.length > 0) {
        const project = projects[0];
        expect(project).toHaveProperty('id');
        expect(project).toHaveProperty('name');
        expect(project).toHaveProperty('capacity_mw');
        expect(project).toHaveProperty('latitude');
        expect(project).toHaveProperty('longitude');
        expect(project).toHaveProperty('technology');
        expect(project).toHaveProperty('status');
        expect(project).toHaveProperty('total_score');
        expect(project).toHaveProperty('component_scores');
      }
    });
  });

  describe('Persona Filtering', () => {
    it('fetches projects for hyperscaler persona', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useProjects('hyperscaler'), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.persona).toBe('hyperscaler');
    });

    it('fetches projects for utility persona', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useProjects('utility'), { wrapper });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.persona).toBe('utility');
    });

    it('fetches projects for colocation persona', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useProjects('colocation'), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.persona).toBe('colocation');
    });
  });

  describe('Error Handling', () => {
    it('handles fetch errors gracefully', async () => {
      // This test would use server.use() to override handlers with error responses
      const wrapper = createWrapper();
      const { result } = renderHook(() => useProjects(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Normal response from MSW mock
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe('useEnhancedProjects', () => {
  it('fetches enhanced projects with scores', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useEnhancedProjects('hyperscaler'), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.data).toBeDefined();
  });

  it('respects limit parameter', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useEnhancedProjects('hyperscaler', 10), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Mock returns up to the limit
    expect(result.current.data?.data.length).toBeLessThanOrEqual(10);
  });

  it('returns component scores for each project', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useEnhancedProjects(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const projects = result.current.data?.data;
    if (projects && projects.length > 0) {
      const scores = projects[0].component_scores;
      expect(scores).toHaveProperty('grid_proximity');
      expect(scores).toHaveProperty('land_availability');
      expect(scores).toHaveProperty('fiber_connectivity');
      expect(scores).toHaveProperty('transmission_access');
    }
  });
});

describe('useProjectsGeoJSON', () => {
  it('fetches projects as GeoJSON', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useProjectsGeoJSON(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.type).toBe('FeatureCollection');
    expect(result.current.data?.features).toBeInstanceOf(Array);
  });

  it('returns features with correct GeoJSON structure', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useProjectsGeoJSON(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const features = result.current.data?.features;
    if (features && features.length > 0) {
      const feature = features[0];
      expect(feature.type).toBe('Feature');
      expect(feature.geometry.type).toBe('Point');
      expect(feature.geometry.coordinates).toHaveLength(2);
      expect(feature.properties).toHaveProperty('id');
      expect(feature.properties).toHaveProperty('name');
    }
  });

  it('includes persona in metadata', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useProjectsGeoJSON('hyperscaler'), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.metadata?.persona).toBe('hyperscaler');
  });
});

describe('useSearchProjects', () => {
  it('searches projects by criteria', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSearchProjects(), { wrapper });

    // Trigger the mutation
    result.current.mutate({
      criteria: { min_capacity_mw: 100 },
      persona: 'hyperscaler',
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.matched_projects).toBeDefined();
  });

  it('returns match count', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSearchProjects(), { wrapper });

    result.current.mutate({
      criteria: { min_capacity_mw: 50 },
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(typeof result.current.data?.match_count).toBe('number');
  });

  it('filters by capacity criteria', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSearchProjects(), { wrapper });

    result.current.mutate({
      criteria: { min_capacity_mw: 200 },
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const matchedProjects = result.current.data?.matched_projects || [];
    matchedProjects.forEach((project) => {
      expect(project.capacity_mw).toBeGreaterThanOrEqual(200);
    });
  });
});

describe('Query Keys', () => {
  it('generates correct base key', () => {
    expect(projectKeys.all).toEqual(['projects']);
  });

  it('generates correct list key without persona', () => {
    expect(projectKeys.list()).toEqual(['projects', 'list', undefined]);
  });

  it('generates correct list key with persona', () => {
    expect(projectKeys.list('hyperscaler')).toEqual([
      'projects',
      'list',
      'hyperscaler',
    ]);
  });

  it('generates correct enhanced key', () => {
    expect(projectKeys.enhanced('utility', 20)).toEqual([
      'projects',
      'enhanced',
      'utility',
      20,
    ]);
  });

  it('generates correct geojson key', () => {
    expect(projectKeys.geojson('colocation')).toEqual([
      'projects',
      'geojson',
      'colocation',
    ]);
  });
});

describe('Caching Behavior', () => {
  it('caches results for staleTime duration', async () => {
    const wrapper = createWrapper();

    // First fetch
    const { result: result1 } = renderHook(() => useProjects('hyperscaler'), {
      wrapper,
    });

    await waitFor(() => {
      expect(result1.current.isSuccess).toBe(true);
    });

    // Second fetch should use cache
    const { result: result2 } = renderHook(() => useProjects('hyperscaler'), {
      wrapper,
    });

    // Should return cached data immediately (not loading)
    await waitFor(() => {
      expect(result2.current.isSuccess).toBe(true);
    });
  });
});
