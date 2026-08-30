from langchain_core.messages import HumanMessage

from graph.build_graph import graph
from graph.state import TravelState
from logging_config import get_logger
from memory_store import get_session, update_session

logger = get_logger(__name__)


def stream_graph_updates(user_input: str, client_ip: str) -> str:
    session = get_session(client_ip)
    messages = session.messages + [HumanMessage(content=user_input)]
    logger.info("[%s] turn start | history=%d msgs | known_constraints=%s", client_ip, len(session.messages), session.trip_constraints)

    state = TravelState(
        messages=messages,
        thread_id=client_ip,
        trip_constraints=session.trip_constraints,
        flight_results=[],
        hotel_results=[],
        local_info_results=[],
        knowledge_context="",
        itinerary_draft=None,
        budget_summary=None,
        agent_scratchpad=[],
    )

    result = graph.invoke(state, config={"configurable": {"thread_id": client_ip}})

    reply = result["messages"][-1].content
    update_session(client_ip, messages=result["messages"], trip_constraints=result.get("trip_constraints", {}))

    agents_run = [entry.get("agent") for entry in result.get("agent_scratchpad", [])]
    logger.info("[%s] turn end | agents_visited=%s | reply_len=%d", client_ip, agents_run, len(reply))
    return reply
