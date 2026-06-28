/**
 * AuthContext — JWT session management for the CHERENKOV dashboard.
 *
 * When AUTH_ENABLED=false on the server, /api/v1/auth/me returns 404 or the
 * server ignores tokens entirely; we treat that as "auth not required" and
 * skip the login gate.  When the server returns 401/403, we surface the
 * LoginPage instead of the main app.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

export type UserRole = 'viewer' | 'reviewer' | 'admin';

export interface AuthUser {
  username: string;
  role: UserRole;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  authRequired: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  token: null,
  user: null,
  authRequired: false,
  loading: true,
  login: async () => {},
  logout: () => {},
});

const TOKEN_KEY = '[cherenkov] auth_token';

async function fetchMe(token: string): Promise<AuthUser | null> {
  try {
    const res = await fetch('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    const data = await res.json();
    return { username: data.username, role: data.role };
  } catch {
    return null;
  }
}

async function probeAuthRequired(): Promise<boolean> {
  try {
    // Doctor is admin-only; if auth is off, it returns 200. If auth is on, it
    // returns 401 without a token.  Health is public so can't be used for this.
    const res = await fetch('/api/v1/doctor');
    return res.status === 401;
  } catch {
    return false;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY)
  );
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authRequired, setAuthRequired] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      const required = await probeAuthRequired();
      if (cancelled) return;
      setAuthRequired(required);

      if (!required) {
        setLoading(false);
        return;
      }

      const saved = localStorage.getItem(TOKEN_KEY);
      if (saved) {
        const me = await fetchMe(saved);
        if (!cancelled) {
          if (me) {
            setToken(saved);
            setUser(me);
          } else {
            localStorage.removeItem(TOKEN_KEY);
            setToken(null);
          }
        }
      }
      if (!cancelled) setLoading(false);
    }

    init();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);

    const res = await fetch('/api/v1/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }

    const data = await res.json();
    const newToken: string = data.access_token;
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);

    const me = await fetchMe(newToken);
    if (!me) throw new Error('Could not load user profile after login');
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ token, user, authRequired, loading, login, logout }),
    [token, user, authRequired, loading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}
