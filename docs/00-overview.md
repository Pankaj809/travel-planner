# ICS Travel Agent — Overview

## What this is

ICS started as a single-node LangGraph RAG customer-service assistant
(`backend/query_data.py`, pre-refactor). This document set describes its
extension into a **multi-agent travel-planning assistant** built on the same
FastAPI service and the same LangGraph/LangChain stack, covering:

- Itinerary planning (single- and multi-city)
- Flight and hotel search
- Budget aggregation and constraint checking
- Weather and visa-requirement lookups
- The original product/policy knowledge-base Q&A (RAG), preserved as one of
  the specialist agents

## Goals

1. Extend the existing FastAPI backend in place (same `/chat` contract),
   not a rewrite into a new service.
2. Route user requests to specialist agents via a LangGraph multi-agent
   graph rather than a single monolithic prompt.
3. Keep every tool's interface stable and provider-agnostic, so mocked
   data sources (used here — see [[04-tools-and-integrations]]) can be
   swapped for real providers without touching agent logic.
4. Produce documentation detailed enough to serve as the basis for a
   research write-up on multi-agent orchestration and tool-use for
   compositional planning tasks — not just an engineering README.

## Non-goals

- Real-money booking/payment flows.
- A production-grade flight/hotel GDS integration (explicitly out of
  scope per the current mocked-data-source decision — see
  [[03-llm-infra-decision]] for how to bring one in later).
- Formal-optimality guarantees for routing/budget algorithms (both use
  documented polynomial-time heuristics, not exact solvers).

## Reading guide

| Doc | Audience | Content |
|---|---|---|
| [01-architecture.md](01-architecture.md) | Engineers | System diagram, request lifecycle, control flow |
| [02-agent-design.md](02-agent-design.md) | Engineers | Agent topology, state schema, handoff protocol |
| [03-llm-infra-decision.md](03-llm-infra-decision.md) | Engineers/Reviewers | LLM/infra choice, comparison matrix, ADR |
| [04-tools-and-integrations.md](04-tools-and-integrations.md) | Engineers | Per-tool spec: real vs. mock, swap-in path |
| [05-data-rag-pipeline.md](05-data-rag-pipeline.md) | Engineers | Ingestion, chunking, vector store |
| [06-api-reference.md](06-api-reference.md) | Integrators | HTTP endpoints |
| [07-security-and-secrets.md](07-security-and-secrets.md) | Everyone | Secret handling, a real incident and its fix |
| [08-evaluation-methodology.md](08-evaluation-methodology.md) | Engineers/Researchers | How to measure this system in-repo |
| [research/RESEARCH-DIRECTION.md](research/RESEARCH-DIRECTION.md) | Researchers | Problem framing, contribution, open questions |
| [research/RELATED-WORK.md](research/RELATED-WORK.md) | Researchers | Literature pointers to verify and extend |
| [research/EVALUATION-PROTOCOL.md](research/EVALUATION-PROTOCOL.md) | Researchers | Formal experimental design |
