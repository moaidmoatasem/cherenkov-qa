/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * VisualRegressionScreen — Epoch 9 VLM-powered visual regression dashboard.
 *
 * Shows each visual scenario with:
 *   - pixel_diff gate result (pass/fail)
 *   - vlm_semantic gate classification (ANOMALY / HARMLESS_SHIFT / REDESIGN / UNKNOWN)
 *   - Baseline vs actual screenshot comparison
 *   - Approve / reject workflow (suggest-only, D7 invariant)
 *
 * Inspired by AutoMate TestGenie's VisualRegressionPage — adds VLM semantic
 * classification on top of raw pixel diffing so teams can distinguish real
 * bugs from anti-aliasing noise without manual triage.
 */

import React, { useState, useEffect } from 'react';
import {
  Eye,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Cpu,
  Layers,
  ChevronDown,
  ChevronUp,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { API_BASE } from '../lib/api';

// ── types ─────────────────────────────────────────────────────────────────────

type VlmKind = 'anomaly' | 'harmless_shift' | 'redesign' | 'unknown';

interface VisualGate {
  gate: string;
  passed: boolean;
  diff_pixels: number;
  baseline_path: string;
  actual_path: string;
}

interface VisualScenario {
  scenario_id: string;
  status: 'ok' | 'failed' | 'degraded';
  verdict: 'AUTO_APPROVE' | 'HITL';
  gates: VisualGate[];
  vlm_kind?: VlmKind;
  vlm_confidence?: number;
  vlm_detail?: string;
  url?: string;
}

// ── helpers ───────────────────────────────────────────────────────────────────

const VLM_KIND_META: Record<VlmKind, { label: string; color: string; icon: React.ReactNode }> = {
  anomaly: {
    label: 'Anomaly',
    color: 'text-red-400 bg-red-400/10 border-red-400/30',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
  harmless_shift: {
    label: 'Harmless Shift',
    color: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  redesign: {
    label: 'Redesign',
    color: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
  },
  unknown: {
    label: 'Unknown',
    color: 'text-slate-400 bg-slate-400/10 border-slate-400/30',
    icon: <Cpu className="w-3.5 h-3.5" />,
  },
};

function VlmBadge({ kind }: { kind: VlmKind }) {
  const meta = VLM_KIND_META[kind];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-mono font-semibold ${meta.color}`}>
      {meta.icon}
      {meta.label}
    </span>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'ok') return <CheckCircle className="w-4 h-4 text-emerald-400" />;
  if (status === 'degraded') return <AlertTriangle className="w-4 h-4 text-amber-400" />;
  return <XCircle className="w-4 h-4 text-red-400" />;
}

// ── main component ────────────────────────────────────────────────────────────

export default function VisualRegressionScreen() {
  const [scenarios, setScenarios] = useState<VisualScenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [decisions, setDecisions] = useState<Record<string, 'approved' | 'rejected'>>({});
  const [filterKind, setFilterKind] = useState<VlmKind | 'all'>('all');

  useEffect(() => {
    fetchScenarios();
  }, []);

  async function fetchScenarios() {
    setLoading(true);
    try {
      const { fetchVisualScenarios } = await import('../lib/api');
      const data = await fetchVisualScenarios();
      setScenarios(data || []);
    } catch {
      setScenarios([]);
    }
    setLoading(false);
  }

  function toggleExpand(id: string) {
    setExpanded(p => ({ ...p, [id]: !p[id] }));
  }

  function decide(id: string, verdict: 'approved' | 'rejected') {
    setDecisions(p => ({ ...p, [id]: verdict }));
  }

  const filtered = filterKind === 'all'
    ? scenarios
    : scenarios.filter(s => s.vlm_kind === filterKind);

  const counts = {
    anomaly: scenarios.filter(s => s.vlm_kind === 'anomaly').length,
    harmless_shift: scenarios.filter(s => s.vlm_kind === 'harmless_shift').length,
    redesign: scenarios.filter(s => s.vlm_kind === 'redesign').length,
    unknown: scenarios.filter(s => s.vlm_kind === 'unknown').length,
    pending: scenarios.filter(s => s.verdict === 'HITL' && !decisions[s.scenario_id]).length,
  };

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-display font-semibold text-text-primary flex items-center gap-2">
            <Eye className="w-5 h-5 text-glow-blue" />
            Visual Regression
          </h2>
          <p className="text-xs text-[#7D8DA1] mt-0.5">
            VLM-semantic classification — distinguishes real anomalies from harmless pixel drift
          </p>
        </div>
        <button
          onClick={fetchScenarios}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-glow-bright border border-white/10 rounded-lg hover:bg-white/5 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(Object.keys(VLM_KIND_META) as VlmKind[]).map(kind => (
          <button
            key={kind}
            onClick={() => setFilterKind(filterKind === kind ? 'all' : kind)}
            className={`rounded-xl border p-3 text-left transition cursor-pointer ${
              filterKind === kind ? VLM_KIND_META[kind].color : 'border-white/10 bg-white/5 hover:bg-white/8'
            }`}
          >
            <div className="flex items-center gap-1.5 mb-1">
              {VLM_KIND_META[kind].icon}
              <span className="text-xs font-semibold text-text-primary">{VLM_KIND_META[kind].label}</span>
            </div>
            <div className="text-2xl font-mono font-bold text-text-primary">{counts[kind]}</div>
          </button>
        ))}
      </div>

      {/* Pending HITL badge */}
      {counts.pending > 0 && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-400/10 border border-amber-400/30 text-amber-300 text-xs">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span><strong>{counts.pending}</strong> scenario{counts.pending > 1 ? 's' : ''} awaiting your review (HITL verdict)</span>
        </div>
      )}

      {/* Scenario list */}
      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map(i => (
            <div key={i} className="h-20 rounded-xl bg-white/5 border border-white/10 animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-3 text-center">
          <Layers className="w-10 h-10 text-[#7D8DA1]" />
          <p className="text-sm text-[#7D8DA1]">No visual scenarios found.</p>
          <p className="text-xs text-[#7D8DA1]/60">Run <code className="font-mono bg-white/10 px-1 rounded">cherenkov validate --visual</code> to generate them.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(s => {
            const isOpen = !!expanded[s.scenario_id];
            const decision = decisions[s.scenario_id];
            const pixelGate = s.gates.find(g => g.gate === 'pixel_diff');
            const vlmGate = s.gates.find(g => g.gate === 'vlm_semantic');
            const vlmKind = s.vlm_kind ?? 'unknown';

            return (
              <div key={s.scenario_id} className="rounded-xl border border-white/10 bg-white/3 overflow-hidden">
                {/* Row header */}
                <button
                  onClick={() => toggleExpand(s.scenario_id)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition text-left cursor-pointer"
                >
                  <StatusIcon status={s.status} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-mono text-text-primary truncate">{s.scenario_id}</span>
                      {s.vlm_kind && <VlmBadge kind={vlmKind} />}
                      {decision && (
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
                          decision === 'approved'
                            ? 'text-emerald-400 border-emerald-400/30 bg-emerald-400/10'
                            : 'text-red-400 border-red-400/30 bg-red-400/10'
                        }`}>
                          {decision === 'approved' ? '✓ Approved' : '✗ Rejected'}
                        </span>
                      )}
                    </div>
                    {s.url && <span className="text-xs text-[#7D8DA1] truncate block">{s.url}</span>}
                  </div>

                  {/* Gate pills */}
                  <div className="hidden sm:flex items-center gap-2 shrink-0">
                    <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
                      pixelGate?.passed
                        ? 'text-emerald-400 border-emerald-400/30'
                        : 'text-red-400 border-red-400/30'
                    }`}>
                      pixel {pixelGate?.passed ? '✓' : `✗ ${pixelGate?.diff_pixels ?? '?'}px`}
                    </span>
                    {vlmGate && (
                      <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
                        vlmGate.passed
                          ? 'text-emerald-400 border-emerald-400/30'
                          : 'text-amber-400 border-amber-400/30'
                      }`}>
                        vlm {vlmGate.passed ? '✓' : '⚑'}
                      </span>
                    )}
                  </div>

                  {isOpen ? <ChevronUp className="w-4 h-4 text-[#7D8DA1] shrink-0" /> : <ChevronDown className="w-4 h-4 text-[#7D8DA1] shrink-0" />}
                </button>

                {/* Expanded detail */}
                {isOpen && (
                  <div className="border-t border-white/10 px-4 pb-4 pt-3 space-y-4">
                    {/* VLM explanation */}
                    {s.vlm_detail && (
                      <div className="rounded-lg bg-black/30 border border-white/10 p-3">
                        <div className="flex items-center gap-1.5 mb-1.5 text-xs text-[#7D8DA1] font-semibold uppercase tracking-wider">
                          <Cpu className="w-3 h-3" />
                          VLM Analysis
                          {s.vlm_confidence !== undefined && (
                            <span className="ml-auto font-mono text-glow-blue">{(s.vlm_confidence * 100).toFixed(0)}% confidence</span>
                          )}
                        </div>
                        <p className="text-xs text-text-primary leading-relaxed">{s.vlm_detail}</p>
                      </div>
                    )}

                    {/* Screenshot placeholder — real paths would load from API */}
                    {pixelGate && !pixelGate.passed && (
                      <div className="grid grid-cols-2 gap-3">
                        {(['Baseline', 'Actual'] as const).map(label => (
                          <div key={label} className="rounded-lg border border-white/10 bg-black/20 p-3 text-center">
                            <div className="text-xs text-[#7D8DA1] mb-2 font-semibold">{label}</div>
                            <div className="h-32 flex items-center justify-center rounded bg-white/5 text-[#7D8DA1] text-xs font-mono">
                              {label === 'Baseline' ? pixelGate.baseline_path : pixelGate.actual_path || 'generating…'}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* HITL approval workflow */}
                    {s.verdict === 'HITL' && !decision && (
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-[#7D8DA1]">Your decision (suggest-only):</span>
                        <button
                          onClick={() => decide(s.scenario_id, 'approved')}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-emerald-400/40 text-emerald-400 hover:bg-emerald-400/10 transition cursor-pointer"
                        >
                          <ThumbsUp className="w-3.5 h-3.5" />
                          Approve change
                        </button>
                        <button
                          onClick={() => decide(s.scenario_id, 'rejected')}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-red-400/40 text-red-400 hover:bg-red-400/10 transition cursor-pointer"
                        >
                          <ThumbsDown className="w-3.5 h-3.5" />
                          Reject — fix needed
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
