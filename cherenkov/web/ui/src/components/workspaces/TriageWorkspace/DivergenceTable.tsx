/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { List } from 'react-window';
import { Card, Skeleton, EmptyState, useToast } from '../../ui';
import { fetchDivergences, actOnDivergence } from '../../../lib/api';
import { Divergence } from '../../../types';
import { Zap, AlertTriangle, CheckCircle2, ShieldAlert, RefreshCw } from 'lucide-react';

interface DivergenceTableProps {
  onSelectDivergence?: (divergence: Divergence) => void;
  /** Row to emphasize when deep-linked via ?divergence=<id> (N-3). */
  highlightId?: string;
}

const ROW_HEIGHT = 64;
const LIST_HEIGHT = 440;

function confidenceBadge(confidence?: number) {
  if (confidence == null) return null;
  const pct = Math.round(confidence * 100);
  const tone =
    confidence >= 0.9
      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
      : confidence >= 0.75
      ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
      : 'bg-rose-500/10 text-rose-400 border-rose-500/30';
  return (
    <span
      className={`px-2 py-0.5 rounded text-[10px] font-bold border ${tone}`}
      title={`Reproduction stability: reproduced with ${pct}% confidence across runs`}
    >
      {pct}%
    </span>
  );
}

type DivergenceRowProps = {
  divergences: Divergence[];
  hasConfidence?: boolean;
  highlightId?: string;
  onSelectDivergence?: (divergence: Divergence) => void;
  onAction?: (id: string, action: 'close_with_test' | 'mark_intended' | 'reject') => void;
};

// J2: row component used by the virtualized List. Rows are only mounted when
// they enter the window, so 500+ finding tables stay cheap.
const DivergenceRow = ({
  index,
  style,
  ariaAttributes,
  divergences,
  hasConfidence,
  highlightId,
  onSelectDivergence,
  onAction,
}: {
  ariaAttributes: { 'aria-posinset': number; 'aria-setsize': number; role: 'listitem' };
  index: number;
  style: React.CSSProperties;
} & DivergenceRowProps): React.ReactElement => {
  const div = divergences[index];
  if (!div) return null;
  const isHighlighted = highlightId != null && div.id === highlightId;
  return (
    <div
      style={style}
      role={ariaAttributes.role}
      aria-posinset={ariaAttributes['aria-posinset']}
      aria-setsize={ariaAttributes['aria-setsize']}
      ref={isHighlighted ? (el) => el?.scrollIntoView({ block: 'nearest' }) : undefined}
      onClick={() => onSelectDivergence && onSelectDivergence(div)}
      className={`flex items-center gap-3 px-3 border-b border-white/5 transition cursor-pointer ${
        isHighlighted ? 'bg-cyan-500/10 hover:bg-cyan-500/15' : 'hover:bg-white/5'
      }`}
      data-testid={`divergence-row-${div.id}`}
      data-highlighted={isHighlighted || undefined}
      title={div.reproSteps ? `Repro: ${div.reproSteps}` : undefined}
    >
      <span className="w-14 shrink-0 font-bold text-cyan-400">{div.divergenceClass}</span>
      <span className="w-44 shrink-0 min-w-0 truncate font-semibold text-text-primary">{div.endpoint}</span>
      <span
        className={`w-20 shrink-0 px-2 py-0.5 rounded text-[10px] font-bold uppercase text-center ${
          div.severity === 'critical' || div.severity === 'high'
            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
        }`}
      >
        {div.severity}
      </span>
      {hasConfidence && (
        <span className="w-16 shrink-0 flex justify-center">{confidenceBadge(div.confidence)}</span>
      )}
      <span className="flex-[3] min-w-0 line-clamp-2 leading-snug text-text-muted" title={div.claimA}>{div.claimA}</span>
      <span className="flex-[3] min-w-0 line-clamp-2 leading-snug text-rose-300" title={div.claimB}>{div.claimB}</span>
      <span className="shrink-0 flex items-center gap-1.5">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onAction && onAction(div.id, 'mark_intended');
          }}
          className="px-2 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px]"
          title="This difference is deliberate — stop flagging it"
        >
          Expected
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onAction && onAction(div.id, 'close_with_test');
          }}
          className="px-2 py-1 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-[10px]"
          title="Close & update test"
        >
          Fix Test
        </button>
      </span>
    </div>
  );
};

export const DivergenceTable: React.FC<DivergenceTableProps> = ({ onSelectDivergence, highlightId }) => {
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: divergences = [], isLoading, isFetching, error, refetch } = useQuery<Divergence[]>({
    queryKey: ['divergences'],
    queryFn: fetchDivergences,
  });

  const handleAction = async (divergenceId: string, action: 'close_with_test' | 'mark_intended' | 'reject') => {
    try {
      await actOnDivergence(divergenceId, action);
      const label = action === 'mark_intended' ? 'marked as intended' : 'closed with test';
      toast(`Divergence ${divergenceId} ${label}`, 'success');
      queryClient.invalidateQueries({ queryKey: ['divergences'] });
    } catch (err) {
      toast(`Action failed: ${(err as Error).message}`, 'danger');
    }
  };

  const filteredDivergences = useMemo(() => {
    if (severityFilter === 'all') return divergences;
    return divergences.filter((d) => d.severity === severityFilter);
  }, [divergences, severityFilter]);

  const hasConfidence = useMemo(
    () => divergences.some((d) => d.confidence != null),
    [divergences]
  );

  const visibleHeight = Math.min(LIST_HEIGHT, filteredDivergences.length * ROW_HEIGHT);

  return (
    <Card className="p-6 space-y-4" data-testid="divergence-table">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            <span>Risk-Scored Divergence Triage Table</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Where your live API disagrees with its spec
            {hasConfidence ? ' with reproduction-stability confidence' : ''}.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            aria-label="Filter divergences by severity"
            className="bg-bg-base border border-border-subtle rounded-lg px-2 py-1 text-xs font-mono text-cyan-400"
            data-testid="divergence-severity-filter"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-lg border border-border-subtle hover:border-border-strong text-text-muted hover:text-text-primary transition"
            title="Refresh Divergences"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
        </div>
      ) : error ? (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400">
          Failed to load divergences: {(error as Error)?.message}
        </div>
      ) : filteredDivergences.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="No Open Divergences"
          description="All endpoints conform to spec claims. Code is clean to ship."
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-white/5">
          {/* Fixed header row -- stays put while the body virtualizes. */}
          <div className="flex items-center gap-3 px-3 py-2.5 bg-black/30 border-b border-white/10 text-text-muted uppercase text-[10px] font-mono">
            <span className="w-14 shrink-0">Class</span>
            <span className="w-44 shrink-0 min-w-0 truncate">Endpoint</span>
            <span className="w-20 shrink-0">Severity</span>
            {hasConfidence && <span className="w-16 shrink-0">Confidence</span>}
            <span className="flex-[3] min-w-0 truncate">Spec Claim (A)</span>
            <span className="flex-[3] min-w-0 truncate">Server Reality (B)</span>
            <span className="shrink-0">Actions</span>
          </div>

          <List
            rowComponent={DivergenceRow}
            rowCount={filteredDivergences.length}
            rowHeight={ROW_HEIGHT}
            overscanCount={8}
            defaultHeight={visibleHeight}
            style={{ height: visibleHeight }}
            rowProps={{
              divergences: filteredDivergences,
              hasConfidence,
              highlightId,
              onSelectDivergence,
              onAction: handleAction,
            }}
          />

          {filteredDivergences.length > LIST_HEIGHT / ROW_HEIGHT && (
            <p className="px-3 py-2 text-[10px] font-mono text-text-muted border-t border-white/5">
              Virtualized list — {filteredDivergences.length} findings rendered on demand for large result sets.
            </p>
          )}
        </div>
      )}
    </Card>
  );
};

export default DivergenceTable;
