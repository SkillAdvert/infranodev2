/**
 * API Configuration
 *
 * Central configuration for API endpoints and settings.
 */

// Environment-based API URL
export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://infranodev2.onrender.com';

// Request timeout in milliseconds
export const API_TIMEOUT = 90000; // 90 seconds

// Cache TTL in milliseconds
export const DEFAULT_CACHE_TTL = 5 * 60 * 1000; // 5 minutes
export const INFRASTRUCTURE_CACHE_TTL = 10 * 60 * 1000; // 10 minutes

// Retry configuration
export const MAX_RETRIES = 3;
export const RETRY_DELAY = 1000; // 1 second

// API Endpoints
export const ENDPOINTS = {
  // Health
  health: '/',
  healthCheck: '/health',

  // Projects
  projects: '/api/projects',
  projectsEnhanced: '/api/projects/enhanced',
  projectsGeoJSON: '/api/projects/geojson',
  projectsCustomerMatch: '/api/projects/customer-match',
  projectsCompareScoring: '/api/projects/compare-scoring',
  projectsPowerDeveloper: '/api/projects/power-developer-analysis',

  // Infrastructure
  infrastructureTransmission: '/api/infrastructure/transmission',
  infrastructureSubstations: '/api/infrastructure/substations',
  infrastructureGSP: '/api/infrastructure/gsp',
  infrastructureFiber: '/api/infrastructure/fiber',
  infrastructureTNUOS: '/api/infrastructure/tnuos',
  infrastructureIXP: '/api/infrastructure/ixp',
  infrastructureWater: '/api/infrastructure/water',
  infrastructureDNOAreas: '/api/infrastructure/dno-areas',

  // TEC
  tecConnections: '/api/tec/connections',

  // User Sites
  userSitesScore: '/api/user-sites/score',

  // Financial Model
  financialModel: '/api/financial-model',
} as const;

// Helper to construct full URL
export function getApiUrl(endpoint: keyof typeof ENDPOINTS): string {
  return `${API_BASE}${ENDPOINTS[endpoint]}`;
}

// UK Coordinate Bounds
export const UK_BOUNDS = {
  minLat: 49.8,
  maxLat: 60.9,
  minLon: -8.0,
  maxLon: 2.0,
} as const;

// Validate UK coordinates
export function isValidUKCoordinate(lat: number, lon: number): boolean {
  return (
    lat >= UK_BOUNDS.minLat &&
    lat <= UK_BOUNDS.maxLat &&
    lon >= UK_BOUNDS.minLon &&
    lon <= UK_BOUNDS.maxLon
  );
}

// Persona types
export const PERSONAS = [
  'hyperscaler',
  'utility',
  'colocation',
  'power_developer',
  'greenfield',
  'investor',
] as const;

export type Persona = (typeof PERSONAS)[number];

// Technology types
export const TECHNOLOGIES = ['Solar', 'Wind', 'Battery', 'Hybrid'] as const;

export type Technology = (typeof TECHNOLOGIES)[number];
