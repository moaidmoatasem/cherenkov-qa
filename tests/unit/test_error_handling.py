from cherenkov.core.error_handling import (
    GracefulDegradation, DegradationLevel, HealthStatus, get_degradation
)


def test_degradation_levels():
    assert DegradationLevel.HEALTHY in DegradationLevel
    assert DegradationLevel.DEGRADED in DegradationLevel
    assert DegradationLevel.CRITICAL in DegradationLevel
    assert DegradationLevel.DOWN in DegradationLevel


def test_health_status_starts_healthy():
    h = HealthStatus()
    assert h.level == DegradationLevel.HEALTHY


def test_health_status_update_all_pass():
    h = HealthStatus()
    h.update("ollama", True)
    h.update("redis", True)
    assert h.level == DegradationLevel.HEALTHY


def test_health_status_update_half_fail():
    h = HealthStatus()
    h.update("ollama", True)
    h.update("redis", False)
    assert h.level == DegradationLevel.DEGRADED


def test_health_status_update_all_fail():
    h = HealthStatus()
    h.update("ollama", False)
    h.update("redis", False)
    assert h.level == DegradationLevel.DOWN


def test_health_status_to_dict():
    h = HealthStatus()
    h.update("ollama", True)
    d = h.to_dict()
    assert "level" in d
    assert "checks" in d
    assert "last_checked" in d
    assert d["checks"]["ollama"]


def test_graceful_degradation_singleton():
    gd1 = get_degradation()
    gd2 = get_degradation()
    assert gd1 is gd2


def test_graceful_degradation_initial_healthy():
    gd = GracefulDegradation()
    assert not gd.degraded_or_worse()
    assert not gd.critical_or_worse()


def test_graceful_degradation_check_success():
    gd = GracefulDegradation()
    ok = gd.check("test", lambda: True)
    assert ok
    assert not gd.degraded_or_worse()


def test_graceful_degradation_check_failure():
    gd = GracefulDegradation()
    ok = gd.check("test", lambda: False)
    assert not ok
    assert gd.degraded_or_worse()


def test_graceful_degradation_check_exception():
    gd = GracefulDegradation()
    ok = gd.check("test", lambda: (_ for _ in ()).throw(Exception("fail")))
    assert not ok


def test_graceful_degradation_wrap_degraded_blocks():
    gd = GracefulDegradation()
    gd.check("vital", lambda: False)
    gd.check("other", lambda: False)
    wrapped = gd.wrap("blocked", lambda: "called")
    assert wrapped() is None


def test_graceful_degradation_wrap_healthy_passes():
    gd = GracefulDegradation()
    wrapped = gd.wrap("ok", lambda: "called")
    assert wrapped() == "called"
