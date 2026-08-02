/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Card, Skeleton, SeverityPill } from '../../ui';
import { fetchDivergences, actOnDivergence } from '../../../lib/api';
import { Divergence } from '../../../types';
import { SplitSquareHorizontal, CheckCircle2, XCircle, Code2, Play, RefreshCw } from 'lucide-react';

interface SpecVsRealityDiffViewerProps {
  divergenceId?: string;
}

export const SpecVsRealityDiffViewer: React.FC<SpecVsRealityDiffViewerProps> = ({ divergenceId }) => {
  const [divergences, setDivergences] = useState<Divergence[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(divergenceId || null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchDivergences();
      setDivergences(data || []);
      if (data && data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const selectedDiv = divergences.find((d) => d.id === selectedId) || divergences[0];

  const handleAction = async (id: string, action: 'close_with_test' | 'mark_intended' | 'reject') => {
    try {
      await actOnDivergence(id, action);
      setDivergences((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="spec-vs-reality-diff-viewer">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <SplitSquareHorizontal className="w-4 h-4 text-cyan-400" />
            <span>Spec vs Reality Payload Comparison</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Side-by-side spec claim vs live server runtime payload comparison.
          </p>
        </div>
        <button
          onClick={loadData}
          className="p-1.5 rounded-lg border border-border-subtle hover:border-border-strong text-text-muted hover:text-text-primary transition"
          title="Refresh Diffs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : error ? (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400">
          Failed to load diffs: {error}
        </div>
      ) : !selectedDiv ? (
        <div className="p-6 text-center text-xs text-text-muted font-mono">
          No divergence payload diffs to display.
        </div>
      ) : (
        <div className="space-y-4 font-mono text-xs">
          {/* Header */}
          <div className="p-3 rounded-xl bg-black/30 border border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <SeverityPill severity={selectedDiv.severity} />
              <span className="font-bold text-text-primary text-sm">{selectedDiv.endpoint}</span>
              <span className="text-[10px] text-cyan-400">{selectedDiv.divergenceClass}</span>
            </div>
            <span className="text-[10px] text-text-muted">Divergence ID: {selectedDiv.id}</span>
          </div>

          {/* Side-by-Side Diff Panes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Spec Claim Pane */}
            <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 space-y-2">
              <div className="flex items-center gap-2 text-emerald-400 font-bold uppercase text-[10px]">
                <Code2 className="w-4 h-4" />
                <span>OpenAPI Spec Claim (Expectation)</span>
              </div>
              <div className="p-3 bg-black/40 rounded-lg text-emerald-300 leading-relaxed border border-emerald-500/10">
                <p className="font-bold text-xs">{selectedDiv.claimA}</p>
              </div>
            </div>

            {/* Server Reality Pane */}
            <div className="p-4 rounded-xl bg-rose-500/5 border border-rose-500/20 space-y-2">
              <div className="flex items-center gap-2 text-rose-400 font-bold uppercase text-[10px]">
                <Play className="w-4 h-4" />
                <span>Runtime Server Reality (Observed)</span>
              </div>
              <div className="p-3 bg-black/40 rounded-lg text-rose-300 leading-relaxed border border-rose-500/10">
                <p className="font-bold text-xs">{selectedDiv.claimB}</p>
              </div>
            </div>
          </div>

          {/* Evidence Footer */}
          <div className="p-3 rounded-xl bg-black/20 border border-white/5 flex items-center justify-between text-xs">
            <div className="max-w-[70%]">
              <span className="text-text-muted font-bold">Evidence: </span>
              <span className="text-text-primary">{selectedDiv.evidence}</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleAction(selectedDiv.id, 'mark_intended')}
                className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold"
              >
                Mark Intended
              </button>
              <button
                onClick={() => handleAction(selectedDiv.id, 'close_with_test')}
                className="px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-bold"
              >
                Accept & Update
              </button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};

export default SpecVsRealityDiffViewer;
