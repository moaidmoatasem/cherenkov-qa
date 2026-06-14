# ADR-005: Event-Driven Architecture (asyncio.Queue → Redis Streams)

**Date:** 2026-06-08
**Status:** Accepted
**Deciders:** Project Owner + AI Agents
**Related EPIC:** #277 (Phase -1), #279 (Phase 0b)

---

## Context

CHERENKOV-QA needs to coordinate between modules:
- HITL decisions → Reflector learning
- Pipeline events → Dashboard updates
- Chat messages → Knowledge queries
- Mobile traces → Dashboard display

Options considered:
1. **Airflow/Prefect** (batch scheduling)
2. **asyncio.Queue** (simple in-process events)
3. **Redis Streams** (advanced multi-process events)

## Decision

**Event-driven with asyncio.Queue initially, Redis Streams when available**:
- Start with `asyncio.Queue` for in-process events (zero dependencies)
- Upgrade to Redis Streams when Redis is available (multi-process, persistence)
- **No Airflow/Prefect**: CHERENKOV is event-driven, not batch-scheduled

### Rationale

1. **Start simple**: asyncio.Queue works without Docker/Redis
2. **Upgrade when needed**: Redis Streams adds persistence, fan-out, replay
3. **Event-driven fits**: CHERENKOV reacts to events (HITL approval, pipeline completion), not schedules
4. **Solo dev friendly**: No Airflow DAGs to maintain
5. **Graceful degradation**: Falls back to asyncio.Queue if Redis unavailable

### Architecture

```
┌─────────────────────────────────────┐
│  Event Bus (Protocol)               │
│  - emit(event)                      │
│  - subscribe(event_type, handler)   │
│  - unsubscribe(event_type, handler) │
└──────────────┬──────────────────────┘
               │
               ├─→ AsyncQueueEventBus (default)
               │   - In-process events
               │   - No persistence
               │   - No fan-out
               │
               └─→ RedisStreamsEventBus (upgrade)
                   - Multi-process events
                   - Persistence (Redis Streams)
                   - Fan-out (multiple subscribers)
                   - Replay (consumer groups)
```

### Event Types

```python
# cherenkov/core/events.py
@dataclass
class CHERENKOVEvent:
    event_id: str
    timestamp: datetime
    event_type: str
    payload: dict[str, Any]

@dataclass
class HITLDecisionMade(CHERENKOVEvent):
    item_id: str
    action: Literal["approve", "reject"]
    actor: str
    reason: str | None = None

@dataclass
class VerdictRecorded(CHERENKOVEvent):
    verdict: str
    endpoint: str
    confidence: float

@dataclass
class TestGenerated(CHERENKOVEvent):
    test_path: str
    scenario: str
    mutation_id: str

@dataclass
class KnowledgeQueried(CHERENKOVEvent):
    query: str
    results_count: int
    latency_ms: float

@dataclass
class HealingSuggested(CHERENKOVEvent):
    failure_class: str
    suggested_fix: str
    code_diff: str
```

### Usage

**Emit events:**
```python
from cherenkov.core.events import HITLDecisionMade, event_bus

event = HITLDecisionMade(
    item_id="123",
    action="approve",
    actor="user",
    reason="Looks good"
)
event_bus.emit(event)
```

**Subscribe to events:**
```python
from cherenkov.core.events import HITLDecisionMade, event_bus

def on_hitl_decision(event: HITLDecisionMade):
    """Handle HITL decision."""
    reflector.ingest_human_verdict(
        item_id=event.item_id,
        verdict=event.action,
        reason=event.reason
    )

event_bus.subscribe("HITLDecisionMade", on_hitl_decision)
```

### Fallback Chain

```python
def get_event_bus() -> EventBus:
    """Get event bus (Redis if available, else asyncio.Queue)."""
    try:
        import redis
        r = redis.from_url("redis://localhost:6379")
        r.ping()
        return RedisStreamsEventBus(r)
    except:
        return AsyncQueueEventBus()
```

### Consequences

**Positive:**
- Start simple (asyncio.Queue, zero dependencies)
- Upgrade when needed (Redis Streams for persistence, fan-out)
- Event-driven fits CHERENKOV (reacts to events, not schedules)
- Solo dev friendly (no Airflow DAGs)
- Graceful degradation (falls back to asyncio.Queue)

**Negative:**
- asyncio.Queue has no persistence (events lost on crash)
- asyncio.Queue has no fan-out (one subscriber per event)
- Redis Streams adds complexity (Redis dependency)
- Event ordering not guaranteed (asyncio.Queue is FIFO, Redis Streams is not)

**Mitigations:**
- Persist critical events to database (HITL decisions, verdicts)
- Use Redis Streams for multi-process scenarios
- Document event ordering requirements
- Add event replay for debugging

## Alternatives Considered

### Alternative 1: Airflow/Prefect
Use Airflow or Prefect for batch scheduling.

**Rejected because:**
- CHERENKOV is event-driven, not batch-scheduled
- Adds complexity (Airflow DAGs, Prefect flows)
- Solo dev overhead (maintaining DAGs/flows)
- Overkill for current scope (5 event types)

### Alternative 2: Redis Streams Only
Use Redis Streams for all events (no asyncio.Queue fallback).

**Rejected because:**
- Requires Redis (not available on all systems)
- Adds complexity (Redis dependency)
- Slower startup (wait for Redis)
- No graceful degradation (fails if Redis unavailable)

### Alternative 3: asyncio.Queue Only
Use asyncio.Queue for all events (no Redis Streams upgrade).

**Rejected because:**
- No persistence (events lost on crash)
- No fan-out (one subscriber per event)
- No replay (can't replay events for debugging)
- Doesn't scale to multi-process scenarios

## Implementation Plan

### Phase 0b: Foundations (1 week)
- Create domain events (ticket #314)
- Create AsyncQueueEventBus adapter
- Create RedisStreamsEventBus adapter
- Add event bus to dependency injection

### Phase 1: Second Brain (3 weeks)
- Bridge HITL → Reflector via events (ticket #333)
- Emit `HITLDecisionMade` on approve/reject
- Subscribe in Reflector to ingest human verdicts

### Phase 4: Chat Agents (2 weeks)
- Emit `KnowledgeQueried` on chat queries
- Subscribe in dashboard to display query history

## References

- EPIC #279 (Phase 0b: Foundations)
- `cherenkov/core/events.py` (to be created)
- `cherenkov/hitl/store.py` (existing HITL queue)
- Redis Streams documentation: https://redis.io/docs/data-types/streams/

## Notes

This ADR establishes event-driven architecture for module coordination. All Phase 0b through Phase 8 tickets must use the event bus for inter-module communication.

If a future requirement cannot be implemented via event-driven architecture, a new ADR must be created to justify the exception.
