from langgraph.graph import END, START, StateGraph

from agents.budget_agent import budget_node
from agents.flight_agent import flight_node
from agents.hotel_agent import hotel_node
from agents.itinerary_agent import itinerary_node
from agents.local_info_agent import local_info_node
from agents.rag_agent import rag_node
from agents.responder import responder_node
from agents.supervisor import supervisor_node
from graph.state import TravelState


def build_graph():
    builder = StateGraph(TravelState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("rag", rag_node)
    builder.add_node("flight", flight_node)
    builder.add_node("hotel", hotel_node)
    builder.add_node("local_info", local_info_node)
    builder.add_node("itinerary", itinerary_node)
    builder.add_node("budget", budget_node)
    builder.add_node("responder", responder_node)

    builder.add_edge(START, "supervisor")
    builder.add_edge("responder", END)
    # Every other transition (supervisor -> specialist, specialist ->
    # supervisor) is dynamic: each node returns a Command(goto=...) rather
    # than being wired with add_conditional_edges. See
    # docs/02-agent-design.md for why this Command-based handoff pattern was
    # chosen over static conditional routing.

    return builder.compile()


graph = build_graph()
