# Research Direction

*This document frames the system in `docs/00-overview.md` through
`docs/08-evaluation-methodology.md` as a starting point for a research
write-up, not as a finished paper. Every claim below that would need a
citation or an experimental result is marked as such — treat this as a
research proposal / positioning draft, not as established findings.*

## Problem statement

Travel planning is a compositional task: satisfying it requires
retrieving and reconciling information from several independent,
differently-shaped sources (flight/hotel availability and price,
destination weather and entry requirements, a fixed budget, and a
user-specified but incompletely stated set of constraints), then
synthesizing a coherent multi-day plan that respects all of them
simultaneously. It is a natural instance of the broader open problem of
using LLM-based agents for **multi-constraint, multi-tool planning under
partial information** — and, unlike many synthetic agent benchmarks, has
an existing benchmark built specifically around it (TravelPlanner; see
[RELATED-WORK.md](RELATED-WORK.md)), which is what makes it a reasonable
vehicle for studying multi-agent orchestration design choices rather than
just building a demo.

## System as implemented, and the design axes it exposes

The system described in this repository (see
[../02-agent-design.md](../02-agent-design.md)) makes four concrete
design choices, each of which is a variable that could be ablated or
compared against an alternative in a follow-up study:

1. **Command-based dynamic handoff vs. static conditional routing.**
   The supervisor and every specialist return `Command(goto=...)`
   objects rather than being wired through `add_conditional_edges`. This
   trades graph-shape transparency (a statically declared graph is
   easier to visualize/verify exhaustively) for co-locating a node's
   routing decision with the state update that produced it.
   **RQ1:** For a fixed task set, does dynamic Command-based routing
   differ measurably from an equivalent static-conditional-edge graph in
   task success rate, hop count, or latency? (Hypothesis: no difference
   in outcome, since both express the same policy — the comparison is
   really about maintainability, which would need a code-complexity or
   developer-study proxy rather than a runtime metric.)

2. **Tiered model allocation.** A larger "orchestrator" model handles
   routing/slot-filling/synthesis; a smaller "worker" model handles the
   narrow RAG-answering task; four specialists make no LLM call at all
   (see [../03-llm-infra-decision.md](../03-llm-infra-decision.md)).
   **RQ2:** What is the accuracy/cost Pareto frontier of this tiered
   allocation versus a uniform-large-model baseline, and versus a
   uniform-small-model baseline, on a fixed task set? This is directly
   measurable with the cost/latency instrumentation described in
   [../08-evaluation-methodology.md](../08-evaluation-methodology.md).

3. **Deterministic tool nodes vs. LLM-in-the-loop nodes.** Four of eight
   nodes (`flight`, `hotel`, `local_info`, `budget`) are pure function
   calls with no LLM step, on the premise that structured-data retrieval
   and arithmetic don't benefit from (and add hallucination surface via)
   an LLM call. **RQ3:** Does adding an LLM step to a currently-
   deterministic node improve any measured metric, or only add
   cost/latency/variance for no accuracy gain? This is a clean ablation
   in this codebase — reroute one specialist's `Command` through an LLM
   summarization step and re-run the same task set.

4. **Bounded-hop supervisor loop.** `MAX_HOPS_PER_TURN = 6` is a fixed,
   unvalidated constant. **RQ4:** What is the actual distribution of
   hops-to-completion for realistic multi-constraint requests, and how
   does the completion rate change as the cap is varied? This bears on
   the general question of how to bound agentic loops without either
   truncating legitimate multi-step tasks or allowing runaway cost.

## A fifth axis specific to the tool layer

5. **Hybrid symbolic-neural itinerary construction.** Multi-city
   ordering is computed by a deterministic nearest-neighbor heuristic
   (`tools/routing_tools.py`) and *handed to* the LLM as a fixed input
   for narrative drafting, rather than letting the LLM freely decide the
   visiting order itself. **RQ5:** Does grounding the LLM's itinerary
   synthesis in an externally-computed route (vs. letting the LLM infer
   ordering from city names alone) measurably reduce geographically
   incoherent itineraries (e.g. backtracking across a continent)? This
   is directly checkable against `total_km` from the same heuristic
   applied to the LLM's own chosen order vs. the tool's order.

## Threats to validity / limitations of the current implementation

- Flight and hotel data are deterministic **mocks**, not real market
  data (explicit scoping decision — see
  [../04-tools-and-integrations.md](../04-tools-and-integrations.md)).
  Any accuracy/success-rate claim is therefore about the *orchestration
  logic*, not about real-world booking correctness, until real providers
  are integrated.
- The visa dataset covers ~14 corridors — far from comprehensive; visa
  RQ-style evaluation would need either a much larger static dataset or
  a real provider integration first.
- All experiments so far would run against a single model family/vendor
  (Qwen via SiliconFlow) — cross-provider generalization is untested.
- No human evaluation of itinerary quality (usefulness, tone, factual
  presentation) has been conducted; the metrics in
  [../08-evaluation-methodology.md](../08-evaluation-methodology.md) are
  all automatically computable proxies.

## Suggested future work

- Build the test harness sketched in
  [../08-evaluation-methodology.md](../08-evaluation-methodology.md) and
  run RQ1-RQ5 against it.
- Replace the nearest-neighbor routing heuristic with an exact/ILP
  solver for small n and measure the approximation gap on real
  city-distance data (addresses the open question in
  [../08-evaluation-methodology.md](../08-evaluation-methodology.md)).
- Integrate one real flight/hotel provider behind the existing tool
  interfaces (no agent-level changes required — see
  [../04-tools-and-integrations.md](../04-tools-and-integrations.md))
  and re-run the same evaluation to separate "orchestration quality"
  from "mock-data artifacts."
- A small human-subjects study comparing this system's itineraries
  against a single-agent ReAct-style baseline on the same tasks would
  be the natural next step toward a publishable comparison, since
  TravelPlanner-style automatic metrics capture constraint satisfaction
  but not itinerary quality/usefulness.
