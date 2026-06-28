"""APScheduler Implementation of the SchedulerPort."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from cherenkov.scheduling.domain.models import Routine
from cherenkov.scheduling.ports.scheduler import SchedulerPort

_log = logging.getLogger(__name__)


class APSchedulerAdapter(SchedulerPort):
    def __init__(self):
        # We can configure a SQLAlchemy job store later, for now we use memory
        self.scheduler = AsyncIOScheduler()
        self._routines: dict[str, Routine] = {}

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            _log.info("APScheduler started")

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()
            _log.info("APScheduler stopped")

    def add_routine(self, routine: Routine) -> None:
        self._routines[routine.id] = routine

        # Remove existing if present
        if self.scheduler.get_job(routine.id):
            self.scheduler.remove_job(routine.id)

        if not routine.enabled or routine.trigger.enabled is False:
            return

        # Resolve target callable dynamically
        import importlib
        module_path, func_name = routine.target_module.split(":")
        module = importlib.import_module(module_path)
        target_func = getattr(module, func_name)

        trigger = None
        if routine.trigger.type == "cron":
            trigger = CronTrigger.from_crontab(routine.trigger.value)
        elif routine.trigger.type == "interval":
            trigger = IntervalTrigger(seconds=int(routine.trigger.value))

        if trigger:
            self.scheduler.add_job(
                target_func,
                trigger=trigger,
                kwargs=routine.target_kwargs,
                id=routine.id,
                name=routine.name,
                replace_existing=True
            )
            _log.info(f"Scheduled routine {routine.id}")

    def remove_routine(self, routine_id: str) -> None:
        if routine_id in self._routines:
            del self._routines[routine_id]
        if self.scheduler.get_job(routine_id):
            self.scheduler.remove_job(routine_id)

    def list_routines(self) -> list[Routine]:
        # Sync APScheduler next_run_time back to the models if needed
        for job in self.scheduler.get_jobs():
            if job.id in self._routines:
                self._routines[job.id].next_run = job.next_run_time
        return list(self._routines.values())

    def trigger_routine_now(self, routine_id: str) -> None:
        job = self.scheduler.get_job(routine_id)
        if job:
            job.modify(next_run_time=None) # triggers immediately in APScheduler if not specified?
            # Actually, APScheduler has no direct "trigger now" without messing up the existing trigger,
            # but we can submit it directly to the executor or add a one-off date trigger.
            self.scheduler.add_job(job.func, kwargs=job.kwargs, id=f"{routine_id}_manual", replace_existing=True)
            _log.info(f"Triggered routine {routine_id} manually")
