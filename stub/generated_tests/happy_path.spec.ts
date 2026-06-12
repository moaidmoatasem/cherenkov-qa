import { client } from '../client';
import { test, expect } from '@playwright/test';

const _body = {
  "id": 1,
  "name": "Cherenkov Test",
  "status": "available"
};

test('post /_webhook/newPet happy_path happy_path', async () => {
  const { data, response } = await client.POST('/_webhook/newPet', { body: _body });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('status');
});
