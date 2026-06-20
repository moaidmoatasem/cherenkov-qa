/**
 * Cherenkov QA API Client Configuration
 * In development, Vite proxies /api/v1/* to http://127.0.0.1:8000/api/v1/*.
 * In production builds, the static files and API are hosted under the same origin.
 */

import type {
  SddStatusResponse, SddSessionSummary, SddSessionDetail,
  SddExperience, SddTokenData, SddContextData,
  GraphData, PatternInsight, WikiEntry, SddFinding,
} from '../types';

export const API_BASE = '/api/v1';

export interface IngestResponse {
  spec_path: string;
  endpoints: any[];
  richness: number;
}

export interface RunPipelinePayload {
  spec_path: string;
  target_url?: string;
  auth_header?: string;
  demo_mode?: boolean;
  intent?: string;
}

export interface RunPipelineResponse {
  run_id: string;
  status: string;
}

export interface GeneratedTestFile {
  name: string;
  scenario_id: string;
  endpoint: string;
  method: string;
  code: string;
}

export interface ReviewQueueItem {
  id: string;
  endpoint: string;
  method: string;
  confidence: number;
  confidence_reason: string | null;
  review_gate_failed: string | null;
  status: string;
  generated_test: string | null;
  created_at: string;
}

export interface ValidationResponse {
  status: string;
  target_url: string;
  reports: any[];
}

/**
 * Checks if the backend server is online and operational
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
    return res.ok;
  } catch (e) {
    return false;
  }
}

/**
 * Fetches the full backend health status
 */
export async function fetchHealth(): Promise<{ status: string; device: string; gen_model: string; demo_mode: boolean }> {
  const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
  if (!res.ok) throw new Error(`Health endpoint failed: ${res.status}`);
  return res.json();
}

/**
 * Ingests an OpenAPI spec file or URL to parse richness coverage segments
 */
export async function ingestSpec(
  file: File | null,
  url: string | null
): Promise<IngestResponse> {
  const formData = new FormData();
  if (file) {
    formData.append('file', file);
  }
  if (url) {
    formData.append('url', url);
  }

  const res = await fetch(`${API_BASE}/ingest`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Spec ingestion failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Triggers the core OrchestrationEngine pipeline run asynchronously
 */
export async function runPipeline(payload: RunPipelinePayload): Promise<RunPipelineResponse> {
  const res = await fetch(`${API_BASE}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to run generation pipeline: ${res.status}`);
  }

  return res.json();
}

/**
 * Fetch all generated spec files
 */
export async function fetchGeneratedTests(): Promise<GeneratedTestFile[]> {
  const res = await fetch(`${API_BASE}/tests`);
  if (!res.ok) return [];
  return res.json();
}

/**
 * Handles approving a test scenario inside the HITL review queue
 */
export async function approveTestScenario(scenarioId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/review/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  if (!res.ok) {
    throw new Error(`Failed to approve scenario ${scenarioId}`);
  }
}

/**
 * Handles rejecting and triggering regeneration of a test scenario
 */
export async function rejectTestScenario(scenarioId: string, reason: string): Promise<void> {
  const res = await fetch(`${API_BASE}/review/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId, reason }),
  });
  if (!res.ok) {
    throw new Error(`Failed to reject scenario ${scenarioId}`);
  }
}

/**
 * Request an AI explanation for why a test was flagged in the review gate
 */
export async function explainTestScenario(scenarioId: string): Promise<{ explanation: string }> {
  const res = await fetch(`${API_BASE}/review/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  if (!res.ok) {
    throw new Error(`Failed to explain scenario ${scenarioId}`);
  }
  return res.json();
}

/**
 * Handles saving custom manual edits to a generated test file
 */
export async function editTestScenario(scenarioId: string, testCode: string): Promise<void> {
  const res = await fetch(`${API_BASE}/review/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId, test_code: testCode }),
  });
  if (!res.ok) {
    throw new Error(`Failed to save edits for scenario ${scenarioId}`);
  }
}

/**
 * Triggers the Playwright ValidationEngine run against the target URL
 */
export async function validateSuite(targetUrl: string): Promise<ValidationResponse> {
  const res = await fetch(`${API_BASE}/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_url: targetUrl }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Validation execution failed: ${res.status}`);
  }

  return res.json();
}


export interface EjectResponse {
  status: string;
  output_path: string;
  files: string[];
}

export async function ejectSuite(outputPath: string): Promise<EjectResponse> {
  const res = await fetch(`${API_BASE}/eject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ output_path: outputPath }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Eject operation failed: ${res.status}`);
  }

  return res.json();
}

import { Divergence, FailingTest } from '../types';

export interface OverviewData {
  releaseReadiness: number;
  falsePositiveRate: number;
  recentLearnings: Array<{ id: string; text: string }>;
}

export async function fetchOverviewData(): Promise<OverviewData> {
  const res = await fetch(`${API_BASE}/overview`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch overview: ${res.status}`);
  }
  return res.json();
}

export type ProvenanceType = 'spec' | 'code' | 'traffic' | 'db';

export interface TruthMapNode {
  endpoint: string;
  hasDivergence: boolean;
  claims: Array<{
    id: string;
    provenance: ProvenanceType;
    claim: string;
  }>;
}

export async function fetchTruthMapData(): Promise<TruthMapNode[]> {
  const res = await fetch(`${API_BASE}/truth-map`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch truth map: ${res.status}`);
  }
  return res.json();
}

export async function fetchFailuresData(): Promise<FailingTest[]> {
  const res = await fetch(`${API_BASE}/failures`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch failures: ${res.status}`);
  }
  return res.json();
}

export interface MetricsData {
  status: string;
  metrics: {
    requestCount: number;
    totalTokens: number;
    totalCost: number;
    totalDurationMs: number;
    defectEscapeCount: number;
    falsePositiveRate: number;
    maintenanceEfficiency: number;
  };
}

export async function fetchMetricsData(): Promise<MetricsData> {
  const res = await fetch(`${API_BASE}/metrics`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch metrics: ${res.status}`);
  }
  return res.json();
}

export async function fetchDivergencesData(): Promise<Divergence[]> {
  const res = await fetch(`${API_BASE}/divergences`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch divergences: ${res.status}`);
  }
  return res.json();
}

export async function submitReviewApprove(scenarioId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/review/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to approve scenario ${scenarioId}: ${res.status}`);
  }
}

export async function submitReviewReject(scenarioId: string, reason: string): Promise<void> {
  const res = await fetch(`${API_BASE}/review/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId, reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to reject scenario ${scenarioId}: ${res.status}`);
  }
}

export async function fetchDivergences(): Promise<Divergence[]> {
  const res = await fetch(`${API_BASE}/divergences`);
  if (!res.ok) {
    throw new Error(`Failed to fetch divergences: ${res.status}`);
  }
  return res.json();
}

export async function actOnDivergence(
  divergenceId: string,
  action: 'close_with_test' | 'mark_intended' | 'reject',
  reason?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/divergences/act`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ divergence_id: divergenceId, action, reason }),
  });
  if (!res.ok) {
    throw new Error(`Failed to perform action ${action} on divergence ${divergenceId}`);
  }
}

export async function fetchReviewQueue(status?: string): Promise<ReviewQueueItem[]> {
  const params = status ? `?status=${encodeURIComponent(status)}` : '';
  const res = await fetch(`${API_BASE}/review/queue${params}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch review queue: ${res.status}`);
  }
  return res.json();
}

export interface SystemSettings {
  target: { url: string; auth_header?: string };
  engine: { model_tier: string; enable_demo_mode: boolean; execution_budget: number; workers: number };
  security: { egress_policy: string; auth_secret?: string };
  ui: { density: string; reduced_motion: boolean };
}

export async function fetchSettings(): Promise<SystemSettings> {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error('Failed to load settings');
  return res.json();
}

export async function updateSettings(settings: SystemSettings): Promise<void> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save settings');
}

export interface DoctorCheck {
  id: string;
  name: string;
  status: 'passed' | 'failed' | 'warning' | 'pending';
  message?: string;
}

export async function fetchDoctor(): Promise<{ checks: DoctorCheck[], ready: boolean }> {
  const res = await fetch(`${API_BASE}/doctor`);
  if (!res.ok) throw new Error('Failed to run doctor checks');
  return res.json();
}

export async function fetchProjects() {
  const res = await fetch(`${API_BASE}/projects`);
  if (!res.ok) return [];
  return res.json();
}

export async function createProject(payload: {
  name: string;
  target_url?: string;
  spec_path?: string;
  repo_type?: 'new' | 'existing';
  repo_path?: string;
}) {
  const res = await fetch(`${API_BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to create project');
  return res.json();
}

export async function updateProject(id: string, payload: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/projects/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to update project');
  return res.json();
}

export async function fetchTruthMap() {
  const res = await fetch(`${API_BASE}/truth-map`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchFailures() {
  const res = await fetch(`${API_BASE}/failures`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchGovernance() {
  const res = await fetch(`${API_BASE}/governance`);
  if (!res.ok) return { score: 100, issues: [] };
  return res.json();
}

export async function fetchMemory() {
  const res = await fetch(`${API_BASE}/memory`);
  if (!res.ok) return { idioms: [], pairing: [] };
  return res.json();
}

export async function fetchSignals() {
  const res = await fetch(`${API_BASE}/signals`);
  if (!res.ok) return { performance: [], visual: [], coverage: [] };
  return res.json();
}

export async function fetchOverview() {
  const res = await fetch(`${API_BASE}/overview`);
  if (!res.ok) return { falsePositiveRate: 0, recentLearnings: [] };
  return res.json();
}

export async function createChatSession(persona_id = 'qa_assistant'): Promise<{ session_id: string; persona_id: string }> {
  const res = await fetch(`${API_BASE}/chat/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona_id }),
  });
  if (!res.ok) throw new Error(`Failed to create chat session: ${res.status}`);
  return res.json();
}

/**
 * Stream a chat message via SSE. Calls onToken for each streamed token,
 * resolves the full accumulated response when the stream completes.
 */
export async function streamChatMessage(
  sessionId: string,
  content: string,
  onToken: (token: string) => void,
  signal?: AbortSignal,
): Promise<string> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
    signal,
  });
  if (!res.ok) throw new Error(`Chat stream failed: ${res.status}`);

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';
  let accumulated = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';
    for (const part of parts) {
      if (!part.trim()) continue;
      const dataLine = part.split('\n').find((l) => l.startsWith('data:'));
      if (!dataLine) continue;
      try {
        const parsed = JSON.parse(dataLine.slice(5).trim());
        if (parsed.token) {
          accumulated += parsed.token;
          onToken(parsed.token);
        }
      } catch {
        // ignore malformed SSE frames
      }
    }
  }
  return accumulated;
}

export async function fetchChatMessages(sessionId: string): Promise<{ messages: Array<{ role: string; content: string }> }> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error(`Failed to fetch chat messages: ${res.status}`);
  return res.json();
}

export async function queryKnowledge(query: string): Promise<any> {
  const res = await fetch(`${API_BASE}/chat/knowledge/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`Knowledge query failed: ${res.status}`);
  return res.json();
}

export interface PilotStep {
  step_id: string;
  action: string;
  target: string;
  expected: string;
  actual: string;
  status: string;
}

export interface PilotStatus {
  status: 'idle' | 'running' | 'done' | 'failed';
  current_step: number;
  total_steps: number;
  steps: PilotStep[];
}

export async function fetchMobilePilotStatus(): Promise<PilotStatus> {
  const res = await fetch(`${API_BASE}/mobile/pilot/status`);
  if (!res.ok) throw new Error(`Failed to fetch pilot status: ${res.status}`);
  return res.json();
}

export async function startMobilePilot(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/mobile/pilot/start`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to start pilot: ${res.status}`);
  return res.json();
}

// ── SDD Agent Cockpit API ─────────────────────────────────────────────

export async function fetchSddStatus(): Promise<SddStatusResponse> {
  const res = await fetch(`${API_BASE}/sdd/status`);
  if (!res.ok) return { session: {}, current_tokens: { session_id: null, prompt: 0, generate: 0, read: 0, search: 0, total: 0 }, budget: {}, historical: { total_all_time: 0, sessions_completed: 0, avg_per_session: 0, by_task_type: {} }, experience_count: 0, sessions_since_compact: 0 };
  return res.json();
}

export async function fetchSddSessions(limit = 50, taskType?: string): Promise<SddSessionSummary[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (taskType) params.set('task_type', taskType);
  const res = await fetch(`${API_BASE}/sdd/sessions?${params}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchSddSessionDetail(sessionId: string): Promise<SddSessionDetail> {
  const res = await fetch(`${API_BASE}/sdd/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Session not found: ${res.status}`);
  return res.json();
}

export async function querySddExperience(pattern?: string, outcome?: string, sort?: string, limit = 50): Promise<SddExperience[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (pattern) params.set('pattern', pattern);
  if (outcome) params.set('outcome', outcome);
  if (sort) params.set('sort', sort);
  const res = await fetch(`${API_BASE}/sdd/experience?${params}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchSddTokens(): Promise<SddTokenData> {
  const res = await fetch(`${API_BASE}/sdd/tokens`);
  if (!res.ok) return { current_session: { session_id: null, prompt: 0, generate: 0, read: 0, search: 0, total: 0 }, budget: {}, historical: { total_all_time: 0, sessions_completed: 0, avg_per_session: 0, by_task_type: {} }, top_consumers: [] };
  return res.json();
}

export async function fetchSddContext(): Promise<SddContextData> {
  const res = await fetch(`${API_BASE}/sdd/context`);
  if (!res.ok) return { version: 1, last_refreshed: '', snippets: [], task_type_map: {} };
  return res.json();
}

export async function triggerSddCompact(force = false): Promise<void> {
  await fetch(`${API_BASE}/sdd/compact?force=${force}`, { method: 'POST' });
}

export async function fetchSddGraph(): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/sdd/graph/export`);
  if (!res.ok) return { nodes: [], edges: [] };
  return res.json();
}

export async function fetchSddPatterns(): Promise<PatternInsight[]> {
  const res = await fetch(`${API_BASE}/sdd/graph/patterns`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchSddWikiTree(): Promise<WikiEntry[]> {
  const res = await fetch(`${API_BASE}/sdd/wiki/tree`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchSddWikiFile(path: string): Promise<{ path: string; content: string; size: number; last_updated: string }> {
  const res = await fetch(`${API_BASE}/sdd/wiki/${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error(`Wiki file not found: ${res.status}`);
  return res.json();
}

export async function fetchSddFindings(sessionId?: string, limit = 100): Promise<SddFinding[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (sessionId) params.set('session_id', sessionId);
  const res = await fetch(`${API_BASE}/sdd/findings?${params}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchVisualScenarios(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/visual/scenarios`);
  if (!res.ok) return [];
  return res.json();
}

export async function runExplorer(payload: { base_url: string; ui_url?: string; use_ui_probe?: boolean; max_links?: number }): Promise<any> {
  const res = await fetch(`${API_BASE}/explore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Explorer run failed: ${res.status}`);
  return res.json();
}

// ── OCR Review API ──────────────────────────────────────────────────

export interface OCRFindingResponse {
  file: string;
  line: number;
  column: number;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  rule: string;
  message: string;
  suggestion: string;
}

export interface OCRReviewResponse {
  passed: boolean;
  findings: OCRFindingResponse[];
  score_deduction: number;
  agent_summary: string;
  llm_model: string;
  duration_ms: number;
  error: string;
}

export async function fetchOcrReview(scenarioId: string): Promise<OCRReviewResponse> {
  const res = await fetch(`${API_BASE}/ocr/review/${encodeURIComponent(scenarioId)}`);
  if (!res.ok) {
    if (res.status === 404) throw new Error('No OCR review available for this scenario');
    throw new Error(`OCR review fetch failed: ${res.status}`);
  }
  return res.json();
}

export async function runOcrReview(scenarioId: string, code: string): Promise<OCRReviewResponse> {
  const res = await fetch(`${API_BASE}/ocr/review/${encodeURIComponent(scenarioId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  if (!res.ok) throw new Error(`OCR review run failed: ${res.status}`);
  return res.json();
}

export async function fetchOcrStatus(): Promise<{ installed: boolean; binary: string; version: string; error: string }> {
  const res = await fetch(`${API_BASE}/ocr/status`);
  if (!res.ok) return { installed: false, binary: 'ocr', version: '', error: 'Could not check status' };
  return res.json();
}
