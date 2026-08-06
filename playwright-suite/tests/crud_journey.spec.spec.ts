import { client } from '../client';
import { test, expect } from '@playwright/test';

test('crud journey for user', async () => {
  // Create a new user
  const createUser = await client.POST('/user', {
    body: {
      username: 'theUser',
      firstName: 'John',
      lastName: 'James',
      email: 'john@email.com',
      password: '12345',
      phone: '12345',
      userStatus: 1
    }
  });
  expect(createUser.response.status).toBe(200);
  const userId = createUser.data.id;

  // Retrieve the created user
  const getUser = await client.GET(`/user/${userId}`);
  expect(getUser.response.status).toBe(200);
  expect(getUser.data).toHaveProperty('id', userId);

  // Delete the created user
  const deleteUser = await client.DELETE(`/user/${userId}`);
  expect(deleteUser.response.status).toBe(200);
});