/**
 * App Store Tests
 *
 * Tests for the global Zustand store.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useAppStore } from '../appStore';

describe('appStore', () => {
  beforeEach(() => {
    // Reset store before each test
    const { result } = renderHook(() => useAppStore());
    act(() => {
      result.current.reset();
    });
  });

  describe('Initial State', () => {
    it('has default persona as greenfield', () => {
      const { result } = renderHook(() => useAppStore());
      expect(result.current.persona).toBe('greenfield');
    });

    it('has no selected project initially', () => {
      const { result } = renderHook(() => useAppStore());
      expect(result.current.selectedProject).toBeNull();
      expect(result.current.selectedProjectId).toBeNull();
    });

    it('has sidebar open by default', () => {
      const { result } = renderHook(() => useAppStore());
      expect(result.current.sidebarOpen).toBe(true);
    });

    it('has default map center in UK', () => {
      const { result } = renderHook(() => useAppStore());
      const [lon, lat] = result.current.mapCenter;

      // UK center approximately
      expect(lon).toBe(-1.5);
      expect(lat).toBe(53.0);
    });

    it('has default zoom level', () => {
      const { result } = renderHook(() => useAppStore());
      expect(result.current.mapZoom).toBe(6);
    });

    it('has projects layer visible by default', () => {
      const { result } = renderHook(() => useAppStore());
      expect(result.current.visibleLayers.projects).toBe(true);
    });

    it('has infrastructure layers hidden by default', () => {
      const { result } = renderHook(() => useAppStore());
      expect(result.current.visibleLayers.transmission).toBe(false);
      expect(result.current.visibleLayers.substations).toBe(false);
      expect(result.current.visibleLayers.fiber).toBe(false);
    });
  });

  describe('Persona', () => {
    it('sets persona correctly', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setPersona('hyperscaler');
      });

      expect(result.current.persona).toBe('hyperscaler');
    });

    it('can change persona multiple times', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setPersona('utility');
      });
      expect(result.current.persona).toBe('utility');

      act(() => {
        result.current.setPersona('colocation');
      });
      expect(result.current.persona).toBe('colocation');
    });
  });

  describe('Selected Project', () => {
    const mockProject = {
      id: 'proj-001',
      name: 'Test Project',
      capacity_mw: 100,
      latitude: 52.0,
      longitude: -1.5,
      technology: 'Solar' as const,
      status: 'active' as const,
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
    };

    it('sets selected project', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setSelectedProject(mockProject);
      });

      expect(result.current.selectedProject).toEqual(mockProject);
      expect(result.current.selectedProjectId).toBe('proj-001');
    });

    it('clears selected project', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setSelectedProject(mockProject);
      });

      act(() => {
        result.current.setSelectedProject(null);
      });

      expect(result.current.selectedProject).toBeNull();
      expect(result.current.selectedProjectId).toBeNull();
    });
  });

  describe('Sidebar', () => {
    it('toggles sidebar', () => {
      const { result } = renderHook(() => useAppStore());

      expect(result.current.sidebarOpen).toBe(true);

      act(() => {
        result.current.toggleSidebar();
      });

      expect(result.current.sidebarOpen).toBe(false);

      act(() => {
        result.current.toggleSidebar();
      });

      expect(result.current.sidebarOpen).toBe(true);
    });

    it('sets sidebar open state directly', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setSidebarOpen(false);
      });

      expect(result.current.sidebarOpen).toBe(false);

      act(() => {
        result.current.setSidebarOpen(true);
      });

      expect(result.current.sidebarOpen).toBe(true);
    });
  });

  describe('Map View', () => {
    it('sets map view', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setMapView([-2.0, 54.0], 10);
      });

      expect(result.current.mapCenter).toEqual([-2.0, 54.0]);
      expect(result.current.mapZoom).toBe(10);
    });
  });

  describe('Layer Visibility', () => {
    it('toggles layer visibility', () => {
      const { result } = renderHook(() => useAppStore());

      expect(result.current.visibleLayers.transmission).toBe(false);

      act(() => {
        result.current.toggleLayer('transmission');
      });

      expect(result.current.visibleLayers.transmission).toBe(true);

      act(() => {
        result.current.toggleLayer('transmission');
      });

      expect(result.current.visibleLayers.transmission).toBe(false);
    });

    it('sets layer visibility directly', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setLayerVisibility('fiber', true);
      });

      expect(result.current.visibleLayers.fiber).toBe(true);

      act(() => {
        result.current.setLayerVisibility('fiber', false);
      });

      expect(result.current.visibleLayers.fiber).toBe(false);
    });

    it('preserves other layers when toggling', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.toggleLayer('transmission');
        result.current.toggleLayer('substations');
      });

      expect(result.current.visibleLayers.transmission).toBe(true);
      expect(result.current.visibleLayers.substations).toBe(true);
      expect(result.current.visibleLayers.fiber).toBe(false);
    });
  });

  describe('Top Projects', () => {
    it('sets top projects', () => {
      const { result } = renderHook(() => useAppStore());
      const projects = [
        { id: 'proj-001', name: 'Project 1' },
        { id: 'proj-002', name: 'Project 2' },
      ];

      act(() => {
        result.current.setTopProjects(projects as never);
      });

      expect(result.current.topProjects).toHaveLength(2);
    });

    it('clears top projects', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setTopProjects([{ id: 'proj-001', name: 'Test' }] as never);
      });

      act(() => {
        result.current.setTopProjects([]);
      });

      expect(result.current.topProjects).toHaveLength(0);
    });
  });

  describe('Reset', () => {
    it('resets all state to initial values', () => {
      const { result } = renderHook(() => useAppStore());

      // Modify various state
      act(() => {
        result.current.setPersona('hyperscaler');
        result.current.setSidebarOpen(false);
        result.current.toggleLayer('transmission');
        result.current.setMapView([-2.0, 54.0], 10);
      });

      // Reset
      act(() => {
        result.current.reset();
      });

      // Verify reset
      expect(result.current.persona).toBe('greenfield');
      expect(result.current.sidebarOpen).toBe(true);
      expect(result.current.visibleLayers.transmission).toBe(false);
      expect(result.current.mapCenter).toEqual([-1.5, 53.0]);
      expect(result.current.mapZoom).toBe(6);
    });
  });
});
