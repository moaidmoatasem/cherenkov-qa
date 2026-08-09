/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type WorkspaceId =
  | 'dashboard'
  | 'authoring'
  | 'triage'
  | 'intelligence'
  | 'settings'
  | 'mobile'
  | 'enterprise';

export type StepStatus =
  | 'not_started'
  | 'running'
  | 'complete'
  | 'failed'
  | 'blocked'
  | 'skipped';

/** "auto" steps are run by the engine; "manual" ones are a person's job. */
export type StepExecution = 'auto' | 'manual';

export interface JourneyStep {
  id: string;
  kind: string;
  label: string;
  blurb: string;
  surface: WorkspaceId;
  execution: StepExecution;
  requires: string[];
  optional: boolean;
}

/** One user-facing stage: several engine steps rolled up under one surface. */
export interface JourneyStage {
  surface: WorkspaceId;
  step: number;
  label: string;
  blurb: string;
  step_ids: string[];
}

export interface JourneyDefinition {
  id: string;
  version: number;
  label: string;
  description: string;
  steps: JourneyStep[];
  stages: JourneyStage[];
}

export interface JourneyCatalogue {
  default: string | null;
  journeys: JourneyDefinition[];
}

export interface RunStepState {
  id: string;
  label: string;
  surface: WorkspaceId;
  execution: StepExecution;
  status: StepStatus;
  duration_ms: number | null;
}

export interface RunStageState extends JourneyStage {
  status: StepStatus;
}

export interface JourneyRunState {
  run_id: string;
  journey_id: string;
  status: 'running' | 'complete' | 'failed' | 'aborted';
  verdict: string;
  target_url: string;
  timestamp: string;
  duration_ms: number;
  steps: RunStepState[];
  stages: RunStageState[];
}

export interface ChainStepSummary {
  id: string;
  method: string;
  endpoint: string;
  expected_status: number;
  creates_resource: boolean;
  captures: { name: string; pointer: string }[];
  uses: Record<string, string>;
}

export interface DetectedChain {
  id: string;
  label: string;
  resource: string;
  mutating: boolean;
  detected_by: string;
  confidence: number;
  steps: ChainStepSummary[];
}
