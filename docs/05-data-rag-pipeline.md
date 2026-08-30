# Data and RAG Pipeline

This pipeline is unchanged in structure from the pre-refactor
implementation; only hardcoded config values were centralized into
`backend/config.py`.

## Ingestion (`backend/seed_db.py`)

1. Walks `backend/data/` (gitignored — populate locally, see
   `ICS_配置文档.md`), loading `.json` via `JSONLoader` and `.pdf` via
   `PyPDFLoader` (page-mode, `\n\x0c` page delimiter).
2. Splits documents with `RecursiveCharacterTextSplitter`
   (`chunk_size=1000`, `chunk_overlap=200`).
3. Embeds each 64-document batch with `text-embedding-3-small` (via the configured `LLM_BASE_URL` provider)
   and writes to a local Chroma collection (`config.CHROMA_COLLECTION_NAME`,
   persisted at `config.CHROMA_DIR_PATH`), clearing any prior store first.

Run with `python seed_db.py` from `backend/` after populating `data/`
and setting `LLM_API_KEY` (see `.env.example`).

## Retrieval (`backend/retrieval_db.py`)

`get_db(query)` runs `similarity_search_with_score(query, k=25)` against
the same Chroma collection and embedding model, filters on
`RELEVANCE_THRESHOLD = 0.5`, and returns the concatenated page contents as
one context string. It returns `0` (falsy) rather than an empty string
when nothing sufficiently relevant is found — callers should treat both
as "no context," but note the type is `int | str`, a pre-existing quirk
carried over rather than changed in this pass to keep the ingestion/
retrieval refactor scoped to config centralization.

## Consumer: the `rag` agent

`backend/agents/rag_agent.py` calls `get_db(query)`, then asks the
**worker**-tier LLM (see
[03-llm-infra-decision.md](03-llm-infra-decision.md)) to answer strictly
from that context (`PROMPTS["customer_questions"]`), writing the result
into `TravelState.knowledge_context` for the `responder` to incorporate.
This is the direct continuation of the original single-node bot's core
function, now one specialist among several rather than the only
capability.

## Known limitations (carried over, not introduced by this refactor)

- No re-ranking step after the top-25 similarity search.
- `RELEVANCE_THRESHOLD` is a single global cutoff, not tuned per document
  type.
- Ingestion always wipes and rebuilds the whole collection — no
  incremental/delta indexing.

These are reasonable candidates for follow-up work but are out of scope
for the multi-agent travel-planning extension.
