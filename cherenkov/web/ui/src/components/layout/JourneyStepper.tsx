/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Sparkles, LayoutDashboard, CheckSquare, Brain, ChevronRight } from 'lucide-react';
import { WorkspaceId } from './NavigationBar';

export interface JourneyStage {
  id: WorkspaceId;
  step: number;
  label: string;
  blurb: string;
  icon: React.ComponentType<{ className?: string }>;
}

// The actual QA loop, in the order a manual tester moving to automation
// walks it -- distinct from the sidebar's destination-order list, which
// also includes Settings (not part of the loop).
export const JOURNEY_STAGES: JourneyStage[] = [
  { id: 'authoring', step: 1, label: 'Generate', blurb: 'Bring a spec, get a test suite', icon: Sparkles },
  { id: 'dashboard', step: 2, label: 'Validate', blurb: 'Run it against the real API', icon: LayoutDashboard },
  { id: 'triage', step: 3, label: 'Triage', blurb: 'Review what the AI flagged', icon: CheckSquare },
  { id: 'intelligence', step: 4, label: 'Knowledge', blurb: 'See what Cherenkov learned', icon: Brain },
];

interface JourneyStepperProps {
  activeWorkspace: WorkspaceId;
  onSelectWorkspace: (workspace: WorkspaceId) => void;
  pendingReviewCount?: number;
}

export const JourneyStepper: React.FC<JourneyStepperProps> = ({
  activeWorkspace,
  onSelectWorkspace,
  pendingReviewCount = 0,
}) => {
  const activeIndex = JOURNEY_STAGES.findIndex((s) => s.id === activeWorkspace);

  // Settings isn't part of the pipeline -- showing it "lit up" here would
  // wrongly imply it comes after Knowledge in the loop.
  if (activeIndex === -1) return null;

  return (
    <div
      className="flex items-center gap-1 px-6 py-2 border-b border-border-subtle bg-bg-surface/60 overflow-x-auto shrink-0"
      data-testid="journey-stepper"
      aria-label="Cherenkov QA workflow"
    >
      {JOURNEY_STAGES.map((stage, idx) => {
        const Icon = stage.icon;
        const isActive = stage.id === activeWorkspace;
        const isPast = idx < activeIndex;
        const badge = stage.id === 'triage' ? pendingReviewCount : undefined;

        return (
          <React.Fragment key={stage.id}>
            <button
              onClick={() => onSelectWorkspace(stage.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono transition-all whitespace-nowrap cursor-pointer ${
                isActive
                  ? 'bg-cyan-500/15 border border-cyan-500/40 text-cyan-400'
                  : 'text-text-muted hover:text-text-primary hover:bg-white/5 border border-transparent'
              }`}
              title={stage.blurb}
              data-testid={`journey-step-${stage.id}`}
            >
              <span
                className={`flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold shrink-0 ${
                  isActive
                    ? 'bg-cyan-400 text-slate-950'
                    : isPast
                    ? 'bg-text-muted/40 text-bg-base'
                    : 'border border-text-muted/40 text-text-muted'
                }`}
              >
                {stage.step}
              </span>
              <Icon className="w-3.5 h-3.5 shrink-0" />
              <span className="font-semibold">{stage.label}</span>
              {!!badge && (
                <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  {badge}
                </span>
              )}
            </button>
            {idx < JOURNEY_STAGES.length - 1 && (
              <ChevronRight className="w-3.5 h-3.5 text-text-muted/40 shrink-0" />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

export default JourneyStepper;
