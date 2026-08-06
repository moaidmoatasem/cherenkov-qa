import { client } from '../client';
import { test, expect } from '@playwright/test';

/**
 * CORRECT TEST — the baseline CHERENKOV generates from the spec.
 * All 6 gates pass: status is spec-derived (201), body shape asserts real fields.
 */
test('post /users happy_path — creates user with 201 and returns id + email', async () => {
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
  expect(data).not.toHaveProperty('password_hash');
});
