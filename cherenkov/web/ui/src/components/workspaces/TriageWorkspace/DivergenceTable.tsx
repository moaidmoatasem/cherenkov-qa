/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Card, Skeleton, EmptyState, useToast } from '../../ui';
import { fetchDivergences, actOnDivergence } from '../../../lib/api';
import { Divergence } from '../../../types';
import { Zap, AlertTriangle, CheckCircle2, XCircle, ShieldAlert, RefreshCw } from 'lucide-react';

interface DivergenceTableProps {
  onSelectDivergence?: (divergence: Divergence) => void;
  /** Row to emphasize when deep-linked via ?divergence=<id> (N-3). */
  highlightId?: string;
}

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

  return (
    <Card className="p-6 space-y-4" data-testid="divergence-table">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            <span>Risk-Scored Divergence Triage Table</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            API contract drift reports from <code className="font-mono">/api/v1/divergences</code>.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-bg-base border border-border-subtle rounded-lg px-2 py-1 text-xs font-mono text-cyan-400"
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
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-white/10 text-text-muted uppercase text-[10px]">
                <th className="py-2.5 px-3">Class</th>
                <th className="py-2.5 px-3">Endpoint</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Spec Claim (A)</th>
                <th className="py-2.5 px-3">Server Reality (B)</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredDivergences.map((div) => {
                const isHighlighted = highlightId != null && div.id === highlightId;
                return (
                  <tr
                    key={div.id}
                    ref={isHighlighted ? (el) => el?.scrollIntoView({ block: 'nearest' }) : undefined}
                    onClick={() => onSelectDivergence && onSelectDivergence(div)}
                    className={`transition cursor-pointer ${
                      isHighlighted
                        ? 'bg-cyan-500/10 ring-1 ring-cyan-500/40 hover:bg-cyan-500/15'
                        : 'hover:bg-white/5'
                    }`}
                    data-testid={`divergence-row-${div.id}`}
                    data-highlighted={isHighlighted || undefined}
                  >
                    <td className="py-2.5 px-3 font-bold text-cyan-400">{div.divergenceClass}</td>
                    <td className="py-2.5 px-3 font-semibold text-text-primary">{div.endpoint}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          div.severity === 'critical' || div.severity === 'high'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}
                      >
                        {div.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-text-muted max-w-[200px] truncate">{div.claimA}</td>
                    <td className="py-2.5 px-3 text-rose-300 max-w-[200px] truncate">{div.claimB}</td>
                    <td className="py-2.5 px-3 text-right space-x-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAction(div.id, 'mark_intended');
                        }}
                        className="px-2 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px]"
                        title="Mark as intended change"
                      >
                        Intended
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAction(div.id, 'close_with_test');
                        }}
                        className="px-2 py-1 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-[10px]"
                        title="Close & update test"
                      >
                        Fix Test
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};

export default DivergenceTable;
