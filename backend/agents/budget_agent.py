from typing import Literal

from langgraph.types import Command

from logging_config import get_logger
from tools.budget_tools import aggregate_budget

logger = get_logger(__name__)


def budget_node(state) -> Command[Literal["supervisor"]]:
    constraints = state.get("trip_constraints", {})

    summary = aggregate_budget(
        flights=state.get("flight_results", []),
        hotels=state.get("hotel_results", []),
        travelers=constraints.get("travelers") or 1,
        budget_total=constraints.get("budget_total"),
        currency=constraints.get("currency") or "USD",
    )
    logger.info("[%s] budget: total=%s over_budget=%s", state.get("thread_id"), summary["total_cost"], summary["over_budget"])

    return Command(
        goto="supervisor",
        update={
            "budget_summary": summary,
            "agent_scratchpad": [{"agent": "budget", "note": "Computed budget summary."}],
        },
    )
