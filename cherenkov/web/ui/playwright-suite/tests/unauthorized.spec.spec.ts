import { client } from '../client';
import { test, expect } from '@playwright/test';

test('delete user unauthorized - returns 401', async () => {
  const { error, response } = await client.DELETE('/user/testuser');
  expect(response.status).toBe(401);
  expect(error).toBeTruthy();
});