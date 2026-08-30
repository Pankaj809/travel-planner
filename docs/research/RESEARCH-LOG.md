# Research Log

Dated entries recording what was actually run and found, as distinct
from [RESEARCH-DIRECTION.md](RESEARCH-DIRECTION.md) (proposal) and
[EVALUATION-PROTOCOL.md](EVALUATION-PROTOCOL.md) (protocol to follow).
This document reports results; treat everything here as pilot-scale
per the caveats in [PILOT-TASK-SET.md](PILOT-TASK-SET.md).

## 2026-08-30: RQ2 pilot run (tiered vs. uniform model allocation)

Ran all 13 tasks in `backend/pilot/task_set.py` through
`backend/pilot/harness.py` under all three of
EVALUATION-PROTOCOL.md section 2's model-allocation conditions:

```
python3 -m pilot.harness --condition all --out results/<condition>.json
```

Raw output: `backend/pilot/results/{tiered,uniform_orchestrator,uniform_worker}.{json,log}`.
Comparison tables: `python3 -m pilot.score` (`backend/pilot/score.py`).

### Result: identical pass rate across all three conditions

| Condition | Pass rate | Total hops | Orchestrator calls | Worker (rag) calls |
|---|---|---|---|---|
| Tiered (gpt-4o orchestrator / gpt-4o-mini worker) | 9/13 | 99 | 61 | 9 |
| Uniform-large (gpt-4o everywhere) | 9/13 | 97 | 60 | 9 |
| Uniform-small (gpt-4o-mini everywhere) | 9/13 | 93 | 58 | 4 |

The same four tasks fail in **every** condition: T1, T5, T8, T9. Since
model tier has no effect on which tasks pass, these four failures are
implementation defects, not model-capability gaps:

- **T1** (`local_info_results empty`, `budget_summary missing`) and
  **T10/T11**'s known geocoding/ISO-code coupling
  (PILOT-TASK-SET.md defect 1) both point at `local_info_node`
  passing one destination string to two lookups that expect different
  formats.
- **T5** (`budget_summary missing` for a 3-city trip) is
  PILOT-TASK-SET.md defect 2: `aggregate_budget` only ever reflects
  one leg of a multi-city trip.
- **T8** (`knowledge_context missing`): the supervisor never routes a
  domain-mix turn (trip-planning question that also touches the RAG
  knowledge base) to the `rag` agent. Not a hop-budget issue — this is
  a routing miss on the first turn.
- **T9** (`agent_scratchpad` has 7 entries against
  `MAX_HOPS_PER_TURN=6`): the hop cap is not actually enforced as a
  hard ceiling for a 5-city stress request.

None of these four are sensitive to which model handles orchestration
vs. worker calls — worth fixing before a properly-powered RQ2 run,
since right now they're a fixed 4/13 floor on pass rate regardless of
model allocation.

### One real difference: routing efficiency, not accuracy

`uniform_worker` (gpt-4o-mini doing orchestration too) made only 4 calls
to the `rag` agent across all 13 tasks' turns, vs. 9 in both other
conditions — despite passing the same 9/13 tasks. The smaller model
is routing to RAG less readily even where it doesn't change final
pass/fail outcome. This is a routing-efficiency signal worth a closer
look (e.g. whether it's under- or over-triggering RAG relative to
ground truth) rather than a rate this pilot's task set can explain on
its own — T8's routing-miss failure is identical across conditions,
so this isn't simply "uniform_worker fixes T8 differently."

Total hops and elapsed time are within noise of each other across
conditions (93-99 hops, 273-286s) — no condition shows a cost/latency
advantage large enough to matter at n=13.

### What this does and doesn't establish

Per PILOT-TASK-SET.md's own scope note: n=13 is far below the 30-50
per stratum EVALUATION-PROTOCOL.md section 1 calls for, and no
proportion test was run (section 5) — a 9/13 vs. 9/13 vs. 9/13 tie
isn't a claim that model allocation has zero effect on accuracy, just
that this pilot found no directional signal worth a significance test
at this scale. The routing-efficiency gap above is the one result
that looks worth carrying into a bigger run.

### Next step

Fix the four structural defects (or explicitly scope them as known
limitations) before running EVALUATION-PROTOCOL.md at its intended
scale — otherwise every condition will share the same artificial 4/13
floor and mask whatever the actual model-allocation effect is.
