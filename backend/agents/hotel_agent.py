from typing import Literal

from langgraph.types import Command

from logging_config import get_logger
from tools.hotel_tools import search_hotels

logger = get_logger(__name__)


def hotel_node(state) -> Command[Literal["supervisor"]]:
    constraints = state.get("trip_constraints", {})
    destinations = constraints.get("destinations") or []
    start_date = constraints.get("start_date")
    end_date = constraints.get("end_date")

    if not destinations or not start_date or not end_date:
        note = "Missing destination and/or check-in/check-out dates - cannot search hotels yet."
        logger.info("[%s] hotel: %s", state.get("thread_id"), note)
        return Command(goto="supervisor", update={"agent_scratchpad": [{"agent": "hotel", "note": note}]})

    results = []
    for destination in destinations:
        results.extend(search_hotels(destination, start_date, end_date, budget_per_night=None))

    logger.info("[%s] hotel: %s found %d offer(s)", state.get("thread_id"), destinations, len(results))

    return Command(
        goto="supervisor",
        update={
            "hotel_results": results,
            "agent_scratchpad": [{"agent": "hotel", "note": f"Found {len(results)} hotel offer(s)."}],
        },
    )
