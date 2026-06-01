/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export interface Project {
  id: string;
  name: string;
  lastRun: string;
  pipelineStatus: {
    ingest: 'done' | 'running' | 'queued' | 'failed';
    plan: 'done' | 'running' | 'queued' | 'failed';
    generate: 'done' | 'running' | 'queued' | 'failed';
    review: 'done' | 'running' | 'queued' | 'failed';
    visual?: 'done' | 'running' | 'queued' | 'failed';
    perf?: 'done' | 'running' | 'queued' | 'failed';
  };
  stats: {
    testsCount: number;
    passRate: number; // 0 to 100
    healingCount: number;
  };
  sparkline: number[]; // Array of pass rates over last runs
  lastRunDuration?: {
    durationMs: number;
    limitMs: number;
  };
}

export interface EndpointRichness {
  id: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  path: string;
  richness: number; // 0.0 to 1.0
  band: 'full' | 'inferred' | 'degraded';
  missingElements: string[];
}

export type StageId = 'ingest' | 'plan' | 'generate' | 'review' | 'visual' | 'perf';

export interface PipelineStage {
  id: StageId;
  name: string;
  status: 'done' | 'running' | 'queued' | 'failed';
  summary: string;
}

export interface TestGate {
  syntax: boolean;
  structure: boolean;
  ast: boolean;
  novelty: boolean;
  dryRun: boolean;
  quality: boolean;
}

export interface TestItem {
  id: string;
  name: string;
  path: string;
  method: string;
  confidence: number; // 0 to 1
  verdict: 'approved' | 'review' | 'regenerating' | 'rejected';
  gates: TestGate;
  gateReasons: { [key in keyof TestGate]?: string };
  code: string;
  actualResult?: {
    status: 'passed' | 'failed';
    stdout: string;
    duration: string;
  };
}

export interface FailingTest {
  id: string;
  name: string;
  failureType: 'CONTRACT_DRIFT' | 'AUTH_EXPIRY' | 'STATE_SEQUENCING' | 'NETWORK_FLAKY' | 'ASSERTION_DRIFT';
  diagnosis: string;
  oldCode: string;
  proposedCode: string;
  hasAssertionWarning?: boolean;
}
