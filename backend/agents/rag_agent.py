from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command

from llm import get_llm
from logging_config import get_logger
from prompt import PROMPTS
from retrieval_db import get_db

logger = get_logger(__name__)


def rag_node(state) -> Command[Literal["supervisor"]]:
    query = state["messages"][-1].content
    logger.info("[%s] rag: querying knowledge base", state.get("thread_id"))
    context_text = get_db(query)

    llm = get_llm("worker")
    prompt = ChatPromptTemplate.from_template(PROMPTS["customer_questions"])
    response = (prompt | llm).invoke({"knowledge_base": context_text, "question": query})

    return Command(
        goto="supervisor",
        update={
            "knowledge_context": response.content,
            "agent_scratchpad": [{"agent": "rag", "note": "Retrieved product/policy knowledge."}],
        },
    )
