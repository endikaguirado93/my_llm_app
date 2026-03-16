# SQLite Logging Layer
## Overview
Every arena request is logged to a local SQLite database — capturing which models responded, what they said, and how long each one took. This builds the response history foundation needed for Phase 2: using logged latency and quality data to inform RAG-based model selection, so the system can learn which model tends to perform best for a given query type.

## Design Decisions
- **SQLite over Postgres/MySQL** — zero server setup, file-based, and sufficient for local development. One-line `DATABASE_URL` swap to migrate to Postgres when moving to production.
- **SQLAlchemy async** — all DB writes use `AsyncSession` via `aiosqlite` so the FastAPI event loop is never blocked.
- **Per-model latency** — `arena_start` is captured at the top of `run_arena_stream` and each model's `response_time_ms` is computed the moment its future completes, not at the end of the full arena run. This gives true individual model response times rather than a shared total.
- **Queue-based async wrapper** — `run_arena_stream` is a sync generator running a `ThreadPoolExecutor` internally. To stream chunks to the client without blocking the event loop, it runs in `run_in_executor` and pushes chunks into an `asyncio.Queue`. The async generator pulls from the queue and yields immediately to the client.
- **Log after stream** — DB writes happen after the sentinel `None` is received from the queue, meaning the client gets the full stream uninterrupted before any DB I/O occurs.
- **One row per model per session** — `request_logs` stores a separate row for each model so latency and response quality can be compared across models over time.

## How It Works
1. Arena stream completes → `result` event captured from SSE payload
2. Per-model `response_time_ms` values collected from `response` events during streaming
3. After sentinel received, a new session is created in `sessions`
4. One `messages` row written per turn (user + assistant per model)
5. One `request_logs` row written per model with latency and response text

## Schema
**`sessions`** — one row per arena run, UUID primary key

**`messages`** — each user/assistant turn linked to a session
```
id | session_id | role | content | created_at
```
**`request_logs`** — one row per model per session
```
id | session_id | model | prompt_tokens | response_tokens | latency_ms | error | created_at
```

## Useful Queries
```sql
-- Average latency per model
SELECT model, ROUND(AVG(latency_ms)/1000, 1) as avg_seconds, COUNT(*) as runs
FROM request_logs GROUP BY model;

-- Full conversation for a session
SELECT role, substr(content, 1, 80) FROM messages
WHERE session_id = '<id>' ORDER BY created_at;

-- All errored requests
SELECT * FROM request_logs WHERE error IS NOT NULL;
```

## Dependencies
- `sqlalchemy` + `aiosqlite` — async ORM and SQLite driver
- `asyncio.Queue` + `run_in_executor` — bridges sync generator to async stream
- `fastapi` `lifespan` — runs `create_all` on startup to auto-create tables