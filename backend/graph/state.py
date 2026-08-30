import operator
from typing import Annotated, Optional

from copilotkit import CopilotKitState
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TravelState(CopilotKitState):
    """Shared state channel for the travel-planning multi-agent graph.

    `trip_constraints` is the running slot-filling result (origin,
    destinations, dates, budget, travelers, nationality) that the supervisor
    extracts/updates from each turn. `agent_scratchpad` accumulates one
    entry per node visited this turn (via the `operator.add` reducer) and is
    the audit trail used for tracing routing decisions - see
    docs/08-evaluation-methodology.md.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str

    trip_constraints: dict

    flight_results: list[dict]
    hotel_results: list[dict]
    local_info_results: list[dict]
    knowledge_context: str
    itinerary_draft: Optional[str]
    budget_summary: Optional[dict]

    agent_scratchpad: Annotated[list[dict], operator.add]
