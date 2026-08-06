/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link2, AlertTriangle, ArrowRight } from 'lucide-react';
import { Card, EmptyState, Skeleton } from '../../ui';
import { fetchDetectedChains } from '../../../lib/api';
import { useJourney } from '../../../journey/config';
import type { DetectedChain } from '../../../journey/types';

interface DetectedChainsPanelProps {
  specPath: string;
}

const METHOD_COLORS: Record<string, string> = {
  POST: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
  GET: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10',
  PUT: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
  PATCH: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
  DELETE: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
};

/** How the chain was found, in the user's terms rather than ours. */
const EVIDENCE_LABEL: Record<string, string> = {
  links: 'the spec declares this relationship',
  path_family: 'matching collection and item paths',
  schema_ref: 'both operations return the same schema',
};

function ChainCard({ chain }: { chain: DetectedChain }) {
  return (
    <div className="rounded-xl border border-border-subtle bg-bg-surface/60 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-mono text-xs font-bold text-text-primary">
            {chain.label}
          </h4>
          <p className="text-[10px] text-text-muted mt-0.5">
            Detected by {EVIDENCE_LABEL[chain.detected_by] ?? chain.detected_by} ·{' '}
            {Math.round(chain.confidence * 100)}% confidence
          </p>
        </div>
        {chain.mutating && (
          <span
            className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 shrink-0"
            title="Running this writes to the target API. It is not run unless you allow mutations."
          >
            <AlertTriangle className="w-3 h-3" />
            WRITES DATA
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        {chain.steps.map((step, idx) => (
          <React.Fragment key={step.id}>
            <div className="flex items-center gap-1.5 rounded-lg border border-border-subtle px-2 py-1">
              <span
                className={`px-1.5 rounded text-[9px] font-mono font-bold border ${
                  METHOD_COLORS[step.method] ??
                  'text-text-muted border-border-subtle'
                }`}
              >
                {step.method}
              </span>
              <span className="font-mono text-[10px] text-text-secondary">
                {step.endpoint}
              </span>
              <span className="font-mono text-[9px] text-text-muted">
                → {step.expected_status}
              </span>
            </div>
            {idx < chain.steps.length - 1 && (
              <ArrowRight className="w-3 h-3 text-text-muted/50 shrink-0" />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* The whole point of a chain: the id is captured from a real response,
          never invented. Showing it makes that checkable. */}
      {chain.steps
        .filter((s) => s.captures.length > 0)
        .map((step) => (
          <p key={step.id} className="text-[10px] text-text-muted font-mono">
            {step.captures
              .map(
                (c) =>
                  `captures ${c.name} from the ${step.method} response at ${c.pointer}`
              )
              .join(', ')}
          </p>
        ))}
    </div>
  );
}

export const DetectedChainsPanel: React.FC<DetectedChainsPanelProps> = ({
  specPath,
}) => {
  const { journey } = useJourney();
  const { data, isLoading, error } = useQuery({
    queryKey: ['chains', journey.id, specPath],
    queryFn: () => fetchDetectedChains(journey.id, specPath),
    enabled: !!specPath,
  });

  if (!specPath) return null;

  return (
    <Card className="p-6 space-y-4" data-testid="detected-chains-panel">
      <div>
        <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
          <Link2 className="w-4 h-4 text-cyan-400" />
          <span>Multi-step journeys</span>
        </h2>
        <p className="text-xs text-text-muted mt-0.5">
          Sequences that need state from an earlier call. Each one captures a
          real id from a real response rather than guessing one.
        </p>
      </div>

      {isLoading && (
        <div className="space-y-2">
          <Skeleton className="h-20 w-full rounded-xl" />
          <Skeleton className="h-20 w-full rounded-xl" />
        </div>
      )}

      {error && (
        <p className="text-xs text-rose-400 font-mono">
          Could not analyse the spec: {(error as Error).message}
        </p>
      )}

      {data && data.chains.length === 0 && (
        <EmptyState
          icon={Link2}
          title="No multi-step journeys found"
          description="This spec has no collection/item pairs that create a resource and then read it back. Single-endpoint tests still cover it."
        />
      )}

      {data && data.chains.length > 0 && (
        <div className="space-y-3">
          {data.chains.map((chain) => (
            <ChainCard key={chain.id} chain={chain} />
          ))}
        </div>
      )}
    </Card>
  );
};

export default DetectedChainsPanel;
