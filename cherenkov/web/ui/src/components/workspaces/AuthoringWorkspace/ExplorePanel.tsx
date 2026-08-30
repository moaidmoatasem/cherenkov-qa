/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Card, useToast } from '../../ui';
import { runExplore, ExploreResponse, ExploreFindingDto } from '../../../lib/api';
import { Radar, Play, Loader2, AlertTriangle, CheckCircle2, Compass } from 'lucide-react';

const KIND_LABELS: Record<ExploreFindingDto['kind'], string> = {
  server_error: '5xx',
  client_error: '4xx',
  js_error: 'js',
  visual_break: 'visual',
  slow_response: 'slow',
  unreachable: 'unreachable',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
  high: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  medium: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  low: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
};

export const ExplorePanel: React.FC = () => {
  const [baseUrl, setBaseUrl] = useState('http://localhost:8000');
  const [paths, setPaths] = useState('/, /health');
  const [method, setMethod] = useState('GET');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ExploreResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const handleRun = async () => {
    const pathList = paths
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean);
    if (pathList.length === 0) {
      toast('Enter at least one path to crawl.', 'danger');
      return;
    }
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await runExplore({
        base_url: baseUrl,
        paths: pathList,
        method,
        slow_ms: 2000,
        discover: true,
      });
      setResult(res);
      const issueCount = res.findings.length;
      toast(
        issueCount > 0
          ? `Exploration found ${issueCount} signal(s) for review.`
          : 'Exploration complete: no anomalies on the probed paths.',
        issueCount > 0 ? 'warning' : 'success'
      );
    } catch (err) {
      setError((err as Error).message);
      toast(`Exploration failed: ${(err as Error).message}`, 'danger');
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="explore-panel">
      <div>
        <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
          <Radar className="w-4 h-4 text-fuchsia-400" />
          <span>Live Surface Explorer</span>
        </h2>
        <p className="text-xs text-text-muted mt-0.5">
          Crawl a running service and surface anomalies. Findings are
          evidence for Triage — never auto-confirmed defects.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_120px_auto] gap-3 items-end">
        <div className="space-y-1">
          <label className="text-[10px] font-mono uppercase tracking-wider text-text-muted" htmlFor="explore-base-url">
            Base URL
          </label>
          <input
            id="explore-base-url"
            data-testid="explore-base-url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="http://localhost:8000"
            className="w-full bg-bg-base border border-border-subtle rounded-lg px-3 py-2 text-xs font-mono text-cyan-400 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-mono uppercase tracking-wider text-text-muted" htmlFor="explore-paths">
            Paths (comma-separated)
          </label>
          <input
            id="explore-paths"
            data-testid="explore-paths"
            value={paths}
            onChange={(e) => setPaths(e.target.value)}
            placeholder="/, /health, /pets"
            className="w-full bg-bg-base border border-border-subtle rounded-lg px-3 py-2 text-xs font-mono text-text-primary focus:outline-none focus:border-cyan-500/50"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-mono uppercase tracking-wider text-text-muted" htmlFor="explore-method">
            Method
          </label>
          <select
            id="explore-method"
            data-testid="explore-method"
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="w-full bg-bg-base border border-border-subtle rounded-lg px-2 py-2 text-xs font-mono text-cyan-400"
          >
            <option>GET</option>
            <option>POST</option>
            <option>PUT</option>
            <option>DELETE</option>
          </select>
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          data-testid="btn-run-explore"
          className="px-4 py-2 rounded-lg bg-fuchsia-500/10 border border-fuchsia-500/30 hover:bg-fuchsia-500/20 text-fuchsia-400 text-xs font-bold uppercase tracking-wider transition disabled:opacity-50 flex items-center gap-2"
        >
          {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {running ? 'Crawling…' : 'Run Crawl'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400" data-testid="explore-error">
          <AlertTriangle className="w-3.5 h-3.5 inline mr-1" />
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-3" data-testid="explore-results">
          <div className="flex items-center justify-between text-xs font-mono text-text-muted">
            <span>
              Probed <span className="text-text-primary">{result.probed}</span> path(s) on{' '}
              <span className="text-cyan-400">{result.base_url}</span>
            </span>
            <span className="flex items-center gap-1">
              {result.findings.length > 0 ? (
                <span className="flex items-center gap-1 text-amber-400">
                  <AlertTriangle className="w-3.5 h-3.5" /> {result.findings.length} finding(s)
                </span>
              ) : (
                <span className="flex items-center gap-1 text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5" /> No anomalies
                </span>
              )}
            </span>
          </div>

          {result.discovered.length > 0 && (
            <div>
              <h3 className="text-[10px] font-mono uppercase tracking-wider text-text-muted mb-1.5 flex items-center gap-1">
                <Compass className="w-3 h-3" /> Discovered flows ({result.discovered.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.discovered.map((flow, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 rounded-lg border border-white/10 bg-white/5 text-[10px] font-mono text-text-secondary"
                  >
                    {flow.method} {flow.path}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.discover_note && (
            <p className="text-[11px] text-amber-400/80 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
              {result.discover_note}
            </p>
          )}

          {result.findings.length > 0 && (
            <div className="overflow-x-auto border border-border-subtle rounded-xl">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-white/10 text-text-muted uppercase text-[10px]">
                    <th className="py-2.5 px-3">Severity</th>
                    <th className="py-2.5 px-3">Kind</th>
                    <th className="py-2.5 px-3">URL</th>
                    <th className="py-2.5 px-3 text-right">Status</th>
                    <th className="py-2.5 px-3 text-right">Latency</th>
                    <th className="py-2.5 px-3">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {result.findings.map((f) => (
                    <tr key={f.id} className="hover:bg-white/5 transition" data-testid={`explore-finding-${f.id}`}>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                            SEVERITY_COLORS[f.severity] ?? SEVERITY_COLORS.medium
                          }`}
                        >
                          {f.severity}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-bold text-fuchsia-400">{KIND_LABELS[f.kind] ?? f.kind}</td>
                      <td className="py-2.5 px-3 text-text-primary max-w-[20rem] truncate" title={f.url}>
                        {f.method} {f.url}
                      </td>
                      <td className="py-2.5 px-3 text-right">{f.status ?? '—'}</td>
                      <td className="py-2.5 px-3 text-right">{f.latency_ms}ms</td>
                      <td className="py-2.5 px-3 text-text-muted max-w-[24rem] truncate" title={f.detail}>
                        {f.detail}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="text-[11px] text-text-muted border-t border-white/5 pt-3">
            Explorer findings are hypotheses, not verdicts. Review them in the Triage workspace before anything
            becomes a confirmed defect or a generated test.
          </p>
        </div>
      )}
    </Card>
  );
};

export default ExplorePanel;
