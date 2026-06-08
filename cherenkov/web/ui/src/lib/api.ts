/**
 * Cherenkov QA API Client Configuration
 * In development, Vite proxies /api/v1/* to http://127.0.0.1:8000/api/v1/*.
 * In production builds, the static files and API are hosted under the same origin.
 */

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
 * Fetches the backend health info and determines if Ollama is available
 */
export async function fetchHealth(): Promise<{ ollama_available: boolean }> {
  const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
  if (!res.ok) throw new Error(`Health endpoint failed: ${res.status}`);
  const data = await res.json();
  return { ollama_available: data.device !== 'unknown' };
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

import { Divergence } from '../types';

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
  if (!res.ok) return { performance: [], visual: [], coverage: {} };
  return res.json();
}

export async function fetchOverview() {
  const res = await fetch(`${API_BASE}/overview`);
  if (!res.ok) return { falsePositiveRate: 0, recentLearnings: [] };
  return res.json();
}

export async function createChatSession(): Promise<{ session_id: string; persona_id: string }> {
  const res = await fetch(`${API_BASE}/chat/sessions`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to create chat session: ${res.status}`);
  return res.json();
}

export async function fetchChatMessages(sessionId: string): Promise<{ messages: Array<{ role: string; content: string }> }> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error(`Failed to fetch chat messages: ${res.status}`);
  return res.json();
}
