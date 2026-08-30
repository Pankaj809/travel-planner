from dataclasses import dataclass, field

from langchain_core.messages import BaseMessage

from logging_config import get_logger

logger = get_logger(__name__)

# Bounds per-session history so long-running conversations don't grow the
# prompt (and therefore cost/latency) unboundedly.
MAX_HISTORY_MESSAGES = 20


@dataclass
class SessionMemory:
    messages: list[BaseMessage] = field(default_factory=list)
    trip_constraints: dict = field(default_factory=dict)


_STORE: dict[str, SessionMemory] = {}


def get_session(session_id: str) -> SessionMemory:
    is_new = session_id not in _STORE
    session = _STORE.setdefault(session_id, SessionMemory())
    if is_new:
        logger.info("New session created: %s", session_id)
    return session


def update_session(session_id: str, messages: list[BaseMessage], trip_constraints: dict) -> None:
    session = _STORE[session_id]
    session.messages = messages[-MAX_HISTORY_MESSAGES:]
    session.trip_constraints = trip_constraints
    logger.debug("[%s] session updated | constraints=%s", session_id, trip_constraints)
