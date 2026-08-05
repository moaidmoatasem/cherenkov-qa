/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState, useMemo } from 'react';
import { ShieldCheck, ShieldAlert, ShieldX, Activity } from 'lucide-react';
import { fetchSignals, fetchMetricsData, fetchTruthMapData, fetchDivergences } from '../../../lib/api';
import { Card, Skeleton } from '../../ui';
import type { Divergence } from '../../../types';

export interface EndpointIntegrity {
  id: string;
  path: string;
  method: string;
  integrityScore: number;
  driftCount: number;
  severity?: Divergence['severity'];
}

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
        const divergences = await fetchDivergences().catch(() => [] as Divergence[]);

        if (divergences && divergences.length > 0) {
          // Group divergences by endpoint and compute real integrity scores from severity
          const endpointMap = new Map<string, { method: string; path: string; severities: Divergence['severity'][] }>();
          
          for (const div of divergences) {
            const [method, ...pathParts] = div.endpoint.split(' ');
            const path = pathParts.join(' ') || div.endpoint;
            const key = `${method}:${path}`;
            
            if (!endpointMap.has(key)) {
              endpointMap.set(key, { method, path, severities: [] });
            }
            endpointMap.get(key)!.severities.push(div.severity);
          }

          // Compute integrity score based on severity deductions
          const SEVERITY_DEDUCTION: Record<Divergence['severity'], number> = {
            critical: 57,
            high: 37,
            medium: 20,
            low: 10,
            info: 5,
          };

          const mapped: EndpointIntegrity[] = Array.from(endpointMap.values()).map((ep, i) => {
            const totalDeduction = ep.severities.reduce((sum, sev) => sum + SEVERITY_DEDUCTION[sev], 0);
            const integrityScore = Math.max(0, 100 - totalDeduction);
            return {
              id: `ep-${i}`,
              method: ep.method,
              path: ep.path,
              integrityScore,
              driftCount: ep.severities.length,
              severity: ep.severities[0],
            };
          });
          setEndpoints(mapped);
        } else {
          // No divergences = all endpoints at 100% integrity
          const truthMap = await fetchTruthMapData().catch(() => []);
          if (truthMap && truthMap.length > 0) {
            const mapped: EndpointIntegrity[] = truthMap.map((node, i) => {
              const [method, ...pathParts] = node.endpoint.split(' ');
              const path = pathParts.join(' ') || node.endpoint;
              return {
                id: `ep-${i}`,
                method: method || 'GET',
                path: path || node.endpoint,
                integrityScore: 100,
                driftCount: 0,
              };
            });
            setEndpoints(mapped);
          } else {
            setEndpoints([]);
          }
        }
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
