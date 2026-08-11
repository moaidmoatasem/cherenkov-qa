"""In-process implementation of the JourneyRunner port.

Threads, as before. The value here is not that this scales -- it does not --
but that the API layer now depends on the port rather than on a module-level
dict of threads, so a queue-backed or operator-backed runner can replace it
without touching the routes.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


class ThreadJourneyRunner:
    """Runs journeys on daemon threads in the current process.

    Single-process only: the thread registry does not survive a restart and is
    invisible to other replicas. `is_running` therefore answers "is this
    process running it", not "is it running". The RunStore is the authority.
    """

    def __init__(self) -> None:
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def start(self, journey_id: str, spec_path: str, run_id: str) -> str:
        thread = threading.Thread(
            target=self._run,
            args=(journey_id, spec_path, run_id),
            name=f"journey-{run_id}",
            daemon=True,
        )
        with self._lock:
            self._threads[run_id] = thread
        thread.start()
        return run_id

    def is_running(self, run_id: str) -> bool:
        with self._lock:
            thread = self._threads.get(run_id)
        return bool(thread and thread.is_alive())

    def _run(self, journey_id: str, spec_path: str, run_id: str) -> None:
        from cherenkov.core.orchestrator import OrchestrationEngine
        from cherenkov.web.routes.deps import ws_event_callback
        try:
            engine = OrchestrationEngine(run_id=run_id, event_callback=ws_event_callback)
            engine.journey_id = journey_id
            engine.run_pipeline(spec_path)
        except Exception as e:
            logger.exception("journey run %s failed", run_id)
            try:
                ws_event_callback("pipeline_error", {"detail": str(e)})
            except Exception:
                logger.debug("could not broadcast pipeline_error", exc_info=True)
            # The engine records terminal state itself on the paths it controls;
            # this covers a failure before or outside that.
            try:
                from cherenkov.persistence.run_store import RunStore
                RunStore().update_status(run_id, "failed")
            except Exception:
                logger.debug("could not mark run failed", exc_info=True)
        finally:
            with self._lock:
                self._threads.pop(run_id, None)


_runner: ThreadJourneyRunner | None = None

def get_journey_runner() -> ThreadJourneyRunner:
    global _runner
    if _runner is None:
        _runner = ThreadJourneyRunner()
    return _runner
