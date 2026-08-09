/**
 * TestSurfacesPanel — surfaces Web UI Probe and k6 Performance (Issue #882).
 *
 * Design principle (from issue): certified spec-conformance stays primary.
 * These surfaces appear in a visually distinct SECONDARY group, labeled
 * exactly for what they do, never implying more than the backend delivers.
 */

import React, { useCallback, useEffect, useState } from "react";
import { Card, Skeleton } from "../../ui";
import {
  getUiProbeStatus,
  getPerfMetrics,
  runUiProbe,
  runPerfTest,
  UIProbeStatusResult,
  UIProbeRun,
  PerfMetric,
} from "../../../lib/api";
import {
  Globe,
  Zap,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Play,
  RefreshCw,
  Lock,
} from "lucide-react";

interface TestSurfacesPanelProps {
  targetUrl?: string;
}

// ── Tiny badge helpers ────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    clean:          { label: "Clean",         cls: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" },
    issues_found:   { label: "Issues found",  cls: "bg-rose-500/10 text-rose-400 border border-rose-500/20" },
    ok:             { label: "OK",            cls: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" },
    degraded:       { label: "Degraded",      cls: "bg-amber-500/10 text-amber-400 border border-amber-500/20" },
    anomaly:        { label: "Anomaly",       cls: "bg-rose-500/10 text-rose-400 border border-rose-500/20" },
    initializing:   { label: "Initializing",  cls: "bg-blue-500/10 text-blue-400 border border-blue-500/20" },
  };
  const { label, cls } = map[status] ?? { label: status, cls: "bg-white/5 text-text-muted border border-white/10" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${cls}`}>
      {label}
    </span>
  );
}

// ── Web UI Probe sub-panel ────────────────────────────────────────────────────
function UiProbePanel({ targetUrl }: { targetUrl?: string }) {
  const [probe, setProbe] = useState<UIProbeStatusResult | null>(null);
  const [result, setResult] = useState<UIProbeRun | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getUiProbeStatus().then(setProbe);
  }, []);

  const handleRun = useCallback(async () => {
    if (!targetUrl) return;
    setRunning(true);
    setError(null);
    try {
      const r = await runUiProbe(targetUrl, ["/", "/dashboard"]);
      setResult(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }, [targetUrl]);

  return (
    <div className="ds-glass-panel p-4 rounded-xl flex flex-col gap-3" data-testid="ui-probe-panel">
      <div className="flex items-center gap-2">
        <Globe className="w-4 h-4 text-violet-400 shrink-0" />
        <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Web UI Probe</span>
        <span className="ml-auto text-[10px] text-text-muted italic">
          {probe === null ? "loading…" : probe.available ? "Playwright available" : "Playwright not installed"}
        </span>
      </div>

      {probe && !probe.available && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300">
          <Lock className="w-3.5 h-3.5 inline mr-1.5" />
          {probe.install_hint ?? "Playwright not installed on this host."}
        </div>
      )}

      {result && (
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <StatusBadge status={result.status} />
            <span className="text-text-muted">{result.issue_count} issue(s) · {result.total_findings} finding(s) total</span>
          </div>
          {result.findings.slice(0, 5).map((f, i) => (
            <div key={i} className="text-[10px] font-mono text-text-muted truncate">
              <span className="text-cyan-400">{f.kind}</span> — {f.message}
            </div>
          ))}
        </div>
      )}

      {error && <p className="text-xs text-rose-400">{error}</p>}

      <button
        onClick={handleRun}
        disabled={running || !targetUrl || (probe !== null && !probe.available)}
        className="mt-auto self-start ds-button ds-button-primary text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5 disabled:opacity-40"
        data-testid="ui-probe-run-btn"
      >
        {running ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
        {running ? "Probing…" : "Run Probe"}
      </button>
    </div>
  );
}

// ── k6 Performance sub-panel ──────────────────────────────────────────────────
function PerfPanel({ targetUrl }: { targetUrl?: string }) {
  const [metrics, setMetrics] = useState<PerfMetric[]>([]);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<(PerfMetric & { exit_code?: number }) | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPerfMetrics().then(setMetrics);
  }, []);

  const handleRun = useCallback(async () => {
    setRunning(true);
    setError(null);
    try {
      const r = await runPerfTest(targetUrl);
      setRunResult(r);
      // refresh baseline list
      getPerfMetrics().then(setMetrics);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }, [targetUrl]);

  return (
    <div className="ds-glass-panel p-4 rounded-xl flex flex-col gap-3" data-testid="perf-panel">
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-amber-400 shrink-0" />
        <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Performance / k6</span>
        <span className="ml-auto text-[10px] text-text-muted italic">
          {metrics.length > 0 ? `${metrics.length} baseline(s) stored` : "No baselines yet"}
        </span>
      </div>

      {runResult && (
        <div className="flex items-center gap-2 text-xs">
          <StatusBadge status={runResult.status} />
          <span className="text-text-muted font-mono">{runResult.latency_ms.toFixed(1)} ms avg</span>
          {runResult.message && <span className="text-text-muted truncate">{runResult.message}</span>}
        </div>
      )}

      {metrics.length > 0 && (
        <table className="w-full text-left text-[10px] font-mono">
          <thead>
            <tr className="border-b border-white/10 text-text-muted uppercase">
              <th className="pb-1.5 pr-3">Endpoint</th>
              <th className="pb-1.5 pr-3">Method</th>
              <th className="pb-1.5 pr-3">Latency</th>
              <th className="pb-1.5">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {metrics.slice(0, 6).map((m, i) => (
              <tr key={i}>
                <td className="py-1.5 pr-3 text-cyan-400">{m.endpoint}</td>
                <td className="py-1.5 pr-3 text-text-muted">{m.method}</td>
                <td className="py-1.5 pr-3 text-text-primary">{m.latency_ms.toFixed(1)} ms</td>
                <td className="py-1.5"><StatusBadge status={m.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {error && <p className="text-xs text-rose-400">{error}</p>}

      <button
        onClick={handleRun}
        disabled={running}
        className="mt-auto self-start ds-button ds-button-primary text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5 disabled:opacity-40"
        data-testid="perf-run-btn"
      >
        {running ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
        {running ? "Running k6…" : "Run Perf Test"}
      </button>
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────
export const TestSurfacesPanel: React.FC<TestSurfacesPanelProps> = ({ targetUrl }) => (
  <Card className="p-6 space-y-4" data-testid="test-surfaces-panel">
    <div>
      <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
        <Globe className="w-4 h-4 text-violet-400" />
        <span>Additional Test Surfaces</span>
        <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-text-muted normal-case tracking-normal">
          secondary
        </span>
      </h2>
      <p className="text-xs text-text-muted mt-0.5">
        Web UI probing and k6 performance baselines — real backends, honest scope.
      </p>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <UiProbePanel targetUrl={targetUrl} />
      <PerfPanel targetUrl={targetUrl} />
    </div>
  </Card>
);

export default TestSurfacesPanel;
