import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get post by ID - unauthorized', async () => {
  const { error, response } = await client.GET('/posts/1');
  expect(response.status).toBe(401);
  expect(error).toBeTruthy();
});