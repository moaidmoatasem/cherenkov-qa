import React, { useState, useEffect, useMemo } from 'react';
import { Terminal } from 'lucide-react';
import { PageHeader, Card, Skeleton, EmptyState } from '../components/ui';
import IntegrityHeatmap from '../components/IntegrityHeatmap';
import { fetchDivergences } from '../lib/api';
import { Divergence, SeverityType } from '../types';

const SEVERITY_PENALTY: Record<SeverityType, number> = {
  critical: 40,
  high: 25,
  medium: 12,
  low: 5,
  info: 2,
};

interface EndpointIntegrity {
  id: string;
  path: string;
  method: string;
  integrityScore: number;
  driftCount: number;
}

function deriveEndpointIntegrity(divergences: Divergence[]): EndpointIntegrity[] {
  const byEndpoint = new Map<string, Divergence[]>();
  for (const d of divergences) {
    const list = byEndpoint.get(d.endpoint) ?? [];
    list.push(d);
    byEndpoint.set(d.endpoint, list);
  }

  return Array.from(byEndpoint.entries()).map(([endpoint, divs]) => {
    const [method, ...pathParts] = endpoint.split(' ');
    const path = pathParts.length > 0 ? pathParts.join(' ') : endpoint;
    const penalty = divs.reduce((sum, d) => sum + (SEVERITY_PENALTY[d.severity] ?? 10), 0);
    return {
      id: endpoint,
      path,
      method: pathParts.length > 0 ? method : 'API',
      integrityScore: Math.max(0, 100 - penalty),
      driftCount: divs.length,
    };
  });
}

export default function CoverageScreen() {
  const [divergences, setDivergences] = useState<Divergence[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchDivergences()
      .then((data) => {
        if (!cancelled) setDivergences(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : 'Failed to load divergences');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const endpoints = useMemo(() => deriveEndpointIntegrity(divergences), [divergences]);

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10">
      <PageHeader
        title="Coverage & Certification"
        description="Per-endpoint integrity, derived from live divergence data, and how to issue a signed certificate."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Main Coverage Heatmap (Spans 2 columns) */}
        <div className="lg:col-span-2 space-y-3">
          {isLoading ? (
            <Skeleton className="h-64 w-full rounded-lg" />
          ) : loadError ? (
            <div className="p-4 text-center text-xs text-amber-400 font-mono">{loadError}</div>
          ) : endpoints.length === 0 ? (
            <EmptyState
              title="No drift recorded yet"
              description="Run `cherenkov verify` against a target to populate this heatmap."
            />
          ) : (
            <>
              <IntegrityHeatmap endpoints={endpoints} />
              <p className="text-[11px] text-text-muted font-mono px-1">
                Scores are derived client-side from live divergence severity/count (`/api/v1/divergences`) —
                only endpoints with at least one recorded finding appear here, this is not a full endpoint inventory.
              </p>
            </>
          )}
        </div>

        {/* Right side: Certification */}
        <Card className="p-6 flex flex-col h-full">
          <div className="flex items-center gap-2 mb-4">
            <Terminal className="w-5 h-5 text-glow-blue" />
            <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-primary">
              Issue a Certificate
            </h2>
          </div>
          <p className="text-xs text-text-muted mb-4">
            Signed cryptographic proof of API integrity. There's no dashboard-side certificate store yet — this
            is a CLI-issued artifact today, not something this screen fabricates a history for.
          </p>
          <pre className="text-[11px] font-mono bg-black/30 border border-white/10 rounded-lg p-3 text-[#a5d6ff] overflow-x-auto">
            cherenkov certify \{'\n'}  --url &lt;target&gt; \{'\n'}  --output cert.json
          </pre>
          <p className="text-[11px] text-text-muted mt-3">
            Add <code className="text-glow-bright">--fail-on-fail</code> to gate CI on the verdict, or{' '}
            <code className="text-glow-bright">--verify cert.json</code> to re-check a previously issued certificate.
          </p>
        </Card>
      </div>
    </div>
  );
}
