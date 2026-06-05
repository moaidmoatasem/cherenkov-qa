import { client } from '../client';
import { test, expect } from '@playwright/test';

test('happy_path', async () => {
    const body = { email: 'test@example.com', password: 'password123' };
    const { response, data } = await client.POST('/users', { body });
    expect(response.status).toBe(201);
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('email');
});
