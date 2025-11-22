/**
 * App Store
 *
 * Global application state using Zustand.
 * Manages persona selection, UI state, and caching.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Persona } from '@/lib/api-config';
import type { Project } from '@/hooks/useProjects';

interface AppState {
  // Persona
  persona: Persona;
  setPersona: (persona: Persona) => void;

  // Selected project
  selectedProjectId: string | null;
  selectedProject: Project | null;
  setSelectedProject: (project: Project | null) => void;

  // UI state
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;

  // Map state
  mapCenter: [number, number];
  mapZoom: number;
  setMapView: (center: [number, number], zoom: number) => void;

  // Layer visibility
  visibleLayers: Record<string, boolean>;
  toggleLayer: (layer: string) => void;
  setLayerVisibility: (layer: string, visible: boolean) => void;

  // Cached data
  topProjects: Project[];
  setTopProjects: (projects: Project[]) => void;

  // Reset
  reset: () => void;
}

const initialState = {
  persona: 'greenfield' as Persona,
  selectedProjectId: null,
  selectedProject: null,
  sidebarOpen: true,
  mapCenter: [-1.5, 53.0] as [number, number], // UK center
  mapZoom: 6,
  visibleLayers: {
    projects: true,
    transmission: false,
    substations: false,
    fiber: false,
    gsp: false,
    tnuos: false,
    ixp: false,
    water: false,
    dnoAreas: false,
  },
  topProjects: [] as Project[],
};

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...initialState,

      setPersona: (persona) => set({ persona }),

      setSelectedProject: (project) =>
        set({
          selectedProject: project,
          selectedProjectId: project?.id || null,
        }),

      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      setMapView: (center, zoom) => set({ mapCenter: center, mapZoom: zoom }),

      toggleLayer: (layer) =>
        set((state) => ({
          visibleLayers: {
            ...state.visibleLayers,
            [layer]: !state.visibleLayers[layer],
          },
        })),

      setLayerVisibility: (layer, visible) =>
        set((state) => ({
          visibleLayers: {
            ...state.visibleLayers,
            [layer]: visible,
          },
        })),

      setTopProjects: (projects) => set({ topProjects: projects }),

      reset: () => set(initialState),
    }),
    {
      name: 'infranode-app-store',
      partialize: (state) => ({
        persona: state.persona,
        sidebarOpen: state.sidebarOpen,
        visibleLayers: state.visibleLayers,
        mapCenter: state.mapCenter,
        mapZoom: state.mapZoom,
      }),
    }
  )
);

// Selectors
export const selectPersona = (state: AppState) => state.persona;
export const selectSelectedProject = (state: AppState) => state.selectedProject;
export const selectVisibleLayers = (state: AppState) => state.visibleLayers;
export const selectTopProjects = (state: AppState) => state.topProjects;

export default useAppStore;
