# Related Work (pointers to verify and extend)

*These are pointers for a literature review, not a vetted bibliography —
verify each citation's exact venue/year/details independently before
using them in a paper; author memory of exact publication metadata can
be imprecise, and hosted-model/benchmark details change over time.*

## Tool-use and reasoning-acting agents

- **ReAct** (Yao et al.) — interleaving reasoning traces and tool-use
  actions in an LLM's generation loop. Directly relevant as the
  single-agent baseline this system's multi-agent design should be
  compared against (RQ1-style comparisons in
  [RESEARCH-DIRECTION.md](RESEARCH-DIRECTION.md)).
- **Reflexion** (Shinn et al.) — self-critique/verbal-reinforcement
  loops for agents that fail a task. Relevant to the "bounded-hop
  supervisor loop" axis (RQ4): Reflexion-style self-correction is an
  alternative to a hard hop cap for keeping an agent loop productive.
- **Toolformer** (Schick et al.) — teaching a model to decide when/how
  to call external tools. Relevant background for the "deterministic
  vs. LLM-in-the-loop node" design choice (RQ3): this system makes that
  decision by construction (per-node) rather than learning it.

## Multi-agent orchestration

- **AutoGen** (Wu et al.) and **CAMEL** (Li et al.) — general multi-agent
  conversation/orchestration frameworks; useful for contrasting this
  system's fixed hub-and-spoke topology
  ([../02-agent-design.md](../02-agent-design.md)) against more
  general peer-to-peer agent-communication frameworks.
- **Multiagent debate** (Du et al.) — using multiple agents/rounds to
  improve factuality/reasoning via disagreement, a different multi-agent
  paradigm than the supervisor/specialist division of labor used here
  (specialists here don't communicate with or critique each other).
- Anthropic, **"Building Effective Agents"** (engineering blog, 2024) —
  describes the orchestrator-worker pattern this system's supervisor
  topology follows; useful as a practitioner-level design reference
  alongside the more formal academic citations above.
- LangGraph's own documentation on multi-agent systems and `Command`-
  based handoff (the library this system is built on) is the direct
  primary source for the routing mechanism described in
  [../02-agent-design.md](../02-agent-design.md); cite the current
  official docs rather than this summary when writing up the mechanism
  formally, since library APIs evolve.

## Benchmarks directly relevant to this domain

- **TravelPlanner** (Xie et al.) — a benchmark specifically for
  real-world travel planning with language agents, evaluating plans
  against hard constraint satisfaction (budget, dates, preferences).
  This is the most directly relevant existing benchmark for evaluating
  this system's `itinerary`/`budget` agents' output against an
  established methodology, rather than only the in-repo metrics in
  [../08-evaluation-methodology.md](../08-evaluation-methodology.md).
  Worth reading closely before finalizing
  [EVALUATION-PROTOCOL.md](EVALUATION-PROTOCOL.md).

## Suggested next step for the literature review

Search recent (post-2024) surveys of "LLM multi-agent systems" and
"LLM agent planning benchmarks" to catch work published after this
document's authoring — the field moves quickly enough that a six-month-
old related-work section is likely incomplete.
