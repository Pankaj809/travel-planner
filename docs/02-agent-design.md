# Agent Design

## Topology: supervisor (hub-and-spoke) with Command-based handoff

The graph uses a single supervisor node that routes to one specialist at a
time and receives control back after each specialist completes
(`backend/agents/supervisor.py`, `backend/graph/build_graph.py`). This is
the "orchestrator-worker" pattern described in Anthropic's *Building
Effective Agents* (2024) and implemented in LangGraph via `Command`
objects returned directly from node functions, rather than
`add_conditional_edges` declared on the graph builder.

**Why Command-based handoff instead of static conditional edges:**

- Every specialist always returns to the same place (`supervisor`), so the
  "specialist → supervisor" edges are just as fixed as the ones the
  original single-node graph had. What genuinely varies is the
  *supervisor → specialist* choice, which is a run-time decision, not a
  compile-time graph shape.
- `add_conditional_edges` would require a separate router function whose
  branch table has to be kept in sync with the specialist's own
  `Command.update` payload. Returning `Command(goto=..., update=...)`
  directly from the deciding node keeps the routing decision and the
  state mutation it causes co-located in one function — one fewer place
  for the two to drift out of sync.
- It also makes each node's possible destinations self-documenting via
  its `Command[Literal[...]]` return-type annotation, which is what the
  graph-render tooling (`graph.get_graph()`) uses to draw edges even
  though none are statically declared.

**Why hub-and-spoke instead of a peer-to-peer/swarm topology** (where
specialists can hand off directly to each other): every specialist agent
here is stateless with respect to the others — flight results don't
change what the hotel agent does, for example — the only thing that
sequences them is unmet slot requirements. Centralizing that sequencing
in one supervisor keeps the *policy* for "what to do next" in one place,
which matters for the routing-policy evaluation in
[08-evaluation-methodology.md](08-evaluation-methodology.md). A
peer-to-peer topology becomes preferable once specialists need to react
directly to each other's output without a shared bottleneck (see
[research/RESEARCH-DIRECTION.md](research/RESEARCH-DIRECTION.md) RQ1 for
the direct comparison this motivates).

## State schema (`backend/graph/state.py`)

```python
class TravelState(CopilotKitState):
    messages: Annotated[list[BaseMessage], add_messages]  # reducer: append
    thread_id: str
    trip_constraints: dict                                  # slot-filled across turns
    flight_results: list[dict]
    hotel_results: list[dict]
    local_info_results: list[dict]                          # weather + visa
    knowledge_context: str                                  # RAG output
    itinerary_draft: Optional[str]
    budget_summary: Optional[dict]
    agent_scratchpad: Annotated[list[dict], operator.add]    # reducer: append
```

Two fields use non-default reducers because multiple nodes write to them
across a single turn's multi-hop loop:

- `messages` uses LangGraph's `add_messages` reducer so the responder's
  `{"messages": [response]}` update appends rather than replacing the
  whole history.
- `agent_scratchpad` uses `operator.add` so every node's one-line note
  accumulates into a full per-turn trace, rather than each node
  overwriting the last one's note.

Every other field is a plain replace-on-write channel — a specialist only
ever writes the field(s) it owns, so replace semantics are correct and
simpler than a reducer would be.

## Per-agent responsibilities

| Agent | LLM used | Deterministic component | Depends on |
|---|---|---|---|
| `supervisor` | orchestrator (structured output) | — | full conversation |
| `rag` | worker | `retrieval_db.get_db` (Chroma similarity search) | user query only |
| `flight` | none | `tools.flight_tools.search_flights` | `origin`, `destinations`, `start_date` |
| `hotel` | none | `tools.hotel_tools.search_hotels` | `destinations`, `start_date`, `end_date` |
| `local_info` | none | `tools.weather_tools`, `tools.visa_tools` | `destinations` (nationality optional for visa) |
| `itinerary` | orchestrator | `tools.routing_tools.order_multi_city_route` | prior flight/hotel/local_info results |
| `budget` | none | `tools.budget_tools.aggregate_budget` | prior flight/hotel results |
| `responder` | orchestrator | — | everything gathered so far |

**Deterministic vs. LLM-in-the-loop is a deliberate per-agent choice, not
a blanket policy.** `flight`, `hotel`, `local_info`, and `budget` are pure
tool calls with no LLM step: their outputs are structured data that the
`responder` later narrates, so adding an LLM call inside them would only
add cost/latency/hallucination surface without adding capability. `rag`,
`itinerary`, and `responder` genuinely need synthesis over unstructured
or multi-source input, so they call an LLM. This split is itself a
variable worth ablating — see
[research/RESEARCH-DIRECTION.md](research/RESEARCH-DIRECTION.md).

## Slot-filling protocol

The supervisor extracts trip details from the latest turn via structured
output (`RouteDecision.constraints_update`, a `TripConstraintsUpdate`
Pydantic model) in the *same* LLM call used for routing, rather than a
separate NLU pass. Fields are `origin`, `destinations`, `start_date`,
`end_date`, `budget_total`, `currency`, `travelers`, `nationality`. A
specialist that's missing a constraint it needs does not fail loudly — it
returns a short note into `agent_scratchpad` and hands control back to
the supervisor, whose prompt is instructed to route to `responder` (to
ask the user directly) rather than a specialist it already knows will be
under-specified.

## Guardrails

- `MAX_HOPS_PER_TURN = 6` — see [01-architecture.md](01-architecture.md).
- Every prompt (`backend/prompt.py`) instructs its agent not to fabricate
  facts (prices, dates, visa rules) beyond what's in the supplied
  structured context — mirroring the original single-agent prompt's
  "never provide fabricated information" instruction.
