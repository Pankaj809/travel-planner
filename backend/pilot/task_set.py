"""Scripted conversation set for the RQ2 pilot (tiered vs. uniform model
allocation - see docs/research/EVALUATION-PROTOCOL.md section 2).

Each PilotTask is a fixed, hand-authored multi-turn conversation plus an
`assertions` function that scores the final graph state deterministically.
This is intentionally small (13 conversations) relative to the 30-50/stratum
the full protocol calls for - see docs/research/PILOT-TASK-SET.md for why
that's an acceptable pilot scope and what it does not establish.

`assertions(final_state)` takes a TravelState-shaped dict (the return value
of `graph.invoke`, not `stream_graph_updates`'s reply-string wrapper) and
returns a list of failure-description strings; an empty list means pass.
Checks are structural (fields present/absent, numeric relationships,
agent-visitation sets) rather than string-matching LLM prose, except where a
factual grounding check needs a substring look-up against a known-correct
value from the RAG corpus or the static visa dataset.
"""

from dataclasses import dataclass, field
from typing import Callable

Assertions = Callable[[dict], list[str]]


@dataclass
class PilotTask:
    id: str
    strata: dict
    turns: list
    notes: str
    assertions: Assertions
    thread_id: str = field(default="")

    def __post_init__(self):
        if not self.thread_id:
            self.thread_id = f"pilot-{self.id}"


def _agents_visited(state: dict) -> list:
    return [entry.get("agent") for entry in state.get("agent_scratchpad", [])]


def _last_reply_text(state: dict) -> str:
    messages = state.get("messages", [])
    return messages[-1].content if messages else ""


# ---------------------------------------------------------------------------
# T1 - fully specified, single city, budget comfortable, pure trip-planning
# ---------------------------------------------------------------------------

def _assert_t1(state: dict) -> list:
    fails = []
    c = state.get("trip_constraints", {})
    if not c.get("origin"):
        fails.append("origin not extracted")
    if c.get("destinations") != ["Paris"] and "Paris" not in (c.get("destinations") or []):
        fails.append(f"destinations should include Paris, got {c.get('destinations')}")
    if c.get("start_date") != "2026-09-05":
        fails.append(f"start_date mismatch: {c.get('start_date')}")
    if c.get("budget_total") != 3000:
        fails.append(f"budget_total mismatch: {c.get('budget_total')}")
    if not state.get("flight_results"):
        fails.append("flight_results empty")
    if not state.get("hotel_results"):
        fails.append("hotel_results empty")
    if not state.get("local_info_results"):
        fails.append("local_info_results empty")
    if not state.get("itinerary_draft"):
        fails.append("itinerary_draft missing")
    budget = state.get("budget_summary")
    if not budget:
        fails.append("budget_summary missing")
    elif budget.get("budget_total") != 3000:
        fails.append(f"budget_summary.budget_total mismatch: {budget.get('budget_total') if budget else None}")
    return fails


T1_single_full_comfortable = PilotTask(
    id="T1_single_full_comfortable",
    strata={"slot_completeness": "full", "destination_count": "single", "constraint_tightness": "comfortable", "domain": "trip_planning"},
    turns=[
        "Hi, I'm planning a solo trip from New York to Paris, departing 2026-09-05 and "
        "returning 2026-09-12. I'm a US citizen, my total budget is $3000, and it's just "
        "me traveling. Can you find flights, a hotel, and put together a day-by-day itinerary?"
    ],
    notes="Happy-path baseline: every slot given up front, single destination, budget well "
    "above the mock providers' plausible cheapest total (~$100-1500 range for 1 traveler).",
    assertions=_assert_t1,
)


# ---------------------------------------------------------------------------
# T2 - fully specified, single city, deliberately near-impossible budget
# ---------------------------------------------------------------------------

def _assert_t2(state: dict) -> list:
    fails = []
    budget = state.get("budget_summary")
    if not budget:
        fails.append("budget_summary missing")
        return fails
    if budget.get("over_budget") is not True:
        fails.append(f"expected over_budget=True for a $800 total against 2 travelers, got {budget.get('over_budget')}")
    if budget.get("remaining") is not None and budget["remaining"] >= 0:
        fails.append(f"expected negative remaining, got {budget.get('remaining')}")
    return fails


T2_single_full_overbudget = PilotTask(
    id="T2_single_full_overbudget",
    strata={"slot_completeness": "full", "destination_count": "single", "constraint_tightness": "tight_over", "domain": "trip_planning"},
    turns=[
        "I want to fly from Chicago to Tokyo, 2026-09-10 to 2026-09-17, for 2 travelers. "
        "My total budget is only $800 for everything. I'm a US citizen. Find flights and a "
        "hotel and tell me whether we're within budget."
    ],
    notes="$800 total for 2 travelers is below the mock providers' minimum plausible combined "
    "total (cheapest flight >= $120/traveler, cheapest hotel >= ~$60/night) - a near-certain "
    "over_budget=True case, used to check the budget node doesn't silently clip or mis-flag it.",
    assertions=_assert_t2,
)


# ---------------------------------------------------------------------------
# T3 - fully specified, multi-city (3), comfortable budget, tests routing tool
# ---------------------------------------------------------------------------

def _assert_t3(state: dict) -> list:
    fails = []
    c = state.get("trip_constraints", {})
    dests = c.get("destinations") or []
    if len(dests) < 3:
        fails.append(f"expected 3 destinations extracted, got {dests}")
    itinerary = state.get("itinerary_draft") or ""
    if not itinerary:
        fails.append("itinerary_draft missing")
    elif "km" not in itinerary and "route" not in itinerary.lower() and "order" not in itinerary.lower():
        fails.append("itinerary_draft doesn't appear to reference the computed routing order/distance")
    if not state.get("flight_results"):
        fails.append("flight_results empty")
    if not state.get("hotel_results"):
        fails.append("hotel_results empty")
    return fails


T3_multi_full_comfortable = PilotTask(
    id="T3_multi_full_comfortable",
    strata={"slot_completeness": "full", "destination_count": "multi_3", "constraint_tightness": "comfortable", "domain": "trip_planning"},
    turns=[
        "Plan a 10-day multi-city Europe trip for me: Paris, then Rome, then Barcelona, "
        "flying out of London on 2026-09-08 and back on 2026-09-18. I'm British, 1 traveler, "
        "budget $5000. Include flights, hotels, weather, and a suggested visiting order."
    ],
    notes="Exercises order_multi_city_route (RQ5 in RESEARCH-DIRECTION.md) - itinerary_node "
    "only calls it when origin is known and len(destinations) > 1. Scored on whether the "
    "drafted itinerary text reflects the tool-computed order rather than an LLM-invented one "
    "(exact route match isn't asserted here; RQ5 needs total_km comparison, out of pilot scope).",
    assertions=_assert_t3,
)


# ---------------------------------------------------------------------------
# T4 - under-specified, multi-turn slot-filling, single city
# ---------------------------------------------------------------------------

def _assert_t4_turn1(state: dict) -> list:
    fails = []
    if state.get("flight_results"):
        fails.append("flight_results should be empty before origin/dates are known")
    if state.get("hotel_results"):
        fails.append("hotel_results should be empty before dates are known")
    return fails


def _assert_t4_turn2(state: dict) -> list:
    fails = []
    c = state.get("trip_constraints", {})
    if not c.get("origin"):
        fails.append("origin still missing after turn 2")
    if not c.get("start_date") or not c.get("end_date"):
        fails.append("dates still missing after turn 2")
    if not state.get("flight_results"):
        fails.append("flight_results still empty after all slots filled")
    if not state.get("hotel_results"):
        fails.append("hotel_results still empty after all slots filled")
    return fails


T4_single_slotfill = PilotTask(
    id="T4_single_slotfill",
    strata={"slot_completeness": "under_specified_multiturn", "destination_count": "single", "constraint_tightness": "comfortable", "domain": "trip_planning"},
    turns=[
        "I want to go to Bangkok sometime, can you help?",
        "I'll fly from Singapore, departing 2026-09-08, returning 2026-09-14, just me, "
        "budget around $1500. I'm Indian.",
    ],
    notes="Turn 1 deliberately omits origin/dates - correct behavior is supervisor routing to "
    "responder to ask for the missing slot rather than calling flight/hotel with partial info "
    "(both nodes' own guard clauses should also prevent a call if reached). Turn 2 supplies "
    "everything; per-turn assertions are indexed by turn (see run_pilot.py in the harness).",
    assertions=_assert_t4_turn2,
)
T4_single_slotfill.per_turn_assertions = [_assert_t4_turn1, _assert_t4_turn2]


# ---------------------------------------------------------------------------
# T5 - under-specified, multi-turn, multi-city (3), tight budget
# ---------------------------------------------------------------------------

def _assert_t5(state: dict) -> list:
    fails = []
    c = state.get("trip_constraints", {})
    dests = c.get("destinations") or []
    if len(dests) < 3:
        fails.append(f"expected 3 destinations, got {dests}")
    if c.get("travelers") != 2:
        fails.append(f"expected travelers=2, got {c.get('travelers')}")
    budget = state.get("budget_summary")
    if not budget:
        fails.append("budget_summary missing")
    return fails


T5_multi_slotfill_tight = PilotTask(
    id="T5_multi_slotfill_tight",
    strata={"slot_completeness": "under_specified_multiturn", "destination_count": "multi_3", "constraint_tightness": "tight", "domain": "trip_planning"},
    turns=[
        "My partner and I want to visit a few cities in Southeast Asia.",
        "We'd start in Kuala Lumpur, then Bangkok, then Singapore. Flying from Mumbai, "
        "2026-09-12 to 2026-09-19, 2 travelers, budget $1200 total, we're Indian citizens.",
    ],
    notes="Known scoring caveat: aggregate_budget only ever prices ONE cheapest flight leg and "
    "ONE cheapest hotel stay, not one per destination in a multi-city trip - so its "
    "over_budget verdict systematically understates true multi-city cost. This is a real gap "
    "in tools/budget_tools.py (see docs/08-evaluation-methodology.md's greedy-heuristic note), "
    "not a pilot scoring bug; T5 is scored only on whether budget_summary is produced at all, "
    "not on the correctness of over_budget for this case.",
    assertions=_assert_t5,
)


# ---------------------------------------------------------------------------
# T6 - pure RAG, in-corpus factual question (grounding check, positive case)
# ---------------------------------------------------------------------------

def _assert_t6(state: dict) -> list:
    fails = []
    reply = _last_reply_text(state)
    if "250" not in reply:
        fails.append("reply doesn't mention the MLU370-X8's 250W TDP figure from the manual")
    if "48" not in reply:
        fails.append("reply doesn't mention the MLU370-X8's 48GB memory figure from the manual")
    if state.get("flight_results") or state.get("hotel_results"):
        fails.append("a pure product-spec question should not trigger flight/hotel search")
    return fails


T6_rag_grounded = PilotTask(
    id="T6_rag_grounded",
    strata={"slot_completeness": "n/a", "destination_count": "n/a", "constraint_tightness": "n/a", "domain": "rag_in_corpus"},
    turns=["What are the power consumption (TDP) and memory capacity of the MLU370-X8 accelerator card?"],
    notes="Ground truth from backend/data/pdf (MLU370-X8 manual, section 4.1): TDP 250W, "
    "memory capacity 48GB. Verifies the multi-agent refactor didn't regress the original "
    "single-node RAG chatbot's core capability (docs/05-data-rag-pipeline.md).",
    assertions=_assert_t6,
)


# ---------------------------------------------------------------------------
# T7 - pure RAG, out-of-corpus question (anti-fabrication check, negative case)
# ---------------------------------------------------------------------------

def _assert_t7(state: dict) -> list:
    fails = []
    reply = _last_reply_text(state).lower()
    fabrication_signals = ["$", "usd", "rmb", "cny", "price is", "costs"]
    if any(sig in reply for sig in fabrication_signals):
        fails.append(f"reply appears to fabricate a price figure not present in the manuals: {reply[:200]!r}")
    return fails


T7_rag_ungrounded = PilotTask(
    id="T7_rag_ungrounded",
    strata={"slot_completeness": "n/a", "destination_count": "n/a", "constraint_tightness": "n/a", "domain": "rag_out_of_corpus"},
    turns=["What is the retail price of the MLU370-X8 accelerator card?"],
    notes="The product manuals in backend/data/pdf contain specs, not pricing - get_db should "
    "return 0/no-context (score below RELEVANCE_THRESHOLD or simply no pricing content), and "
    "PROMPTS['role_prompts']/['responder_prompt'] both explicitly forbid fabrication. Checks "
    "the reply doesn't invent a number instead of declining or deferring to a human rep.",
    assertions=_assert_t7,
)


# ---------------------------------------------------------------------------
# T8 - domain mix within one session: RAG question, then trip-planning
# ---------------------------------------------------------------------------

def _assert_t8(state: dict) -> list:
    fails = []
    if not state.get("knowledge_context"):
        fails.append("knowledge_context missing - rag agent doesn't appear to have been consulted for turn 1's question")
    if not state.get("flight_results"):
        fails.append("flight_results missing - trip-planning half of the session didn't complete")
    return fails


T8_domain_mix = PilotTask(
    id="T8_domain_mix",
    strata={"slot_completeness": "full", "destination_count": "single", "constraint_tightness": "comfortable", "domain": "mixed"},
    turns=[
        "Quick question first: how much memory does the MLU370-S4 accelerator card have?",
        "Thanks. Separately - can you find me a flight from Boston to Tokyo on 2026-09-09, "
        "just me, US citizen, no strict budget?",
    ],
    notes="Verifies the supervisor correctly re-routes between rag and flight across turns in "
    "the same session (EVALUATION-PROTOCOL.md's 'domain mix' stratum) rather than getting "
    "stuck on whichever specialist it picked first.",
    assertions=_assert_t8,
)


# ---------------------------------------------------------------------------
# T9 - 5-destination stress test (routing + hop-budget pressure)
# ---------------------------------------------------------------------------

def _assert_t9(state: dict) -> list:
    fails = []
    scratchpad = state.get("agent_scratchpad", [])
    if len(scratchpad) > 6:
        fails.append(f"agent_scratchpad has {len(scratchpad)} entries - MAX_HOPS_PER_TURN=6 should cap this within one turn")
    c = state.get("trip_constraints", {})
    if len(c.get("destinations") or []) < 5:
        fails.append(f"expected 5 destinations extracted, got {c.get('destinations')}")
    return fails


T9_multi_stress_5city = PilotTask(
    id="T9_multi_stress_5city",
    strata={"slot_completeness": "full", "destination_count": "multi_5", "constraint_tightness": "comfortable", "domain": "trip_planning"},
    turns=[
        "I want a whirlwind Southeast Asia trip: Tokyo, then Bangkok, then Singapore, then "
        "Kuala Lumpur, then Bali, flying out of Seoul on 2026-09-06 and back on 2026-09-16. "
        "1 traveler, South Korean citizen, budget $8000. Give me flights, hotels, weather for "
        "each stop, a suggested order, and a full itinerary."
    ],
    notes="Largest destination_count in the pilot set (protocol caps at 2-5 for TSP-heuristic "
    "tractability) and the request most likely to need every specialist in one turn - directly "
    "probes MAX_HOPS_PER_TURN=6 (RQ4) headroom, since a full pass (flight+hotel+local_info+"
    "itinerary+budget) is already 5 hops before the supervisor's own routing entries are added "
    "to the same list.",
    assertions=_assert_t9,
)


# ---------------------------------------------------------------------------
# T10 - visa lookup, natural city-name phrasing (near-certain graceful miss)
# ---------------------------------------------------------------------------

def _assert_t10(state: dict) -> list:
    fails = []
    local_info = state.get("local_info_results") or []
    if not local_info:
        fails.append("local_info_results empty")
        return fails
    visa = local_info[0].get("visa", {})
    reply = _last_reply_text(state).lower()
    if visa.get("known") is True:
        # Not a failure by itself (see notes) - but if it happens, the reply must not
        # contradict the dataset's actual visa_required value.
        return fails
    fabrication_signals = ["you do not need a visa", "no visa is required", "visa-free for sure"]
    if any(sig in reply for sig in fabrication_signals):
        fails.append("reply asserts a confident visa answer despite an unresolved lookup (known=False)")
    return fails


T10_visa_city_phrasing = PilotTask(
    id="T10_visa_city_phrasing",
    strata={"slot_completeness": "full", "destination_count": "single", "constraint_tightness": "comfortable", "domain": "trip_planning"},
    turns=[
        "I'm a US citizen planning to visit Paris, 2026-09-10 to 2026-09-15, 1 traveler. "
        "Do I need a visa? Also find me a flight from Boston and a hotel."
    ],
    notes="tools/visa_tools.py keys its ~14-row static table by ISO country code (e.g. 'FR'), "
    "but local_info_node passes the SAME destination string used for weather geocoding (a "
    "city name like 'Paris') into get_visa_requirement - so a naturally-phrased destination "
    "will almost always miss the table (known=False) even though a US->France row exists. "
    "This is a real coupling defect worth reporting (destinations conflates 'geocodable city' "
    "and 'ISO country code' into one slot), not a pilot artifact - see docs/research/"
    "PILOT-TASK-SET.md. Scored on graceful degradation (no fabricated confident answer), not "
    "on achieving known=True.",
    assertions=_assert_t10,
)


# ---------------------------------------------------------------------------
# T11 - visa lookup, explicit ISO-style phrasing (best-case hit attempt)
# ---------------------------------------------------------------------------

def _assert_t11(state: dict) -> list:
    fails = []
    local_info = state.get("local_info_results") or []
    if not local_info:
        fails.append("local_info_results empty")
    return fails


T11_visa_iso_phrasing = PilotTask(
    id="T11_visa_iso_phrasing",
    strata={"slot_completeness": "full", "destination_count": "single", "constraint_tightness": "comfortable", "domain": "trip_planning"},
    turns=[
        "I'm a US citizen (nationality code US) traveling to CN, mainland China "
        "(destination code CN), 2026-09-10 to 2026-09-20, 1 traveler. What's the visa "
        "requirement? I know US travelers need a Chinese tourist visa (L visa)."
    ],
    notes="Companion to T10: phrases the destination to nudge slot extraction toward the exact "
    "ISO code the static table is keyed on ('CN'), to empirically observe whether known=True "
    "is achievable at all under realistic phrasing, and whether it differs across model "
    "conditions (Condition A/B). Not asserted as must-pass=True since extraction format is "
    "itself an LLM decision - see the T10/T11 pairing note in PILOT-TASK-SET.md.",
    assertions=_assert_t11,
)


# ---------------------------------------------------------------------------
# T12 - weather forecast horizon exceeded
# ---------------------------------------------------------------------------

def _assert_t12(state: dict) -> list:
    fails = []
    local_info = state.get("local_info_results") or []
    if not local_info:
        fails.append("local_info_results empty")
        return fails
    weather = local_info[0].get("weather", {})
    if weather.get("forecast_horizon_exceeded") is not True:
        fails.append(f"expected forecast_horizon_exceeded=True for a start_date ~6 months out, got {weather.get('forecast_horizon_exceeded')}")
    reply = _last_reply_text(state).lower()
    if "exact" in reply and "forecast" in reply and "cannot" not in reply and "can't" not in reply and "not" not in reply:
        fails.append("reply may be presenting the near-term forecast as if it covers the actual travel dates")
    return fails


T12_weather_horizon_exceeded = PilotTask(
    id="T12_weather_horizon_exceeded",
    strata={"slot_completeness": "full", "destination_count": "single", "constraint_tightness": "comfortable", "domain": "trip_planning"},
    turns=[
        "I'm planning a trip to Reykjavik from Boston, 2027-03-15 to 2027-03-22, 1 traveler, "
        "US citizen, budget $4000. What's the weather going to be like, and can you find "
        "flights and a hotel?"
    ],
    notes="start_date is ~6.5 months out, far beyond Open-Meteo's ~16-day forecast horizon "
    "(tools/weather_tools.py FORECAST_HORIZON_DAYS). Checks both the structured flag "
    "(forecast_horizon_exceeded=True) and, as a soft signal, that the composed reply doesn't "
    "present the returned near-term forecast as if it were the actual travel-date forecast - "
    "this is the grounding/uncertainty-communication design point flagged in "
    "docs/04-tools-and-integrations.md.",
    assertions=_assert_t12,
)


# ---------------------------------------------------------------------------
# T13 - mid-conversation contradiction / constraint correction
# ---------------------------------------------------------------------------

def _assert_t13(state: dict) -> list:
    fails = []
    c = state.get("trip_constraints", {})
    dests = c.get("destinations") or []
    if "Rome" not in dests:
        fails.append(f"expected corrected destination 'Rome' in trip_constraints, got {dests}")
    if "Paris" in dests:
        fails.append(f"stale destination 'Paris' was not overwritten after correction, got {dests}")
    if c.get("start_date") != "2026-09-10":
        fails.append(f"expected corrected start_date '2026-09-10', got {c.get('start_date')}")
    return fails


T13_contradiction_correction = PilotTask(
    id="T13_contradiction_correction",
    strata={"slot_completeness": "under_specified_multiturn", "destination_count": "single", "constraint_tightness": "comfortable", "domain": "trip_planning"},
    turns=[
        "I want to fly from Boston to Paris on 2026-09-05, 1 traveler, US citizen, budget $2500.",
        "Actually, change of plans - make that Rome instead of Paris, and push the date to "
        "2026-09-10. Same origin, traveler, and budget.",
    ],
    notes="Tests whether the supervisor's constraints_update correctly overwrites (not merges "
    "alongside) a corrected slot - dict.update() semantics in supervisor_node mean a new "
    "destinations value should fully replace the old one, but this depends on the LLM emitting "
    "a complete replacement list rather than an incremental addition.",
    assertions=_assert_t13,
)


ALL_TASKS = [
    T1_single_full_comfortable,
    T2_single_full_overbudget,
    T3_multi_full_comfortable,
    T4_single_slotfill,
    T5_multi_slotfill_tight,
    T6_rag_grounded,
    T7_rag_ungrounded,
    T8_domain_mix,
    T9_multi_stress_5city,
    T10_visa_city_phrasing,
    T11_visa_iso_phrasing,
    T12_weather_horizon_exceeded,
    T13_contradiction_correction,
]
