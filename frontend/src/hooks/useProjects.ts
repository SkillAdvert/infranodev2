/**
 * useProjects Hook
 *
 * Manages project data fetching, filtering, and caching.
 * Uses React Query for data management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// API Configuration
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://infranodev2.onrender.com';
const API_TIMEOUT = 90000;

// Types
export interface Project {
  id: string;
  name: string;
  capacity_mw: number;
  latitude: number;
  longitude: number;
  technology: 'Solar' | 'Wind' | 'Battery' | 'Hybrid';
  status: 'active' | 'development' | 'planned' | 'completed';
  total_score: number;
  component_scores: ComponentScores;
  match_reasons?: string[];
  created_at?: string;
}

export interface ComponentScores {
  grid_proximity: number;
  land_availability: number;
  fiber_connectivity: number;
  transmission_access: number;
  water_access: number;
  planning_status: number;
  environmental: number;
  financial_viability: number;
}

export interface ProjectsResponse {
  success: boolean;
  data: Project[];
  persona: string;
  count: number;
}

export interface GeoJSONFeature {
  type: 'Feature';
  properties: {
    id: string;
    name: string;
    capacity_mw: number;
    technology: string;
    status: string;
    total_score: number;
  };
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
}

export interface ProjectsGeoJSON {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
  metadata?: {
    persona: string;
    count: number;
  };
}

export interface CustomerMatchCriteria {
  min_capacity_mw?: number;
  max_capacity_mw?: number;
  max_fiber_distance_km?: number;
  max_transmission_distance_km?: number;
  min_score?: number;
  technologies?: string[];
}

export interface CustomerMatchRequest {
  criteria: CustomerMatchCriteria;
  persona?: string;
}

export interface CustomerMatchResponse {
  success: boolean;
  matched_projects: Project[];
  persona: string;
  match_count: number;
}

export type Persona = 'hyperscaler' | 'utility' | 'colocation' | 'power_developer' | 'greenfield' | 'investor';

// API Functions
async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchProjects(persona?: Persona): Promise<ProjectsResponse> {
  const url = persona
    ? `${API_BASE}/api/projects?persona=${persona}`
    : `${API_BASE}/api/projects`;

  const response = await fetchWithTimeout(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch projects: ${response.status}`);
  }

  return response.json();
}

async function fetchEnhancedProjects(
  persona?: Persona,
  limit?: number
): Promise<ProjectsResponse> {
  const params = new URLSearchParams();
  if (persona) params.append('persona', persona);
  if (limit) params.append('limit', limit.toString());

  const url = `${API_BASE}/api/projects/enhanced?${params}`;
  const response = await fetchWithTimeout(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch enhanced projects: ${response.status}`);
  }

  return response.json();
}

async function fetchProjectsGeoJSON(persona?: Persona): Promise<ProjectsGeoJSON> {
  const url = persona
    ? `${API_BASE}/api/projects/geojson?persona=${persona}`
    : `${API_BASE}/api/projects/geojson`;

  const response = await fetchWithTimeout(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch projects GeoJSON: ${response.status}`);
  }

  return response.json();
}

async function searchProjects(request: CustomerMatchRequest): Promise<CustomerMatchResponse> {
  const response = await fetchWithTimeout(`${API_BASE}/api/projects/customer-match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to search projects: ${response.status}`);
  }

  return response.json();
}

// Query Keys
export const projectKeys = {
  all: ['projects'] as const,
  lists: () => [...projectKeys.all, 'list'] as const,
  list: (persona?: Persona) => [...projectKeys.lists(), persona] as const,
  enhanced: (persona?: Persona, limit?: number) =>
    [...projectKeys.all, 'enhanced', persona, limit] as const,
  geojson: (persona?: Persona) => [...projectKeys.all, 'geojson', persona] as const,
  search: (criteria: CustomerMatchCriteria) => [...projectKeys.all, 'search', criteria] as const,
};

// Hooks

/**
 * Fetch all projects
 */
export function useProjects(persona?: Persona) {
  return useQuery({
    queryKey: projectKeys.list(persona),
    queryFn: () => fetchProjects(persona),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (previously cacheTime)
  });
}

/**
 * Fetch enhanced projects with scoring
 */
export function useEnhancedProjects(persona?: Persona, limit?: number) {
  return useQuery({
    queryKey: projectKeys.enhanced(persona, limit),
    queryFn: () => fetchEnhancedProjects(persona, limit),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * Fetch projects as GeoJSON for maps
 */
export function useProjectsGeoJSON(persona?: Persona) {
  return useQuery({
    queryKey: projectKeys.geojson(persona),
    queryFn: () => fetchProjectsGeoJSON(persona),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * Search/filter projects by criteria
 */
export function useSearchProjects() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: searchProjects,
    onSuccess: (data, variables) => {
      // Cache the search results
      queryClient.setQueryData(
        projectKeys.search(variables.criteria),
        data
      );
    },
  });
}

/**
 * Prefetch projects for a persona
 */
export function usePrefetchProjects() {
  const queryClient = useQueryClient();

  return (persona: Persona) => {
    queryClient.prefetchQuery({
      queryKey: projectKeys.list(persona),
      queryFn: () => fetchProjects(persona),
      staleTime: 5 * 60 * 1000,
    });
  };
}

/**
 * Invalidate and refetch all project queries
 */
export function useRefreshProjects() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: projectKeys.all });
  };
}

export default useProjects;
