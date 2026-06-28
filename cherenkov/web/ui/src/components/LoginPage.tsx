/**
 * LoginPage — shown when AUTH_ENABLED=true and no valid session exists.
 */

import React, { FormEvent, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-base text-text-primary font-sans antialiased">
      {/* Ambient glow */}
      <div className="absolute top-[-150px] left-[-150px] w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-100px] right-[-100px] w-[400px] h-[400px] bg-blue-600/8 rounded-full blur-[100px] pointer-events-none" />

      <div className="relative z-10 w-full max-w-sm mx-4">
        {/* Logo / title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-3">
            <span className="text-cyan-400 text-2xl font-bold tracking-widest uppercase">
              CHERENKOV
            </span>
          </div>
          <p className="text-text-secondary text-sm">Sign in to the QA dashboard</p>
        </div>

        {/* Card */}
        <form
          onSubmit={handleSubmit}
          className="bg-surface-overlay border border-border-subtle rounded-xl p-6 shadow-2xl space-y-4"
        >
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full bg-bg-raised border border-border-subtle rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 transition"
              placeholder="admin"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-bg-raised border border-border-subtle rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 transition"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:bg-cyan-500/40 text-black font-semibold rounded-lg px-4 py-2 text-sm transition focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-text-muted text-xs mt-6">
          First run? Create an admin account via{' '}
          <code className="text-cyan-400">POST /api/v1/auth/users</code> with your{' '}
          <code className="text-cyan-400">CHERENKOV_BOOTSTRAP_KEY</code>.
        </p>
      </div>
    </div>
  );
}
