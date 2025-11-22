/**
 * useInfrastructure Hook
 *
 * Manages infrastructure data fetching for map layers.
 * Handles transmission lines, substations, GSP, fiber, etc.
 */

import { useQuery, useQueries } from '@tanstack/react-query';

// API Configuration
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://infranodev2.onrender.com';
const API_TIMEOUT = 90000;

// Types
export type InfrastructureType =
  | 'transmission'
  | 'substations'
  | 'gsp'
  | 'fiber'
  | 'tnuos'
  | 'ixp'
  | 'water'
  | 'dno-areas';

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

export interface GeoJSONFeature {
  type: 'Feature';
  properties: Record<string, unknown>;
  geometry: {
    type: 'Point' | 'LineString' | 'Polygon' | 'MultiPolygon';
    coordinates: number[] | number[][] | number[][][] | number[][][][];
  };
}

export interface TransmissionProperties {
  id: string;
  name: string;
  voltage: number;
  operator?: string;
}

export interface SubstationProperties {
  id: string;
  name: string;
  capacity_mva: number;
  voltage?: number;
}

export interface GSPProperties {
  id: string;
  name: string;
  capacity_mw: number;
  dno?: string;
}

export interface FiberProperties {
  id: string;
  name: string;
  provider: string;
  type?: string;
}

export interface IXPProperties {
  id: string;
  name: string;
  participants?: number;
  bandwidth_gbps?: number;
}

export interface WaterProperties {
  id: string;
  name: string;
  type: 'river' | 'reservoir' | 'treatment';
}

export interface TNUOSProperties {
  id: string;
  zone: string;
  tariff: number;
  year?: number;
}

export interface DNOAreaProperties {
  id: string;
  name: string;
  operator: string;
}

// API Functions
async function fetchWithTimeout(url: string): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    const response = await fetch(url, { signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchInfrastructure(type: InfrastructureType): Promise<GeoJSONFeatureCollection> {
  const url = `${API_BASE}/api/infrastructure/${type}`;
  const response = await fetchWithTimeout(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch ${type}: ${response.status}`);
  }

  return response.json();
}

// Query Keys
export const infrastructureKeys = {
  all: ['infrastructure'] as const,
  type: (type: InfrastructureType) => [...infrastructureKeys.all, type] as const,
};

// Individual layer hooks

/**
 * Fetch transmission lines
 */
export function useTransmission(enabled = true) {
  return useQuery({
    queryKey: infrastructureKeys.type('transmission'),
    queryFn: () => fetchInfrastructure('transmission'),
    staleTime: 10 * 60 * 1000, // 10 minutes (infrastructure rarely changes)
    gcTime: 30 * 60 * 1000,
    enabled,
  });
}

/**
 * Fetch substations
 */
export function useSubstations(enabled = true) {
  return useQuery({
    queryKey: infrastructureKeys.type('substations'),
    queryFn: () => fetchInfrastructure('substations'),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    enabled,
  });
}

/**
 * Fetch Grid Supply Points
 */
export function useGSP(enabled = true) {
  return useQuery({
    queryKey: infrastructureKeys.type('gsp'),
    queryFn: () => fetchInfrastructure('gsp'),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    enabled,
  });
}

/**
 * Fetch fiber network
 */
export function useFiber(enabled = true) {
  return useQuery({
    queryKey: infrastructureKeys.type('fiber'),
    queryFn: () => fetchInfrastructure('fiber'),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    enabled,
  });
}

/**
 * Fetch TNUOS zones
 */
export function useTNUOS(enabled = true) {
  return useQuery({
    queryKey: infrastructureKeys.type('tnuos'),
    queryFn: () => fetchInfrastructure('tnuos'),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    enabled,
  });
}

/**
 * Fetch Internet Exchange Points
 */
export function useIXP(enabled = true) {
  return useQuery({
    queryKey: infrastructureKeys.type('ixp'),
    queryFn: () => fetchInfrastructure('ixp'),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    enabled,
  });
}

/**
 * Fetch water resources
 */
export function useWater(enabled = true) {
  return useQuery({
    queryKey: infrastructureKeys.type('water'),
    queryFn: () => fetchInfrastructure('water'),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    enabled,
  });
}

/**
 * Fetch DNO areas
 */
export function useDNOAreas(enabled = true) {
  return useQuery({
    queryKey: infrastructureKeys.type('dno-areas'),
    queryFn: () => fetchInfrastructure('dno-areas'),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    enabled,
  });
}

/**
 * Fetch all infrastructure layers at once
 */
export function useAllInfrastructure(enabledLayers?: InfrastructureType[]) {
  const allLayers: InfrastructureType[] = [
    'transmission',
    'substations',
    'gsp',
    'fiber',
    'tnuos',
    'ixp',
    'water',
    'dno-areas',
  ];

  const layers = enabledLayers || allLayers;

  const queries = useQueries({
    queries: layers.map((type) => ({
      queryKey: infrastructureKeys.type(type),
      queryFn: () => fetchInfrastructure(type),
      staleTime: 10 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
    })),
  });

  // Combine results into a map
  const data = layers.reduce(
    (acc, type, index) => {
      acc[type] = queries[index].data || null;
      return acc;
    },
    {} as Record<InfrastructureType, GeoJSONFeatureCollection | null>
  );

  const isLoading = queries.some((q) => q.isLoading);
  const isError = queries.some((q) => q.isError);
  const errors = queries.filter((q) => q.error).map((q) => q.error);

  return {
    data,
    isLoading,
    isError,
    errors,
    queries,
  };
}

/**
 * Generic hook for any infrastructure type
 */
export function useInfrastructure(type: InfrastructureType, enabled = true) {
  return useQuery({
    queryKey: infrastructureKeys.type(type),
    queryFn: () => fetchInfrastructure(type),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    enabled,
  });
}

export default useInfrastructure;
