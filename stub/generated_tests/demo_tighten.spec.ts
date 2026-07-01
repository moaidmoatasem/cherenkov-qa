import { client } from '../client';
import { test, expect } from '@playwright/test';

/**
 * TIGHTENING FIXTURE: uses a static email so TighteningAnalyzer can suggest
 * value-specific assertions when the response echoes the field back.
 *
 * Expected bench result: PASS; TighteningAnalyzer suggests:
 *   consider -> expect(data.email).toBe('test@example.com')
 *   consider -> expect(data.email).toBe(body.email)
 */
test('post /users happy_path — creates user with static email for tightening', async () => {
  const { data, response } = await client.POST('/users', {
    body: {
      email: 'test@example.com',
      password: 'SecurePass1!',
    },
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
  expect(data).toHaveProperty('email');
});
