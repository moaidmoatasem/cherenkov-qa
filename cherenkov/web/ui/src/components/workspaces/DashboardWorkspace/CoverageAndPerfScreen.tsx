/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Activity, BarChart3, TrendingUp, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { Card } from '../../ui';
import { CoverageTrendChart } from '../../ui/CoverageTrendChart';
import type { CoverageMap, CoverageEndpoint } from '../../../lib/api';
import { getCoverageMap, getCoverageTrend, fetchSignals } from '../../../lib/api';

type Status = 'idle' | 'loading' | 'done' | 'error';

// `value` (not `coverage_pct`) so this stays structurally compatible with
// CoverageTrendChart's own TrendPoint, which is what it is passed to.
interface TrendPoint {
  timestamp: string;
  value: number;
  verdict?: string;
  divergence_count?: number;
}

interface PerfMetric {
  endpoint: string;
  method: string;
  latency_ms: number;
  status: 'passed' | 'failed' | 'anomaly_detected' | 'initializing';
  baseline_mean?: number;
  baseline_stddev?: number;
  threshold_limit?: number;
}

export const CoverageAndPerfScreen: React.FC = () => {
  const [coverageStatus, setCoverageStatus] = useState<Status>('idle');
  const [coverageMap, setCoverageMap] = useState<CoverageMap | null>(null);
  const [trendPoints, setTrendPoints] = useState<TrendPoint[]>([]);
  const [perfMetrics, setPerfMetrics] = useState<PerfMetric[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCoverageData();
  }, []);

  const loadCoverageData = async () => {
    setCoverageStatus('loading');
    setError(null);
    try {
      const [mapRes, trendRes, signalsRes] = await Promise.all([
        getCoverageMap(),
        getCoverageTrend(60),
        fetchSignals().catch(() => ({ performance: [], visual: [], coverage: [] })),
      ]);
      setCoverageMap(mapRes);
      setTrendPoints(
        trendRes.points.map((p: any) => ({
          timestamp: new Date(p.timestamp * 1000).toLocaleString(),
          value: p.coverage_pct,
          verdict: p.verdict,
          divergence_count: p.divergence_count,
        }))
      );
      if (signalsRes && signalsRes.performance) {
        setPerfMetrics(signalsRes.performance);
      }
      setCoverageStatus('done');
    } catch (err) {
      setError((err as Error).message);
      setCoverageStatus('error');
    }
  };

  const severityColor = (severity: string | null) => {
    switch (severity) {
      case 'critical': return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      case 'high': return 'text-orange-400 bg-orange-500/10 border-orange-500/30';
      case 'medium': return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      case 'low': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      case 'info': return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      default: return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    }
  };

  if (coverageStatus === 'loading') {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-sm text-text-muted font-mono animate-pulse">Loading coverage & performance data...</div>
      </div>
    );
  }

  if (coverageStatus === 'error' && !coverageMap) {
    return (
      <Card className="p-6 border-rose-500/30 bg-rose-500/10">
        <div className="flex items-center gap-3 text-rose-400">
          <AlertTriangle className="w-5 h-5" />
          <span className="font-mono text-sm">Failed to load coverage data: {error}</span>
        </div>
      </Card>
    );
  }

  const totalEndpoints = coverageMap?.totalEndpoints ?? 0;
  const testedCount = coverageMap?.testedCount ?? 0;
  const coveragePct = coverageMap?.coveragePct ?? 0;
  const openIssues = coverageMap?.openIssueCount ?? 0;

  return (
    <div className="space-y-6" data-testid="coverage-perf-screen">
      {/* Header Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 space-y-2">
          <div className="flex items-center gap-2 text-text-muted">
            <BarChart3 className="w-4 h-4" />
            <span className="text-xs font-mono uppercase tracking-wider">Coverage</span>
          </div>
          <div className="text-2xl font-bold text-glow-bright font-mono">{coveragePct.toFixed(1)}%</div>
          <div className="text-[10px] text-text-muted">
            {testedCount}/{totalEndpoints} endpoints tested
          </div>
        </Card>

        <Card className="p-4 space-y-2">
          <div className="flex items-center gap-2 text-text-muted">
            <TrendingUp className="w-4 h-4" />
            <span className="text-xs font-mono uppercase tracking-wider">Trend</span>
          </div>
          <div className="text-2xl font-bold text-glow-bright font-mono">
            {trendPoints.length > 1 
              ? ((trendPoints[trendPoints.length - 1].value - trendPoints[0].value) >= 0 ? '+' : '') + 
                (trendPoints[trendPoints.length - 1].value - trendPoints[0].value).toFixed(1) + '%'
              : '—'}
          </div>
          <div className="text-[10px] text-text-muted">
            {trendPoints.length > 0 ? 'vs. first run' : 'No history'}
          </div>
        </Card>

        <Card className="p-4 space-y-2">
          <div className="flex items-center gap-2 text-text-muted">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-xs font-mono uppercase tracking-wider">Open Issues</span>
          </div>
          <div className={`text-2xl font-bold font-mono ${openIssues > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
            {openIssues}
          </div>
          <div className="text-[10px] text-text-muted">
            {openIssues > 0 ? 'Active divergences' : 'All clear'}
          </div>
        </Card>

        <Card className="p-4 space-y-2">
          <div className="flex items-center gap-2 text-text-muted">
            <Activity className="w-4 h-4" />
            <span className="text-xs font-mono uppercase tracking-wider">Perf Tests</span>
          </div>
          <div className="text-2xl font-bold text-glow-bright font-mono">
            {perfMetrics.length > 0 ? perfMetrics.length : '—'}
          </div>
          <div className="text-[10px] text-text-muted">
            k6 performance runs
          </div>
        </Card>
      </div>

      {/* Coverage Trend Chart */}
      <Card className="p-6">
        <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted mb-4 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-cyan-400" />
          <span>Coverage Trend Over Time</span>
        </h2>
        {trendPoints.length > 0 ? (
          <CoverageTrendChart points={trendPoints} height={180} />
        ) : (
          <div className="text-xs text-text-muted font-mono py-8 text-center">
            No coverage history yet. Run <code className="bg-white/10 px-2 py-0.5 rounded">cherenkov verify</code> or <code className="bg-white/10 px-2 py-0.5 rounded">cherenkov certify</code> to build history.
          </div>
        )}
      </Card>

      {/* Endpoint Coverage Map */}
      <Card className="p-6">
        <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          <span>Endpoint Coverage Map</span>
        </h2>
        {coverageMap && coverageMap.endpoints.length > 0 ? (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {coverageMap.endpoints.map((ep: CoverageEndpoint, idx: number) => (
              <div
                key={idx}
                className={`flex items-center gap-3 p-3 rounded-lg border text-xs font-mono ${
                  ep.tested 
                    ? ep.activeSeverity 
                      ? severityColor(ep.activeSeverity)
                      : 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                    : 'text-slate-400 border-white/10 bg-white/5'
                }`}
              >
                <span className="font-bold w-16 shrink-0">{ep.method}</span>
                <span className="flex-1 truncate">{ep.path}</span>
                {ep.tested ? (
                  <>
                    <CheckCircle className="w-3.5 h-3.5 shrink-0" />
                    <span className="text-[10px]">
                      {ep.divergenceCount > 0 ? `${ep.divergenceCount} divergence(s)` : 'clean'}
                    </span>
                    {ep.activeSeverity && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider">
                        {ep.activeSeverity}
                      </span>
                    )}
                  </>
                ) : (
                  <>
                    <Clock className="w-3.5 h-3.5 shrink-0" />
                    <span className="text-[10px]">not tested</span>
                  </>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-xs text-text-muted font-mono py-8 text-center">
            No endpoints found. Upload an OpenAPI spec and run verification.
          </div>
        )}
      </Card>

      {/* Performance Metrics */}
      <Card className="p-6">
        <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <span>Performance Baselines</span>
        </h2>
        {perfMetrics.length > 0 ? (
          <div className="space-y-2">
            {perfMetrics.map((metric, idx) => (
              <div
                key={idx}
                className={`flex items-center gap-3 p-3 rounded-lg border text-xs font-mono ${
                  metric.status === 'passed' 
                    ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                    : metric.status === 'anomaly_detected'
                    ? 'text-rose-400 border-rose-500/30 bg-rose-500/10'
                    : 'text-amber-400 border-amber-500/30 bg-amber-500/10'
                }`}
              >
                <span className="font-bold w-16 shrink-0">{metric.method}</span>
                <span className="flex-1 truncate">{metric.endpoint}</span>
                <span className="text-[10px]">{metric.latency_ms.toFixed(0)}ms</span>
                {metric.baseline_mean && (
                  <span className="text-[10px] text-text-muted">
                    baseline: {metric.baseline_mean.toFixed(0)}±{metric.baseline_stddev?.toFixed(0)}ms
                  </span>
                )}
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider">
                  {metric.status.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-xs text-text-muted font-mono py-8 text-center">
            No performance metrics yet. Run <code className="bg-white/10 px-2 py-0.5 rounded">cherenkov perf</code> or enable k6 runner to collect latency baselines.
          </div>
        )}
      </Card>

      {/* Untested Endpoints (Gap Analysis) */}
      {coverageMap && coverageMap.endpoints.some((ep: CoverageEndpoint) => !ep.tested) && (
        <Card className="p-6 border-amber-500/30 bg-amber-500/10">
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-amber-400 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span>Coverage Gaps</span>
          </h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {coverageMap.endpoints
              .filter((ep: CoverageEndpoint) => !ep.tested)
              .map((ep: CoverageEndpoint, idx: number) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 p-3 rounded-lg border border-amber-500/30 bg-amber-500/20 text-xs font-mono text-amber-300"
                >
                  <span className="font-bold w-16 shrink-0">{ep.method}</span>
                  <span className="flex-1 truncate">{ep.path}</span>
                  <Clock className="w-3.5 h-3.5 shrink-0" />
                  <span className="text-[10px]">not probed in any run</span>
                </div>
              ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default CoverageAndPerfScreen;
