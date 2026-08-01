import React, { useState, useEffect, useMemo } from 'react';
import { FileCode, Clock, ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react';
import { PageHeader, Card, Skeleton, EmptyState, CoverageTrendChart } from '../components/ui';
import { fetchGeneratedTests, fetchRuns, GeneratedTestFile, RunRecord } from '../lib/api';

export default function TestManagementScreen() {
  const [tests, setTests] = useState<GeneratedTestFile[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setLoadError(null);
      try {
        const [testFiles, runRecords] = await Promise.all([
          fetchGeneratedTests(),
          fetchRuns(undefined, 20),
        ]);
        if (cancelled) return;
        setTests(testFiles);
        setRuns(runRecords);
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : 'Failed to load test inventory');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // RunStore returns most-recent-first; the trend chart reads left-to-right chronologically.
  const coveragePoints = useMemo(
    () =>
      runs
        .filter((r) => r.coverage_pct != null)
        .slice()
        .reverse()
        .map((r) => ({ timestamp: r.timestamp, value: r.coverage_pct as number })),
    [runs]
  );

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10">
      <PageHeader
        title="Test Plans"
        description="Generated test inventory and run history, pulled live from the backend RunStore."
      />

      {!isLoading && !loadError && (
        <Card className="p-6">
          <CoverageTrendChart points={coveragePoints} />
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Test inventory (from /api/v1/tests) */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <FileCode className="w-5 h-5 text-glow-blue" />
              <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-primary">
                Generated Suites
              </h2>
            </div>
            <span className="bg-white/10 px-2 py-0.5 rounded text-[10px] text-[#7D8DA1] font-mono">{tests.length}</span>
          </div>

          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
            </div>
          ) : loadError ? (
            <div className="flex flex-col items-center justify-center text-center py-12 space-y-1.5">
              <AlertTriangle className="w-8 h-8 text-amber-400" />
              <p className="text-text-muted text-xs font-semibold">{loadError}</p>
            </div>
          ) : tests.length === 0 ? (
            <EmptyState
              title="No generated suites yet"
              description="Run `cherenkov generate` against a spec to populate this list."
            />
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {tests.map((t) => (
                <div key={t.scenario_id} className="p-3 rounded-xl bg-black/20 border border-white/5 flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-mono font-bold uppercase text-glow-bright">{t.method}</span>
                      <span className="text-xs font-mono text-text-primary truncate">{t.endpoint}</span>
                    </div>
                    <div className="text-[10px] text-text-muted font-mono truncate mt-0.5">{t.name}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Run history (from /api/v1/runs) */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-glow-blue" />
              <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-primary">
                Run History
              </h2>
            </div>
            <span className="bg-white/10 px-2 py-0.5 rounded text-[10px] text-[#7D8DA1] font-mono">{runs.length}</span>
          </div>

          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
            </div>
          ) : runs.length === 0 ? (
            <EmptyState
              title="No runs recorded yet"
              description="Run `cherenkov verify` or `cherenkov certify` against a target to populate run history."
            />
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {runs.map((r) => {
                const isClean = r.divergence_count === 0;
                return (
                  <div key={r.run_id} className="p-3 rounded-xl bg-black/20 border border-white/5 flex items-center justify-between">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        {isClean ? (
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        ) : (
                          <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        )}
                        <span className="text-xs font-mono text-text-primary truncate">{r.target_url}</span>
                      </div>
                      <div className="text-[10px] text-text-muted font-mono mt-0.5">
                        {r.timestamp} &middot; {r.divergence_count} divergence(s)
                        {r.coverage_pct != null ? ` · ${r.coverage_pct.toFixed(0)}% coverage` : ''}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
