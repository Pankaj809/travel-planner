# API Reference

Unchanged endpoint contract from the pre-refactor implementation — the
multi-agent graph is entirely behind `stream_graph_updates()`, so no
frontend or integration changes are required.

## `GET /chat`

Returns `frontend/home.html` as-is (`HTMLResponse`). Serves the minimal
chat UI.

## `POST /chat`

**Request body:**

```json
{ "text": "Plan a 5-day trip from New York to Paris starting Sep 15, budget $2500" }
```

**Response body:**

```json
{ "reply": "<final assistant message text>" }
```

**Session identity:** the caller's `request.client.host` (IP) is used as
both the LangGraph `thread_id` and the `memory_store` session key. This is
a coarse, non-authenticated session boundary carried over from the
original implementation — see
[07-security-and-secrets.md](07-security-and-secrets.md) for the
implications and suggested follow-up.

**Behavior:** each call runs the full multi-agent graph to completion
(`graph.invoke`, not streamed to the client) and returns one final reply;
intermediate per-agent steps are not exposed over this endpoint today.
Streaming intermediate steps (e.g. for a "searching flights..." UI
indicator) would require exposing `graph.stream(...)` events through a
Server-Sent Events or WebSocket endpoint — noted as future work in
[research/RESEARCH-DIRECTION.md](research/RESEARCH-DIRECTION.md) rather
than implemented here, to keep this pass scoped to the agent/backend
redesign.

## CORS

`allow_origins=["*"]` (unchanged) — the existing code comment already
flags this as intended to be restricted to the real frontend origin
before any production deployment.
