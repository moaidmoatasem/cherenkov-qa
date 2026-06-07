import { useEffect, useRef, useState, useCallback } from 'react';
import { API_BASE } from './api';

export type HealthState = {
  /** true once at least one probe has resolved successfully */
  online: boolean;
  /** backend reported demo_mode */
  demoMode: boolean;
  /** generation model reported by the backend, if any */
  genModel: string | null;
  /** true until the first probe resolves (avoids a flash of the offline overlay on load) */
  checking: boolean;
  /** force an immediate re-probe (e.g. from a Retry button) */
  refresh: () => void;
  /** timestamp of the last health check */
  lastCheckedAt: Date | null;
};

/**
 * Polls GET /api/v1/health on an interval and reports liveness.
 *
 * The dashboard is a thin client over the FastAPI review API; when that engine
 * is down, LIVE screens cannot load real data. This hook is the single source
 * of truth for "is the backend reachable", so the shell can render an honest
 * offline state instead of silently failing (see issue #221).
 */
export function useHealth(intervalMs = 10000): HealthState {
  const [online, setOnline] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [genModel, setGenModel] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [lastCheckedAt, setLastCheckedAt] = useState<Date | null>(null);
  const tick = useRef(0);

  const probe = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
      if (!res.ok) throw new Error(`health ${res.status}`);
      const data = await res.json();
      setOnline(data?.status === 'online');
      setDemoMode(Boolean(data?.demo_mode));
      setGenModel(data?.gen_model ?? null);
    } catch {
      setOnline(false);
    } finally {
      setChecking(false);
      setLastCheckedAt(new Date());
    }
  }, []);

  const refresh = useCallback(() => {
    tick.current += 1;
    setChecking(true);
    void probe();
  }, [probe]);

  useEffect(() => {
    let cancelled = false;
    const run = () => { if (!cancelled) void probe(); };
    run();
    const id = window.setInterval(run, intervalMs);
    return () => { cancelled = true; window.clearInterval(id); };
  }, [probe, intervalMs, tick.current]);

  return { online, demoMode, genModel, checking, refresh, lastCheckedAt };
}
