import { test, expect } from '@playwright/test';
import { client } from '../client';

test('create user failing assertion spec', async () => {
  const { response } = await client.POST('/users', {
    body: {
      name: 'Healing Test',
      email: 'deep_healing_test@cherenkov.local',
      password: 'secure_password_123'
    }
  });
  // Deliberate assertion failure: real server returns 201, but we assert 500
  expect(response.status).toBe(500);
});
