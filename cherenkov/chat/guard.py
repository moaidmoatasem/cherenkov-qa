from __future__ import annotations

import functools
import logging
import os
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

AGENT_DID = "did:cherenkov:chat-agent"


class GuardResult:
    def __init__(self, allowed: bool, reason: str = "", metadata: dict | None = None):
        self.allowed = allowed
        self.reason = reason
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "reason": self.reason, "metadata": self.metadata}


class SafetyGuard:
    """Unified safety layer: Sponsio contracts + MS AGT policy + AgentRR recording.

    Each integration is optional — if the library is not installed, that layer
    is silently skipped. This keeps the chat agent operational on minimal installs.
    """

    def __init__(self):
        self._sponsio = None
        self._agt_engine = None
        self._agentrr_recorder = None
        self._init_sponsio()
        self._init_agt()
        self._init_agentrr()

    # ── Sponsio: runtime contract enforcement ─────────────────────────────

    def _init_sponsio(self) -> None:
        try:
            from sponsio import Sponsio
            self._sponsio = Sponsio()
            logger.info("SafetyGuard: Sponsio runtime contracts active")
        except ImportError:
            logger.debug("SafetyGuard: Sponsio not installed — contract checks skipped")
        except Exception as exc:
            logger.warning("SafetyGuard: Sponsio init failed — %s", exc)

    def _check_sponsio(self, fn_name: str, fn_args: dict[str, Any]) -> GuardResult:
        if self._sponsio is None:
            return GuardResult(allowed=True)
        try:
            result = self._sponsio.guard_before(fn_name, fn_args)
            if result is not None and getattr(result, "allowed", True) is False:
                return GuardResult(
                    allowed=False,
                    reason=f"Sponsio contract blocked: {getattr(result, 'reason', 'unknown')}",
                    metadata={"sponsio": str(result)},
                )
            return GuardResult(allowed=True)
        except Exception as exc:
            logger.error("SafetyGuard: Sponsio check failed — %s", exc)
            return GuardResult(allowed=True, metadata={"sponsio_error": str(exc)})

    # ── MS AGT: policy enforcement ────────────────────────────────────────

    def _init_agt(self) -> None:
        try:
            from agentmesh.governance import PolicyEngine
            self._agt_engine = PolicyEngine(conflict_strategy="priority_first_match")
            policy_path = os.getenv("CHERENKOV_AGT_POLICY", "policy.yaml")
            if os.path.exists(policy_path):
                policy = self._agt_engine.load_yaml_file(policy_path)
                self._agt_engine.load_policy(policy)
                logger.info("SafetyGuard: MS AGT policy engine active (policy=%s)", policy_path)
            else:
                logger.debug("SafetyGuard: policy.yaml not found at %s", policy_path)
        except ImportError:
            logger.debug("SafetyGuard: agent-governance-toolkit not installed — policy checks skipped")
        except Exception as exc:
            logger.warning("SafetyGuard: MS AGT init failed — %s", exc)

    def _check_agt(self, fn_name: str, fn_args: dict[str, Any]) -> GuardResult:
        if self._agt_engine is None:
            return GuardResult(allowed=True)
        try:
            context: dict[str, Any] = {
                "action_type": fn_name,
                "tool_name": fn_name,
                "call_count": 0,
            }
            if fn_name == "run_test":
                context["spec_validation"] = True
            decision = self._agt_engine.evaluate(
                AGENT_DID,
                context,
                stage="pre_tool",
            )
            if not decision.allowed:
                return GuardResult(
                    allowed=False,
                    reason=f"AGT policy denied: {decision.action}",
                    metadata={
                        "agt_allowed": decision.allowed,
                        "agt_action": decision.action,
                    },
                )
            return GuardResult(allowed=True, metadata={"agt_allowed": decision.allowed})
        except Exception as exc:
            logger.error("SafetyGuard: AGT check failed — %s", exc)
            return GuardResult(allowed=True, metadata={"agt_error": str(exc)})

    # ── AgentRR: record/replay debugging ──────────────────────────────────

    def _init_agentrr(self) -> None:
        import uuid as _uuid

        try:
            from agentrr_core.log.writer import LogWriter, LogWriterConfig
            from agentrr_core.schema.events import RunHeader
            from agentrr_recorder import Recorder
        except ImportError:
            logger.debug("SafetyGuard: agentrr not installed — replay recording skipped")
            return

        try:
            log_path = Path(os.getenv("AGENTRR_LOG_DIR", ".agentrr/runs"))
            log_path.mkdir(parents=True, exist_ok=True)
            config = LogWriterConfig(path=log_path)
            writer = LogWriter(config=config)
            header = RunHeader(
                run_id=f"cherenkov-{_uuid.uuid4().hex[:8]}",
                entrypoint="cherenkov.chat.guard",
            )
            recorder = Recorder.create(writer, header)
            self._agentrr_ctx = recorder.begin_run()
            self._agentrr_recorder = recorder
            logger.info("SafetyGuard: AgentRR recording active (%s)", log_path)
        except Exception as exc:
            logger.warning("SafetyGuard: AgentRR init failed — %s", exc)

    def _record(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._agentrr_recorder is None:
            return
        try:
            import uuid as _uuid
            from agentrr_core.schema.events import EventType
            from agentrr_recorder.pending_event import PendingBoundary

            et = getattr(EventType, event_type.upper(), EventType.RECORD)
            pending = PendingBoundary(
                event_id=f"e-{_uuid.uuid4().hex[:12]}",
                event_type=et,
                request=payload,
                parent_id=None,
            )
            self._agentrr_ctx.record_boundary(pending, response=None)
        except Exception as exc:
            logger.debug("SafetyGuard: AgentRR record failed — %s", exc)

    # ── Public API ────────────────────────────────────────────────────────

    def check_tool_call(self, name: str, args: dict[str, Any]) -> GuardResult:
        """Evaluate a tool call against Sponsio + MS AGT before execution."""

        result_sponsio = self._check_sponsio(name, args)
        if not result_sponsio.allowed:
            return result_sponsio

        result_agt = self._check_agt(name, args)
        if not result_agt.allowed:
            return result_agt

        return GuardResult(allowed=True)

    def record_tool_call(self, name: str, args: dict[str, Any], result: Any) -> None:
        self._record("tool_call", {
            "name": name,
            "args": args,
            "result": result,
        })

    def record_llm_call(self, messages: list[dict], response: str) -> None:
        self._record("llm_call", {
            "messages_count": len(messages),
            "response_preview": response[:200],
        })

    def wrap_tool(self, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator factory: wrap a tool function with check-then-execute-then-record."""
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(fn)
            def wrapped(**kwargs: Any) -> dict[str, Any]:
                guard_result = self.check_tool_call(name, kwargs)
                if not guard_result.allowed:
                    return {
                        "error": guard_result.reason,
                        "guard": guard_result.to_dict(),
                        "tool": name,
                    }
                result = fn(**kwargs)
                self.record_tool_call(name, kwargs, result)
                return result
            return wrapped
        return decorator

    def wrap_llm(self, fn: Callable[..., str]) -> Callable[..., str]:
        """Wrap the LLM call function with recording."""
        @functools.wraps(fn)
        def wrapped(messages: list[dict]) -> str:
            response = fn(messages)
            self.record_llm_call(messages, response)
            return response
        return wrapped


_global_guard: SafetyGuard | None = None


def get_guard() -> SafetyGuard:
    global _global_guard
    if _global_guard is None:
        _global_guard = SafetyGuard()
    return _global_guard
