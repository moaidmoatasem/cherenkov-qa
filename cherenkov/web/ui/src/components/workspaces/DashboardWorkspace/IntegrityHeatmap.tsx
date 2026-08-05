/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState, useMemo } from 'react';
import { ShieldCheck, ShieldAlert, ShieldX, Activity, ShieldQuestion } from 'lucide-react';
import { fetchTruthMapData, fetchDivergences } from '../../../lib/api';
import { Card, Skeleton, EmptyState } from '../../ui';

export interface EndpointIntegrity {
  id: string;
  path: string;
  method: string;
  integrityScore: number;
  driftCount: number;
  severity?: Divergence['severity'];
}

// Severity -> points deducted from a 98-point baseline. Mirrors the same
// severity vocabulary the backend divergence corpus uses (see
// cherenkov/web/divergences.py), so this reads real audit findings rather
// than a hardcoded score.
const SEVERITY_PENALTY: Record<string, number> = {
  critical: 55,
  high: 35,
  medium: 18,
  low: 8,
};

export const IntegrityHeatmap: React.FC<{ endpoints?: EndpointIntegrity[] }> = ({ endpoints: initialEndpoints }) => {
  const [endpoints, setEndpoints] = useState<EndpointIntegrity[]>(initialEndpoints || []);
  const [isLoading, setIsLoading] = useState(!initialEndpoints || initialEndpoints.length === 0);

  useEffect(() => {
    if (initialEndpoints && initialEndpoints.length > 0) {
      setEndpoints(initialEndpoints);
      setIsLoading(false);
      return;
    }

    const loadLiveIntegrity = async () => {
      try {
        setIsLoading(true);
        const [truthMap, divergences] = await Promise.all([
          fetchTruthMapData().catch(() => []),
          fetchDivergences().catch(() => []),
        ]);

        // Only count divergences that are still an open finding -- a
        // rejected/false-positive divergence shouldn't drag the score down.
        const activeDivergences = (divergences || []).filter((d) => d.status !== 'rejected');

        const knownEndpoints = new Set<string>([
          ...(truthMap || []).map((n) => n.endpoint),
          ...activeDivergences.map((d) => d.endpoint),
        ]);

        const mapped: EndpointIntegrity[] = Array.from(knownEndpoints).map((endpoint, i) => {
          const [method, ...pathParts] = endpoint.split(' ');
          const path = pathParts.join(' ') || endpoint;
          const matches = activeDivergences.filter((d) => d.endpoint === endpoint);
          const penalty = matches.reduce((sum, d) => sum + (SEVERITY_PENALTY[d.severity] || 10), 0);
          const integrityScore = Math.max(5, 98 - penalty);
          return {
            id: `ep-${i}`,
            method: method || 'GET',
            path,
            integrityScore,
            driftCount: matches.length,
          };
        });

        setEndpoints(mapped);
      } catch {
        setEndpoints([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadLiveIntegrity();
  }, [initialEndpoints]);

  const getIntegrityColor = (score: number) => {
    if (score >= 90) return 'bg-[#3FB950]/20 border-[#3FB950]/50 text-emerald-400';
    if (score >= 60) return 'bg-amber-500/20 border-amber-500/50 text-amber-400';
    return 'bg-rose-500/20 border-rose-500/50 text-rose-400';
  };

  const getIcon = (score: number) => {
    if (score >= 90) return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
    if (score >= 60) return <ShieldAlert className="w-4 h-4 text-amber-400" />;
    return <ShieldX className="w-4 h-4 text-rose-400" />;
  };

  const sortedEndpoints = useMemo(() => {
    return [...endpoints].sort((a, b) => a.integrityScore - b.integrityScore);
  }, [endpoints]);

  return (
    <Card className="p-6 space-y-4" data-testid="integrity-heatmap">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span>Integrity & Risk Heatmap</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Spec coverage and risk signals from live API endpoints.
          </p>
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono text-text-muted">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[#3FB950]" /> &ge;90%
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" /> 60-89%
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-500" /> &lt;60%
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
        </div>
      ) : sortedEndpoints.length === 0 ? (
        <EmptyState
          icon={ShieldQuestion}
          title="No integrity signal yet"
          description="Run a generation and validate against your API to see per-endpoint drift and risk here."
        />
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {sortedEndpoints.map((ep) => (
            <div
              key={ep.id}
              className={`group relative flex flex-col p-3 rounded-lg border transition-all duration-200 hover:scale-105 cursor-pointer shadow-md ${getIntegrityColor(ep.integrityScore)}`}
            >
              <div className="flex items-start justify-between mb-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider bg-black/40 px-1.5 py-0.5 rounded text-text-primary">
                  {ep.method}
                </span>
                {getIcon(ep.integrityScore)}
              </div>
              <div className="text-xs font-medium font-mono truncate text-text-primary" title={ep.path}>
                {ep.path}
              </div>
              <div className="mt-2 text-2xl font-bold font-mono tracking-tight">
                {ep.integrityScore}%
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

export default IntegrityHeatmap;
