/**
 * useCurrentUser Hook
 * 
 * Fetches and caches the current user from /api/auth/me.
 * Handles automatic token refresh via the backend.
 * 
 * Usage:
 *   const { user, loading, error, refetch, logout } = useCurrentUser();
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';

export interface CurrentUser {
  id: number;
  displayName: string;
  discordId: string | null;
  discordUsername: string | null;
  discordAvatar: string | null;
  tier: string | null;
  tierLabel: string | null;
  tierColor: string | null;
  isDiscordUser: boolean;
}

interface UseCurrentUserResult {
  user: CurrentUser | null;
  loading: boolean;
  error: string | null;
  authenticated: boolean;
  refetch: () => Promise<void>;
  logout: () => Promise<void>;
}

export function useCurrentUser(options?: { redirectOnUnauth?: boolean }): UseCurrentUserResult {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const fetchUser = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/me', {
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status === 401) {
          setUser(null);
          if (options?.redirectOnUnauth) {
            router.push('/login');
          }
          return;
        }
        throw new Error('Failed to fetch user');
      }

      const data = await response.json();

      if (data.authenticated && data.user) {
        setUser(data.user);
      } else {
        setUser(null);
        if (options?.redirectOnUnauth) {
          router.push('/login');
        }
      }
    } catch (err) {
      console.error('[useCurrentUser] Error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [options?.redirectOnUnauth, router]);

  const logout = useCallback(async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (err) {
      console.error('[useCurrentUser] Logout error:', err);
    }
    
    setUser(null);
    router.push('/login');
  }, [router]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return {
    user,
    loading,
    error,
    authenticated: !!user,
    refetch: fetchUser,
    logout,
  };
}

export default useCurrentUser;
