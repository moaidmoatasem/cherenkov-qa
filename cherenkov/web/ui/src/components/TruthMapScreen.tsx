/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Network, AlertCircle, ArrowRight, Zap } from 'lucide-react';
import { Card, PageHeader, ProvenanceChip, MockBadge, Skeleton } from './ui';
import { fetchTruthMapData, TruthMapNode, ProvenanceType } from '../lib/api';

interface TruthMapScreenProps {
  onNavigate: (tab: string) => void;
}

export default function TruthMapScreen({ onNavigate }: TruthMapScreenProps) {
  const [selectedIdx, setSelectedIdx] = useState<number>(0);
  const [nodes, setNodes] = useState<TruthMapNode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    fetchTruthMapData()
      .then(data => {
        setNodes(data || []);
        setIsLoading(false);
      })
      .catch(err => {
        setError(err instanceof Error ? err.message : 'Failed to load truth map');
        setIsLoading(false);
      });
  }, []);

  if (isLoading) {
    return (
      <div className="p-6 h-full overflow-hidden flex flex-col grid-bg bg-transparent relative z-10" id="truth-map-screen">
        <MockBadge />
        <PageHeader title="Endpoint Truth Graph" description="Unified claims graph mapping the alignment between OpenAPI specifications, server source code, and live HTTP database footprints." />
        <div className="flex-1 flex items-center justify-center">
          <Skeleton className="w-32 h-32 rounded-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 h-full overflow-hidden flex flex-col grid-bg bg-transparent relative z-10" id="truth-map-screen">
        <MockBadge />
        <PageHeader title="Endpoint Truth Graph" description="Unified claims graph mapping the alignment between OpenAPI specifications, server source code, and live HTTP database footprints." />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-3">
            <Zap className="w-12 h-12 text-amber-400 mx-auto" />
            <p className="text-text-muted text-sm font-semibold">Failed to load truth map</p>
            <p className="text-[11px] text-text-muted/60">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const currentEndpoint = nodes[selectedIdx] || nodes[0];

  if (!currentEndpoint) {
    return (
      <div className="p-6 h-full overflow-hidden flex flex-col grid-bg bg-transparent relative z-10" id="truth-map-screen">
        <MockBadge />
        <PageHeader title="Endpoint Truth Graph" description="Unified claims graph mapping the alignment between OpenAPI specifications, server source code, and live HTTP database footprints." />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-3">
            <Network className="w-12 h-12 text-text-muted/40 mx-auto" />
            <p className="text-text-muted text-sm font-semibold">No endpoints mapped yet</p>
            <p className="text-[11px] text-text-muted/60">Run a spec ingest to build the endpoint truth graph.</p>
            <button onClick={() => onNavigate('setup')} className="mt-2 px-4 py-1.5 rounded bg-accent-bg border border-glow-blue text-glow-bright text-xs hover:bg-glow-blue hover:text-bg-base transition duration-300">
              Go to Spec Ingest
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-hidden flex flex-col justify-between grid-bg bg-transparent relative z-10" id="truth-map-screen">
      <MockBadge />
      <PageHeader
        title="Endpoint Truth Graph"
        description="Unified claims graph mapping the alignment between OpenAPI specifications, server source code, and live HTTP database footprints."
      />
      <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-5 gap-6 mt-6 items-stretch">
        {/* Endpoint List Panel (2/5) */}
        <div className="lg:col-span-2 flex flex-col bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden h-full">
          <div className="p-3 bg-black/40 border-b border-white/5 font-mono text-[10px] text-[#7D8DA1] uppercase tracking-wider">
            Monitored Endpoint Claims
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {nodes.map((node, idx) => (
              <div
                key={idx}
                onClick={() => setSelectedIdx(idx)}
                className={`p-3.5 rounded-xl border transition cursor-pointer flex justify-between items-center ${
                  selectedIdx === idx
                    ? 'bg-white/10 border-glow-blue shadow-lg shadow-cyan-500/5'
                    : 'bg-black/20 border-white/5 hover:border-text-muted hover:bg-white/5'
                }`}
              >
                <div>
                  <span className="block font-mono text-xs text-[#E6EDF3] font-semibold">{node.endpoint}</span>
                  <span className="text-[10px] text-[#7D8DA1]/85 font-mono block mt-1">
                    {node.claims.length} Multi-source Claims
                  </span>
                </div>
                {node.hasDivergence && (
                  <span className="flex items-center gap-1 text-[9px] font-mono font-bold text-red-400 border border-red-500/20 bg-red-500/5 px-2 py-0.5 rounded animate-pulse">
                    <AlertCircle className="w-3 h-3" />
                    DIVERGENT
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Claims Detail Panel (3/5) */}
        <div className="lg:col-span-3 flex flex-col bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden h-full">
          <div className="p-4 bg-black/40 border-b border-white/5 flex items-center justify-between shrink-0">
            <div>
              <h3 className="font-display font-semibold text-sm text-text-primary">
                {currentEndpoint.endpoint}
              </h3>
              <p className="text-[10px] font-mono text-[#7D8DA1] mt-0.5 uppercase">Provenanced Verification Claims</p>
            </div>
            {currentEndpoint.hasDivergence && (
              <button
                onClick={() => onNavigate('divergences')}
                className="px-3 py-1 bg-red-500/10 hover:bg-red-500 hover:text-slate-950 text-red-400 border border-red-500/20 hover:border-red-500 text-[10px] font-mono font-bold uppercase rounded-xl transition flex items-center gap-1.5 cursor-pointer"
              >
                <span>HUNT DIVERGENCES</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>

          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {currentEndpoint.claims.map((c) => (
              <div key={c.id} className="p-4 rounded-xl border border-white/5 bg-black/10 space-y-2">
                <div className="flex items-center gap-2">
                  <ProvenanceChip type={c.provenance} />
                  <span className="font-mono text-[9px] text-[#7D8DA1] uppercase">{c.provenance.toUpperCase()} VERIFIED</span>
                </div>
                <p className="text-xs text-[#E6EDF3] leading-relaxed font-mono whitespace-pre-wrap">{c.claim}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
