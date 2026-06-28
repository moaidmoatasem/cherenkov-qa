import pytest
from cherenkov.scheduling.adapters.apscheduler_adapter import APSchedulerAdapter
from cherenkov.scheduling.use_cases.manage_routines import create_routine, toggle_routine


@pytest.mark.anyio
@pytest.mark.parametrize('anyio_backend', ['asyncio'])
async def test_scheduler_lifecycle():
    scheduler = APSchedulerAdapter()
    scheduler.start()

    r = create_routine(
        scheduler,
        name="test",
        description="test",
        trigger_type="interval",
        trigger_value="60",
        target_module="cherenkov.scheduling.templates.daily_health_check:run",
        target_kwargs={}
    )

    assert len(scheduler.list_routines()) == 1

    toggle_routine(scheduler, r.id, False)
    assert not scheduler.list_routines()[0].enabled

    scheduler.trigger_routine_now(r.id)

    scheduler.remove_routine(r.id)
    assert len(scheduler.list_routines()) == 0

    scheduler.stop()
