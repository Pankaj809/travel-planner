import os

from dotenv import load_dotenv

load_dotenv()

LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_BASE_URL = "https://aizex.top/v1"

# Two model tiers keep cost/latency proportional to task difficulty: the
# orchestrator model handles routing, slot-filling, and creative synthesis
# (itinerary drafting, final response composition); the worker model handles
# narrow, well-specified tasks (RAG answer formatting). See
# docs/03-llm-infra-decision.md for the full comparison and rationale.
EMBEDDING_MODEL = "text-embedding-3-small"
ORCHESTRATOR_MODEL = "gpt-4o"
WORKER_MODEL = "gpt-4o-mini"

CHROMA_DIR_PATH = "./chroma"
CHROMA_COLLECTION_NAME = "chromadb"
