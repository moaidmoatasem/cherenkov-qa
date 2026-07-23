import { client } from '../client';
import { test, expect } from '@playwright/test';

test('get post by ID happy path', async () => {
  const id = 1; // Replace with a valid post ID
  const { data, response } = await client.GET(`/posts/${id}`);
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('id');
});