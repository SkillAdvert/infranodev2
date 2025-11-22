/**
 * useFinancialModel Hook Tests
 *
 * Tests for financial modeling calculations including NPV, IRR, LCOE.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import {
  useFinancialModel,
  useQuickIRR,
  useScenarioComparison,
  FinancialModelRequest,
} from '../useFinancialModel';

// Create a fresh query client for each test
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useFinancialModel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial State', () => {
    it('starts with no result', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      expect(result.current.result).toBeNull();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isError).toBe(false);
    });

    it('provides calculate function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      expect(typeof result.current.calculate).toBe('function');
    });

    it('provides reset function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      expect(typeof result.current.reset).toBe('function');
    });

    it('provides calculateSensitivity function', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      expect(typeof result.current.calculateSensitivity).toBe('function');
    });
  });

  describe('Calculate Financial Model', () => {
    it('calculates model for solar project', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.result).toBeDefined();
      expect(result.current.result?.success).toBe(true);
    });

    it('returns NPV in result', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.standard.npv).toBeDefined();
      });

      expect(typeof result.current.result?.standard.npv).toBe('number');
    });

    it('returns IRR in result', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.standard.irr).toBeDefined();
      });

      expect(typeof result.current.result?.standard.irr).toBe('number');
      expect(result.current.result?.standard.irr).toBeGreaterThan(0);
      expect(result.current.result?.standard.irr).toBeLessThan(1);
    });

    it('returns LCOE in result', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.standard.lcoe).toBeDefined();
      });

      expect(typeof result.current.result?.standard.lcoe).toBe('number');
      expect(result.current.result?.standard.lcoe).toBeGreaterThan(0);
    });

    it('returns payback period', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.standard.payback_years).toBeDefined();
      });

      expect(result.current.result?.standard.payback_years).toBeGreaterThan(0);
    });

    it('returns cashflows array', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.standard.cashflows).toBeDefined();
      });

      const cashflows = result.current.result?.standard.cashflows;
      expect(Array.isArray(cashflows)).toBe(true);
      expect(cashflows?.length).toBe(25); // 25-year project life

      if (cashflows && cashflows.length > 0) {
        expect(cashflows[0]).toHaveProperty('year');
        expect(cashflows[0]).toHaveProperty('revenue');
        expect(cashflows[0]).toHaveProperty('opex');
        expect(cashflows[0]).toHaveProperty('net_cashflow');
      }
    });
  });

  describe('Autoproducer Scenario', () => {
    it('returns autoproducer results', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.autoproducer).toBeDefined();
      });

      expect(result.current.result?.autoproducer.npv).toBeDefined();
      expect(result.current.result?.autoproducer.irr).toBeDefined();
    });

    it('autoproducer has higher returns', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result).toBeDefined();
      });

      const standard = result.current.result?.standard;
      const autoproducer = result.current.result?.autoproducer;

      if (standard && autoproducer) {
        expect(autoproducer.irr).toBeGreaterThan(standard.irr);
        expect(autoproducer.npv).toBeGreaterThan(standard.npv);
      }
    });

    it('returns uplift percentage', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.autoproducer.uplift_percent).toBeDefined();
      });

      expect(result.current.result?.autoproducer.uplift_percent).toBeGreaterThan(0);
    });
  });

  describe('Metrics', () => {
    it('returns capacity factor', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.metrics.capacity_factor).toBeDefined();
      });

      expect(result.current.result?.metrics.capacity_factor).toBeGreaterThan(0);
      expect(result.current.result?.metrics.capacity_factor).toBeLessThan(1);
    });

    it('returns annual generation', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.metrics.annual_generation_mwh).toBeDefined();
      });

      // 100 MW * 8760 hours * ~0.25 capacity factor = ~219,000 MWh
      expect(result.current.result?.metrics.annual_generation_mwh).toBeGreaterThan(100000);
    });
  });

  describe('Reset', () => {
    it('clears result on reset', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      await waitFor(() => {
        expect(result.current.result).toBeDefined();
      });

      act(() => {
        result.current.reset();
      });

      expect(result.current.result).toBeNull();
    });
  });

  describe('Loading State', () => {
    it('sets loading during calculation', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      // Start calculation without await
      act(() => {
        result.current.calculate({
          capacity_mw: 100,
          technology: 'Solar',
        });
      });

      // Should complete eventually
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });
  });

  describe('Different Technologies', () => {
    it('calculates for Wind projects', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 150,
          technology: 'Wind',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.success).toBe(true);
      });
    });

    it('calculates for Battery projects', async () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useFinancialModel(), { wrapper });

      await act(async () => {
        await result.current.calculate({
          capacity_mw: 50,
          technology: 'Battery',
        });
      });

      await waitFor(() => {
        expect(result.current.result?.success).toBe(true);
      });
    });
  });
});

describe('useQuickIRR', () => {
  it('calculates IRR quickly', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useQuickIRR(), { wrapper });

    let irr: number | undefined;
    await act(async () => {
      irr = await result.current.calculateIRR(100, 'Solar');
    });

    expect(irr).toBeDefined();
    expect(typeof irr).toBe('number');
    expect(irr).toBeGreaterThan(0);
  });

  it('provides loading state', () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useQuickIRR(), { wrapper });

    expect(result.current.isLoading).toBe(false);
  });
});

describe('useScenarioComparison', () => {
  it('compares two scenarios', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useScenarioComparison(), { wrapper });

    const scenario1: FinancialModelRequest = {
      capacity_mw: 100,
      technology: 'Solar',
      discount_rate: 0.08,
    };

    const scenario2: FinancialModelRequest = {
      capacity_mw: 100,
      technology: 'Solar',
      discount_rate: 0.06,
    };

    await act(async () => {
      await result.current.compare(scenario1, scenario2);
    });

    await waitFor(() => {
      expect(result.current.scenario1).toBeDefined();
      expect(result.current.scenario2).toBeDefined();
    });
  });

  it('calculates difference between scenarios', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useScenarioComparison(), { wrapper });

    const scenario1: FinancialModelRequest = {
      capacity_mw: 100,
      technology: 'Solar',
    };

    const scenario2: FinancialModelRequest = {
      capacity_mw: 200,
      technology: 'Solar',
    };

    await act(async () => {
      await result.current.compare(scenario1, scenario2);
    });

    await waitFor(() => {
      expect(result.current.difference).toBeDefined();
    });

    expect(result.current.difference?.npv).toBeDefined();
    expect(result.current.difference?.irr).toBeDefined();
  });
});
