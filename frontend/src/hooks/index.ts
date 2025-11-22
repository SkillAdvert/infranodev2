/**
 * Hooks Index
 *
 * Central export point for all custom React hooks.
 */

export { useAuth, AuthProvider } from './useAuth';
export type { User, Session, AccessStatus, AuthContextType } from './useAuth';

export {
  useProjects,
  useEnhancedProjects,
  useProjectsGeoJSON,
  useSearchProjects,
  usePrefetchProjects,
  useRefreshProjects,
  projectKeys,
} from './useProjects';
export type {
  Project,
  ComponentScores,
  ProjectsResponse,
  ProjectsGeoJSON,
  CustomerMatchCriteria,
  CustomerMatchRequest,
  CustomerMatchResponse,
  Persona,
} from './useProjects';

export {
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
} from './useInfrastructure';
export type {
  InfrastructureType,
  GeoJSONFeatureCollection,
  GeoJSONFeature,
} from './useInfrastructure';

export {
  useFinancialModel,
  useQuickIRR,
  useScenarioComparison,
  financialModelKeys,
} from './useFinancialModel';
export type {
  FinancialModelRequest,
  FinancialModelResponse,
  ScenarioResult,
  CashflowYear,
  FinancialMetrics,
  SensitivityResult,
} from './useFinancialModel';
