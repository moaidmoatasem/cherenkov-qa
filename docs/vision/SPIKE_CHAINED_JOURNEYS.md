<!--
⚠️ SPIKE / SCRATCH — DO NOT CITE AS A CURRENT PLAN

Investigation note from an earlier horizon. The chained/stateful journey
direction has been folded into the consolidated Phase plan. See
[../../docs/PHASE_PLAN.md](../../PHASE_PLAN.md) for the current plan and
[../../docs/STATUS.md](../../STATUS.md) for the current state.
-->

# SPIKE: Chained / Stateful CRUD Journeys (Horizon V - Issue #193)

## Objective
Assess the feasibility and design requirements for generating stateful, chained API journeys (e.g., `POST` create -> capture ID -> `PATCH` update -> `DELETE` remove). Currently, CHERENKOV operates on depth-1 slices per endpoint, testing them in isolation.

## Feasibility
**High Feasibility**. Playwright natively supports sequential test steps and variables to thread state across requests. The challenge is in the **PLAN** stage mapping semantic links between endpoints using OpenAPI specs.

## Contract Changes

### 1. IngestStage
Needs to parse OpenAPI `links` objects (if present) or use heuristics to map entity CRUD operations (e.g., `/users` POST maps to `/users/{id}` GET/PATCH/DELETE).
*   **New Output**: `IngestOutput.journeys` (List of grouped `EndpointSlice` references forming a CRUD lifecycle).

### 2. PlanStage
Needs to output `JourneyScenario` instead of or in addition to `Scenario`.
*   **New Object**: `JourneyScenario`
    *   `steps`: List of mutations to execute sequentially.
    *   `state_bindings`: Instructions for the LLM on which variables to capture and pass.

### 3. GenerateStage
*   Prompt needs adjustment to generate chained Playwright tests in a single `test()` block, rather than isolated tests.
*   System prompt must include instructions on state capture: `const id = responseBody.id;`.

## Prototype Journey on Bundled Spec
Using `stripe_spec.json` (or any generic CRUD API):

**Journey Plan**:
1. `POST /v1/customers` -> Expect 200, capture `id`.
2. `GET /v1/customers/{customer}` -> Expect 200, use `id`.
3. `POST /v1/customers/{customer}` (Update) -> Expect 200, use `id`.
4. `DELETE /v1/customers/{customer}` -> Expect 200, use `id`.

**Generated Playwright Snippet**:
```typescript
import { test, expect } from '@playwright/test';
import { client } from '../client';

test('CRUD Customer Journey', async () => {
  // 1. Create
  const createRes = await client.POST('/v1/customers', { body: { name: "Test" }});
  expect(createRes.response.status).toBe(200);
  const customerId = createRes.data.id;

  // 2. Read
  const readRes = await client.GET('/v1/customers/{customer}', { params: { path: { customer: customerId } }});
  expect(readRes.response.status).toBe(200);

  // 3. Delete
  const delRes = await client.DELETE('/v1/customers/{customer}', { params: { path: { customer: customerId } }});
  expect(delRes.response.status).toBe(200);
});
```

## Conclusion
The architectural boundaries (INGEST -> PLAN -> GENERATE) remain valid. The main investment is in the heuristics to detect CRUD groups in `IngestStage` since most specs lack explicit OpenAPI `links`. We can proceed post-gate as a high-value Horizon feature.
