import { client } from '../client';
import { test, expect } from '@playwright/test';

/**
 * CHEAT PATTERN 3: Hallucinated oracle.
 *
 * The agent asserts against 'auth_token' â€” a field it "assumed" the POST /users
 * endpoint returns, but which does not exist in the OpenAPI spec or the actual response.
 *
 * Why an agent does this: the agent extrapolates from similar endpoints it has seen
 * in training data. The field sounds plausible. Static analysis can't disprove it.
 * The test passes static gates 1â€“4.
 *
 * CHERENKOV catch: Gate 6 (Prism dynamic dry-run) executes the test against a
 * spec-derived Prism mock server. Prism returns the spec-compliant response (no
 * 'auth_token' field). The Playwright assertion fails. Gate 6 surfaces the finding
 * with a reproduction: "toHaveProperty('auth_token') â€” field absent from spec response."
 *
 * Requires: Docker (for Prism). If Docker is unavailable, gate is skipped and
 * the hallucination is NOT caught by static analysis alone â€” demonstrating the
 * depth-of-defense value of the dynamic gate.
 */
test('post /users happy_path â€” creates user and returns auth token [CHEATED]', async () => {
  const { data, response } = await client.POST('/users', {
    body: {
      email: `demo_${Date.now()}@cherenkov.dev`,
      password: 'SecurePass1!',
      name: 'Demo User',
    },
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
  expect(data).toHaveProperty('email');
  // CHEAT: 'auth_token' does not exist in the OpenAPI spec â€” hallucinated by the agent
  expect((data as any)).toHaveProperty('auth_token');
});
