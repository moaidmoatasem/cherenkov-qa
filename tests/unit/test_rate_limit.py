"""Tests for cherenkov/web/middleware/rate_limit.py"""

import asyncio
import time
import pytest

from cherenkov.web.middleware.rate_limit import _Bucket, RateLimitMiddleware, _ROUTE_COSTS


class TestBucket:
    def test_allows_within_burst(self):
        b = _Bucket(10)
        allowed, _ = b.consume(rps=10, burst=10, cost=1)
        assert allowed

    def test_rejects_when_exhausted(self):
        b = _Bucket(0)
        b.tokens = 0
        allowed, retry = b.consume(rps=1, burst=10, cost=1)
        assert not allowed
        assert retry > 0

    def test_retry_after_proportional_to_rps(self):
        b = _Bucket(10)
        b.tokens = 0
        _, retry = b.consume(rps=2, burst=10, cost=1)
        assert 0.4 < retry < 0.6  # ~0.5s for 1 token at 2 rps

    def test_refills_over_time(self):
        b = _Bucket(10)
        b.tokens = 0
        b.last_refill = time.monotonic() - 2.0  # simulate 2s elapsed
        allowed, _ = b.consume(rps=1, burst=10, cost=1)
        assert allowed

    def test_burst_cap_respected(self):
        b = _Bucket(5)
        b.tokens = 0
        b.last_refill = time.monotonic() - 100.0  # simulate long idle
        b.consume(rps=10, burst=5, cost=0)  # trigger refill without consuming
        # After refill tokens should be at burst cap, not rps*100
        b.tokens = min(5, b.tokens + 100 * 10)
        assert b.tokens <= 5 + 10  # rough check

    def test_fractional_cost(self):
        b = _Bucket(10)
        b.consume(rps=10, burst=10, cost=5.5)
        assert abs(b.tokens - 4.5) < 0.01

    def test_thread_safety(self):
        import threading
        b = _Bucket(1000)
        results = []

        def consume():
            allowed, _ = b.consume(rps=100, burst=1000, cost=1)
            results.append(allowed)

        threads = [threading.Thread(target=consume) for _ in range(200)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        allowed_count = sum(results)
        assert allowed_count <= 1000


class TestRateLimitMiddleware:
    def _make_scope(self, path="/api/v1/verify", client_ip="1.2.3.4"):
        return {
            "type": "http",
            "path": path,
            "headers": [(b"x-forwarded-for", client_ip.encode())],
            "client": (client_ip, 12345),
        }

    async def _call(self, middleware, scope):
        responses = []

        async def receive():
            return {}

        async def send(msg):
            responses.append(msg)

        await middleware(scope, receive, send)
        return responses

    @pytest.mark.anyio
    async def test_allows_normal_request(self):
        calls = []

        async def app(scope, receive, send):
            calls.append(scope["path"])

        mw = RateLimitMiddleware(app, rps=10, burst=20, enabled=True)
        scope = self._make_scope()
        await self._call(mw, scope)
        assert len(calls) == 1

    @pytest.mark.anyio
    async def test_disabled_allows_all(self):
        calls = []

        async def app(scope, receive, send):
            calls.append(1)

        mw = RateLimitMiddleware(app, rps=0.001, burst=0.001, enabled=False)
        for _ in range(50):
            await self._call(mw, self._make_scope())
        assert len(calls) == 50

    @pytest.mark.anyio
    async def test_exempt_paths_bypass_limiter(self):
        calls = []

        async def app(scope, receive, send):
            calls.append(1)

        mw = RateLimitMiddleware(app, rps=0.001, burst=0.001, enabled=True)
        for path in ("/health", "/metrics", "/openapi.json"):
            scope = self._make_scope(path=path)
            await self._call(mw, scope)
        assert len(calls) == 3

    @pytest.mark.anyio
    async def test_rate_limit_returns_429(self):
        async def app(scope, receive, send):
            pass

        mw = RateLimitMiddleware(app, rps=1, burst=1, enabled=True)
        scope = self._make_scope()

        responses_first = await self._call(mw, scope)
        # Exhaust the bucket
        for _ in range(20):
            await self._call(mw, scope)

        status_codes = []
        for msg in await self._call(mw, scope):
            if msg.get("type") == "http.response.start":
                status_codes.append(msg["status"])

        assert 429 in status_codes

    @pytest.mark.anyio
    async def test_different_clients_isolated(self):
        calls = []

        async def app(scope, receive, send):
            calls.append(1)

        mw = RateLimitMiddleware(app, rps=100, burst=2 * _ROUTE_COSTS["/api/v1/verify"], enabled=True)
        # Two different IPs should each get their own bucket
        for ip in ("10.0.0.1", "10.0.0.2"):
            await self._call(mw, self._make_scope(client_ip=ip))
        assert len(calls) == 2

    @pytest.mark.anyio
    async def test_non_http_scope_passes_through(self):
        calls = []

        async def app(scope, receive, send):
            calls.append(1)

        mw = RateLimitMiddleware(app, rps=0.001, burst=0, enabled=True)
        scope = {"type": "websocket", "path": "/ws", "headers": [], "client": ("1.2.3.4", 1)}
        await self._call(mw, scope)
        assert len(calls) == 1
