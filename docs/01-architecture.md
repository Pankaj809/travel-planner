# Architecture

## Component overview

```mermaid
flowchart TD
    U[User / frontend] -->|"POST /chat {text}"| API["FastAPI (main.py)"]
    API --> QD["query_data.stream_graph_updates()"]
    QD --> MEM[("memory_store\nper-session messages + trip_constraints")]
    QD --> GRAPH

    subgraph GRAPH["LangGraph: TravelState graph (graph/build_graph.py)"]
        SUP["Supervisor\n(orchestrator LLM: routing + slot-filling)"]
        RAG["RAG Agent\n(worker LLM + Chroma)"]
        FLT["Flight Agent\n(deterministic tool)"]
        HTL["Hotel Agent\n(deterministic tool)"]
        LOC["Local Info Agent\n(weather + visa tools)"]
        ITN["Itinerary Agent\n(orchestrator LLM + routing tool)"]
        BUD["Budget Agent\n(deterministic tool)"]
        RSP["Responder\n(orchestrator LLM: final synthesis)"]

        SUP -. "Command(goto=...)" .-> RAG
        SUP -. "Command(goto=...)" .-> FLT
        SUP -. "Command(goto=...)" .-> HTL
        SUP -. "Command(goto=...)" .-> LOC
        SUP -. "Command(goto=...)" .-> ITN
        SUP -. "Command(goto=...)" .-> BUD
        SUP -. "Command(goto=responder)" .-> RSP
        RAG -. "Command(goto=supervisor)" .-> SUP
        FLT -. "Command(goto=supervisor)" .-> SUP
        HTL -. "Command(goto=supervisor)" .-> SUP
        LOC -. "Command(goto=supervisor)" .-> SUP
        ITN -. "Command(goto=supervisor)" .-> SUP
        BUD -. "Command(goto=supervisor)" .-> SUP
    end

    RSP --> QD
    QD --> API --> U
```

Source of truth for node/edge names: `backend/graph/build_graph.py`.

## Request lifecycle

1. `POST /chat` (`backend/main.py`) receives `{ "text": ... }`, keyed by
   the caller's IP as a coarse session id (unchanged from the original
   single-node implementation).
2. `stream_graph_updates()` (`backend/query_data.py`) loads that session's
   prior messages and `trip_constraints` from `memory_store`, appends the
   new `HumanMessage`, and builds a `TravelState` (see
   [02-agent-design.md](02-agent-design.md) for the schema).
3. `graph.invoke(state, ...)` runs the compiled LangGraph until it reaches
   `END`. Internally, control passes back and forth between the
   `supervisor` node and specialist nodes via `Command(goto=...)` objects
   returned directly by each node — see
   [02-agent-design.md](02-agent-design.md) for why this dynamic
   handoff pattern was chosen over static `add_conditional_edges`.
4. The `responder` node is the only node with a static edge to `END`; it
   composes the final `AIMessage` from every structured result the
   specialists produced.
5. `stream_graph_updates()` persists the updated `trip_constraints` and
   trimmed message history back into `memory_store`, and returns the
   reply text to the FastAPI layer.

## Representative multi-hop trace

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant Sup as Supervisor
    participant Flt as Flight Agent
    participant Loc as Local Info Agent
    participant Itn as Itinerary Agent
    participant Rsp as Responder

    User->>API: "Plan NYC -> Paris, Sep 15-20, budget $2500"
    API->>Sup: TravelState(messages, trip_constraints={})
    Sup->>Sup: extract constraints, decide next=flight
    Sup->>Flt: Command(goto=flight)
    Flt->>Flt: search_flights(origin, dest, date)
    Flt->>Sup: Command(goto=supervisor, flight_results=[...])
    Sup->>Loc: Command(goto=local_info)
    Loc->>Loc: get_weather_forecast(), get_visa_requirement()
    Loc->>Sup: Command(goto=supervisor, local_info_results=[...])
    Sup->>Itn: Command(goto=itinerary)
    Itn->>Itn: order_multi_city_route(), LLM draft
    Itn->>Sup: Command(goto=supervisor, itinerary_draft=...)
    Sup->>Rsp: Command(goto=responder)
    Rsp->>Rsp: synthesize final answer from all state
    Rsp->>API: {"messages": [...]}
    API->>User: JSON reply
```

Each hop appends one entry to `agent_scratchpad` (an `operator.add`-reduced
state channel), giving a per-turn audit trail of which agents ran, in what
order, and why (`RouteDecision.reasoning`). This trail is what
[08-evaluation-methodology.md](08-evaluation-methodology.md) uses for
tracing.

## Robustness

`MAX_HOPS_PER_TURN` (`backend/agents/supervisor.py`) bounds the
supervisor↔specialist loop at 6 hops per user turn, after which the graph
is forced to `responder` regardless of the LLM's routing decision. This
guards against routing loops (e.g. the supervisor repeatedly re-selecting
an agent that cannot make progress because a required constraint is still
missing) turning into unbounded cost/latency.

Diagram sources are duplicated as standalone `.mmd` files under
`docs/diagrams/` for export into other tools.
