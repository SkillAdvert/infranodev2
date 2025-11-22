/**
 * useInfrastructure Hook Tests
 *
 * Tests for infrastructure data fetching (transmission, substations, etc.)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import {
  useInfrastructure,
  useTransmission,
  useSubstations,
  useGSP,
  useFiber,
  useTNUOS,
  useIXP,
  useWater,
  useDNOAreas,
  useAllInfrastructure,
  infrastructureKeys,
} from '../useInfrastructure';

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

describe('useTransmission', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches transmission lines', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useTransmission(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.type).toBe('FeatureCollection');
  });

  it('returns LineString features', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useTransmission(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const features = result.current.data?.features;
    if (features && features.length > 0) {
      expect(features[0].geometry.type).toBe('LineString');
    }
  });

  it('can be disabled', () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useTransmission(false), { wrapper });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });
});

describe('useSubstations', () => {
  it('fetches substations', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSubstations(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.type).toBe('FeatureCollection');
  });

  it('returns Point features', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSubstations(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const features = result.current.data?.features;
    if (features && features.length > 0) {
      expect(features[0].geometry.type).toBe('Point');
    }
  });
});

describe('useGSP', () => {
  it('fetches Grid Supply Points', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useGSP(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.type).toBe('FeatureCollection');
  });
});

describe('useFiber', () => {
  it('fetches fiber network', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useFiber(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.type).toBe('FeatureCollection');
  });

  it('returns features with provider property', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useFiber(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const features = result.current.data?.features;
    if (features && features.length > 0) {
      expect(features[0].properties).toHaveProperty('provider');
    }
  });
});

describe('useTNUOS', () => {
  it('fetches TNUOS zones', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useTNUOS(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.type).toBe('FeatureCollection');
  });

  it('returns Polygon features', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useTNUOS(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const features = result.current.data?.features;
    if (features && features.length > 0) {
      expect(features[0].geometry.type).toBe('Polygon');
    }
  });

  it('includes tariff information', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useTNUOS(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const features = result.current.data?.features;
    if (features && features.length > 0) {
      expect(features[0].properties).toHaveProperty('tariff');
    }
  });
});

describe('useIXP', () => {
  it('fetches Internet Exchange Points', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useIXP(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.type).toBe('FeatureCollection');
  });
});

describe('useWater', () => {
  it('fetches water resources', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useWater(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.type).toBe('FeatureCollection');
  });
});

describe('useDNOAreas', () => {
  it('fetches DNO areas', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDNOAreas(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.type).toBe('FeatureCollection');
  });

  it('returns Polygon features', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDNOAreas(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const features = result.current.data?.features;
    if (features && features.length > 0) {
      expect(features[0].geometry.type).toBe('Polygon');
    }
  });
});

describe('useAllInfrastructure', () => {
  it('fetches all infrastructure layers', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useAllInfrastructure(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toHaveProperty('transmission');
    expect(result.current.data).toHaveProperty('substations');
    expect(result.current.data).toHaveProperty('gsp');
    expect(result.current.data).toHaveProperty('fiber');
    expect(result.current.data).toHaveProperty('tnuos');
    expect(result.current.data).toHaveProperty('ixp');
    expect(result.current.data).toHaveProperty('water');
    expect(result.current.data).toHaveProperty('dno-areas');
  });

  it('fetches only specified layers', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useAllInfrastructure(['transmission', 'substations']),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data.transmission).not.toBeNull();
    expect(result.current.data.substations).not.toBeNull();
  });

  it('reports overall error state', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useAllInfrastructure(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isError).toBe(false);
    expect(result.current.errors).toEqual([]);
  });
});

describe('useInfrastructure (generic)', () => {
  it('fetches any infrastructure type', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useInfrastructure('transmission'), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.type).toBe('FeatureCollection');
  });

  it('can be disabled', () => {
    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useInfrastructure('transmission', false),
      { wrapper }
    );

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });
});

describe('Infrastructure Query Keys', () => {
  it('generates correct base key', () => {
    expect(infrastructureKeys.all).toEqual(['infrastructure']);
  });

  it('generates correct type key', () => {
    expect(infrastructureKeys.type('transmission')).toEqual([
      'infrastructure',
      'transmission',
    ]);
    expect(infrastructureKeys.type('substations')).toEqual([
      'infrastructure',
      'substations',
    ]);
    expect(infrastructureKeys.type('fiber')).toEqual([
      'infrastructure',
      'fiber',
    ]);
  });
});

describe('GeoJSON Structure Validation', () => {
  it('all infrastructure returns valid GeoJSON FeatureCollections', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useAllInfrastructure(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    Object.values(result.current.data).forEach((collection) => {
      if (collection) {
        expect(collection.type).toBe('FeatureCollection');
        expect(Array.isArray(collection.features)).toBe(true);
      }
    });
  });

  it('features have required GeoJSON properties', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useTransmission(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const features = result.current.data?.features || [];
    features.forEach((feature) => {
      expect(feature).toHaveProperty('type', 'Feature');
      expect(feature).toHaveProperty('geometry');
      expect(feature).toHaveProperty('properties');
      expect(feature.geometry).toHaveProperty('type');
      expect(feature.geometry).toHaveProperty('coordinates');
    });
  });
});
