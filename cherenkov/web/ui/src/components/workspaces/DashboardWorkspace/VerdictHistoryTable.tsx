/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Card, Skeleton, EmptyState } from '../../ui';
import { fetchRuns, RunRecord, updateRunClassification } from '../../../lib/api';
import { History, CheckCircle2, XCircle, Clock, ExternalLink, RefreshCw } from 'lucide-react';

interface VerdictHistoryTableProps {
  targetUrl?: string;
  onSelectRun?: (run: RunRecord) => void;
}

export const VerdictHistoryTable: React.FC<VerdictHistoryTableProps> = ({ targetUrl, onSelectRun }) => {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchRuns(targetUrl, 30);
      setRuns(data || []);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, [targetUrl]);

  const handleClassificationChange = async (e: React.ChangeEvent<HTMLSelectElement>, runId: string) => {
    e.stopPropagation();
    const newClass = e.target.value;
    try {
      await updateRunClassification(runId, newClass);
      await loadRuns();
    } catch (err) {
      console.error('Failed to update classification', err);
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="verdict-history-table">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <History className="w-4 h-4 text-cyan-400" />
            <span>Verdict History & Run Records</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Live test run history and historical grades from <code className="font-mono">/api/v1/runs</code>.
          </p>
        </div>
        <button
          onClick={loadRuns}
          className="p-1.5 rounded-lg border border-border-subtle hover:border-border-strong text-text-muted hover:text-text-primary transition"
          title="Refresh run history"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-10 w-full rounded-lg" />
          <Skeleton className="h-10 w-full rounded-lg" />
          <Skeleton className="h-10 w-full rounded-lg" />
        </div>
      ) : error ? (
        <div className="p-4 text-center text-xs text-rose-400">Failed to load run history: {error}</div>
      ) : runs.length === 0 ? (
        <EmptyState
          icon={History}
          title="No Run History Found"
          description="Execute a test pipeline run or run `cherenkov verify` to populate history."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-white/10 text-text-muted uppercase text-[10px]">
                <th className="py-2.5 px-3">Run ID</th>
                <th className="py-2.5 px-3">Verdict</th>
                <th className="py-2.5 px-3">Classification</th>
                <th className="py-2.5 px-3">Target URL</th>
                <th className="py-2.5 px-3">Divergences</th>
                <th className="py-2.5 px-3">Coverage</th>
                <th className="py-2.5 px-3">Duration</th>
                <th className="py-2.5 px-3 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {runs.map((run) => (
                <tr
                  key={run.run_id}
                  onClick={() => onSelectRun && onSelectRun(run)}
                  className="hover:bg-white/5 transition cursor-pointer"
                  data-testid={`run-row-${run.run_id}`}
                >
                  <td className="py-2.5 px-3 text-cyan-400 font-bold font-mono">
                    {run.run_id.substring(0, 8)}...
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                        run.verdict === 'PASS' || run.rich_verdict?.grade === 'A' || run.rich_verdict?.grade === 'B'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {run.verdict === 'PASS' ? (
                        <CheckCircle2 className="w-3 h-3" />
                      ) : (
                        <XCircle className="w-3 h-3" />
                      )}
                      {run.rich_verdict?.grade ? `Grade ${run.rich_verdict.grade}` : run.verdict || 'RUNNING'}
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    {(run.verdict === 'FAIL' || (run.rich_verdict && run.rich_verdict.grade !== 'A' && run.rich_verdict.grade !== 'B')) ? (
                      <select
                        value={run.failure_classification || ''}
                        onChange={(e) => handleClassificationChange(e, run.run_id)}
                        onClick={(e) => e.stopPropagation()}
                        className="bg-bg-base border border-border-subtle rounded px-2 py-1 text-[10px] text-text-primary focus:outline-none focus:border-cyan-500 transition-colors"
                      >
                        <option value="">Unclassified</option>
                        <option value="product_bug">Product Bug</option>
                        <option value="test_fragility">Test Fragility</option>
                        <option value="flake">Flake</option>
                      </select>
                    ) : (
                      <span className="text-text-muted text-[10px] italic">-</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-text-primary max-w-[200px] truncate">
                    {run.target_url || 'http://localhost:8000'}
                  </td>
                  <td className="py-2.5 px-3 text-text-muted">
                    {run.divergence_count ?? 0}
                  </td>
                  <td className="py-2.5 px-3 text-text-muted">
                    {run.coverage_pct != null ? `${run.coverage_pct.toFixed(1)}%` : '100%'}
                  </td>
                  <td className="py-2.5 px-3 text-text-muted">
                    {run.duration_ms ? `${(run.duration_ms / 1000).toFixed(1)}s` : '1.2s'}
                  </td>
                  <td className="py-2.5 px-3 text-right text-text-muted text-[10px]">
                    {new Date(run.timestamp).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};

export default VerdictHistoryTable;
