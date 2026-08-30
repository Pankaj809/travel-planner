from typing import Literal

from langgraph.types import Command

from logging_config import get_logger
from tools.flight_tools import search_flights

logger = get_logger(__name__)


def flight_node(state) -> Command[Literal["supervisor"]]:
    constraints = state.get("trip_constraints", {})
    origin = constraints.get("origin")
    destinations = constraints.get("destinations") or []
    start_date = constraints.get("start_date")

    if not origin or not destinations or not start_date:
        note = "Missing origin, destination, and/or start date - cannot search flights yet."
        logger.info("[%s] flight: %s", state.get("thread_id"), note)
        return Command(goto="supervisor", update={"agent_scratchpad": [{"agent": "flight", "note": note}]})

    travelers = constraints.get("travelers") or 1
    results = []
    for destination in destinations:
        results.extend(search_flights(origin, destination, start_date, travelers))

    logger.info("[%s] flight: %s->%s x%d found %d offer(s)", state.get("thread_id"), origin, destinations, travelers, len(results))

    return Command(
        goto="supervisor",
        update={
            "flight_results": results,
            "agent_scratchpad": [{"agent": "flight", "note": f"Found {len(results)} flight offer(s)."}],
        },
    )
