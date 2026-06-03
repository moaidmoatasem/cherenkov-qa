/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Project, EndpointRichness, TestItem, FailingTest } from './types';

export const INITIAL_PROJECTS: Project[] = [
  {
    id: 'proj-petstore',
    name: 'Swagger Petstore v2',
    lastRun: '2 hours ago',
    pipelineStatus: {
      ingest: 'done',
      plan: 'done',
      generate: 'done',
      review: 'done'
    },
    stats: {
      testsCount: 47,
      passRate: 91,
      healingCount: 3
    },
    sparkline: [75, 80, 82, 88, 91, 91],
    lastRunDuration: { durationMs: 14800, limitMs: 20000 }
  },
  {
    id: 'proj-checkout-api',
    name: 'Checkout Gateway API',
    lastRun: '1 day ago',
    pipelineStatus: {
      ingest: 'done',
      plan: 'done',
      generate: 'done',
      review: 'done'
    },
    stats: {
      testsCount: 32,
      passRate: 84,
      healingCount: 1
    },
    sparkline: [90, 88, 85, 84, 84],
    lastRunDuration: { durationMs: 8400, limitMs: 15000 }
  },
  {
    id: 'proj-auth-identity',
    name: 'Identity Provider OAuth',
    lastRun: '3 days ago',
    pipelineStatus: {
      ingest: 'done',
      plan: 'done',
      generate: 'done',
      review: 'failed'
    },
    stats: {
      testsCount: 18,
      passRate: 61,
      healingCount: 4
    },
    sparkline: [80, 78, 70, 65, 61],
    lastRunDuration: { durationMs: 28200, limitMs: 30000 }
  }
];

export const MOCK_ENDPOINTS: EndpointRichness[] = [
  { id: 'ep-1', method: 'POST', path: '/pets', richness: 0.95, band: 'full', missingElements: [] },
  { id: 'ep-2', method: 'GET', path: '/pets/{petId}', richness: 0.88, band: 'full', missingElements: [] },
  { id: 'ep-3', method: 'PUT', path: '/pets', richness: 0.72, band: 'full', missingElements: ['missing 400 response model details'] },
  { id: 'ep-4', method: 'DELETE', path: '/pets/{petId}', richness: 0.55, band: 'inferred', missingElements: ['missing 404 error schema'] },
  { id: 'ep-5', method: 'POST', path: '/pets/{petId}/uploadImage', richness: 0.42, band: 'degraded', missingElements: ['empty multipart/form-data detail', 'missing 2xx response template'] },
  { id: 'ep-6', method: 'GET', path: '/store/inventory', richness: 0.90, band: 'full', missingElements: [] },
  { id: 'ep-7', method: 'POST', path: '/store/order', richness: 0.82, band: 'full', missingElements: [] },
  { id: 'ep-8', method: 'GET', path: '/store/order/{orderId}', richness: 0.68, band: 'inferred', missingElements: ['missing example UUID path params'] },
  { id: 'ep-9', method: 'DELETE', path: '/store/order/{orderId}', richness: 0.50, band: 'inferred', missingElements: ['undefined deletion state constraints'] },
  { id: 'ep-10', method: 'POST', path: '/user', richness: 0.92, band: 'full', missingElements: [] },
  { id: 'ep-11', method: 'POST', path: '/user/createWithArray', richness: 0.60, band: 'inferred', missingElements: ['missing body example arrays'] },
  { id: 'ep-12', method: 'POST', path: '/user/createWithList', richness: 0.58, band: 'inferred', missingElements: ['missing body list examples'] },
  { id: 'ep-13', method: 'GET', path: '/user/login', richness: 0.85, band: 'full', missingElements: [] },
  { id: 'ep-14', method: 'GET', path: '/user/logout', richness: 0.75, band: 'full', missingElements: [] },
  { id: 'ep-15', method: 'GET', path: '/user/{username}', richness: 0.80, band: 'full', missingElements: [] },
  { id: 'ep-16', method: 'PUT', path: '/user/{username}', richness: 0.65, band: 'inferred', missingElements: ['missing schema constraints for updates'] },
  { id: 'ep-17', method: 'DELETE', path: '/user/{username}', richness: 0.48, band: 'degraded', missingElements: ['missing auth context setup', 'missing 404 response'] },
  { id: 'ep-18', method: 'POST', path: '/checkout/initialize', richness: 0.77, band: 'full', missingElements: [] },
  { id: 'ep-19', method: 'GET', path: '/checkout/{checkoutId}', richness: 0.38, band: 'degraded', missingElements: ['missing checkout schema', 'complex nested links with no examples'] },
  { id: 'ep-20', method: 'POST', path: '/checkout/coupon', richness: 0.25, band: 'degraded', missingElements: ['no request body spec', 'missing coupon validation codes'] },
];

export const PIPELINE_STREAMING_TESTS = [
  {
    endpoint: 'POST /pets',
    agent: 'qwen2.5-coder:7b',
    code: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test.describe('POST /pets - Creates a Pet', () => {
  test('should successfully create a new pet in the inventory', async () => {
    const payload = {
      id: Math.floor(Math.random() * 100000),
      name: 'Cerberus',
      category: { id: 1, name: 'Guard Dogs' },
      photoUrls: ['https://example.com/images/cerberus.jpg'],
      tags: [{ id: 1, name: 'fierce' }, { id: 2, name: 'loyal' }],
      status: 'pending'
    };

    const { data, response } = await client.POST('/pets', { body: payload });
    
    // AST & Schema Compliance Assertions
    expect(response.status).toBe(201);
    expect(data).toBeDefined();
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('name');
    expect(data).toHaveProperty('category');
    expect(data).toHaveProperty('status');
  });

  test('should refuse creation with invalid input payload (400)', async () => {
    const badPayload = { id: 'invalid-string-id', name: '' };
    const { response } = await client.POST('/pets', { body: badPayload });
    expect(response.status).toBe(400);
  });
});`
  },
  {
    endpoint: 'GET /store/order/{orderId}',
    agent: 'qwen2.5-coder:7b',
    code: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test.describe('GET /store/order/{orderId} - Fetch Order Details', () => {
  const targetOrderId = 77102;

  test('should return details for an existing active order', async () => {
    const { data, response } = await client.GET('/store/order/{orderId}', {
      params: { path: { orderId: targetOrderId } }
    });
    
    expect(response.status).toBe(200);
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('petId');
    expect(data).toHaveProperty('quantity');
    expect(data).toHaveProperty('status');
  });

  test('should return 404 for order that does not exist', async () => {
    const fakeOrderId = 999999;
    const { response } = await client.GET('/store/order/{orderId}', {
      params: { path: { orderId: fakeOrderId } }
    });
    expect(response.status).toBe(404);
  });
});`
  }
];

export const INITIAL_TESTS: TestItem[] = [
  {
    id: 'test-1',
    name: 'POST /pets · Creates a pet',
    path: '/pets',
    method: 'POST',
    confidence: 0.98,
    verdict: 'approved',
    gates: { syntax: true, structure: true, ast: true, novelty: true, dryRun: true, quality: true },
    gateReasons: {
      quality: 'All required parameters exist, assert statements robust and structured properly.'
    },
    code: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('creates a pet successfully', async () => {
  const payload = { id: 1045, name: 'GlowDog', status: 'available' };
  const { data, response } = await client.POST('/pets', { body: payload });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
  expect(data).toHaveProperty('name');
});`
  },
  {
    id: 'test-2',
    name: 'GET /pets/{petId} · Returns pet detail',
    path: '/pets/{petId}',
    method: 'GET',
    confidence: 0.94,
    verdict: 'approved',
    gates: { syntax: true, structure: true, ast: true, novelty: true, dryRun: true, quality: true },
    gateReasons: {
      quality: 'Valid query param handling, path extraction matches OpenAPI specification.'
    },
    code: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('fetches pet details by ID', async () => {
  const { data, response } = await client.GET('/pets/{petId}', {
    params: { path: { petId: 1045 } }
  });
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
});`
  },
  {
    id: 'test-3',
    name: 'PUT /pets · Updates pet information',
    path: '/pets',
    method: 'PUT',
    confidence: 0.81,
    verdict: 'review',
    gates: { syntax: true, structure: true, ast: true, novelty: true, dryRun: true, quality: false },
    gateReasons: {
      quality: 'quality 0.78 — assertion checks shape but not the updated pet\'s descriptive name.',
      novelty: 'Somewhat overlap with POST /pets, but updates logic is unique.'
    },
    code: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('updates pet name and state', async () => {
  const updatePayload = { id: 1045, name: 'GlowDog-V2', status: 'pending' };
  const { data, response } = await client.PUT('/pets', { body: updatePayload });
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('status');
  // NOTE: quality warning triggered - missing verification that name matches
});`,
    actualResult: {
      status: 'passed',
      stdout: 'PASS: updates pet name and state (212ms)\nSchema validation OK',
      duration: '212ms'
    }
  },
  {
    id: 'test-4',
    name: 'DELETE /store/order/{orderId} · Removes inventory order',
    path: '/store/order/{orderId}',
    method: 'DELETE',
    confidence: 0.45,
    verdict: 'review',
    gates: { syntax: true, structure: true, ast: false, novelty: true, dryRun: false, quality: false },
    gateReasons: {
      ast: 'Failed check: missing standard error catching block.',
      dryRun: 'Returns 400 instead of 404 on clean database rerun.',
      quality: 'No clean pre-setup sequencing order item created.'
    },
    code: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('removes active store order', async () => {
  const { response } = await client.DELETE('/store/order/{orderId}', {
    params: { path: { orderId: 99201 } }
  });
  expect(response.status).toBe(200); // Bad assumption!
});`,
    actualResult: {
      status: 'failed',
      stdout: 'FAIL: removes active store order (114ms)\nReceived status: 400 (Bad Request). Error: ID is empty or invalid format.',
      duration: '114ms'
    }
  },
  {
    id: 'test-5',
    name: 'POST /checkout/coupon · Validates discount parameters',
    path: '/checkout/coupon',
    method: 'POST',
    confidence: 0.89,
    verdict: 'regenerating',
    gates: { syntax: true, structure: true, ast: true, novelty: false, dryRun: true, quality: true },
    gateReasons: {
      novelty: 'Redundant code: very similar to coupon validator routine from checkout-v1 spec.'
    },
    code: `// Test code currently rewriting dynamically... please wait`
  }
];

export const INITIAL_FAILURES: FailingTest[] = [
  {
    id: 'fail-1',
    name: 'POST /user/login · Validates account credentials',
    failureType: 'CONTRACT_DRIFT',
    diagnosis: 'Playwright execution found response field drift: server returned "user_session_token" but test verified "session_id" according to outdated OpenAPI specs.',
    oldCode: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('login validates contract parameters', async () => {
  const { data, response } = await client.GET('/user/login', {
    params: { query: { username: 'alpha', password: 'foo' } }
  });
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('session_id');
});`,
    proposedCode: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('login validates contract parameters', async () => {
  const { data, response } = await client.GET('/user/login', {
    params: { query: { username: 'alpha', password: 'foo' } }
  });
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('user_session_token');
});`
  },
  {
    id: 'fail-2',
    name: 'GET /store/inventory · Fetches inventory matrix',
    failureType: 'AUTH_EXPIRY',
    diagnosis: 'API server rejected negotiation with status code 401 (Unauthorized) due to invalid API token configuration.',
    oldCode: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('fetches stock level values', async () => {
  const { response } = await client.GET('/store/inventory', {
    params: { header: { 'X-Auth-Token': 'expired-mock-secret-token-uuid' } }
  });
  expect(response.status).toBe(200);
});`,
    proposedCode: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('fetches stock level values', async () => {
  const token = process.env.CHERENKOV_JWT_TOKEN || 'system-active-token';
  const { response } = await client.GET('/store/inventory', {
    params: { header: { 'X-Auth-Token': token } }
  });
  expect(response.status).toBe(200);
});`
  },
  {
    id: 'fail-3',
    name: 'DELETE /pets/{petId} · Removes target pet item',
    failureType: 'STATE_SEQUENCING',
    diagnosis: 'Deletion step isolated failed with reference 404. Deletes is order-dependent on first generating the specific ID token rather than relying on static petId of 99.',
    oldCode: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('removes specific pet', async () => {
  const { response } = await client.DELETE('/pets/{petId}', {
    params: { path: { petId: 99 } }
  });
  expect(response.status).toBe(200);
});`,
    proposedCode: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('removes specific pet', async () => {
  // Create first to capture valid ID
  const { data: pet } = await client.POST('/pets', {
    body: { name: 'Temporary Pet To Remove', status: 'available' }
  });
  const createdId = pet?.id || 99;

  const { response } = await client.DELETE('/pets/{petId}', {
    params: { path: { petId: createdId } }
  });
  expect(response.status).toBe(200);
});`
  },
  {
    id: 'fail-4',
    name: 'POST /checkout/initialize · Initiates shopping session',
    failureType: 'ASSERTION_DRIFT',
    diagnosis: 'Playwright test failed assertion check. Expected payment status count is 1. Received status code 500 (Internal Server Error) during database record locking trace.',
    hasAssertionWarning: true,
    oldCode: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('payment session starts locked in', async () => {
  const { data, response } = await client.POST('/checkout/initialize', {
    body: { amount: 1500, gateway: 'stripe' }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('locked');
});`,
    proposedCode: `import { test, expect } from '@playwright/test';
import { client } from '../clients/api';

test('payment session starts locked in', async () => {
  const { data, response } = await client.POST('/checkout/initialize', {
    body: { amount: 1500, gateway: 'stripe' }
  });
  // WARNING: API returns 500 server error under load of parallel locking tasks.
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('locked');
});`
  }
];

export const MOCK_FILE_TREE = {
  name: 'playwright-suite',
  children: [
    {
      name: 'tests',
      children: [
        { name: 'pets.spec.ts' },
        { name: 'store.spec.ts' },
        { name: 'user.spec.ts' },
        { name: 'checkout.spec.ts' }
      ]
    },
    {
      name: 'clients',
      children: [
        { name: 'api.ts' },
        { name: 'pet.ts' },
        { name: 'store.ts' },
        { name: 'user.ts' },
        { name: 'checkout.ts' },
        { name: 'oauth.ts' }
      ]
    },
    { name: 'playwright.config.ts' },
    { name: 'package.json' },
    { name: 'README.md' }
  ]
};

export const MOCK_DIVERGENCES = [
  {
    id: 'D-01',
    divergenceClass: 'D1' as const,
    endpoint: 'GET /pet/findByStatus',
    severity: 'medium' as const,
    status: 'reproduced' as const,
    claimA: 'schema:\n  type: string\n  enum: [available, pending, sold]',
    claimB: 'Reference server accepts arbitrary status strings and returns 200 OK.',
    evidence: 'Request:  GET /pet/findByStatus?status=CHERENKOV_INVALID_XYZ_9\nResponse: 200 OK\nBody:     []',
    reproSteps: 'curl -s -o /dev/null -w "%{http_code}" \\\n  "https://petstore3.swagger.io/api/v3/pet/findByStatus?status=CHERENKOV_INVALID_XYZ_9"\n# Expected: 400\n# Actual:   200',
    confidence: 0.95
  },
  {
    id: 'D-02',
    divergenceClass: 'D1' as const,
    endpoint: 'POST /pet',
    severity: 'high' as const,
    status: 'reproduced' as const,
    claimA: 'required:\n  - name\n  - photoUrls',
    claimB: 'Server accepts request missing photoUrls field and coerces value to empty list.',
    evidence: 'Request:  POST /pet\nBody:     {"name": "cherenkov-probe", "status": "available"}\nResponse: 200 OK\nBody:     {"id": 9223372036, "name": "cherenkov-probe", "photoUrls": [], "status": "available"}',
    reproSteps: 'curl -s -X POST "https://petstore3.swagger.io/api/v3/pet" \\\n  -H "Content-Type: application/json" \\\n  -d \'{"name": "cherenkov-probe", "status": "available"}\'\n# Expected: 400 (missing required field)\n# Actual:   200 with photoUrls: []',
    confidence: 0.99
  },
  {
    id: 'D-03',
    divergenceClass: 'D5' as const,
    endpoint: 'GET /pet/{petId}',
    severity: 'low' as const,
    status: 'reproduced' as const,
    claimA: '400: Invalid ID supplied\n404: Pet not found',
    claimB: 'Query petId=0 returns 404 error rather than 400 bad request.',
    evidence: 'Request:  GET /pet/0\nResponse: 404 Not Found\nBody:     {"code": 1, "type": "error", "message": "Pet not found"}',
    reproSteps: 'curl -s -o /dev/null -w "%{http_code}" "https://petstore3.swagger.io/api/v3/pet/0"\n# Expected: 400\n# Actual:   404',
    confidence: 0.92
  },
  {
    id: 'D-04',
    divergenceClass: 'D2' as const,
    endpoint: 'GET /store/inventory',
    severity: 'medium' as const,
    status: 'reproduced' as const,
    claimA: 'schema:\n  type: object\n  additionalProperties:\n    type: integer',
    claimB: 'Live server returns extra keys like "string" corresponding to internal test data leak.',
    evidence: 'Request:  GET /store/inventory\nResponse: 200 OK\nBody:     {"sold": 3, "string": 605, "available": 149}',
    reproSteps: 'curl -s "https://petstore3.swagger.io/api/v3/store/inventory"\n# Observe key "string" leaks internal state.',
    confidence: 0.88
  },
  {
    id: 'D-05',
    divergenceClass: 'D5' as const,
    endpoint: 'GET /user/login',
    severity: 'medium' as const,
    status: 'reproduced' as const,
    claimA: 'Response Headers:\n  X-Rate-Limit: integer\n  X-Expires-After: date-time',
    claimB: 'Successful login returns 200 OK but completely omits both required response headers.',
    evidence: 'Request:  GET /user/login?username=test&password=abc123\nResponse Headers:\n  Content-Type: application/json\n  (X-Rate-Limit: ABSENT)\n  (X-Expires-After: ABSENT)',
    reproSteps: 'curl -sI "https://petstore3.swagger.io/api/v3/user/login?username=test&password=abc123" \\\n  | grep -i "x-rate\\|x-expires"',
    confidence: 0.90
  },
  {
    id: 'D-06',
    divergenceClass: 'D3' as const,
    endpoint: 'UI /checkout',
    severity: 'critical' as const,
    status: 'pending' as const,
    claimA: 'Button click triggers checkout callback with order payload',
    claimB: 'Button is visually covered by floating coupon advertisement banner, preventing mouse click event.',
    evidence: 'Visual regression snapshot: 34% pixel discrepancy on selector button element.',
    reproSteps: 'Pilot execution click fails at step: click("#confirm-checkout") due to Ads container overlap.',
    confidence: 0.85
  },
  {
    id: 'D-07',
    divergenceClass: 'D4' as const,
    endpoint: 'POST /user/createWithList',
    severity: 'high' as const,
    status: 'rejected' as const,
    claimA: 'Inserts list payload records into Postgres DB user table',
    claimB: 'Inserts records but fails to hash passwords, storing them in plaintext.',
    evidence: 'DB Query: SELECT password FROM users WHERE username = \'probe\';\nReturned plaintext: \'foo123\'',
    reproSteps: 'Execute post request, fetch user table credentials from test sandbox container db.',
    confidence: 0.97
  }
];
