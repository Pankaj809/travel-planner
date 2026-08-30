def aggregate_budget(
    flights: list[dict],
    hotels: list[dict],
    travelers: int = 1,
    budget_total: float | None = None,
    currency: str = "USD",
) -> dict:
    """Deterministic budget rollup + constraint check.

    Picks the cheapest flight and cheapest hotel from the offers already
    gathered by the flight/hotel agents (a greedy approximation of the
    underlying 0/1-knapsack-style selection problem - see
    docs/08-evaluation-methodology.md for the formal framing and why a
    greedy heuristic is an acceptable approximation at this scale).
    """
    cheapest_flight = min(flights, key=lambda f: f["total_price"], default=None)
    cheapest_hotel = min(hotels, key=lambda h: h["total_price"], default=None)

    flight_cost = cheapest_flight["total_price"] if cheapest_flight else 0.0
    hotel_cost = cheapest_hotel["total_price"] if cheapest_hotel else 0.0
    misc_estimate = round(50 * travelers, 2)  # meals/local transport rule-of-thumb
    total_cost = round(flight_cost + hotel_cost + misc_estimate, 2)

    summary = {
        "currency": currency,
        "breakdown": {
            "flights": flight_cost,
            "hotels": hotel_cost,
            "misc_estimate": misc_estimate,
        },
        "cheapest_flight": cheapest_flight,
        "cheapest_hotel": cheapest_hotel,
        "total_cost": total_cost,
        "budget_total": budget_total,
    }

    if budget_total is not None:
        summary["over_budget"] = total_cost > budget_total
        summary["remaining"] = round(budget_total - total_cost, 2)
    else:
        summary["over_budget"] = None
        summary["remaining"] = None

    return summary
