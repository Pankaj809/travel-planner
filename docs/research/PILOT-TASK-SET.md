# Pilot Task Set (RQ2: tiered vs. uniform model allocation)

This is the scripted conversation set for a pilot run of the protocol in
[EVALUATION-PROTOCOL.md](EVALUATION-PROTOCOL.md), scoped to **RQ2** from
[RESEARCH-DIRECTION.md](RESEARCH-DIRECTION.md): does the current tiered
allocation (`gpt-4o` orchestrator / `gpt-4o-mini` worker, per
[../03-llm-infra-decision.md](../03-llm-infra-decision.md)) differ from a
uniform-model baseline on task success, constraint satisfaction, routing
efficiency, cost, and graceful degradation?

The 13 conversations live as executable data in
`backend/pilot/task_set.py` (`ALL_TASKS`), each with scripted user turns and
an `assertions(final_state)` function that scores the graph's final
`TravelState` deterministically. This document explains the design and its
limits; the task data itself is the source of truth, not a duplicate of it
here.

## Scale and what it does/doesn't establish

EVALUATION-PROTOCOL.md's full design calls for 30-50 conversations per
stratum. This pilot has 13 conversations *total* - enough to sanity-check
the harness and get a directional read across two model-allocation
conditions, not enough for the proportion tests (two-proportion z-test /
Fisher's exact) the protocol specifies for a properly-powered comparison.
Treat any Condition A vs. B difference from this pilot as "worth a bigger
run," not as a supported claim - this matches the protocol's own
section 5 caveat, just at a smaller n than even its "small task set"
framing assumes.

## Stratification coverage

| Task | Slot completeness | Destination count | Constraint tightness | Domain |
|---|---|---|---|---|
| T1 | full | single | comfortable | trip_planning |
| T2 | full | single | tight (over) | trip_planning |
| T3 | full | multi (3) | comfortable | trip_planning |
| T4 | under-specified, multi-turn | single | comfortable | trip_planning |
| T5 | under-specified, multi-turn | multi (3) | tight | trip_planning |
| T6 | n/a | n/a | n/a | rag (in-corpus) |
| T7 | n/a | n/a | n/a | rag (out-of-corpus) |
| T8 | full | single | comfortable | mixed (rag then trip_planning) |
| T9 | full | multi (5) | comfortable | trip_planning (hop-budget stress) |
| T10 | full | single | comfortable | trip_planning (visa, city phrasing) |
| T11 | full | single | comfortable | trip_planning (visa, ISO phrasing) |
| T12 | full | single | comfortable | trip_planning (weather horizon) |
| T13 | under-specified, multi-turn | single | comfortable | trip_planning (contradiction) |

Every axis from EVALUATION-PROTOCOL.md section 1 is touched at least three
times except "domain mix," which is inherently a single-conversation
property (T8) rather than something to replicate many ways in a 13-task
pilot.

## Why the RAG questions are about AI accelerator cards, not travel

`backend/data/pdf/` (the actual RAG corpus, confirmed by extracting text
directly from the three PDFs rather than assuming) contains Cambricon
MLU370-S4/X8/X4 product manuals - hardware spec sheets, not travel content.
This is expected and correct: the `rag` agent is "the direct continuation
of the original single-node bot's core function" per
[../05-data-rag-pipeline.md](../05-data-rag-pipeline.md), and that original
bot was a product-knowledge-base assistant, not a travel bot. T6/T7 are
written against real, verified page content (MLU370-X8 manual, section
4.1: TDP 250W, memory capacity 48GB) rather than an assumed travel FAQ, so
the grounding check is checking something real.

## Two defects surfaced while designing this task set (not introduced by it)

Both are documented here rather than fixed, since fixing them isn't in
scope for a pilot task-set design pass - flagging them is itself a pilot
output (per RESEARCH-DIRECTION.md's framing of this as ablatable design
axes, these are two more candidates for that list):

1. **Visa lookup is coupled to the weather-geocoding string.**
   `local_info_node` (`backend/agents/local_info_agent.py`) passes the same
   `destination` value to both `get_weather_forecast` (expects a
   geocodable city name) and `get_visa_requirement` (keyed by ISO country
   code in `tools/visa_data.json`). A naturally-phrased destination that
   makes weather lookup work ("Paris") will almost always miss the visa
   table, independent of model quality - see T10's notes. T11 tests
   whether prompting the destination as an explicit code changes this,
   which would itself show the failure is a schema/interface issue (one
   slot serving two purposes) rather than an extraction-accuracy issue.
2. **Budget aggregation undercounts multi-city trips.**
   `aggregate_budget` (`tools/budget_tools.py`) always picks a single
   cheapest flight offer and a single cheapest hotel offer, regardless of
   how many destinations were searched - so a 3-city trip's `budget_summary`
   reflects the cost of *one* leg, not three. T5 is scored only on whether
   a `budget_summary` is produced, not on its correctness for this reason.

## Known non-determinism affecting scoring

`destinations`/`origin` are free-text strings extracted by an LLM
(`supervisor_node`'s structured output), not canonicalized. Two consequences
for scoring, both handled by keeping assertions structural rather than
exact-string wherever possible:

- Mock flight/hotel offers are seeded by the *exact* extracted string
  (`tools/flight_tools.py:seed_for`), so the same scripted conversation can
  produce different (but each still internally consistent) mock offers
  across runs/models if the extracted string varies (e.g. "Paris" vs.
  "Paris, France"). Assertions check presence/shape/ordering of offers, not
  specific prices.
- Visa/weather lookups depend on the extracted string matching what the
  respective data source expects (ISO code vs. geocodable name
  respectively - see the coupling defect above), so T10/T11 are scored on
  graceful-degradation behavior, not on achieving a specific `known` value.

## Next step

`backend/pilot/task_set.py` is consumed by the (not-yet-built) harness -
see task tracking for "Build minimal test harness." The harness needs a
thin wrapper around `graph.invoke` directly (bypassing
`query_data.py:stream_graph_updates`'s reply-string-only return) to capture
the full `TravelState` these assertions score against, and must run each
multi-turn task's turns against the *same* `thread_id`/session so
`trip_constraints` accumulates across turns the way `memory_store.py`
does in the real request path.
