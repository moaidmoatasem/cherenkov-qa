import React, { useState, useEffect, useMemo } from 'react';
import { LayoutDashboard, ArrowRight, Zap, GraduationCap, CheckCircle } from 'lucide-react';
import { Card, PageHeader, KpiRing, Skeleton, EmptyState } from './ui';
import { fetchDivergences } from '../lib/api';
import { Divergence } from '../types';
import { MOCK_OVERVIEW } from '../mockData';

interface OverviewScreenProps {
  onNewRun: () => void;
  onNavigate: (tab: string) => void;
}

export default function OverviewScreen({ onNewRun, onNavigate }: OverviewScreenProps) {
  const [divergences, setDivergences] = useState<Divergence[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        setError(null);
        const data = await fetchDivergences();
        setDivergences(data || []);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const topDivergences = useMemo(() => {
    return divergences.slice(0, 3);
  }, [divergences]);

  const readinessScore = useMemo(() => {
    if (divergences.length === 0) return 100;
    const criticalCount = divergences.filter(d => d.severity === 'critical').length;
    const highCount = divergences.filter(d => d.severity === 'high').length;
    let score = 100 - (criticalCount * 15) - (highCount * 5);
    return Math.max(0, score);
  }, [divergences]);

  if (error) {
    return (
      <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10">
        <EmptyState 
          icon={<Zap />}
          title="Failed to load Overview"
          description={`Could not fetch live divergences: ${error}`}
          actionLabel="Retry"
          onAction={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="overview-screen">
      <PageHeader
        title="Release Readiness & Learning"
        description="Core metrics tracking API safety, active divergences, and Reflector self-healing optimizations."
        primaryAction={{
          label: 'Run Discovery Scan',
          onClick: onNewRun,
        }}
      />
      <div className="flex justify-end -mt-4 mb-2">
        <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border bg-amber-500/10 text-amber-400 border-amber-500/30">
          MOCK DATA
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        {/* Release Readiness KPI Ring */}
        <Card className="flex flex-col items-center justify-between p-6">
          <div className="w-full">
            <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted">
              Release Readiness Score
            </h3>
            <p className="text-xs text-[#7D8DA1] mt-1">Weighted score based on unresolved critical divergences.</p>
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
                glowColor={readinessScore > 80 ? "green" : readinessScore > 50 ? "yellow" : "red"}
              />
            )}
          </div>
          <div className="w-full flex items-center justify-between border-t border-white/5 pt-4 text-xs font-mono text-[#7D8DA1]">
            <span>FP Rate: {MOCK_OVERVIEW.falsePositiveRate}%</span>
            <span className="text-glow-bright">99.9% Target</span>
          </div>
        </Card>

        {/* Top Active Divergences */}
        <Card className="flex flex-col justify-between p-6">
          <div>
            <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
              <Zap className="w-4 h-4 text-glow-blue" />
              <span>Top Unresolved Divergences</span>
            </h3>
            <div className="mt-4 space-y-3">
              {isLoading ? (
                <>
                  <Skeleton className="h-16 w-full rounded-xl" />
                  <Skeleton className="h-16 w-full rounded-xl" />
                </>
              ) : topDivergences.length === 0 ? (
                <div className="text-xs text-[#7D8DA1] text-center py-4">No active divergences found.</div>
              ) : (
                topDivergences.map((div) => (
                  <div
                    key={div.id}
                    onClick={() => onNavigate('divergences')}
                    className="p-3 rounded-xl bg-black/20 border border-white/5 hover:border-glow-blue/50 hover:bg-white/5 transition-all duration-200 cursor-pointer text-xs"
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
                  </div>
                ))
              )}
            </div>
          </div>
          <button
            onClick={() => onNavigate('divergences')}
            className="w-full mt-4 py-2 border border-white/10 rounded-xl text-xs font-mono font-semibold text-[#7D8DA1] hover:text-[#E6EDF3] hover:bg-white/5 transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            disabled={isLoading}
          >
            <span>View All Divergences</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </Card>

        {/* Recent Learning Activity Feed */}
        <Card className="flex flex-col justify-between p-6">
          <div>
            <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-glow-blue" />
              <span>Reflector Verdict Memory</span>
            </h3>
            <div className="mt-4 space-y-4">
              {MOCK_OVERVIEW.recentLearnings.map((item, idx) => (
                <div key={idx} className="flex gap-3 text-xs">
                  <div className="mt-0.5 p-1 bg-glow-blue/10 text-glow-bright rounded-full h-fit">
                    <CheckCircle className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <p className="text-text-primary leading-relaxed">{item.text}</p>
                    <span className="text-[10px] text-[#7D8DA1]/75 font-mono block mt-1">Incremental Verdict Sync</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <button
            onClick={() => onNavigate('memory')}
            className="w-full mt-4 py-2 border border-white/10 rounded-xl text-xs font-mono font-semibold text-[#7D8DA1] hover:text-[#E6EDF3] hover:bg-white/5 transition flex items-center justify-center gap-2 cursor-pointer"
          >
            <span>Manage Reflector Memory</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </Card>
      </div>
    </div>
  );
}
