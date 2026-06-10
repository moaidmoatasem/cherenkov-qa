import { client } from '../client';
import { test, expect } from '@playwright/test';

test('password_too_short', async () => {
    const body = { email: 'test@example.com', password: 'short' };
    const { response } = await client.POST('/users', { body });
    expect(response.status).toBe(400);
});
