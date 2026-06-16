import { Project, EndpointRichness, TestItem, FailingTest, Divergence } from '../../src/types';
import { INITIAL_PROJECTS, MOCK_ENDPOINTS, INITIAL_TESTS, INITIAL_FAILURES, MOCK_DIVERGENCES } from '../api_mocks';

let _counter = 0;
function uid(prefix = 'id') { return `${prefix}-${++_counter}-${Date.now()}`; }

export function resetCounter() { _counter = 0; }

export function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: uid('proj'),
    name: `Test Project ${_counter}`,
    lastRun: 'just now',
    pipelineStatus: { ingest: 'done', plan: 'done', generate: 'done', review: 'done' },
    stats: { testsCount: 10, passRate: 90, healingCount: 0 },
    sparkline: [80, 85, 88, 90],
    lastRunDuration: { durationMs: 5000, limitMs: 10000 },
    ...overrides,
  };
}

export function makeProjects(n: number, overrides: Partial<Project> = {}): Project[] {
  return Array.from({ length: n }, (_, i) => makeProject({ ...overrides, id: `proj-batch-${i}`, name: `Batch Project ${i}` }));
}

export function makeEndpoint(overrides: Partial<EndpointRichness> = {}): EndpointRichness {
  const methods: EndpointRichness['method'][] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'];
  return {
    id: uid('ep'),
    method: methods[_counter % methods.length],
    path: `/api/resource-${_counter}`,
    richness: Math.random(),
    band: 'full',
    missingElements: [],
    ...overrides,
  };
}

export function makeEndpoints(n: number): EndpointRichness[] {
  return Array.from({ length: n }, (_, i) => makeEndpoint({ id: `ep-batch-${i}`, path: `/api/resource-${i}` }));
}

export function makeTestItem(overrides: Partial<TestItem> = {}): TestItem {
  return {
    id: uid('test'),
    name: `Test ${_counter}`,
    path: `/api/test-${_counter}`,
    method: 'GET',
    confidence: 0.9,
    verdict: 'approved',
    gates: { syntax: true, structure: true, ast: true, novelty: true, dryRun: true, quality: true },
    gateReasons: {},
    code: `test('generated test ${_counter}', async () => { expect(true).toBe(true); });`,
    ...overrides,
  };
}

export function makeFailingTest(overrides: Partial<FailingTest> = {}): FailingTest {
  const types: FailingTest['failureType'][] = ['CONTRACT_DRIFT', 'AUTH_EXPIRY', 'STATE_SEQUENCING', 'NETWORK_FLAKY', 'ASSERTION_DRIFT'];
  return {
    id: uid('fail'),
    name: `Failing Test ${_counter}`,
    failureType: types[_counter % types.length],
    diagnosis: `Diagnosis for test ${_counter}`,
    oldCode: `// old code ${_counter}`,
    proposedCode: `// proposed code ${_counter}`,
    ...overrides,
  };
}

export function makeDivergence(overrides: Partial<Divergence> = {}): Divergence {
  const severities: Divergence['severity'][] = ['critical', 'high', 'medium', 'low', 'info'];
  const statuses: Divergence['status'][] = ['reproduced', 'pending', 'rejected', 'live'];
  const classes: Divergence['divergenceClass'][] = ['D1', 'D2', 'D3', 'D4', 'D5'];
  return {
    id: uid('D'),
    divergenceClass: classes[_counter % classes.length],
    endpoint: `POST /api/resource-${_counter}`,
    severity: severities[_counter % severities.length],
    status: statuses[_counter % statuses.length],
    claimA: 'Spec claim',
    claimB: 'Runtime claim',
    evidence: 'Evidence payload',
    reproSteps: 'Step 1: Reproduce',
    confidence: 0.9,
    ...overrides,
  };
}

export function makeDivergences(n: number): Divergence[] {
  return Array.from({ length: n }, (_, i) => makeDivergence({ id: `D-batch-${i}`, endpoint: `POST /api/resource-${i}` }));
}

export const STRESS_PROJECTS = makeProjects(50);
export const STRESS_ENDPOINTS = makeEndpoints(100);
export const STRESS_DIVERGENCES = makeDivergences(20);
export const EMPTY_PROJECTS: Project[] = [];
export const EMPTY_ENDPOINTS: EndpointRichness[] = [];
export const EMPTY_TESTS: TestItem[] = [];
export const EMPTY_FAILURES: FailingTest[] = [];
export const EMPTY_DIVERGENCES: Divergence[] = [];

export function makeXssPayloads(): string[] {
  return [
    '<script>alert("xss")</script>',
    '<img src=x onerror=alert(1)>',
    '"><script>alert(String.fromCharCode(88,83,83))</script>',
    "' OR '1'='1",
    '"; DROP TABLE users; --',
    '<svg/onload=alert(document.cookie)>',
    '{{constructor.constructor("return this")()}}',
    '${7*7}',
    'javascript:alert(1)',
    '<iframe src="javascript:alert(1)">',
    null as any,
    undefined as any,
    '',
  ].filter(p => p !== null && p !== undefined);
}

export function makeBoundaryValues(): { field: string; values: (string | number)[] }[] {
  return [
    { field: 'passRate', values: [0, 1, 50, 99, 100, -1, 101, 999999, 0.5, NaN] },
    { field: 'confidence', values: [0, 0.01, 0.5, 0.99, 1, -0.1, 1.5, NaN] },
    { field: 'testsCount', values: [0, 1, 100, 10000, -1, 999999999] },
    { field: 'string', values: ['', 'a', ' '.repeat(10000), '\x00', '\n\r\t', 'émojis 🎉🚀', '<>'.repeat(500)] },
  ];
}
