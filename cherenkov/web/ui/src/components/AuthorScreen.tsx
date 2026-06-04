/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Compass, Sparkles, Terminal, Download, CheckCircle2, Play, Circle } from 'lucide-react';
import { Card, PageHeader, EmptyState } from './ui';
import { MOCK_MENTOR_IDIOMS, MOCK_PILOT_STEPS } from '../mockData';
import { useToast } from './ui/Toast';

export default function AuthorScreen() {
  const { addToast } = useToast();
  const [intent, setIntent] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentStepIdx, setCurrentStepIdx] = useState(-1);
  const [steps, setSteps] = useState(MOCK_PILOT_STEPS);
  const [isDone, setIsDone] = useState(false);

  const handleStart = () => {
    if (!intent.trim()) {
      addToast('Please type an intent first.', 'warning');
      return;
    }
    setIsRunning(true);
    setIsDone(false);
    setCurrentStepIdx(0);
    setSteps(MOCK_PILOT_STEPS.map((s, idx) => ({
      ...s,
      status: idx === 0 ? 'running' as const : 'pending' as const
    })));
  };

  const handleConfirmStep = () => {
    const nextIdx = currentStepIdx + 1;
    if (nextIdx < steps.length) {
      setSteps(prev => prev.map((s, idx) => {
        if (idx === currentStepIdx) return { ...s, status: 'done' as const };
        if (idx === nextIdx) return { ...s, status: 'running' as const };
        return s;
      }));
      setCurrentStepIdx(nextIdx);
    } else {
      setSteps(prev => prev.map((s, idx) => idx === currentStepIdx ? { ...s, status: 'done' as const } : s));
      setIsRunning(false);
      setIsDone(true);
      addToast('Pilot execution completed. Test scenario ready for eject!', 'success');
    }
  };

  const handleEject = () => {
    addToast('Ejected Playwright spec successfully: tests/checkout.spec.ts', 'success');
    setIsDone(false);
    setIsRunning(false);
    setIntent('');
  };

  const exampleIntents = [
    'Verify that guests can checkout with valid cart items and coupons.',
    'Test account profile modification checks username collision validation.',
    'Check inventory levels decrease after successful purchases.'
  ];

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="author-screen">
      <PageHeader
        title="Author by Intent"
        description="Transform natural language test goals into active client browser runs and eject standalone Playwright specifications."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left 2 columns: Authoring core */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="p-6 space-y-4">
            <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
              <Compass className="w-4 h-4 text-glow-blue" />
              <span>Describe Test Scenario Intent</span>
            </h3>

            <textarea
              id="txt-author-intent"
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
              placeholder="e.g. Verify that guest checkouts apply 15% discount code and succeed with 200 OK..."
              className="w-full h-32 p-4 font-sans text-sm text-[#E6EDF3] bg-black/30 border border-white/10 rounded-xl focus:outline-none focus:border-glow-blue transition leading-relaxed"
            />

            {/* Example chips */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono text-[#7D8DA1] uppercase">Quick Examples:</span>
              <div className="flex flex-wrap gap-2">
                {exampleIntents.map((ex, idx) => (
                  <button
                    key={idx}
                    onClick={() => setIntent(ex)}
                    className="text-[11px] font-sans px-2.5 py-1 rounded-lg border border-white/5 bg-white/5 hover:border-glow-blue/50 hover:bg-white/10 text-[#7D8DA1] hover:text-[#E6EDF3] transition cursor-pointer text-left"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={handleStart}
                disabled={isRunning}
                className="flex items-center gap-2 px-6 py-2.5 bg-glow-blue hover:bg-opacity-95 disabled:opacity-50 text-slate-950 font-bold text-xs rounded-xl uppercase tracking-wider transition cursor-pointer font-mono shadow-lg shadow-cyan-500/10"
              >
                <Play className="w-4 h-4 text-slate-950" />
                <span>Initialize Pilot Run</span>
              </button>
            </div>
          </Card>

          {/* Stepped execution panel */}
          {(isRunning || isDone) && (
            <Card className="p-6 space-y-4 animate-fadeIn">
              <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Terminal className="w-4 h-4 text-glow-blue" />
                <span>Pilot Agent Client Execution Drawer</span>
              </h3>

              <div className="space-y-3 font-mono text-xs">
                {steps.map((s, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center justify-between p-3 rounded-xl border ${
                      s.status === 'done' ? 'bg-[#3FB950]/5 border-[#3FB950]/20 text-[#3FB950]' :
                      s.status === 'running' ? 'bg-glow-blue/5 border-glow-blue/30 text-glow-bright animate-pulse' :
                      'bg-black/10 border-white/5 text-[#7D8DA1]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {s.status === 'done' ? <CheckCircle2 className="w-4 h-4 shrink-0 text-[#3FB950]" /> :
                       s.status === 'running' ? <Circle className="w-4 h-4 shrink-0 text-glow-bright animate-spin border-t-2 border-t-glow-blue" /> :
                       <Circle className="w-4 h-4 shrink-0 text-[#7D8DA1]" />}
                      <span className={s.status === 'running' ? 'beam-flow' : ''}>{s.step}</span>
                    </div>

                    {s.status === 'running' && (
                      <button
                        onClick={handleConfirmStep}
                        className="px-2.5 py-1 bg-glow-bright hover:bg-opacity-95 text-slate-950 font-bold text-[9px] rounded font-mono uppercase transition cursor-pointer"
                      >
                        Confirm Step
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {isDone && (
                <div className="pt-4 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4">
                  <div className="text-xs text-[#7D8DA1] font-mono">
                    ✨ CHERENKOV learned from this interactive session. Ejecting updates internal weights.
                  </div>
                  <button
                    onClick={handleEject}
                    className="flex items-center gap-2 px-6 py-2 bg-[#3FB950] hover:bg-opacity-95 text-white font-bold text-xs rounded-xl uppercase tracking-wider transition cursor-pointer font-mono"
                  >
                    <Download className="w-4 h-4 text-white" />
                    <span>Save & Eject Test Suite</span>
                  </button>
                </div>
              )}
            </Card>
          )}
        </div>

        {/* Right column: Mentor suggestions */}
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#E6EDF3] border-b border-white/5 pb-3 flex items-center gap-2 font-display">
              <Sparkles className="w-4 h-4 text-glow-blue" />
              <span>Mentor Context Idioms</span>
            </h3>
            <p className="text-xs text-[#7D8DA1] leading-relaxed">
              Based on the current endpoints and active workspace service contexts, seniors recommend incorporating these validations:
            </p>

            <div className="space-y-3">
              {MOCK_MENTOR_IDIOMS.map((idm) => (
                <div key={idm.id} className="p-3 bg-white/5 border border-white/5 rounded-xl space-y-1">
                  <h4 className="text-xs font-bold text-text-primary font-sans">{idm.title}</h4>
                  <p className="text-[11px] text-[#7D8DA1]/85 leading-normal">{idm.desc}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
