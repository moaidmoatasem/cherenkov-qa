/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Brain, GraduationCap, CheckCircle } from 'lucide-react';
import { Card, PageHeader } from './ui';
import { MOCK_IDIOMS, MOCK_PAIRING } from '../mockData';

export default function MemoryScreen() {
  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="memory-screen">
      <PageHeader
        title="Reflector Memory & Pairing"
        description="Verify stored testing idioms and view context-specific guidelines explained by the Mentor assistant agent."
      />
      <div className="flex justify-end -mt-4 mb-2">
        <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border bg-amber-500/10 text-amber-400 border-amber-500/30">
          MOCK DATA
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-stretch">
        {/* Idioms List Panel (3/5) */}
        <div className="lg:col-span-3 flex flex-col bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden">
          <div className="p-4 bg-black/40 border-b border-white/5 font-mono text-[10px] text-[#7D8DA1] uppercase tracking-wider">
            Accumulated Senior Testing Idioms
          </div>
          <div className="p-4 space-y-4">
            {MOCK_IDIOMS.map((idm) => (
              <div key={idm.id} className="p-4 rounded-xl border border-white/5 bg-black/20 space-y-2">
                <p className="text-xs text-[#E6EDF3] leading-relaxed font-mono">{idm.text}</p>
                <div className="flex justify-between items-center text-[10px] font-mono text-[#7D8DA1] pt-2 border-t border-white/5">
                  <span>Confidence Matches: {idm.count}</span>
                  <span className="text-glow-bright uppercase font-bold">{idm.decay}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Pairing Explanation Panel (2/5) */}
        <div className="lg:col-span-2 flex flex-col bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-[#E6EDF3] border-b border-white/5 pb-3 flex items-center gap-2 font-display">
            <GraduationCap className="w-4.5 h-4.5 text-glow-blue" />
            <span>Mentor Junior-Senior Pairing</span>
          </h3>

          <div className="space-y-4">
            {MOCK_PAIRING.map((p, idx) => (
              <div key={idx} className="space-y-2">
                <span className="inline-block text-[10px] font-mono font-bold bg-glow-blue/10 text-glow-bright px-2 py-0.5 rounded">
                  CONTEXT: {p.context.toUpperCase()}
                </span>
                <p className="text-xs text-[#7D8DA1] leading-relaxed">
                  {p.explanation}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
