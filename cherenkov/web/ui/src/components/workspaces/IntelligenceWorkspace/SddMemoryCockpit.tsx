/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Card, Skeleton, KpiRing } from '../../ui';
import { fetchSddStatus, fetchSddTokens, triggerSddCompact } from '../../../lib/api';
import { SddStatusResponse, SddTokenData } from '../../../types';
import { Cpu, RefreshCw, Layers } from 'lucide-react';

export const SddMemoryCockpit: React.FC = () => {
  const [status, setStatus] = useState<SddStatusResponse | null>(null);
  const [tokens, setTokens] = useState<SddTokenData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadSddData = async () => {
    try {
      setIsLoading(true);
      const [sData, tData] = await Promise.all([
        fetchSddStatus().catch(() => null),
        fetchSddTokens().catch(() => null),
      ]);
      setStatus(sData);
      setTokens(tData);
    } catch {
      setStatus(null);
      setTokens(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSddData();
  }, []);

  const handleCompact = async () => {
    await triggerSddCompact(true);
    loadSddData();
  };

  const tok = tokens?.current_session;
  const budget = tokens?.budget as Record<string, unknown> | undefined;
  const perSessionBudget = (budget?.per_session as number) || 50000;
  const pct = tok?.total ? Math.round((tok.total / perSessionBudget) * 100) : 15;
  const tokenGlowColor: 'danger' | 'warning' | 'success' = pct > 80 ? 'danger' : pct > 60 ? 'warning' : 'success';

  return (
    <Card className="p-6 space-y-4" data-testid="sdd-memory-cockpit">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span>SDD Agent Cockpit & Memory Budget</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Token pool metrics and memory retention from <code className="font-mono">/api/v1/sdd/status</code>.
          </p>
        </div>
        <button
          onClick={handleCompact}
          className="px-3 py-1 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-lg text-xs font-mono font-bold hover:bg-cyan-500/30 transition"
        >
          Compact Memory
        </button>
      </div>

      {isLoading ? (
        <Skeleton className="h-28 w-full rounded-xl" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex items-center gap-3">
            <KpiRing value={pct} title="Budget" size={64} strokeWidth={6} glowColor={tokenGlowColor} />
            <div>
              <p className="text-[10px] font-mono uppercase text-text-muted">Token Budget</p>
              <p className="text-lg font-bold font-mono text-text-primary mt-0.5">{pct}% Used</p>
              <p className="text-[10px] text-text-muted">Max {perSessionBudget.toLocaleString()}</p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex flex-col justify-between">
            <p className="text-[10px] font-mono uppercase text-text-muted">Total All Time</p>
            <p className="text-xl font-bold font-mono text-cyan-400 mt-1">
              {(status?.historical?.total_all_time || 0).toLocaleString()}
            </p>
            <p className="text-[10px] text-text-muted">across all sessions</p>
          </div>

          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex flex-col justify-between">
            <p className="text-[10px] font-mono uppercase text-text-muted">Experience Records</p>
            <p className="text-xl font-bold font-mono text-emerald-400 mt-1">
              {status?.experience_count || 0}
            </p>
            <p className="text-[10px] text-text-muted">compounded learnings</p>
          </div>

          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex flex-col justify-between">
            <p className="text-[10px] font-mono uppercase text-text-muted">Session State</p>
            <p className="text-xl font-bold font-mono text-amber-400 mt-1">
              {status?.session?.status === 'open' ? 'ACTIVE' : 'READY'}
            </p>
            <p className="text-[10px] text-text-muted">SDD Protocol v3.1</p>
          </div>
        </div>
      )}
    </Card>
  );
};

export default SddMemoryCockpit;
