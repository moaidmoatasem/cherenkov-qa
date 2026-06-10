import { client } from '../client';
import { test, expect } from '@playwright/test';

test('golden_edit', async () => {
    const body = { email: 'user@example.com', password: 'securepass1' };
    const { response, data } = await client.POST('/users', { body });
    expect(response.status).toBe(201);
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('email');
    expect((data as any).email).toBe(body.email);
});
