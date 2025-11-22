/**
 * Test Utilities
 *
 * Custom render functions and utilities for testing React components
 * with all necessary providers (React Query, Zustand stores, Router, etc.)
 */

import { ReactElement, ReactNode } from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';

// Create a fresh QueryClient for each test
function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// Props for the AllProviders wrapper
interface AllProvidersProps {
  children: ReactNode;
  queryClient?: QueryClient;
}

// Wrapper component that includes all providers
function AllProviders({ children, queryClient }: AllProvidersProps): ReactElement {
  const client = queryClient ?? createTestQueryClient();

  return (
    <QueryClientProvider client={client}>
      {children}
    </QueryClientProvider>
  );
}

// Custom render options
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient;
  initialRoute?: string;
}

// Custom render function that wraps components with all providers
function customRender(
  ui: ReactElement,
  options: CustomRenderOptions = {}
): RenderResult & { user: ReturnType<typeof userEvent.setup> } {
  const { queryClient, ...renderOptions } = options;

  const user = userEvent.setup();

  const result = render(ui, {
    wrapper: ({ children }) => (
      <AllProviders queryClient={queryClient}>
        {children}
      </AllProviders>
    ),
    ...renderOptions,
  });

  return {
    ...result,
    user,
  };
}

// Re-export everything from testing-library
export * from '@testing-library/react';

// Override render with our custom render
export { customRender as render };

// Export additional utilities
export { userEvent, createTestQueryClient };

// Utility to wait for loading states to resolve
export async function waitForLoadingToFinish(): Promise<void> {
  // Wait for any pending promises and updates
  await new Promise((resolve) => setTimeout(resolve, 0));
}

// Utility to create mock functions with type safety
export function createMockFn<T extends (...args: unknown[]) => unknown>(): jest.Mock<ReturnType<T>, Parameters<T>> {
  return vi.fn() as jest.Mock<ReturnType<T>, Parameters<T>>;
}

// Utility to mock fetch responses
export function mockFetchResponse<T>(data: T, options: { status?: number; ok?: boolean } = {}): void {
  const { status = 200, ok = true } = options;

  globalThis.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
}

// Utility to mock fetch error
export function mockFetchError(error: Error | string): void {
  const errorMessage = typeof error === 'string' ? error : error.message;

  globalThis.fetch = vi.fn().mockRejectedValue(new Error(errorMessage));
}

// Utility to flush promises
export function flushPromises(): Promise<void> {
  return new Promise((resolve) => setImmediate(resolve));
}

// Utility to wait for element to be removed
export async function waitForElementToBeRemoved(
  callback: () => HTMLElement | null
): Promise<void> {
  const { waitFor } = await import('@testing-library/react');
  await waitFor(() => {
    expect(callback()).toBeNull();
  });
}

// Mock data generators for common types
export const mockGenerators = {
  project: (overrides = {}) => ({
    id: Math.random().toString(36).substr(2, 9),
    name: 'Test Project',
    capacity_mw: 100,
    latitude: 52.0,
    longitude: -1.5,
    technology: 'Solar',
    status: 'active',
    created_at: new Date().toISOString(),
    ...overrides,
  }),

  user: (overrides = {}) => ({
    id: Math.random().toString(36).substr(2, 9),
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    ...overrides,
  }),

  infrastructure: (type: string, overrides = {}) => ({
    id: Math.random().toString(36).substr(2, 9),
    type,
    name: `Test ${type}`,
    latitude: 52.0,
    longitude: -1.5,
    capacity: 500,
    ...overrides,
  }),

  financialModel: (overrides = {}) => ({
    npv: 1000000,
    irr: 0.12,
    lcoe: 45.5,
    payback_years: 8,
    annual_revenue: 500000,
    ...overrides,
  }),
};

// Type definitions for test utilities
declare global {
  namespace Vi {
    interface JestAssertion<T = unknown> {
      toBeInTheDocument(): T;
      toHaveTextContent(text: string | RegExp): T;
      toBeVisible(): T;
      toBeDisabled(): T;
      toBeEnabled(): T;
      toHaveClass(className: string): T;
      toHaveAttribute(attr: string, value?: string): T;
      toHaveValue(value: string | number | string[]): T;
      toBeChecked(): T;
      toHaveFocus(): T;
    }
  }
}
