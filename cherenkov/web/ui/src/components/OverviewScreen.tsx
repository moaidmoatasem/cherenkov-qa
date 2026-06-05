/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { LayoutDashboard, ArrowRight, Zap, GraduationCap, CheckCircle } from 'lucide-react';
import { Card, PageHeader, KpiRing } from './ui';
import { MOCK_OVERVIEW, MOCK_DIVERGENCES } from '../mockData';

interface OverviewScreenProps {
  onNewRun: () => void;
  onNavigate: (tab: string) => void;
}

export default function OverviewScreen({ onNewRun, onNavigate }: OverviewScreenProps) {
  const topDivergences = MOCK_DIVERGENCES.slice(0, 3);

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="overview-screen">
      <PageHeader
        title="Release Readiness & Learning"
        description="Core metrics tracking API safety, active divergences, and Reflector self-healing optimizations."
        primaryAction={{
          label: 'Run Discovery Scan',
          onClick: onNewRun,
        }}
      />
      <div className="flex justify-end -mt-4 mb-2">
        <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border bg-amber-500/10 text-amber-400 border-amber-500/30">
          MOCK DATA
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        {/* Release Readiness KPI Ring */}
        <Card className="flex flex-col items-center justify-between p-6">
          <div className="w-full">
            <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted">
              Release Readiness Score
            </h3>
            <p className="text-xs text-[#7D8DA1] mt-1">Weighted score based on unresolved critical divergences.</p>
          </div>
          <div className="py-6">
            <KpiRing
              value={MOCK_OVERVIEW.releaseReadiness}
              title="Readiness"
              size={160}
              strokeWidth={12}
              glowColor="blue"
            />
          </div>
          <div className="w-full flex items-center justify-between border-t border-white/5 pt-4 text-xs font-mono text-[#7D8DA1]">
            <span>FP Rate: {MOCK_OVERVIEW.falsePositiveRate}%</span>
            <span className="text-glow-bright">99.9% Target</span>
          </div>
        </Card>

        {/* Top Active Divergences */}
        <Card className="flex flex-col justify-between p-6">
          <div>
            <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
              <Zap className="w-4 h-4 text-glow-blue" />
              <span>Top Unresolved Divergences</span>
            </h3>
            <div className="mt-4 space-y-3">
              {topDivergences.map((div) => (
                <div
                  key={div.id}
                  onClick={() => onNavigate('divergences')}
                  className="p-3 rounded-xl bg-black/20 border border-white/5 hover:border-glow-blue/50 hover:bg-white/5 transition-all duration-200 cursor-pointer text-xs"
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-mono font-bold text-glow-bright uppercase">{div.divergenceClass}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[8px] font-mono font-bold uppercase ${
                      div.severity === 'critical' || div.severity === 'high' 
                        ? 'bg-red-500/10 text-red-400 border border-red-500/20' 
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {div.severity}
                    </span>
                  </div>
                  <p className="text-text-primary font-semibold truncate">{div.endpoint}</p>
                  <p className="text-[#7D8DA1] mt-0.5 truncate">{div.claimB}</p>
                </div>
              ))}
            </div>
          </div>
          <button
            onClick={() => onNavigate('divergences')}
            className="w-full mt-4 py-2 border border-white/10 rounded-xl text-xs font-mono font-semibold text-[#7D8DA1] hover:text-[#E6EDF3] hover:bg-white/5 transition flex items-center justify-center gap-2 cursor-pointer"
          >
            <span>View All Divergences</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </Card>

        {/* Recent Learning Activity Feed */}
        <Card className="flex flex-col justify-between p-6">
          <div>
            <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-glow-blue" />
              <span>Reflector Verdict Memory</span>
            </h3>
            <div className="mt-4 space-y-4">
              {MOCK_OVERVIEW.recentLearnings.map((item, idx) => (
                <div key={idx} className="flex gap-3 text-xs">
                  <div className="mt-0.5 p-1 bg-glow-blue/10 text-glow-bright rounded-full h-fit">
                    <CheckCircle className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <p className="text-text-primary leading-relaxed">{item.text}</p>
                    <span className="text-[10px] text-[#7D8DA1]/75 font-mono block mt-1">Incremental Verdict Sync</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <button
            onClick={() => onNavigate('memory')}
            className="w-full mt-4 py-2 border border-white/10 rounded-xl text-xs font-mono font-semibold text-[#7D8DA1] hover:text-[#E6EDF3] hover:bg-white/5 transition flex items-center justify-center gap-2 cursor-pointer"
          >
            <span>Manage Reflector Memory</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </Card>
      </div>
    </div>
  );
}
