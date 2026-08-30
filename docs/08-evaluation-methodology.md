# Evaluation Methodology (in-repo)

This document describes how to measure *this* system as it stands today.
For the more formal experimental design a paper would report, see
[research/EVALUATION-PROTOCOL.md](research/EVALUATION-PROTOCOL.md).

## What's already instrumented

- **`agent_scratchpad`** (in `TravelState`) — one entry per node visited
  per turn, including the supervisor's routing `reasoning`. This is the
  primary trace for measuring routing behavior: how many hops a turn
  took, which agents were visited and in what order, and whether the
  6-hop cap (`MAX_HOPS_PER_TURN`) was hit.
- **`backend/logs/app.log`** (rotating file, via `logging_config.py`) —
  timestamped, per-module logs of every routing decision, tool
  invocation, and result summary, plus full tracebacks on failure. This
  is the raw material for latency and failure-rate analysis (timestamps
  across log lines for the same session id bound each node's wall-clock
  cost).
- **Deterministic mocks** (`tools/flight_tools.py`, `tools/hotel_tools.py`)
  — seeded by query parameters, so the same scripted conversation
  produces the same flight/hotel offers across repeated runs. This is
  what makes repeatable evaluation runs possible without a live market.

## Suggested metrics

| Metric | How to compute | What it measures |
|---|---|---|
| Task success rate | Does the final state contain every field the user's request implied it should (e.g. `itinerary_draft` present when the user asked for an itinerary)? | End-to-end correctness |
| Constraint satisfaction | Does `budget_summary.over_budget` correctly reflect the offers actually selected? Does the itinerary respect `trip_constraints`? | Groundedness in structured data |
| Routing efficiency | Hops per turn (`len(agent_scratchpad)`), and how often a specialist is revisited for a need it already reported as unmet | Supervisor policy quality |
| Cost per turn | Count of orchestrator-tier vs. worker-tier LLM calls per turn (derivable from `agent_scratchpad` agent names + [03-llm-infra-decision.md](03-llm-infra-decision.md)'s per-node model assignment) | Tiered-allocation cost claim |
| Latency | Timestamp deltas between consecutive log lines for one session id | User-facing responsiveness |
| Graceful degradation rate | Fraction of turns where a specialist returns a "missing X" note (`agent_scratchpad`) instead of failing/hallucinating | Robustness to under-specified input |

## Suggested test harness (not yet built)

A minimal harness would script a fixed set of multi-turn conversations
through `backend/query_data.py:stream_graph_updates` directly (bypassing
HTTP), each ending in an assertion over the final `TravelState` fields
and/or the `agent_scratchpad` trace, run against the deterministic mock
tools so results are reproducible. This is a natural next engineering
step and the basis for the formal evaluation design in
[research/EVALUATION-PROTOCOL.md](research/EVALUATION-PROTOCOL.md); it
was not built in this pass to keep this iteration scoped to the
architecture itself plus its documentation.

## Algorithmic components worth benchmarking specifically

- **Multi-city routing** (`tools/routing_tools.order_multi_city_route`):
  nearest-neighbor is a known ≤2x-optimal heuristic in the worst case for
  metric TSP-like problems (not a formal guarantee derived here — verify
  against the routing literature before citing a bound in a paper). For
  n destinations, comparing its route length/km against a brute-force or
  ILP-optimal route (feasible for the typical n ≤ 5-6 of a leisure trip)
  would give a concrete approximation-ratio measurement specific to real
  city-distance distributions.
- **Budget aggregation** (`tools/budget_tools.aggregate_budget`): the
  current implementation always picks the single cheapest flight and
  cheapest hotel — a greedy heuristic for what is really a joint
  selection problem once more than one offer per category is worth
  considering together (e.g. a slightly pricier flight enabling a much
  cheaper hotel). Comparing greedy-selection budget totals against an
  exhaustive/ILP search over the small offer sets returned by the mock
  providers would quantify the gap.
