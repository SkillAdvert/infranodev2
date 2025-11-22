/**
 * useAuth Hook
 *
 * Manages authentication state and provides auth methods.
 * Integrates with Supabase Auth for session management.
 */

import { useState, useEffect, useCallback, createContext, useContext, ReactNode } from 'react';

// Types
export interface User {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  created_at: string;
}

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  user: User;
}

export interface AccessStatus {
  hasDashboardAccess: boolean;
  isEmailVerified: boolean;
  reason: 'none' | 'awaiting_activation' | 'unverified_email';
  roles: string[];
}

export interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  access: AccessStatus;
  roles: string[];
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signUp: (email: string, password: string) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ error: Error | null }>;
}

// Default access status
const defaultAccess: AccessStatus = {
  hasDashboardAccess: false,
  isEmailVerified: false,
  reason: 'none',
  roles: [],
};

// Auth Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Mock Supabase client for demo
const mockSupabase = {
  auth: {
    getSession: async () => ({ data: { session: null }, error: null }),
    signInWithPassword: async (_credentials: { email: string; password: string }) => ({
      data: { user: null, session: null },
      error: null,
    }),
    signUp: async (_credentials: { email: string; password: string }) => ({
      data: { user: null, session: null },
      error: null,
    }),
    signOut: async () => ({ error: null }),
    resetPasswordForEmail: async (_email: string) => ({ error: null }),
    onAuthStateChange: (_callback: (event: string, session: Session | null) => void) => ({
      data: { subscription: { unsubscribe: () => {} } },
    }),
  },
};

// Provider Props
interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Auth Provider Component
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [access, setAccess] = useState<AccessStatus>(defaultAccess);
  const [roles, setRoles] = useState<string[]>([]);

  // Initialize auth state
  useEffect(() => {
    const initAuth = async () => {
      try {
        const { data } = await mockSupabase.auth.getSession();
        if (data.session) {
          setSession(data.session as unknown as Session);
          setUser((data.session as unknown as Session).user);
          await checkAccess((data.session as unknown as Session).user);
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
      } finally {
        setLoading(false);
      }
    };

    initAuth();

    // Subscribe to auth changes
    const { data: { subscription } } = mockSupabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
        setUser(session?.user || null);
        if (session?.user) {
          checkAccess(session.user);
        } else {
          setAccess(defaultAccess);
          setRoles([]);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  // Check user access level
  const checkAccess = async (user: User) => {
    // In real implementation, this would check against backend
    const newAccess: AccessStatus = {
      hasDashboardAccess: true,
      isEmailVerified: true,
      reason: 'none',
      roles: ['user'],
    };
    setAccess(newAccess);
    setRoles(newAccess.roles);
  };

  // Sign in
  const signIn = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const { data, error } = await mockSupabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        return { error: error as unknown as Error };
      }

      if (data.session) {
        setSession(data.session as unknown as Session);
        setUser((data.session as unknown as Session).user);
        await checkAccess((data.session as unknown as Session).user);
      }

      return { error: null };
    } catch (error) {
      return { error: error as Error };
    } finally {
      setLoading(false);
    }
  }, []);

  // Sign up
  const signUp = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const { error } = await mockSupabase.auth.signUp({
        email,
        password,
      });

      if (error) {
        return { error: error as unknown as Error };
      }

      return { error: null };
    } catch (error) {
      return { error: error as Error };
    } finally {
      setLoading(false);
    }
  }, []);

  // Sign out
  const signOut = useCallback(async () => {
    setLoading(true);
    try {
      await mockSupabase.auth.signOut();
      setUser(null);
      setSession(null);
      setAccess(defaultAccess);
      setRoles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Reset password
  const resetPassword = useCallback(async (email: string) => {
    try {
      const { error } = await mockSupabase.auth.resetPasswordForEmail(email);
      return { error: error as unknown as Error | null };
    } catch (error) {
      return { error: error as Error };
    }
  }, []);

  const value: AuthContextType = {
    user,
    session,
    loading,
    access,
    roles,
    signIn,
    signUp,
    signOut,
    resetPassword,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * useAuth Hook
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default useAuth;
