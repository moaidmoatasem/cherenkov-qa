/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

// ── SDD Agent Cockpit Types ──────────────────────────────────────────

export interface SddStatusResponse {
  session: Record<string, unknown>;
  current_tokens: {
    session_id: string | null;
    prompt: number;
    generate: number;
    read: number;
    search: number;
    total: number;
  };
  budget: Record<string, unknown>;
  historical: {
    total_all_time: number;
    sessions_completed: number;
    avg_per_session: number;
    by_task_type: Record<string, { sessions: number; total_tokens: number }>;
  };
  experience_count: number;
  sessions_since_compact: number;
}

export interface SddSessionSummary {
  id: string;
  status: string;
  task: string | null;
  task_type?: string | null;
  started_at: string | null;
  ended_at: string | null;
  findings_count: number;
  token_total: number;
  summary: string | null;
  compacted?: boolean;
}

export interface SddFinding {
  timestamp: string;
  type: string;
  message: string;
  _session_id?: string;
}

export interface SddSessionDetail {
  session: SddSessionSummary;
  findings: SddFinding[];
}

export interface SddExperience {
  id: string;
  timestamp: string;
  task: string | null;
  action: string;
  rationale: string;
  outcome: string;
  token_cost: number;
  patterns: string[];
  session_id: string;
  applicable_tasks?: string[];
}

export interface SddTokenData {
  current_session: {
    session_id: string | null;
    prompt: number;
    generate: number;
    read: number;
    search: number;
    total: number;
  };
  budget: Record<string, unknown>;
  historical: {
    total_all_time: number;
    sessions_completed: number;
    avg_per_session: number;
    by_task_type: Record<string, { sessions: number; total_tokens: number }>;
  };
  top_consumers: Array<{
    timestamp: string;
    action: string;
    count: number;
    item: string;
    running_total: number;
  }>;
}

export interface SddContextData {
  version: number;
  last_refreshed: string;
  snippets: Array<{
    key: string;
    task_types: string[];
    tokens_estimate: number;
    content: string;
  }>;
  task_type_map: Record<string, string[]>;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  properties?: Record<string, unknown>;
  size: number;
  color: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
  label: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface WikiEntry {
  path: string;
  title: string;
  size: number;
  last_updated: string;
  cross_refs: string[];
}

export interface PatternInsight {
  name: string;
  frequency: number;
  success_rate: number;
  avg_token_cost: number;
  experience_ids: string[];
}

// ── End SDD Types ──────────────────────────────────────────────────

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

export type SeverityType = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type StatusType = 'reproduced' | 'pending' | 'rejected' | 'live';

export interface Divergence {
  id: string;
  divergenceClass: 'D1' | 'D2' | 'D3' | 'D4' | 'D5';
  endpoint: string;
  severity: SeverityType;
  status: StatusType;
  claimA: string;
  claimB: string;
  evidence: string;
  reproSteps: string;
  confidence?: number;
}
