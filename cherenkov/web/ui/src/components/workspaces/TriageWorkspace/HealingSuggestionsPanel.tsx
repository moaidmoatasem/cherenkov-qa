/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, Skeleton, EmptyState, useToast } from '../../ui';
import { fetchFailuresData, fetchHealingSuggestion, HealingSuggestion } from '../../../lib/api';
import { FailingTest } from '../../../types';
import { HeartPulse, ShieldCheck, RefreshCw } from 'lucide-react';

interface FailureRow extends FailingTest {
  endpoint?: string | null;
  outcome?: string;
  timestamp?: string;
}

const FAILURE_CLASS_COLORS: Record<string, string> = {
  AUTH_EXPIRY: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
  CONTRACT_DRIFT: 'bg-rose-500/10 text-rose-400 border border-rose-500/20',
  STATE_SEQUENCING: 'bg-violet-500/10 text-violet-400 border border-violet-500/20',
  NETWORK_FLAKY: 'bg-sky-500/10 text-sky-400 border border-sky-500/20',
  ASSERTION_DRIFT: 'bg-orange-500/10 text-orange-400 border border-orange-500/20',
};

export const HealingSuggestionsPanel: React.FC = () => {
  const [selected, setSelected] = useState<HealingSuggestion | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const { toast } = useToast();

  const { data: failures = [], isLoading, error, refetch, isFetching } = useQuery<FailureRow[]>({
    queryKey: ['failures'],
    queryFn: fetchFailuresData,
  });

  const handleSuggestion = async (failure: FailureRow) => {
    setLoadingId(failure.id);
    try {
      const suggestion = await fetchHealingSuggestion(failure.id);
      setSelected(suggestion);
      toast(`Healing suggestion generated for ${suggestion.endpoint || suggestion.verdict_id}`, 'success');
    } catch (err) {
      toast(`Suggestion failed: ${(err as Error).message}`, 'danger');
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="healing-suggestions-panel">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <HeartPulse className="w-4 h-4 text-emerald-400" />
            <span>Suggest-Only Healing</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            What failed, and what Cherenkov suggests you change. It never edits
            your code — you apply the fix.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="p-1.5 rounded-lg border border-border-subtle hover:border-border-strong text-text-muted hover:text-text-primary transition"
          title="Refresh Failures"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
        </div>
      ) : error ? (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400">
          Failed to load failures: {(error as Error)?.message}
        </div>
      ) : failures.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="No Recent Failures"
          description="No rejected or escaped-defect verdicts recorded. Nothing to heal."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-white/10 text-text-muted uppercase text-[10px]">
                <th className="py-2.5 px-3">Failure Class</th>
                <th className="py-2.5 px-3">Endpoint</th>
                <th className="py-2.5 px-3">Diagnosis</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {failures.map((failure) => (
                <tr key={failure.id} className="hover:bg-white/5 transition" data-testid={`failure-row-${failure.id}`}>
                  <td className="py-2.5 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        FAILURE_CLASS_COLORS[failure.failureType] ?? FAILURE_CLASS_COLORS.ASSERTION_DRIFT
                      }`}
                    >
                      {failure.failureType}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-text-primary">
                    {failure.endpoint || failure.name}
                  </td>
                  <td className="py-2.5 px-3 text-text-muted max-w-[26rem] truncate">{failure.diagnosis}</td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => handleSuggestion(failure)}
                      disabled={loadingId === failure.id}
                      className="px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-bold uppercase tracking-wider hover:bg-emerald-500/20 disabled:opacity-50 transition"
                    >
                      {loadingId === failure.id ? 'Generating…' : 'Get Suggestion'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div className="mt-4 space-y-2" data-testid="healing-suggestion-result">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold font-mono uppercase tracking-wider text-text-muted">
              Suggestion for <span className="text-emerald-400">{selected.endpoint || selected.verdict_id}</span>
              <span className="ml-2 text-[10px] text-text-muted">via {selected.healer}</span>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {selected.healed ? 'applied' : 'suggest-only'}
            </span>
          </div>
          {selected.note && (
            <p className="text-xs text-amber-400/90 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
              {selected.note}
            </p>
          )}
          <pre className="text-xs font-mono text-text-primary bg-bg-base border border-border-subtle rounded-xl p-4 overflow-x-auto whitespace-pre-wrap">
            {selected.suggestion}
          </pre>
        </div>
      )}

      <p className="text-[11px] text-text-muted border-t border-white/5 pt-3">
        Healing is suggest-only: nothing is auto-applied and no test file is edited. Direct auto-apply
        (<code className="font-mono">/review/edit</code>) is not wired in this build.
      </p>
    </Card>
  );
};

export default HealingSuggestionsPanel;
