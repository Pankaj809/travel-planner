# Evaluation Protocol (formal experimental design)

This is the experimental design a write-up should report, building on
the in-repo instrumentation described in
[../08-evaluation-methodology.md](../08-evaluation-methodology.md). None
of the runs described here have been executed yet — this is a protocol
to follow, not a report of results.

## 1. Task set construction

Construct a fixed set of scripted multi-turn conversations, stratified
along axes known to stress different parts of the system:

- **Slot completeness**: fully-specified requests (origin, destination,
  dates, budget, travelers all given up front) vs. under-specified ones
  requiring multi-turn slot-filling.
- **Destination count**: single-city vs. multi-city (2-5 destinations,
  to keep `order_multi_city_route`'s brute-force-comparable baseline
  tractable — see [RESEARCH-DIRECTION.md](RESEARCH-DIRECTION.md) RQ5).
- **Constraint tightness**: budget comfortably above vs. below the
  cheapest achievable total (to exercise `budget_summary.over_budget`
  and any downstream re-planning behavior).
- **Domain mix**: pure trip-planning requests vs. requests that also
  touch the original product/policy knowledge base (`rag` agent), to
  verify the multi-agent extension didn't regress the system's original
  capability.

A reasonable starting size is 30-50 conversations per stratum; TravelPlanner
(see [RELATED-WORK.md](RELATED-WORK.md)) is a source of task templates
and constraint-satisfaction scoring logic worth adapting rather than
reinventing.

## 2. Independent variables (what to vary across conditions)

| Variable | Levels |
|---|---|
| Routing mechanism | Command-based (current) vs. static conditional-edge graph (RQ1) |
| Model allocation | Tiered (current: 72B orchestrator / 7B worker) vs. uniform-72B vs. uniform-7B (RQ2) |
| Node determinism | Current (4 deterministic + 3 LLM + supervisor) vs. one deterministic node converted to LLM-in-the-loop (RQ3) |
| Hop budget | `MAX_HOPS_PER_TURN` in `{3, 6 (current), 10, unbounded}` (RQ4) |
| Routing grounding | Tool-computed route handed to itinerary LLM (current) vs. LLM infers order unaided (RQ5) |

Vary one axis at a time against the current implementation as the
control condition; a full factorial across all five is unlikely to be
worth the cost given the small effect sizes plausible for some axes
(e.g. RQ1).

## 3. Dependent variables / metrics

Reuse the definitions in
[../08-evaluation-methodology.md](../08-evaluation-methodology.md)
(task success rate, constraint satisfaction, routing efficiency, cost
per turn, latency, graceful-degradation rate), plus, for RQ5
specifically: total route distance (`order_multi_city_route`'s
`total_km`) of the itinerary the LLM actually produced vs. the
tool-suggested route, as a proxy for geographic coherence.

## 4. Procedure

1. Run each task-set conversation through
   `backend/query_data.py:stream_graph_updates` directly (bypassing
   HTTP) against the deterministic mock tools, once per condition being
   compared.
2. Log every run's full `agent_scratchpad` trace and final `TravelState`
   (not just the reply text) for offline scoring.
3. Score constraint satisfaction and task success programmatically
   against each conversation's known ground-truth constraints (the
   scripted task, since it was authored with known correct answers).
4. Report cost/latency as means with variance (not just means) given the
   likely high per-turn variance in hop count.

## 5. Statistical considerations

- Task success rate and constraint satisfaction are proportions —
  use a proportion test (e.g. two-proportion z-test) or, for small task
  sets, Fisher's exact test, when comparing two conditions.
- Cost/latency are continuous and likely right-skewed (occasional long
  multi-hop turns) — report medians/IQR alongside means, and prefer a
  non-parametric test (e.g. Mann-Whitney U) over a t-test for condition
  comparisons.
- With a hand-authored task set of 30-50 conversations per stratum,
  treat any result as a pilot/directional finding, not a
  well-powered claim — state this explicitly in any write-up rather than
  overstating statistical significance from a small, non-randomly-
  sampled task set.

## 6. What this protocol does not cover

Itinerary *quality* (as opposed to constraint satisfaction) — tone,
usefulness, whether a human traveler would actually want the suggested
plan — is not measurable by the automatic metrics above and would need a
separate human-evaluation study (rating or pairwise comparison against a
baseline), out of scope for this protocol but flagged as necessary before
any claim about itinerary *quality* (not just correctness) in a paper.
