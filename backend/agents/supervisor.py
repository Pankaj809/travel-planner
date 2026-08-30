from typing import Literal, Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.types import Command
from pydantic import BaseModel, Field

from llm import get_llm
from logging_config import get_logger
from prompt import PROMPTS

logger = get_logger(__name__)

NEXT_OPTIONS = Literal["rag", "flight", "hotel", "local_info", "itinerary", "budget", "responder"]

# Guards against an unbounded supervisor <-> specialist loop (e.g. the
# router repeatedly re-selecting an agent that can't make progress).
MAX_HOPS_PER_TURN = 6


class TripConstraintsUpdate(BaseModel):
    origin: Optional[str] = None
    destinations: Optional[list[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget_total: Optional[float] = None
    currency: Optional[str] = None
    travelers: Optional[int] = None
    nationality: Optional[str] = None


class RouteDecision(BaseModel):
    next: NEXT_OPTIONS = Field(
        description="Which specialist agent should act next, or 'responder' if enough "
        "information has been gathered (or no more can be gathered) to answer the user."
    )
    reasoning: str = Field(
        description="One sentence explanation, for the audit/evaluation log only - never shown to the user."
    )
    constraints_update: TripConstraintsUpdate = Field(
        default_factory=TripConstraintsUpdate,
        description="Any trip details newly mentioned or corrected in the latest user turn. "
        "Leave fields unset if unmentioned.",
    )


def supervisor_node(state) -> Command[NEXT_OPTIONS]:
    llm = get_llm("orchestrator").with_structured_output(RouteDecision)

    prompt = ChatPromptTemplate.from_messages([
        ("system", PROMPTS["supervisor_prompt"]),
        ("system", "{context}"),
        MessagesPlaceholder(variable_name="messages"),
    ])

    scratchpad = state.get("agent_scratchpad", [])
    visited = [entry["agent"] for entry in scratchpad]
    context = (
        f"Known trip constraints so far: {state.get('trip_constraints', {})}\n"
        f"Specialists already consulted this turn (in order): {visited or 'none'}\n"
        f"Collected so far: flights={bool(state.get('flight_results'))}, "
        f"hotels={bool(state.get('hotel_results'))}, "
        f"local_info={bool(state.get('local_info_results'))}, "
        f"itinerary={bool(state.get('itinerary_draft'))}, "
        f"budget={bool(state.get('budget_summary'))}, "
        f"knowledge_context={bool(state.get('knowledge_context'))}"
    )

    decision: RouteDecision = (prompt | llm).invoke({
        "context": context,
        "messages": state["messages"],
    })

    hop_capped = len(scratchpad) >= MAX_HOPS_PER_TURN
    goto = "responder" if hop_capped else decision.next
    if hop_capped:
        logger.warning("[%s] hop budget exhausted (%d) - forcing responder", state.get("thread_id"), len(scratchpad))

    updated_constraints = dict(state.get("trip_constraints", {}))
    updated_constraints.update(decision.constraints_update.model_dump(exclude_none=True))

    logger.info("[%s] routing -> %s | reasoning=%s", state.get("thread_id"), goto, decision.reasoning)

    return Command(
        goto=goto,
        update={
            "trip_constraints": updated_constraints,
            "agent_scratchpad": [{"agent": "supervisor", "decision": decision.next, "reasoning": decision.reasoning}],
        },
    )
