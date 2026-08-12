import React, { useEffect, useState } from 'react';
import { Activity, Clock, CheckCircle, AlertTriangle } from 'lucide-react';

interface TrendPoint {
  timestamp: string;
  verdict: string;
  divergence_count: number;
  coverage_pct: number | null;
  target_url: string;
}

interface SlaData {
  // false until at least one run has been recorded — the card grid renders an
  // empty state rather than zeros that would read as measurements.
  measured: boolean;
  source: string;
  total_checks: number;
  failed_checks: number;
  pass_rate_pct: number | null;
  api_response_p99: number | null;
  latest_verdict: string | null;
  status: string;
  trend: TrendPoint[];
}

const SlaDashboard: React.FC = () => {
  const [data, setData] = useState<SlaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSla = async () => {
      try {
        const response = await fetch('/api/enterprise/sla');
        if (!response.ok) throw new Error('Failed to fetch SLA data');
        const json = await response.json();
        setData(json);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchSla();
  }, []);

  if (loading) return <div className="text-slate-500 animate-pulse">Loading SLA metrics...</div>;
  if (error) return <div className="text-red-500 bg-red-50 dark:bg-red-900/20 p-4 rounded-md">Error: {error}</div>;
  if (!data) return null;

  const passRateColor =
    data.pass_rate_pct === null ? 'text-slate-400'
      : data.pass_rate_pct >= 99.9 ? 'text-green-500'
      : 'text-amber-500';
  const fmt = (v: number | null, suffix = '') =>
    v === null ? '\u2014' : `${v.toLocaleString()}${suffix}`;

  if (!data.measured) {
    return (
      <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-lg text-center">
        <div className="text-slate-500 dark:text-slate-400">
          No runs recorded yet, so there are no SLA metrics to show.
        </div>
        <div className="text-xs text-slate-400 mt-2">
          Run <code>cherenkov verify</code> or start a run from the dashboard; these figures are
          derived from stored run records.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Uptime Card */}
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <Activity className="w-4 h-4 mr-2" />
            Conformance pass rate
          </div>
          <div className={`text-3xl font-bold ${passRateColor}`}>{fmt(data.pass_rate_pct, '%')}</div>
          <div className="text-xs text-slate-400 mt-2">Across {data.total_checks.toLocaleString()} recorded runs</div>
        </div>

        {/* Latency Card */}
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <Clock className="w-4 h-4 mr-2" />
            P99 Response
          </div>
          <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">{fmt(data.api_response_p99, ' ms')}</div>
          <div className="text-xs text-slate-400 mt-2">p99 of recorded run durations</div>
        </div>

        {/* Total Checks */}
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <CheckCircle className="w-4 h-4 mr-2" />
            Checks Executed
          </div>
          <div className="text-3xl font-bold text-slate-800 dark:text-slate-100">{data.total_checks.toLocaleString()}</div>
          <div className="text-xs text-slate-400 mt-2">Runs in the stored history</div>
        </div>

        {/* Failed Checks */}
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-lg flex flex-col">
          <div className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Failed Checks
          </div>
          <div className="text-3xl font-bold text-red-500">{data.failed_checks.toLocaleString()}</div>
          <div className="text-xs text-slate-400 mt-2">Requires triage</div>
        </div>
      </div>

      <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Conformance trend</h3>
        {/* This chart was `Math.floor(Math.random() * 40) + 60` per bar, re-rolled on
            every render, with a tooltip claiming "Day N: X% uptime". It is now one bar
            per recorded run, coloured by that run's real verdict. */}
        {data.trend.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-sm text-slate-400">
            No runs recorded yet.
          </div>
        ) : (
          <>
            <div className="h-48 flex items-end space-x-1" data-testid="conformance-trend">
              {data.trend.map((p, i) => {
                const verdict = (p.verdict || '').toUpperCase();
                const colour =
                  verdict === 'PASS' || verdict === 'CERTIFIED'
                    ? 'bg-emerald-500'
                    : verdict === 'WARN'
                    ? 'bg-amber-500'
                    : verdict === 'FAIL'
                    ? 'bg-rose-500'
                    : 'bg-slate-400';
                // Coverage drives bar height where the run recorded it; runs without a
                // coverage figure render at full height so they stay visible as bars
                // rather than silently reading as zero coverage.
                const height = p.coverage_pct === null ? 100 : Math.max(4, p.coverage_pct);
                return (
                  <div
                    key={`${p.timestamp}-${i}`}
                    className={`flex-1 rounded-t-sm ${colour}`}
                    style={{ height: `${height}%` }}
                    title={
                      `${p.timestamp} — ${verdict || 'no verdict'}` +
                      `, ${p.divergence_count} divergence(s)` +
                      (p.coverage_pct === null ? '' : `, ${p.coverage_pct}% coverage`) +
                      (p.target_url ? `\n${p.target_url}` : '')
                    }
                  />
                );
              })}
            </div>
            <div className="flex justify-between text-xs text-slate-400 mt-2">
              <span>Oldest of last {data.trend.length} run(s)</span>
              <span>Latest</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default SlaDashboard;
