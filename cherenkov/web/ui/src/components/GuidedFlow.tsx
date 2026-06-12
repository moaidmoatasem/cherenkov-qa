/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Upload, Play, CheckSquare, Download, CheckCircle2 } from 'lucide-react';

interface GuidedFlowProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  reviewPendingCount?: number;
}

const STEPS = [
  { id: 'setup', label: 'Ingest & Plan', icon: Upload, desc: 'Upload or fetch OpenAPI spec' },
  { id: 'pipeline', label: 'Generate & Pilot', icon: Play, desc: 'AI generates tests live' },
  { id: 'review', label: 'Review Gate', icon: CheckSquare, desc: 'Human-in-the-loop approval' },
  { id: 'eject', label: 'Eject & Integrate', icon: Download, desc: 'Export vanilla Playwright' },
];

const TAB_TO_STEP_INDEX: Record<string, number> = {
  setup: 0, pipeline: 1, review: 2, eject: 3,
  author: 1, healing: 2,
};

export default function GuidedFlow({ activeTab, setActiveTab, reviewPendingCount = 0 }: GuidedFlowProps) {
  const currentStepIndex = TAB_TO_STEP_INDEX[activeTab] ?? -1;

  return (
    <div className="px-3 py-3 space-y-0.5" id="guided-flow" data-testid="guided-flow">
      <p className="text-[9px] font-bold font-mono tracking-widest text-[#7D8DA1]/60 px-1 mb-2 uppercase">Current Run</p>
      {STEPS.map((step, idx) => {
        const Icon = step.icon;
        const isActive = idx === currentStepIndex;
        const isDone = idx < currentStepIndex;
        const isRunning = isActive && step.id === 'pipeline';

        return (
          <button
            key={step.id}
            id={`guided-step-${step.id}`}
            data-testid={`guided-step-${step.id}`}
            onClick={() => setActiveTab(step.id)}
            className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center gap-3 transition-all duration-200 cursor-pointer relative ${
              isActive
                ? 'bg-white/10 border-l-2 border-glow-blue'
                : isDone
                ? 'hover:bg-white/5 border-l-2 border-emerald-500/40'
                : 'hover:bg-white/5 border-l-2 border-white/10'
            }`}
          >
            {/* Step indicator */}
            <div className="shrink-0">
              {isDone ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : isRunning ? (
                <div className="w-4 h-4 rounded-full bg-glow-blue animate-pulse" />
              ) : (
                <Icon className={`w-4 h-4 ${isActive ? 'text-glow-bright' : 'text-[#7D8DA1]'}`} />
              )}
            </div>

            {/* Label + desc */}
            <div className="flex-1 min-w-0 hidden lg:block">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-semibold ${
                  isActive ? 'text-glow-bright' : isDone ? 'text-emerald-400' : 'text-[#7D8DA1]'
                }`}>
                  {idx + 1}. {step.label}
                </span>
                {/* Review pending badge */}
                {step.id === 'review' && reviewPendingCount > 0 && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                    {reviewPendingCount}
                  </span>
                )}
              </div>
              <p className={`text-[10px] mt-0.5 truncate ${
                isActive ? 'text-[#7D8DA1]' : 'text-[#7D8DA1]/60'
              }`}>
                {step.desc}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
