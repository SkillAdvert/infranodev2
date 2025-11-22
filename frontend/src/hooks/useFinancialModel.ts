/**
 * useFinancialModel Hook
 *
 * Handles financial model calculations including NPV, IRR, and LCOE.
 * Integrates with the backend financial modeling API.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback } from 'react';

// API Configuration
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://infranodev2.onrender.com';
const API_TIMEOUT = 90000;

// Types
export interface FinancialModelRequest {
  // Project parameters
  capacity_mw: number;
  technology: 'Solar' | 'Wind' | 'Battery' | 'Hybrid';
  capacity_factor?: number;

  // Capital costs
  capex_per_mw?: number;
  capex_total?: number;

  // Operating costs
  opex_per_mw_year?: number;
  opex_escalation_rate?: number;

  // Revenue parameters
  ppa_price_per_mwh?: number;
  merchant_price_per_mwh?: number;
  merchant_percentage?: number;
  price_escalation_rate?: number;

  // Financial parameters
  discount_rate?: number;
  tax_rate?: number;
  debt_ratio?: number;
  debt_interest_rate?: number;
  debt_term_years?: number;

  // Project parameters
  project_life_years?: number;
  degradation_rate?: number;
  loss_factor?: number;

  // Incentives
  investment_tax_credit?: number;
  production_tax_credit_per_mwh?: number;
  rocs_per_mwh?: number;
}

export interface CashflowYear {
  year: number;
  revenue: number;
  opex: number;
  debt_service?: number;
  tax?: number;
  net_cashflow: number;
  cumulative_cashflow?: number;
}

export interface FinancialMetrics {
  npv: number;
  irr: number;
  lcoe: number;
  payback_years: number;
  annual_revenue: number;
  total_revenue?: number;
  total_opex?: number;
  roi?: number;
}

export interface ScenarioResult {
  npv: number;
  irr: number;
  lcoe: number;
  payback_years: number;
  annual_revenue: number;
  cashflows: CashflowYear[];
  uplift_percent?: number;
}

export interface FinancialModelResponse {
  success: boolean;
  standard: ScenarioResult;
  autoproducer: ScenarioResult;
  metrics: {
    capacity_factor: number;
    annual_generation_mwh: number;
    discount_rate: number;
  };
  error?: string;
}

export interface SensitivityResult {
  parameter: string;
  base_value: number;
  variations: Array<{
    change_percent: number;
    value: number;
    npv: number;
    irr: number;
  }>;
}

// Default values
const DEFAULT_REQUEST: Partial<FinancialModelRequest> = {
  capacity_factor: 0.25,
  capex_per_mw: 800000,
  opex_per_mw_year: 15000,
  opex_escalation_rate: 0.02,
  ppa_price_per_mwh: 50,
  merchant_price_per_mwh: 45,
  merchant_percentage: 0.3,
  price_escalation_rate: 0.02,
  discount_rate: 0.08,
  tax_rate: 0.19,
  debt_ratio: 0.7,
  debt_interest_rate: 0.05,
  debt_term_years: 15,
  project_life_years: 25,
  degradation_rate: 0.005,
  loss_factor: 0.97,
};

// API Functions
async function fetchWithTimeout(url: string, options: RequestInit): Promise<Response> {
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

async function calculateFinancialModel(
  request: FinancialModelRequest
): Promise<FinancialModelResponse> {
  const fullRequest = { ...DEFAULT_REQUEST, ...request };

  const response = await fetchWithTimeout(`${API_BASE}/api/financial-model`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(fullRequest),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Unknown error' }));
    throw new Error(error.message || `Failed to calculate: ${response.status}`);
  }

  return response.json();
}

// Query Keys
export const financialModelKeys = {
  all: ['financial-model'] as const,
  calculation: (params: FinancialModelRequest) =>
    [...financialModelKeys.all, 'calculation', params] as const,
};

// Main Hook
export function useFinancialModel() {
  const queryClient = useQueryClient();
  const [lastResult, setLastResult] = useState<FinancialModelResponse | null>(null);

  const mutation = useMutation({
    mutationFn: calculateFinancialModel,
    onSuccess: (data) => {
      setLastResult(data);
    },
  });

  const calculate = useCallback(
    (request: FinancialModelRequest) => {
      return mutation.mutateAsync(request);
    },
    [mutation]
  );

  const reset = useCallback(() => {
    setLastResult(null);
    mutation.reset();
  }, [mutation]);

  // Calculate sensitivity analysis
  const calculateSensitivity = useCallback(
    async (
      baseRequest: FinancialModelRequest,
      parameter: keyof FinancialModelRequest,
      variations: number[] = [-20, -10, 0, 10, 20]
    ): Promise<SensitivityResult> => {
      const baseValue = baseRequest[parameter] as number;
      const results: SensitivityResult['variations'] = [];

      for (const changePercent of variations) {
        const adjustedValue = baseValue * (1 + changePercent / 100);
        const adjustedRequest = {
          ...baseRequest,
          [parameter]: adjustedValue,
        };

        try {
          const result = await calculateFinancialModel(adjustedRequest);
          results.push({
            change_percent: changePercent,
            value: adjustedValue,
            npv: result.standard.npv,
            irr: result.standard.irr,
          });
        } catch {
          // Skip failed calculations
        }
      }

      return {
        parameter: parameter as string,
        base_value: baseValue,
        variations: results,
      };
    },
    []
  );

  return {
    calculate,
    calculateSensitivity,
    reset,
    result: lastResult,
    isLoading: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
    isSuccess: mutation.isSuccess,
  };
}

/**
 * Quick IRR calculation hook (simplified)
 */
export function useQuickIRR() {
  const { calculate, result, isLoading, error } = useFinancialModel();

  const calculateIRR = useCallback(
    async (capacityMw: number, technology: FinancialModelRequest['technology']) => {
      const response = await calculate({
        capacity_mw: capacityMw,
        technology,
      });
      return response.standard.irr;
    },
    [calculate]
  );

  return {
    calculateIRR,
    irr: result?.standard.irr,
    isLoading,
    error,
  };
}

/**
 * Compare two financial scenarios
 */
export function useScenarioComparison() {
  const { calculate } = useFinancialModel();
  const [comparison, setComparison] = useState<{
    scenario1: FinancialModelResponse | null;
    scenario2: FinancialModelResponse | null;
    difference: Partial<ScenarioResult> | null;
  }>({ scenario1: null, scenario2: null, difference: null });

  const compare = useCallback(
    async (
      request1: FinancialModelRequest,
      request2: FinancialModelRequest
    ) => {
      const [result1, result2] = await Promise.all([
        calculate(request1),
        calculate(request2),
      ]);

      const difference: Partial<ScenarioResult> = {
        npv: result2.standard.npv - result1.standard.npv,
        irr: result2.standard.irr - result1.standard.irr,
        lcoe: result2.standard.lcoe - result1.standard.lcoe,
        payback_years: result2.standard.payback_years - result1.standard.payback_years,
      };

      setComparison({
        scenario1: result1,
        scenario2: result2,
        difference,
      });

      return comparison;
    },
    [calculate, comparison]
  );

  return {
    compare,
    ...comparison,
  };
}

export default useFinancialModel;
