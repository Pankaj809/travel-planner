from typing import Literal

from langgraph.types import Command

from logging_config import get_logger
from tools.visa_tools import get_visa_requirement
from tools.weather_tools import get_weather_forecast

logger = get_logger(__name__)


def local_info_node(state) -> Command[Literal["supervisor"]]:
    constraints = state.get("trip_constraints", {})
    destinations = constraints.get("destinations") or []
    nationality = constraints.get("nationality")
    start_date = constraints.get("start_date")
    end_date = constraints.get("end_date")

    if not destinations:
        note = "No destination known yet - cannot look up weather or visa requirements."
        logger.info("[%s] local_info: %s", state.get("thread_id"), note)
        return Command(goto="supervisor", update={"agent_scratchpad": [{"agent": "local_info", "note": note}]})

    results = []
    for destination in destinations:
        entry = {
            "destination": destination,
            "weather": get_weather_forecast(destination, start_date, end_date),
            "visa": (
                get_visa_requirement(nationality, destination)
                if nationality
                else {"known": False, "message": "Traveler nationality not provided yet."}
            ),
        }
        results.append(entry)

    logger.info("[%s] local_info: looked up %d destination(s)", state.get("thread_id"), len(results))

    return Command(
        goto="supervisor",
        update={
            "local_info_results": results,
            "agent_scratchpad": [{"agent": "local_info", "note": f"Looked up {len(results)} destination(s)."}],
        },
    )
