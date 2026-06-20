import { client } from '../client';
import { test, expect } from '@playwright/test';
test('post /users happy_path', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: `mcp_${Date.now()}@y.com`, password: 'Abc12345!', name: 'MCP User' }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
});
