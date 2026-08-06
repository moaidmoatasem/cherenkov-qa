import { client } from '../client';
import { test, expect } from '@playwright/test';

test('delete user happy path', async () => {
  const username = 'testuser'; // Replace with actual username for testing
  const { response } = await client.DELETE(`/user/${username}`);
  expect(response.status).toBe(200);
});