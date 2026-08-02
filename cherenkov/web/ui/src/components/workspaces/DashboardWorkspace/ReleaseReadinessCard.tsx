/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState, useMemo } from 'react';
import { Card, KpiRing, Skeleton } from '../../ui';
import { fetchOverviewData, fetchMetricsData, fetchDivergences, fetchReviewQueue, ReviewQueueItem } from '../../../lib/api';
import { Divergence } from '../../../types';
import { Zap, CheckCircle2, AlertTriangle, ShieldCheck, RefreshCw } from 'lucide-react';

interface ReleaseReadinessCardProps {
  onNavigateToTriage?: () => void;
}

export const ReleaseReadinessCard: React.FC<ReleaseReadinessCardProps> = ({ onNavigateToTriage }) => {
  const [divergences, setDivergences] = useState<Divergence[]>([]);
  const [pendingReviews, setPendingReviews] = useState<ReviewQueueItem[]>([]);
  const [metrics, setMetrics] = useState<{ totalTokens: number; totalCost: number } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [divData, queueData, metricsData] = await Promise.all([
        fetchDivergences().catch(() => []),
        fetchReviewQueue('pending').catch(() => []),
        fetchMetricsData().catch(() => null),
      ]);
      setDivergences(divData || []);
      setPendingReviews(Array.isArray(queueData) ? queueData : []);
      if (metricsData?.metrics) setMetrics(metricsData.metrics);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const readinessScore = useMemo(() => {
    if (divergences.length === 0) return 100;
    const criticalCount = divergences.filter((d) => d.severity === 'critical').length;
    const highCount = divergences.filter((d) => d.severity === 'high').length;
    const pendingCount = pendingReviews.length;
    const score = 100 - criticalCount * 15 - highCount * 5 - pendingCount * 2;
    return Math.max(0, score);
  }, [divergences, pendingReviews]);

  const verdictGrade = useMemo(() => {
    if (readinessScore >= 90) return 'A';
    if (readinessScore >= 80) return 'B';
    if (readinessScore >= 70) return 'C';
    if (readinessScore >= 60) return 'D';
    return 'F';
  }, [readinessScore]);

  const readinessLabel =
    readinessScore >= 80 ? 'Ship Ready' : readinessScore >= 50 ? 'Review Required' : 'Hold — Critical Issues';
  const readinessColor: 'success' | 'warning' | 'danger' =
    readinessScore >= 80 ? 'success' : readinessScore >= 50 ? 'warning' : 'danger';

  return (
    <Card className="p-6 space-y-6" data-testid="release-readiness-card">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <span>Release Readiness Gate</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Aggregated pass rates, verdict grades, and system execution metrics.
          </p>
        </div>
        <button
          onClick={loadData}
          className="p-1.5 rounded-lg border border-border-subtle hover:border-border-strong text-text-muted hover:text-text-primary transition"
          title="Refresh metrics"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 py-4">
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Readiness Score */}
          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex items-center gap-4">
            <KpiRing
              value={readinessScore}
              title="Score"
              size={72}
              strokeWidth={8}
              glowColor={readinessColor}
            />
            <div>
              <p className="text-[10px] font-mono uppercase text-text-muted">Readiness Score</p>
              <p className="text-xl font-bold font-mono text-text-primary mt-0.5">{readinessScore}/100</p>
              <p className="text-[10px] font-mono text-cyan-400">{readinessLabel}</p>
            </div>
          </div>

          {/* Verdict Grade */}
          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex flex-col justify-between">
            <p className="text-[10px] font-mono uppercase text-text-muted">Verdict Grade</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-3xl font-bold font-mono ${verdictGrade === 'A' || verdictGrade === 'B' ? 'text-emerald-400' : 'text-amber-400'}`}>
                {verdictGrade}
              </span>
              <span className="text-xs text-text-muted">Quality Grade</span>
            </div>
            <p className="text-[10px] text-text-muted">From live /api/v1/overview</p>
          </div>

          {/* Open Divergences */}
          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex flex-col justify-between">
            <p className="text-[10px] font-mono uppercase text-text-muted">Open Divergences</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-3xl font-bold font-mono ${divergences.length === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {divergences.length}
              </span>
              <span className="text-xs text-text-muted">issues</span>
            </div>
            {onNavigateToTriage && (
              <button
                onClick={onNavigateToTriage}
                className="text-[10px] font-mono text-cyan-400 hover:underline text-left"
              >
                Triage Divergences &rarr;
              </button>
            )}
          </div>

          {/* Pending HITL Queue */}
          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex flex-col justify-between">
            <p className="text-[10px] font-mono uppercase text-text-muted">Pending HITL Queue</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-3xl font-bold font-mono ${pendingReviews.length === 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {pendingReviews.length}
              </span>
              <span className="text-xs text-text-muted">scenarios</span>
            </div>
            <p className="text-[10px] text-text-muted">Awaiting human review</p>
          </div>
        </div>
      )}
    </Card>
  );
};

export default ReleaseReadinessCard;
