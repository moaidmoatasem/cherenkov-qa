"""Tests for cherenkov/substrate/retry.py"""

import os
import time
import pytest
from unittest.mock import MagicMock, patch, call


# Patch sleep globally so tests don't actually wait
@pytest.fixture(autouse=True)
def no_sleep():
    with patch("cherenkov.substrate.retry.time.sleep"):
        yield


from cherenkov.substrate.retry import with_retry, retryable, _is_retryable, _delay


class TestIsRetryable:
    def test_rate_limit_is_retryable(self):
        assert _is_retryable(Exception("rate limit exceeded")) is True

    def test_429_is_retryable(self):
        assert _is_retryable(Exception("HTTP 429 too many requests")) is True

    def test_503_is_retryable(self):
        assert _is_retryable(Exception("503 service unavailable")) is True

    def test_timeout_is_retryable(self):
        assert _is_retryable(Exception("connection timeout")) is True

    def test_budget_exceeded_not_retryable(self):
        assert _is_retryable(Exception("budget exceeded: $0.10")) is False

    def test_auth_error_not_retryable(self):
        assert _is_retryable(Exception("invalid api key")) is False

    def test_content_policy_not_retryable(self):
        assert _is_retryable(Exception("content policy violation")) is False

    def test_unknown_error_retryable_by_default(self):
        assert _is_retryable(Exception("mysterious failure")) is True


class TestDelay:
    def test_delay_within_bounds(self):
        for attempt in range(5):
            d = _delay(attempt, base=1.0, maximum=30.0)
            assert 0 <= d <= 30.0

    def test_delay_caps_at_maximum(self):
        for _ in range(20):
            d = _delay(10, base=1.0, maximum=5.0)
            assert d <= 5.0

    def test_delay_increases_with_attempt(self):
        # On average, later attempts have higher delay (probabilistic — use many samples)
        early = sum(_delay(0, 1.0, 60.0) for _ in range(100)) / 100
        late = sum(_delay(5, 1.0, 60.0) for _ in range(100)) / 100
        assert late > early


class TestWithRetry:
    def test_success_first_attempt(self):
        fn = MagicMock(return_value="ok")
        assert with_retry(fn, "arg", max_attempts=3, base_delay=0) == "ok"
        fn.assert_called_once_with("arg")

    def test_retries_on_transient_error(self):
        fn = MagicMock(side_effect=[
            Exception("503 server error"),
            Exception("503 server error"),
            "success",
        ])
        result = with_retry(fn, max_attempts=3, base_delay=0)
        assert result == "success"
        assert fn.call_count == 3

    def test_raises_after_max_attempts(self):
        fn = MagicMock(side_effect=Exception("timeout"))
        with pytest.raises(Exception, match="timeout"):
            with_retry(fn, max_attempts=3, base_delay=0)
        assert fn.call_count == 3

    def test_non_retryable_raises_immediately(self):
        fn = MagicMock(side_effect=Exception("invalid api key"))
        with pytest.raises(Exception, match="invalid api key"):
            with_retry(fn, max_attempts=3, base_delay=0)
        assert fn.call_count == 1

    def test_kwargs_forwarded(self):
        fn = MagicMock(return_value=42)
        with_retry(fn, "a", max_attempts=1, base_delay=0, key="val")
        fn.assert_called_once_with("a", key="val")

    def test_disabled_flag_via_function_arg(self):
        """Test the enabled=False path without module reload side-effects."""
        # Patch _ENABLED directly rather than via env to avoid module reload
        fn = MagicMock(side_effect=[Exception("rate limit"), "ok"])
        with patch("cherenkov.substrate.retry._ENABLED", False):
            with pytest.raises(Exception, match="rate limit"):
                with_retry(fn, max_attempts=3, base_delay=0)
        assert fn.call_count == 1

    def test_budget_exceeded_not_retried(self):
        from cherenkov.core.budget import BudgetExceededError

        exc = BudgetExceededError(spent=0.10, cap=0.10, requested=0.01)
        fn = MagicMock(side_effect=exc)
        with pytest.raises(BudgetExceededError):
            with_retry(fn, max_attempts=3, base_delay=0)
        assert fn.call_count == 1

    def test_sleep_called_between_retries(self):
        fn = MagicMock(side_effect=[Exception("503"), "ok"])
        with patch("cherenkov.substrate.retry.time.sleep") as mock_sleep:
            with_retry(fn, max_attempts=3, base_delay=1.0)
        mock_sleep.assert_called_once()

    def test_no_sleep_on_final_attempt(self):
        fn = MagicMock(side_effect=Exception("timeout"))
        with patch("cherenkov.substrate.retry.time.sleep") as mock_sleep:
            with pytest.raises(Exception):
                with_retry(fn, max_attempts=2, base_delay=1.0)
        assert mock_sleep.call_count == 1  # only between attempt 1 and 2


class TestRetryableDecorator:
    def test_success_passes_through(self):
        @retryable(max_attempts=3, base_delay=0)
        def fn(x):
            return x * 2

        assert fn(5) == 10

    def test_retries_on_failure(self):
        attempts = []

        @retryable(max_attempts=3, base_delay=0)
        def fn():
            attempts.append(1)
            if len(attempts) < 3:
                raise Exception("503")
            return "done"

        assert fn() == "done"
        assert len(attempts) == 3

    def test_preserves_function_name(self):
        @retryable()
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestRouterIntegration:
    def test_router_uses_retry_on_primary(self):
        """SubstrateRouter.route() wraps primary.generate with with_retry."""
        from cherenkov.substrate.router import SubstrateRouter

        mock_primary = MagicMock()
        mock_primary.capabilities.return_value.provider_name = "mock"
        mock_primary.capabilities.return_value.requires_egress = False
        mock_primary.generate.side_effect = [
            Exception("503 transient"),
            MagicMock(cost_usd=0.01, model="m", provider="mock", cached=False),
        ]

        with (
            patch("cherenkov.substrate.router.provider_for_tier", return_value=mock_primary),
            patch("cherenkov.substrate.router.get_run_budget") as mock_budget,
            patch("cherenkov.substrate.router.get_settings") as mock_settings,
            patch("cherenkov.substrate.retry.time.sleep"),
        ):
            mock_budget.return_value.pre_check.return_value = None
            mock_budget.return_value.charge.return_value = None
            mock_settings.return_value.CERTIFICATION_ENABLED = False
            mock_settings.return_value.FALLBACK_ENABLED = False

            router = SubstrateRouter()
            from cherenkov.core.contracts import ReasoningRequest
            req = ReasoningRequest(
                task="test task",
                capability_tier="standard",
                max_cost=0.1,
            )
            result = router.route(req)

        assert mock_primary.generate.call_count == 2
