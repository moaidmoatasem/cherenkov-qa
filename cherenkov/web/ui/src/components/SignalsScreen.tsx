/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { TrendingUp, Activity, Image, Percent, AlertTriangle, CheckCircle } from 'lucide-react';
import { Card, PageHeader, MockBadge, Tabs } from './ui';
import { fetchSignals } from '../lib/api';

export default function SignalsScreen() {
  const [MOCK_SIGNALS, setSignals] = useState<any>({ performance: [], visual: [], coverage: [] });
  useEffect(() => {
    fetchSignals().then(data => {
      setSignals({
        performance: Array.isArray(data.performance) ? data.performance : [],
        visual: Array.isArray(data.visual) ? data.visual : [],
        coverage: Array.isArray(data.coverage) ? data.coverage : [],
      });
    });
  }, []);
  const [activeTab, setActiveTab] = useState('performance');

  const tabs = [
    { id: 'performance', label: 'Performance', icon: Activity },
    { id: 'visual', label: 'Visual Regression', icon: Image },
    { id: 'coverage', label: 'SDET Coverage', icon: Percent },
  ];

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="signals-screen">
      <MockBadge />
      <PageHeader
        title="Telemetry Signals"
        description="Verify performance, visual changes, and functional coverage profiles from live test suite telemetry."
      />
      <div className="flex justify-end -mt-4 mb-2">
        <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border bg-amber-500/10 text-amber-400 border-amber-500/30">
          MOCK DATA
        </span>
      </div>

      <div className="border-b border-white/5 pb-2">
        <Tabs items={tabs} activeId={activeTab} onChange={setActiveTab} />
      </div>

      {activeTab === 'performance' && (
        <Card className="p-6 space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted">
              API Latency & Anomaly Baselines
            </h2>
            <span className="text-[10px] font-mono text-[#7D8DA1]">UPDATED 1M AGO</span>
          </div>

          <div className="space-y-4">
            {MOCK_SIGNALS.performance.map((p, idx) => (
              <div
                key={idx}
                className={`p-3.5 rounded-xl border flex justify-between items-center font-mono text-xs ${
                  p.anomaly
                    ? 'bg-red-500/5 border-red-500/20 text-red-400'
                    : 'bg-black/20 border-white/5 text-[#7D8DA1]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Activity className="w-4 h-4 shrink-0" />
                  <span>Time: {p.time}</span>
                  <span>·</span>
                  <span className="font-semibold text-text-primary">Latency: {p.latency}ms</span>
                  <span>·</span>
                  <span>Baseline: {p.baseline}ms</span>
                </div>
                {p.anomaly ? (
                  <span className="flex items-center gap-1 text-[9px] font-bold border border-red-500/20 bg-red-500/5 px-2 py-0.5 rounded animate-pulse">
                    <AlertTriangle className="w-3 h-3" />
                    ANOMALY DETECTED
                  </span>
                ) : (
                  <span className="text-[9px] text-[#3FB950] font-bold">NORMAL BOUNDS</span>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {activeTab === 'visual' && (
        <Card className="p-6 space-y-6">
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted">
            UI Snapshot Comparisons
          </h2>

          <div className="space-y-4">
            {MOCK_SIGNALS.visual.map((v) => (
              <div
                key={v.id}
                className={`p-3.5 rounded-xl border flex justify-between items-center text-xs ${
                  v.status === 'warning'
                    ? 'bg-amber-500/5 border-amber-500/20 text-amber-400 font-mono'
                    : 'bg-black/20 border-white/5 text-[#7D8DA1] font-mono'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Image className="w-4 h-4 shrink-0 text-[#7D8DA1]" />
                  <span className="font-sans font-semibold text-text-primary">{v.name}</span>
                  <span>·</span>
                  <span>Diff: {v.difference}</span>
                </div>
                {v.status === 'warning' ? (
                  <span className="flex items-center gap-1 text-[9px] font-bold border border-amber-500/20 bg-amber-500/5 px-2 py-0.5 rounded">
                    <AlertTriangle className="w-3 h-3" />
                    DRIFT DETECTED
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-[9px] text-[#3FB950] font-bold border border-[#3FB950]/20 bg-[#3FB950]/5 px-2 py-0.5 rounded">
                    <CheckCircle className="w-3 h-3" />
                    MATCHED
                  </span>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {activeTab === 'coverage' && (
        <Card className="p-6 space-y-6">
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted">
            Code Path Verification Coverage
          </h2>

          <div className="space-y-4">
            {MOCK_SIGNALS.coverage.map((c, idx) => (
              <div key={idx} className="p-4 rounded-xl border border-white/5 bg-black/20 space-y-3">
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="font-semibold text-text-primary">{c.path}</span>
                  <span className="text-glow-bright">Cherenkov: {c.cherenkov}% vs SDET: {c.sdet}%</span>
                </div>
                <div className="w-full bg-black/30 h-2 rounded-full overflow-hidden border border-white/5">
                  <div className="bg-glow-blue h-full rounded-full" style={{ width: `${c.cherenkov}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
