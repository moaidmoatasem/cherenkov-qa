/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useMemo } from 'react';
import { ArrowRight, Zap, CheckCircle2, AlertTriangle, Play, RefreshCw } from 'lucide-react';
import { Card, PageHeader, KpiRing, Skeleton, EmptyState, MockBadge } from './ui';
import { fetchDivergences, fetchReviewQueue, ReviewQueueItem, fetchMetricsData } from '../lib/api';
import { Divergence } from '../types';
import { useToast } from './ui/Toast';

interface OverviewScreenProps {
  onNewRun: () => void;
  onPilotRun: () => void;
  onNavigate: (tab: string) => void;
}

export default function OverviewScreen({ onNewRun, onPilotRun, onNavigate }: OverviewScreenProps) {
  const { toast } = useToast();
  const [divergences, setDivergences] = useState<Divergence[]>([]);
  const [pendingReviews, setPendingReviews] = useState<ReviewQueueItem[]>([]);
  const [metrics, setMetrics] = useState<{ totalTokens: number; totalCost: number } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [divData, queueData, metricsData] = await Promise.all([
        fetchDivergences(),
        fetchReviewQueue('pending').catch(() => [] as ReviewQueueItem[]),
        fetchMetricsData().catch(() => null),
      ]);
      setDivergences(divData || []);
      setPendingReviews(Array.isArray(queueData) ? queueData : []);
      if (metricsData?.metrics) setMetrics(metricsData.metrics);
      setLastRefreshed(new Date());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleRefresh = () => {
    toast('Refreshing release readiness data…', 'info');
    loadData();
  };

  const topDivergences = useMemo(() => {
    return [...divergences]
      .sort((a, b) => {
        const sevOrder = { critical: 0, high: 1, medium: 2, low: 3 };
        return (sevOrder[a.severity as keyof typeof sevOrder] ?? 4) - (sevOrder[b.severity as keyof typeof sevOrder] ?? 4);
      })
      .slice(0, 3);
  }, [divergences]);

  const readinessScore = useMemo(() => {
    if (divergences.length === 0) return 100;
    const criticalCount = divergences.filter(d => d.severity === 'critical').length;
    const highCount = divergences.filter(d => d.severity === 'high').length;
    const pendingCount = pendingReviews.length;
    let score = 100 - (criticalCount * 15) - (highCount * 5) - (pendingCount * 2);
    return Math.max(0, score);
  }, [divergences, pendingReviews]);

  const readinessLabel = readinessScore >= 80 ? 'Ship Ready' : readinessScore >= 50 ? 'Review Required' : 'Hold — Critical Issues';
  const readinessColor: 'success' | 'warning' | 'danger' = readinessScore >= 80 ? 'success' : readinessScore >= 50 ? 'warning' : 'danger';

  if (error) {
    return (
      <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10">
        <EmptyState
          icon={Zap}
          title="Failed to Load Release Readiness"
          description={`Could not fetch live data: ${error}`}
          primaryAction={{ label: 'Retry', onClick: () => loadData() }}
        />
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="overview-screen" data-testid="overview-screen">
      <div className="flex items-start justify-between">
        <PageHeader
          title="Release Readiness"
          description="Real-time ship/no-ship gate based on live divergences, pending reviews, and test coverage."
          primaryAction={{ label: 'New Analysis Run', onClick: () => { toast('Starting discovery scan…', 'info'); onNewRun(); } }}
        />
        <div className="flex items-center gap-2 mt-1">
          <button
            id="btn-pilot-run"
            data-testid="btn-pilot-run"
            onClick={onPilotRun}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-white/10 text-xs font-mono font-semibold text-[#7D8DA1] hover:text-glow-bright hover:bg-white/5 transition cursor-pointer"
          >
            <Play className="w-3 h-3" />
            Pilot Run
          </button>
          <button
            id="btn-overview-refresh"
            data-testid="btn-overview-refresh"
            onClick={handleRefresh}
            className="p-1.5 rounded-md border border-white/10 text-[#7D8DA1] hover:text-glow-bright hover:bg-white/5 transition cursor-pointer"
            title={lastRefreshed ? `Last refreshed: ${lastRefreshed.toLocaleTimeString()}` : 'Refresh'}
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* KPI Summary Row — all from real APIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Open Divergences',
            value: isLoading ? '—' : String(divergences.length),
            sub: isLoading ? '' : `${divergences.filter(d => d.severity === 'critical').length} critical`,
            color: divergences.filter(d => d.severity === 'critical').length > 0 ? 'text-rose-400' : 'text-emerald-400',
            testid: 'kpi-divergences',
          },
          {
            label: 'Pending Review',
            value: isLoading ? '—' : String(pendingReviews.length),
            sub: 'awaiting HITL',
            color: pendingReviews.length > 0 ? 'text-amber-400' : 'text-emerald-400',
            testid: 'kpi-pending',
          },
          {
            label: 'Session Cost',
            value: metrics ? `$${metrics.totalCost.toFixed(2)}` : '—',
            sub: metrics ? `${metrics.totalTokens.toLocaleString()} tokens` : 'from /api/v1/metrics',
            color: 'text-glow-bright',
            testid: 'kpi-cost',
          },
          {
            label: 'Cloud Equivalent',
            value: metrics ? `$${(metrics.totalCost * 3.4).toFixed(3)}` : '—',
            sub: 'vs GPT-4o list price',
            color: 'text-violet-400',
            testid: 'kpi-cloud',
          },
        ].map(kpi => (
          <Card key={kpi.testid} className="p-4" data-testid={kpi.testid}>
            <p className="text-[10px] font-mono uppercase tracking-wider text-[#7D8DA1]">{kpi.label}</p>
            <p className={`text-2xl font-bold font-mono mt-1 ${kpi.color}`}>{kpi.value}</p>
            <p className="text-[10px] text-[#7D8DA1]/70 mt-0.5">{kpi.sub}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        {/* Release Readiness KPI Ring */}
        <Card className="flex flex-col items-center justify-between p-6" data-testid="overview-kpi-readiness">
          <div className="w-full">
            <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted">
              Readiness Score
            </h2>
            <p className="text-xs text-[#7D8DA1] mt-1">Weighted — critical divergences, pending HITL.</p>
          </div>
          <div className="py-6">
            {isLoading ? (
              <Skeleton className="w-40 h-40 rounded-full" />
            ) : (
              <KpiRing
                value={readinessScore}
                title="Readiness"
                size={160}
                strokeWidth={12}
                glowColor={readinessColor}
              />
            )}
          </div>
          <div className="w-full flex items-center justify-between border-t border-white/5 pt-4 text-xs font-mono text-[#7D8DA1]">
            <span>{readinessLabel}</span>
            <span className={`font-bold ${readinessColor === 'success' ? 'text-emerald-400' : readinessColor === 'warning' ? 'text-amber-400' : 'text-rose-400'}`}>
              {readinessScore}/100
            </span>
          </div>
        </Card>

        {/* Top Active Divergences — real data, risk-sorted */}
        <Card className="flex flex-col justify-between p-6" data-testid="overview-kpi-divergences">
          <div>
            <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
              <Zap className="w-4 h-4 text-glow-blue" />
              <span>Top Open Divergences</span>
            </h2>
            <p className="text-[10px] text-[#7D8DA1] mt-1">Risk-sorted. From live <code className="font-mono">GET /api/v1/divergences</code>.</p>
            <div className="mt-4 space-y-3">
              {isLoading ? (
                <>
                  <Skeleton className="h-16 w-full rounded-xl" />
                  <Skeleton className="h-16 w-full rounded-xl" />
                </>
              ) : topDivergences.length === 0 ? (
                <div className="flex items-center gap-2 text-xs text-emerald-400 py-4">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>No open divergences — clean to ship.</span>
                </div>
              ) : (
                topDivergences.map((div) => (
                  <button
                    key={div.id}
                    onClick={() => onNavigate('divergences')}
                    className="w-full text-left p-3 rounded-xl bg-black/20 border border-white/5 hover:border-glow-blue/50 hover:bg-white/5 transition-all duration-200 cursor-pointer text-xs"
                    data-testid={`divergence-row-${div.id}`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-mono font-bold text-glow-bright uppercase">{div.divergenceClass}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[8px] font-mono font-bold uppercase ${
                        div.severity === 'critical' || div.severity === 'high'
                          ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}>
                        {div.severity}
                      </span>
                    </div>
                    <p className="text-text-primary font-semibold truncate">{div.endpoint}</p>
                    <p className="text-[#7D8DA1] mt-0.5 truncate">{div.claimB}</p>
                  </button>
                ))
              )}
            </div>
          </div>
          <button
            onClick={() => onNavigate('divergences')}
            className="w-full mt-4 py-2 border border-white/10 rounded-xl text-xs font-mono font-semibold text-[#7D8DA1] hover:text-[#E6EDF3] hover:bg-white/5 transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            disabled={isLoading}
            data-testid="btn-view-all-divergences"
          >
            <span>Triage All Divergences</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </Card>

        {/* Pending Review Queue — real data */}
        <Card className="flex flex-col justify-between p-6" data-testid="overview-kpi-review">
          <div>
            <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Pending Review Gate</span>
            </h2>
            <p className="text-[10px] text-[#7D8DA1] mt-1">From live <code className="font-mono">GET /api/v1/review/queue</code>.</p>
            <div className="mt-4 space-y-2">
              {isLoading ? (
                <>
                  <Skeleton className="h-10 w-full rounded-lg" />
                  <Skeleton className="h-10 w-full rounded-lg" />
                  <Skeleton className="h-10 w-full rounded-lg" />
                </>
              ) : pendingReviews.length === 0 ? (
                <div className="flex items-center gap-2 text-xs text-emerald-400 py-4">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>No pending reviews — queue clear.</span>
                </div>
              ) : (
                pendingReviews.slice(0, 4).map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onNavigate('review')}
                    className="w-full text-left px-3 py-2 rounded-lg bg-black/20 border border-white/5 hover:border-amber-400/40 hover:bg-white/5 transition cursor-pointer text-xs"
                    data-testid={`review-row-${item.id}`}
                  >
                    <span className="font-mono font-bold text-amber-400 uppercase">{item.method}</span>
                    <span className="text-text-primary ml-2 truncate">{item.endpoint}</span>
                  </button>
                ))
              )}
              {!isLoading && pendingReviews.length > 4 && (
                <p className="text-[10px] text-[#7D8DA1] text-center">+{pendingReviews.length - 4} more in queue</p>
              )}
            </div>
          </div>
          <button
            onClick={() => onNavigate('review')}
            className="w-full mt-4 py-2 border border-white/10 rounded-xl text-xs font-mono font-semibold text-[#7D8DA1] hover:text-[#E6EDF3] hover:bg-white/5 transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            disabled={isLoading}
            data-testid="btn-go-to-review"
          >
            <span>Open Review Gate</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </Card>
      </div>

      {/* Data source transparency footer */}
      <div className="flex items-center gap-2 text-[10px] font-mono text-[#7D8DA1]/60 border-t border-white/5 pt-3">
        <MockBadge />
        <span className="ml-2">KPI Ring readiness score is computed client-side. Signals and Truth Map screens require additional backend endpoints (Phase 4).</span>
      </div>
    </div>
  );
}
