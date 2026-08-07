# ADR 015: Per-Process Concurrency Limiter

## Status
Accepted

## Context
We need to limit the number of concurrent LLM generations or scenario executions per process to prevent resource exhaustion (OOM on local GPUs) and to respect API rate limits when using remote providers.

## Decision
We will use Python's `asyncio.Semaphore` at the application layer, bound to the `MAX_CONCURRENT_SCENARIOS` setting (defaulting to 4). This avoids complex distributed locking for local runs, while still providing safety. For distributed clusters, this acts as a per-worker limit, which combined with worker scaling provides the overall cluster limit.

## Consequences
- Prevents local GPU OOM errors by limiting active generation tasks.
- Does not enforce global rate limits across multiple independent processes or horizontal scaling (each worker gets `N` concurrency).
