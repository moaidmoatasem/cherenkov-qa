"""Routines may only schedule allowlisted targets.

`POST /routines/` used to pass a caller-supplied ``module:func`` straight to
``importlib`` and schedule it with caller-supplied kwargs — with auth off by
default, that is remote code execution on any non-loopback deploy
(``target_module=os:system``, ``target_kwargs={"command": ...}``). These tests
pin the allowlist at every entry point: the model, the use case, the adapter
(defence in depth for routines built without validation), the API and the CLI.
"""
from __future__ import annotations

import pytest
from click.testing import CliRunner
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cherenkov.scheduling.adapters.apscheduler_adapter import APSchedulerAdapter
from cherenkov.scheduling.domain.models import Routine, RoutineTrigger
from cherenkov.scheduling.use_cases.manage_routines import create_routine

ALLOWED = "cherenkov.scheduling.templates.daily_health_check:run"
HOSTILE = ["os:system", "subprocess:run", "builtins:eval", "cherenkov.scheduling.templates.daily_health_check:_log"]


@pytest.mark.parametrize("target", HOSTILE)
def test_model_rejects_unlisted_target(target):
    with pytest.raises(ValueError):
        Routine(
            id="rt_x", name="x", description="", target_module=target,
            trigger=RoutineTrigger(type="interval", value="60"),
        )


@pytest.mark.parametrize("target", HOSTILE)
def test_use_case_rejects_and_schedules_nothing(target):
    scheduler = APSchedulerAdapter()
    with pytest.raises(ValueError):
        create_routine(scheduler, "x", "", "interval", "60", target, {"command": "id"})
    assert scheduler.list_routines() == []
    assert scheduler.scheduler.get_jobs() == []


def test_adapter_rejects_unvalidated_routine(monkeypatch):
    # model_construct skips validation — the adapter must still refuse before
    # anything is imported.
    imported = []
    monkeypatch.setattr("importlib.import_module", lambda name: imported.append(name))
    routine = Routine.model_construct(
        id="rt_x", name="x", description="", target_module="os:system",
        target_kwargs={"command": "id"}, enabled=True,
        trigger=RoutineTrigger(type="interval", value="60"),
    )
    scheduler = APSchedulerAdapter()
    with pytest.raises(ValueError):
        scheduler.add_routine(routine)
    assert imported == []
    assert scheduler.scheduler.get_jobs() == []


def test_allowlisted_target_is_scheduled():
    scheduler = APSchedulerAdapter()
    routine = create_routine(scheduler, "health", "", "interval", "3600", ALLOWED, {})
    assert [r.id for r in scheduler.list_routines()] == [routine.id]
    assert scheduler.scheduler.get_job(routine.id) is not None


def _client():
    from cherenkov.scheduling.api.routes import router, scheduler
    app = FastAPI()
    app.include_router(router)
    return TestClient(app), scheduler


@pytest.mark.parametrize("target", ["os:system", "subprocess:run"])
def test_api_rejects_unlisted_target_with_400(target):
    client, scheduler = _client()
    before = {r.id for r in scheduler.list_routines()}
    with client:
        resp = client.post(
            "/routines/",
            params={"name": "x", "description": "", "trigger_type": "interval",
                    "trigger_value": "60", "target_module": target},
            json={"command": "touch /tmp/pwned"},
        )
    assert resp.status_code == 400
    assert target in resp.text
    assert {r.id for r in scheduler.list_routines()} == before


def test_cli_rejects_unlisted_target():
    from cherenkov.cli.commands.routine_cmd import routine_cmd
    result = CliRunner().invoke(
        routine_cmd,
        ["create", "--name", "x", "--trigger", "interval", "--value", "60", "--target", "os:system"],
    )
    assert result.exit_code == 2
    assert "not an allowed routine target" in result.output
