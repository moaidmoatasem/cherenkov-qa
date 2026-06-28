import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { RunRecord } from '../lib/api';
import { fetchRuns, fetchRun } from '../lib/api';
import VerdictCard from '../components/ui/VerdictCard';
import RunTimeline from '../components/ui/RunTimeline';
import { PageHeader } from '../components/ui/PageHeader';

export default function VerdictScreen() {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selectedRun, setSelectedRun] = useState<RunRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchRuns(undefined, 50);
      setRuns(data);

      const runId = searchParams.get('run');
      if (runId) {
        try {
          const specific = await fetchRun(runId);
          setSelectedRun(specific ?? (data.length > 0 ? data[0] : null));
        } catch {
          if (data.length > 0) setSelectedRun(data[0]);
        }
      } else if (data.length > 0) {
        setSelectedRun(data[0]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load runs');
    } finally {
      setLoading(false);
    }
  }, [searchParams]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSelect = (run: RunRecord) => {
    setSelectedRun(run);
    navigate(`/verdict?run=${run.run_id}`, { replace: true });
  };

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Verdict History"
        description="Run grades, dimensions, and actionable findings"
      />

      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-slate-500 animate-pulse">Loading runs…</p>
        </div>
      )}

      {!loading && error && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-sm text-red-400">{error}</p>
            <button
              className="mt-3 text-xs text-slate-400 hover:text-slate-200 underline"
              onClick={load}
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {!loading && !error && runs.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-2">
            <p className="text-sm text-slate-400">No runs yet</p>
            <p className="text-xs text-slate-600 font-mono">cherenkov verify --url &lt;url&gt; --spec &lt;spec.yaml&gt;</p>
          </div>
        </div>
      )}

      {!loading && !error && runs.length > 0 && (
        <div className="flex-1 flex gap-4 overflow-hidden px-4 pb-4 pt-2">
          {/* Timeline — left 30% */}
          <div className="w-[30%] min-w-[200px] max-w-[280px] shrink-0 overflow-y-auto cherenkov-card rounded-xl px-4 py-4">
            <h2 className="text-[10px] font-semibold tracking-[0.15em] text-slate-500 uppercase mb-4">
              Run History
            </h2>
            <RunTimeline
              runs={runs}
              selectedRunId={selectedRun?.run_id ?? null}
              onSelect={handleSelect}
            />
          </div>

          {/* Card — right 70% */}
          <div className="flex-1 overflow-y-auto">
            {selectedRun ? (
              selectedRun.rich_verdict ? (
                <VerdictCard
                  verdict={selectedRun.rich_verdict}
                  targetUrl={selectedRun.target_url}
                  timestamp={selectedRun.timestamp}
                  durationMs={selectedRun.duration_ms}
                />
              ) : (
                <div className="cherenkov-card rounded-xl p-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <span className={`text-4xl font-mono font-bold ${selectedRun.verdict === 'PASS' ? 'text-cyan-400' : selectedRun.verdict === 'FAIL' ? 'text-red-400' : 'text-amber-400'}`}>
                      {selectedRun.verdict || '—'}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 space-y-1">
                    {selectedRun.target_url && <p className="font-mono text-slate-300">{selectedRun.target_url}</p>}
                    <p>{selectedRun.divergence_count} divergence{selectedRun.divergence_count !== 1 ? 's' : ''}</p>
                    {selectedRun.coverage_pct != null && <p>{selectedRun.coverage_pct.toFixed(1)}% coverage</p>}
                  </div>
                  <p className="text-[11px] text-slate-600">
                    Run this verification again with <span className="font-mono">--rich-verdict</span> to see detailed grades and findings.
                  </p>
                </div>
              )
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
