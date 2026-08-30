from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from llm import get_llm
from logging_config import get_logger
from prompt import PROMPTS

logger = get_logger(__name__)


def responder_node(state):
    logger.info("[%s] responder: composing final answer", state.get("thread_id"))
    llm = get_llm("orchestrator")

    prompt = ChatPromptTemplate.from_messages([
        ("system", PROMPTS["responder_prompt"]),
        ("system", "{context}"),
        MessagesPlaceholder(variable_name="messages"),
    ])

    context = (
        f"Trip constraints: {state.get('trip_constraints', {})}\n"
        f"Knowledge base context: {state.get('knowledge_context') or 'n/a'}\n"
        f"Flight options: {state.get('flight_results') or 'n/a'}\n"
        f"Hotel options: {state.get('hotel_results') or 'n/a'}\n"
        f"Local info (weather/visa): {state.get('local_info_results') or 'n/a'}\n"
        f"Draft itinerary: {state.get('itinerary_draft') or 'n/a'}\n"
        f"Budget summary: {state.get('budget_summary') or 'n/a'}\n"
    )

    response = (prompt | llm).invoke({"context": context, "messages": state["messages"]})

    return {"messages": [response]}
