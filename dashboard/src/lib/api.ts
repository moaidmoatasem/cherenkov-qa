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
