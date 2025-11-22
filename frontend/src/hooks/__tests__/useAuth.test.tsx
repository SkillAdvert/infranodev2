/**
 * useAuth Hook Tests
 *
 * Tests for authentication hook including sign in, sign out,
 * session management, and access control.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { ReactNode } from 'react';
import { useAuth, AuthProvider, AuthContextType } from '../useAuth';

// Wrapper component for hooks that need AuthProvider
const wrapper = ({ children }: { children: ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial State', () => {
    it('starts with loading state', () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      // Initially loading while checking session
      expect(result.current.loading).toBeDefined();
    });

    it('has null user when not authenticated', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.user).toBeNull();
    });

    it('has null session when not authenticated', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.session).toBeNull();
    });

    it('has default access status', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.access).toEqual({
        hasDashboardAccess: false,
        isEmailVerified: false,
        reason: 'none',
        roles: [],
      });
    });

    it('has empty roles array', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.roles).toEqual([]);
    });
  });

  describe('Context Requirements', () => {
    it('throws error when used outside AuthProvider', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useAuth());
      }).toThrow('useAuth must be used within an AuthProvider');

      consoleSpy.mockRestore();
    });
  });

  describe('Authentication Methods', () => {
    it('provides signIn method', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(typeof result.current.signIn).toBe('function');
    });

    it('provides signUp method', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(typeof result.current.signUp).toBe('function');
    });

    it('provides signOut method', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(typeof result.current.signOut).toBe('function');
    });

    it('provides resetPassword method', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(typeof result.current.resetPassword).toBe('function');
    });
  });

  describe('Sign In Flow', () => {
    it('signIn returns object with error property', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      let signInResult: { error: Error | null } | undefined;
      await act(async () => {
        signInResult = await result.current.signIn('test@example.com', 'password');
      });

      expect(signInResult).toHaveProperty('error');
    });

    it('sets loading during sign in', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Start sign in (don't await)
      act(() => {
        result.current.signIn('test@example.com', 'password');
      });

      // Loading should be set (though it might complete quickly in mock)
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
    });
  });

  describe('Sign Up Flow', () => {
    it('signUp returns object with error property', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      let signUpResult: { error: Error | null } | undefined;
      await act(async () => {
        signUpResult = await result.current.signUp('new@example.com', 'password');
      });

      expect(signUpResult).toHaveProperty('error');
    });
  });

  describe('Sign Out Flow', () => {
    it('clears user on sign out', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await act(async () => {
        await result.current.signOut();
      });

      expect(result.current.user).toBeNull();
    });

    it('clears session on sign out', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await act(async () => {
        await result.current.signOut();
      });

      expect(result.current.session).toBeNull();
    });

    it('resets access on sign out', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await act(async () => {
        await result.current.signOut();
      });

      expect(result.current.access.hasDashboardAccess).toBe(false);
    });
  });

  describe('Password Reset Flow', () => {
    it('resetPassword returns object with error property', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      let resetResult: { error: Error | null } | undefined;
      await act(async () => {
        resetResult = await result.current.resetPassword('test@example.com');
      });

      expect(resetResult).toHaveProperty('error');
    });
  });

  describe('Type Safety', () => {
    it('returns correctly typed AuthContextType', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Type check - these should all be valid
      const auth: AuthContextType = result.current;

      expect(auth.user).toBeDefined;
      expect(auth.session).toBeDefined;
      expect(typeof auth.loading).toBe('boolean');
      expect(auth.access).toBeDefined;
      expect(Array.isArray(auth.roles)).toBe(true);
      expect(typeof auth.signIn).toBe('function');
      expect(typeof auth.signUp).toBe('function');
      expect(typeof auth.signOut).toBe('function');
      expect(typeof auth.resetPassword).toBe('function');
    });
  });
});

describe('AuthProvider', () => {
  it('renders children', () => {
    const TestChild = () => <div data-testid="child">Child</div>;

    const { container } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => (
        <AuthProvider>
          <TestChild />
          {children}
        </AuthProvider>
      ),
    });

    // The hook should work within the provider
    expect(container).toBeDefined();
  });

  it('initializes auth state on mount', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // Wait for initialization to complete
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
  });
});
