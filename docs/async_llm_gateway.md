# Async LLM Gateway

## Overview

Each prompt is directed to all available LLMs in parallel, then the best answer is displayed first — decided by peer voting, where each model scores the others' responses. This introduces some latency, but improves output quality and sets the foundation for Phase 2: logging response history into a knowledge base so that RAG can eventually determine which model is best suited to answer a given query.

## Design Decisions

- **Parallel execution** via `ThreadPoolExecutor` — all model calls and votes are fired concurrently, with votes submitted as soon as their inputs are available rather than waiting for all responses to complete first.
- **SSE over polling** — the backend streams progress events to the frontend as they happen (`response`, `vote`, `result`), avoiding the need for the client to poll.
- **JS sprinkles over full SPA** — Jinja2 templates are kept intact; JavaScript intercepts form submission and manages UI state. This keeps the stack simple while still delivering a responsive feel during the latency window.
- **Peer-only voting** — models do not rate their own response, only the others'. With 3 models, each response receives 2 votes, for a max score of 20.
- **Winner drives conversation history** — the browser keeps a `history` array for multi-turn context; after each arena turn, the winning response is appended so follow-up questions remain coherent.

## How It Works

1. User submits a prompt → `POST /api/chat/arena/stream`
2. Backend fires all 3 model calls in parallel via `ThreadPoolExecutor`
3. As each response arrives, vote jobs are immediately submitted for every available pairing
4. Each step emits an SSE event (`response` / `vote` / `result`) to the frontend
5. Frontend updates the progress box in real time — model rows tick green, vote chips light up — then swaps the whole box for the final result card once `result` arrives
6. Winner is shown expanded; runner-ups are collapsed but accessible via `<details>`

## Interfaces

**Endpoint:** `POST /api/chat/arena/stream`
**Input:**
```json
{ "messages": [{ "role": "user", "content": "..." }] }
```

**SSE event stream (output):**
```json
{ "type": "response", "model": "mistral", "text": "...", "done": 1, "total": 3 }
{ "type": "vote", "judge": "llama3.2", "candidate": "mistral", "votes_done": 1, "votes_total": 6 }
{ "type": "result", "responses": {...}, "scores": {...}, "winner": "mistral" }
```

**Dependencies:**
- `ollama` — local model inference (llama3.2, mistral, gemma)
- `fastapi` + `StreamingResponse` — SSE transport
- `concurrent.futures.ThreadPoolExecutor` — parallel model calls and voting