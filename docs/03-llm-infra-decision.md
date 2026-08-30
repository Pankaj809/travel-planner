# LLM / Infrastructure Decision Record

## Update (2026-08-30)

The provider described below (SiliconFlow) was later swapped for an
OpenAI-API-compatible aggregator (base URL configured via `LLM_BASE_URL`
in `config.py`), using `gpt-4o` as the orchestrator-tier model, `gpt-4o-mini`
as the worker-tier model, and `text-embedding-3-small` for embeddings. The
env var is now `LLM_API_KEY` (renamed from `SILI_API_KEY`). The reasoning
below is preserved as the original decision record; the provider-specific
details (SiliconFlow, Qwen model names) are historical rather than
current.

## Context

The pre-existing implementation called SiliconFlow's OpenAI-compatible API
with `Qwen/Qwen2.5-Coder-32B-Instruct` for chat and `Pro/BAAI/bge-m3` for
embeddings, with commented-out alternatives for Volcengine ARK
(`deepseek-r1-250120`) and NVIDIA NIM (`ChatNVIDIA`) left in the code. The
multi-agent redesign needed a routing/orchestrator model with reliable
structured-output (function-calling-equivalent) support, and a decision
on whether every agent should share one model or use different tiers.

## Decision

1. **Keep SiliconFlow as the inference provider.** It is already
   configured (`SILI_API_KEY`), OpenAI-compatible (works with
   `langchain_openai.ChatOpenAI`/`OpenAIEmbeddings` with no new client
   code), and hosts the full Qwen and DeepSeek model families at
   competitive CNY-denominated pricing. Switching providers would add
   integration and cost-tracking work with no capability this system
   needs today.
2. **Replace `Qwen2.5-Coder-32B-Instruct` with a two-tier general-purpose
   allocation:**
   - `Qwen/Qwen2.5-72B-Instruct` (**orchestrator** tier) for the
     `supervisor`, `itinerary`, and `responder` nodes — routing, slot
     extraction, multi-source synthesis, and free-form itinerary
     drafting.
   - `Qwen/Qwen2.5-7B-Instruct` (**worker** tier) for the `rag` node —
     answering from an already-retrieved knowledge-base context is a
     narrow, well-specified task that a smaller model handles reliably
     at a fraction of the cost/latency.
   - `flight`, `hotel`, `local_info`, `budget` nodes make **no LLM
     call** at all (see [02-agent-design.md](02-agent-design.md)).
3. **Keep `bge-m3` for embeddings.** It's already integrated, is strong
   on multilingual retrieval (relevant since the underlying product
   knowledge base is Chinese-language while trip-planning queries may be
   in English), and changing it would require re-embedding the existing
   Chroma store for no established benefit here.

## Why `Qwen2.5-Coder-32B-Instruct` was the wrong model for this system

It is a **code-specialized** fine-tune; the original single-node RAG
chatbot only needed adequate general instruction-following, and
"Coder" happened to satisfy that. A router/orchestrator role additionally
needs: (a) reliable Pydantic-schema-constrained structured output across
many turns, (b) good general-domain reasoning (travel constraints,
budget trade-offs, natural language), and (c) low refusal/derailment risk
outside programming contexts. A general-instruct model is the better fit
on all three axes; a code model has no advantage here since none of the
new agents generate or reason about code.

## Comparison matrix

| Option | Structured output | Est. relative cost | Multilingual | Fit for this system |
|---|---|---|---|---|
| **Qwen2.5-72B-Instruct** (chosen, orchestrator) | Strong | Medium | Strong (incl. Chinese) | Best balance for routing + synthesis |
| Qwen2.5-7B-Instruct (chosen, worker) | Adequate for narrow tasks | Low | Strong | Right-sized for RAG answer formatting |
| Qwen2.5-Coder-32B-Instruct (previous) | Adequate | Medium | Adequate | Wrong specialization (code-tuned) for a travel domain |
| DeepSeek-V3 (via SiliconFlow or Volcengine ARK) | Strong | Medium-Low | Strong | Credible alternative orchestrator; not selected only to avoid mixing two provider auth paths (SiliconFlow + ARK) for a first version — worth an A/B in follow-up work |
| GPT-4o-mini / Claude Haiku (non-China-region providers) | Strong | Medium (USD-billed) | Strong | Would require new provider integration/auth and USD billing; no capability gap justifies the switch given (1)/(2) above |

This matrix is a starting point, not a benchmark result — see
[research/EVALUATION-PROTOCOL.md](research/EVALUATION-PROTOCOL.md) for
how to turn "Est. relative cost" and routing-accuracy claims into
measured numbers, and re-verify current model availability/pricing on
SiliconFlow's own listing before relying on this table, since hosted
catalogs change over time.

## Consequences

- `backend/llm.py` centralizes model construction behind
  `get_llm(role="orchestrator"|"worker")`, replacing the per-call
  `ChatOpenAI(...)` construction duplicated in the original
  `search_info`/`query_rag` functions.
- `backend/config.py` is the single place to change model names or swap
  providers; no agent file references a model name directly.
- Two live API calls per multi-hop turn are now typical (supervisor
  routing + one specialist/responder LLM call), each on the 72B tier,
  plus at most one 7B call if `rag` is visited — worth tracking against
  the cost baseline once real usage data exists.
