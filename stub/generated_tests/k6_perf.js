import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = { vus: 1, duration: '1s' };

export default function () {
  const url = __ENV.API_URL || 'http://localhost:3000';
  const r = http.request('GET', url + '/api/compat');
  check(r, { 'status is 2xx': (res) => res.status >= 200 && res.status < 300 });
  sleep(0.5);
}
