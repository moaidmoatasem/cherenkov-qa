# CHERENKOV-QA Logging Strategy

**Date:** 2026-06-08  
**Status:** Active  
**Related EPIC:** #277 (Phase -1), #279 (Phase 0b)

---

## Log Levels

| Level | When |
|-------|------|
| `DEBUG` | SQL queries, individual event emissions, LLM raw prompts |
| `INFO` | Phase transitions, pipeline start/end, config loaded, engine started |
| `WARNING` | Degradation (Redis unavailable, falling back to SQLite), VLM confidence below 0.7, migration running |
| `ERROR` | LLM timeout, Docker unavailable, migration failure, sandbox crash |

---

## Format

JSON structured logs to stderr. Each line:

```json
{"ts":"ISO8601","level":"INFO","logger":"cherenkov.orchestrator","msg":"Pipeline started","event":"pipeline_start","trace_id":"uuid"}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `ts` | string | ISO8601 timestamp |
| `level` | string | Log level (DEBUG, INFO, WARNING, ERROR) |
| `logger` | string | Logger name (module path) |
| `msg` | string | Human-readable message |
| `event` | string | Event type (for structured queries) |
| `trace_id` | string | Correlation ID (pipeline run, chat session, etc.) |
| `*` | any | Additional context fields |

---

## Outputs

| Output | Format | Location |
|--------|--------|----------|
| stderr | JSON stream | Default |
| `cherenkov.log` | File (rotating, 10MB max, 3 backups) | `.cherenkov/logs/` |
| `/api/v1/logs` | SSE stream | Dashboard |

---

## Correlation IDs

Every pipeline run gets a `trace_id`. Every HITL decision gets `parent_trace_id`. Every chat message gets `session_id + message_index`.

### Example

```json
{"ts":"2026-06-08T10:00:00Z","level":"INFO","logger":"cherenkov.orchestrator","msg":"Pipeline started","event":"pipeline_start","trace_id":"abc123"}
{"ts":"2026-06-08T10:00:01Z","level":"INFO","logger":"cherenkov.stages.ingest","msg":"Ingesting spec","event":"ingest_start","trace_id":"abc123","spec_path":"/path/to/spec.yaml"}
{"ts":"2026-06-08T10:00:05Z","level":"INFO","logger":"cherenkov.stages.ingest","msg":"Ingest complete","event":"ingest_end","trace_id":"abc123","endpoints":42}
{"ts":"2026-06-08T10:00:06Z","level":"INFO","logger":"cherenkov.stages.plan","msg":"Planning scenarios","event":"plan_start","trace_id":"abc123"}
{"ts":"2026-06-08T10:00:10Z","level":"INFO","logger":"cherenkov.stages.plan","msg":"Plan complete","event":"plan_end","trace_id":"abc123","scenarios":126}
```

---

## Implementation

### Setup

```python
# cherenkov/core/logging.py
import structlog
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """Setup structured logging."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if log_format == "json" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, log_level.upper()),
    )
    
    # Add file handler (rotating)
    log_dir = Path(".cherenkov/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_dir / "cherenkov.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=3,
    )
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(file_handler)

def get_logger(name: str = "cherenkov"):
    """Get structured logger."""
    return structlog.get_logger(name)
```

### Usage

```python
# cherenkov/core/orchestrator.py
from cherenkov.core.logging import get_logger
import uuid

logger = get_logger()

def run_pipeline(spec_path: str, trace_id: str | None = None):
    """Run pipeline with structured logging."""
    trace_id = trace_id or str(uuid.uuid4())
    log = logger.bind(trace_id=trace_id, spec_path=spec_path)
    
    log.info("pipeline_start")
    
    try:
        # Ingest
        log.info("ingest_start")
        ingest_output = ingest_stage.ingest(spec_path)
        log.info("ingest_end", endpoints=len(ingest_output.endpoints))
        
        # Plan
        log.info("plan_start")
        plan_output = plan_stage.plan(ingest_output)
        log.info("plan_end", scenarios=len(plan_output.scenarios))
        
        # Generate
        log.info("generate_start")
        generate_output = generate_stage.generate(plan_output)
        log.info("generate_end", tests=len(generate_output.tests))
        
        # Review
        log.info("review_start")
        review_output = review_stage.review(generate_output)
        log.info("review_end", approved=review_output.approved, hitl=review_output.hitl)
        
        log.info("pipeline_end", status="success")
        
    except Exception as e:
        log.error("pipeline_error", error=str(e), exc_info=True)
        raise
```

---

## Migration from print()

Replace all `print()` calls in core pipeline path with structured logger. Keep `print()` only for CLI user-facing output.

### Before

```python
def run_pipeline(spec_path: str):
    print(f"Starting pipeline for {spec_path}")
    # ... pipeline logic ...
    print(f"Generated {len(tests)} tests")
```

### After

```python
from cherenkov.core.logging import get_logger
import uuid

logger = get_logger()

def run_pipeline(spec_path: str, trace_id: str | None = None):
    trace_id = trace_id or str(uuid.uuid4())
    log = logger.bind(trace_id=trace_id, spec_path=spec_path)
    
    log.info("pipeline_start")
    # ... pipeline logic ...
    log.info("pipeline_end", tests_generated=len(tests))
```

---

## Log Queries

### Find all pipeline runs

```bash
cat .cherenkov/logs/cherenkov.log | jq 'select(.event == "pipeline_start")'
```

### Find all errors

```bash
cat .cherenkov/logs/cherenkov.log | jq 'select(.level == "ERROR")'
```

### Find all logs for a specific trace

```bash
cat .cherenkov/logs/cherenkov.log | jq 'select(.trace_id == "abc123")'
```

### Find all slow operations (>1s)

```bash
cat .cherenkov/logs/cherenkov.log | jq 'select(.duration_ms > 1000)'
```

---

## Dashboard Integration

### SSE Endpoint

```python
# cherenkov/web/api.py
from fastapi.responses import StreamingResponse
import asyncio

@app.get("/api/v1/logs")
async def stream_logs():
    """Stream logs via SSE."""
    async def event_generator():
        log_file = Path(".cherenkov/logs/cherenkov.log")
        last_pos = 0
        
        while True:
            if log_file.exists():
                with open(log_file, "r") as f:
                    f.seek(last_pos)
                    new_lines = f.readlines()
                    last_pos = f.tell()
                    
                    for line in new_lines:
                        yield f"data: {line}\n\n"
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### Dashboard Widget

```tsx
// cherenkov/web/ui/src/components/LogViewer.tsx
import React, { useState, useEffect } from 'react';

export function LogViewer() {
  const [logs, setLogs] = useState<any[]>([]);
  
  useEffect(() => {
    const eventSource = new EventSource('/api/v1/logs');
    
    eventSource.onmessage = (event) => {
      const log = JSON.parse(event.data);
      setLogs(prev => [...prev.slice(-100), log]);  // Keep last 100 logs
    };
    
    return () => eventSource.close();
  }, []);
  
  return (
    <div className="log-viewer">
      {logs.map((log, i) => (
        <div key={i} className={`log-line ${log.level.toLowerCase()}`}>
          <span className="timestamp">{log.ts}</span>
          <span className="level">{log.level}</span>
          <span className="logger">{log.logger}</span>
          <span className="message">{log.msg}</span>
        </div>
      ))}
    </div>
  );
}
```

---

## Testing

```python
# tests/unit/test_logging.py
from cherenkov.core.logging import setup_logging, get_logger
import json

def test_structured_logging():
    setup_logging(log_level="INFO", log_format="json")
    logger = get_logger("test")
    
    # Capture logs
    import io
    import sys
    captured = io.StringIO()
    sys.stderr = captured
    
    logger.info("test_message", key="value")
    
    sys.stderr = sys.__stderr__
    output = captured.getvalue()
    
    # Parse JSON
    log = json.loads(output.strip())
    assert log["level"] == "INFO"
    assert log["msg"] == "test_message"
    assert log["key"] == "value"
```

---

## References

- EPIC #279 (Phase 0b: Foundations)
- Issue #322 (Structured logging framework)
- `cherenkov/core/logging.py` (to be created)
- structlog documentation: https://www.structlog.org/
