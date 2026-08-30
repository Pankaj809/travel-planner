from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command

from llm import get_llm
from logging_config import get_logger
from prompt import PROMPTS
from tools.routing_tools import order_multi_city_route

logger = get_logger(__name__)


def itinerary_node(state) -> Command[Literal["supervisor"]]:
    constraints = state.get("trip_constraints", {})
    origin = constraints.get("origin")
    destinations = constraints.get("destinations") or []

    routing_note = "n/a (single destination or origin unknown)"
    if origin and len(destinations) > 1:
        route = order_multi_city_route(origin, destinations)
        routing_note = f"Suggested visiting order (nearest-neighbor, ~{route['total_km']} km total): {route['ordered']}"
        if route["unresolved"]:
            routing_note += f" (could not geocode: {route['unresolved']})"

    payload = (
        f"Trip constraints: {constraints}\n"
        f"Multi-city routing: {routing_note}\n"
        f"Flight options: {state.get('flight_results') or 'none gathered'}\n"
        f"Hotel options: {state.get('hotel_results') or 'none gathered'}\n"
        f"Local info (weather/visa): {state.get('local_info_results') or 'none gathered'}\n"
    )

    llm = get_llm("orchestrator")
    prompt = ChatPromptTemplate.from_messages([
        ("system", PROMPTS["itinerary_prompt"]),
        ("human", "{payload}"),
    ])
    response = (prompt | llm).invoke({"payload": payload})
    logger.info("[%s] itinerary: drafted (%d chars)", state.get("thread_id"), len(response.content))

    return Command(
        goto="supervisor",
        update={
            "itinerary_draft": response.content,
            "agent_scratchpad": [{"agent": "itinerary", "note": "Drafted itinerary."}],
        },
    )
