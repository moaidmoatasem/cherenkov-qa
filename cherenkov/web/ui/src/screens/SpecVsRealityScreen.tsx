import React, { useState, useEffect } from 'react';
import { SplitSquareHorizontal, CheckCircle2, XCircle, Code2, Play } from 'lucide-react';
import { fetchDivergences, actOnDivergence } from '../lib/api';
import { Divergence, StatusType } from '../types';
import { SeverityPill, StatusDot, Skeleton, EmptyState, useToast } from '../components/ui';

export default function SpecVsRealityScreen() {
  const { toast } = useToast();
  const [divergences, setDivergences] = useState<Divergence[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchDivergences()
      .then((data) => {
        if (cancelled) return;
        setDivergences(data);
        setSelectedId((prev) => prev ?? data[0]?.id ?? null);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : 'Failed to load divergences');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const selectedDiv = divergences.find((d) => d.id === selectedId) ?? null;

  async function handleAction(id: string, action: 'close_with_test' | 'mark_intended' | 'reject') {
    const previousStatus = divergences.find((d) => d.id === id)?.status;
    const targetStatus: StatusType = action === 'mark_intended' ? 'rejected' : action === 'reject' ? 'rejected' : 'live';
    setDivergences((prev) => prev.map((d) => (d.id === id ? { ...d, status: targetStatus } : d)));
    try {
      await actOnDivergence(id, action);
      toast(
        action === 'close_with_test'
          ? 'Divergence resolved by emitting a client test suite.'
          : action === 'mark_intended'
          ? 'Marked as intended behaviour.'
          : 'Divergence rejected.',
        'success'
      );
    } catch {
      toast('Action failed: unable to update divergence state.', 'danger');
      if (previousStatus) {
        setDivergences((prev) => prev.map((d) => (d.id === id ? { ...d, status: previousStatus } : d)));
      }
    }
  }

  return (
    <div className="h-full flex flex-col bg-bg-base overflow-hidden">
      <div className="shrink-0 px-6 py-5 border-b border-white/10 flex items-center justify-between bg-black/20">
        <div>
          <h1 className="text-xl font-semibold text-text-primary flex items-center gap-2">
            <SplitSquareHorizontal className="w-5 h-5 text-glow-blue" />
            Spec vs Reality
          </h1>
          <p className="text-sm text-text-muted mt-1">Live divergences between the OpenAPI spec's claims and observed runtime behavior.</p>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Drift Items */}
        <div className="w-80 border-r border-white/10 bg-black/10 overflow-y-auto flex flex-col">
          <div className="p-3 border-b border-white/10 sticky top-0 bg-black/40 backdrop-blur z-10 flex items-center justify-between">
            <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider font-mono">Detected Drift</h2>
            <span className="text-[10px] font-mono text-text-muted">{divergences.length}</span>
          </div>
          <div className="flex-1 p-2 space-y-2">
            {isLoading ? (
              <div className="space-y-2 p-1">
                <Skeleton className="h-16 w-full rounded-lg" />
                <Skeleton className="h-16 w-full rounded-lg" />
                <Skeleton className="h-16 w-full rounded-lg" />
              </div>
            ) : loadError ? (
              <div className="p-4 text-center text-xs text-amber-400 font-mono">{loadError}</div>
            ) : divergences.length === 0 ? (
              <EmptyState
                title="No divergences detected"
                description="Run `cherenkov verify` against a target to populate this view."
              />
            ) : (
              divergences.map((div) => (
                <button
                  key={div.id}
                  onClick={() => setSelectedId(div.id)}
                  className={`w-full text-left p-3 rounded-lg border transition-all duration-200 cursor-pointer ${selectedId === div.id ? 'bg-white/10 border-glow-blue shadow-[0_0_15px_rgba(34,211,238,0.15)]' : 'bg-transparent border-transparent hover:bg-white/5 hover:border-white/10'}`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <SeverityPill severity={div.severity} />
                    <span className="text-xs font-medium font-mono text-text-primary truncate">{div.endpoint}</span>
                  </div>
                  <div className="text-[11px] text-text-secondary line-clamp-1">{div.claimA}</div>
                  <div className="text-[11px] text-red-400 line-clamp-1 mt-0.5">{div.claimB}</div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right Content: The Diff */}
        <div className="flex-1 flex flex-col overflow-hidden bg-black/5">
          {!selectedDiv ? (
            <div className="flex-1 flex items-center justify-center text-text-muted text-sm">
              Select a divergence to view its spec-vs-reality breakdown.
            </div>
          ) : (
            <>
              <div className="shrink-0 p-4 border-b border-white/10 bg-black/20 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <SeverityPill severity={selectedDiv.severity} />
                  <h2 className="text-lg font-mono font-medium text-text-primary">{selectedDiv.endpoint}</h2>
                </div>
                <StatusDot status={selectedDiv.status} showLabel />
              </div>

              <div className="flex-1 flex overflow-hidden">
                {/* Spec Expectation Pane */}
                <div className="flex-1 border-r border-white/10 flex flex-col relative group">
                  <div className="shrink-0 bg-black/40 p-2 text-center border-b border-white/10">
                    <h3 className="text-sm font-semibold tracking-wide text-cyan-400 flex items-center justify-center gap-2">
                      <Code2 className="w-4 h-4" /> Spec Expectation
                    </h3>
                  </div>
                  <div className="flex-1 p-4 overflow-y-auto font-mono text-sm">
                    <div className="flex items-center gap-2 text-green-400 bg-green-400/10 px-3 py-2 rounded border border-green-400/20">
                      <CheckCircle2 className="w-4 h-4 shrink-0" /> {selectedDiv.claimA}
                    </div>
                  </div>
                </div>

                {/* Reality Pane */}
                <div className="flex-1 flex flex-col relative group bg-red-900/5">
                  <div className="shrink-0 bg-red-900/20 p-2 text-center border-b border-white/10">
                    <h3 className="text-sm font-semibold tracking-wide text-red-400 flex items-center justify-center gap-2">
                      <Play className="w-4 h-4" /> Runtime Reality
                    </h3>
                  </div>
                  <div className="flex-1 p-4 overflow-y-auto font-mono text-sm">
                    <div className="flex items-center gap-2 text-red-400 bg-red-400/10 px-3 py-2 rounded border border-red-400/20 shadow-[inset_0_0_10px_rgba(248,113,113,0.1)]">
                      <XCircle className="w-4 h-4 shrink-0" /> {selectedDiv.claimB}
                    </div>
                  </div>
                </div>
              </div>

              {/* Footer Action Bar */}
              <div className="shrink-0 p-4 bg-black/40 border-t border-white/10 flex items-center justify-between gap-4">
                <div className="text-sm text-text-secondary min-w-0">
                  <span className="font-semibold text-text-primary">Evidence:</span> {selectedDiv.evidence}
                  {selectedDiv.reproSteps && (
                    <div className="text-xs text-text-muted mt-1 font-mono truncate">Repro: {selectedDiv.reproSteps}</div>
                  )}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    onClick={() => handleAction(selectedDiv.id, 'mark_intended')}
                    className="px-4 py-1.5 rounded bg-white/10 text-white text-xs font-semibold hover:bg-white/20 transition cursor-pointer"
                  >
                    Mark Intended
                  </button>
                  <button
                    onClick={() => handleAction(selectedDiv.id, 'close_with_test')}
                    className="px-4 py-1.5 rounded bg-glow-blue text-bg-base text-xs font-bold hover:bg-cyan-300 transition shadow-[0_0_10px_rgba(34,211,238,0.5)] cursor-pointer"
                  >
                    Close with Test
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
