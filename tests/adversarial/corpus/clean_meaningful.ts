// CLEAN: meaningful assertions — should NOT be flagged by the gate
import { test, expect } from '@playwright/test';

test('GET /pet/findByStatus — meaningful', async ({ request }) => {
  const res = await request.get('/pet/findByStatus?status=available');
  expect(res.status()).toBe(200);
  const pets = await res.json();
  expect(Array.isArray(pets)).toBe(true);
  expect(pets.length).toBeGreaterThan(0);
  expect(pets[0]).toHaveProperty('name');
  expect(pets[0]).toHaveProperty('status', 'available');
});

test('POST /pet — validates required fields', async ({ request }) => {
  const res = await request.post('/pet', {
    data: { name: 'doggie', photoUrls: ['http://example.com/dog.jpg'], status: 'available' },
  });
  expect(res.status()).toBe(200);
  const pet = await res.json();
  expect(pet).toHaveProperty('id');
  expect(pet.name).toBe('doggie');
});
