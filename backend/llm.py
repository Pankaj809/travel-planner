from langchain_openai import ChatOpenAI

import config


def get_llm(role: str = "worker", temperature: float = 0) -> ChatOpenAI:
    """Model factory shared by every agent node.

    role="orchestrator" selects the larger model used for routing and
    open-ended synthesis; role="worker" selects the smaller model used for
    narrow, well-specified tasks. Centralizing construction here avoids the
    per-call client duplication in the original single-node graph and gives
    a single place to swap providers (see docs/03-llm-infra-decision.md).
    """
    model_name = config.ORCHESTRATOR_MODEL if role == "orchestrator" else config.WORKER_MODEL
    return ChatOpenAI(
        openai_api_key=config.LLM_API_KEY,
        openai_api_base=config.LLM_BASE_URL,
        model_name=model_name,
        max_tokens=None,
        temperature=temperature,
    )
