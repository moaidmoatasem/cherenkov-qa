/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { ChevronRight, Check, X, Loader2, Minus } from 'lucide-react';
import { useJourney, SURFACE_CHROME } from '../../journey/config';
import { useJourneyRun } from '../../journey/useJourneyRun';
import type { StepStatus, WorkspaceId } from '../../journey/types';

interface JourneyStepperProps {
  activeWorkspace: WorkspaceId;
  onSelectWorkspace: (workspace: WorkspaceId) => void;
  pendingReviewCount?: number;
  /** The run whose progress this rail reflects, if any. */
  activeRunId?: string | null;
}

const STATUS_STYLES: Record<StepStatus, string> = {
  complete: 'bg-emerald-500/80 text-slate-950 border-transparent',
  running: 'bg-cyan-400 text-slate-950 border-transparent',
  failed: 'bg-rose-500/90 text-slate-950 border-transparent',
  blocked: 'bg-slate-700 text-slate-400 border-transparent',
  skipped: 'bg-slate-700 text-slate-400 border-transparent',
  not_started: 'border border-text-muted/40 text-text-muted',
};

/** Screen readers get the state in words, not just a colour. */
const STATUS_WORDS: Record<StatusKey, string> = {
  complete: 'complete',
  running: 'in progress',
  failed: 'failed',
  blocked: 'blocked',
  skipped: 'skipped',
  not_started: 'not started',
};

type StatusKey = StepStatus;

function StatusMark({ status, step }: { status: StepStatus; step: number }) {
  if (status === 'complete') return <Check className="w-2.5 h-2.5" />;
  if (status === 'failed') return <X className="w-2.5 h-2.5" />;
  if (status === 'running') return <Loader2 className="w-2.5 h-2.5 animate-spin" />;
  if (status === 'blocked' || status === 'skipped') {
    return <Minus className="w-2.5 h-2.5" />;
  }
  return <>{step}</>;
}

export const JourneyStepper: React.FC<JourneyStepperProps> = ({
  activeWorkspace,
  onSelectWorkspace,
  pendingReviewCount = 0,
  activeRunId = null,
}) => {
  const { journey } = useJourney();
  const { data: run } = useJourneyRun(activeRunId);

  const stages = journey.stages;
  const activeIndex = stages.findIndex((s) => s.surface === activeWorkspace);

  // Settings and Mobile are not steps in the loop; lighting them up here would
  // imply they come after Knowledge.
  if (activeIndex === -1) return null;

  const statusBySurface = new Map(
    (run?.stages ?? []).map((s) => [s.surface, s.status as StepStatus])
  );

  return (
    <div
      className="flex items-center gap-1 px-6 py-2 border-b border-border-subtle bg-bg-surface/60 overflow-x-auto shrink-0"
      data-testid="journey-stepper"
      aria-label="Cherenkov QA workflow"
    >
      {stages.map((stage, idx) => {
        const Icon = SURFACE_CHROME[stage.surface].icon;
        const isActive = stage.surface === activeWorkspace;
        // Progress comes from the run, never from where the user happens to be
        // standing. Without a run, nothing is claimed to have happened.
        const status: StepStatus = statusBySurface.get(stage.surface) ?? 'not_started';
        const badge = stage.surface === 'triage' ? pendingReviewCount : undefined;

        return (
          <React.Fragment key={stage.surface}>
            <button
              onClick={() => onSelectWorkspace(stage.surface)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono transition-all whitespace-nowrap cursor-pointer ${
                isActive
                  ? 'bg-cyan-500/15 border border-cyan-500/40 text-cyan-400'
                  : 'text-text-muted hover:text-text-primary hover:bg-white/5 border border-transparent'
              }`}
              title={stage.blurb}
              aria-current={isActive ? 'step' : undefined}
              data-testid={`journey-step-${stage.surface}`}
              data-status={status}
            >
              <span
                className={`flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold shrink-0 ${STATUS_STYLES[status]}`}
              >
                <StatusMark status={status} step={stage.step} />
              </span>
              <Icon className="w-3.5 h-3.5 shrink-0" />
              <span className="font-semibold">{stage.label}</span>
              <span className="sr-only">{STATUS_WORDS[status]}</span>
              {!!badge && (
                <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  {badge}
                </span>
              )}
            </button>
            {idx < stages.length - 1 && (
              <ChevronRight className="w-3.5 h-3.5 text-text-muted/40 shrink-0" />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

export default JourneyStepper;
