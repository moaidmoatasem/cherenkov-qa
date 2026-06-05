import { client } from '../client';
import { test, expect } from '@playwright/test';

// NOTE: this spec asserts 422 (the OpenAPI-declared validation status). The
// target API normalizes validation errors to 400, so this test is EXPECTED to
// go RED against the live target — it is the canonical "catches a status
// conformance bug" example. The eject smoke test runs only happy_path.spec.ts;
// this file ships as a reference fixture, not as part of the green gate.
test('create user with password too short', async () => {
  const { response } = await client.POST('/users', {
    body: { email: 'test@example.com', password: 'short' }
  });
  expect(response.status).toBe(422);
});
