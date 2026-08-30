from datetime import date

from tools.flight_tools import seed_for

HOTEL_NAMES = ["Grand Central Hotel", "Harbor View Inn", "The Metropolitan", "Sunrise Suites", "Old Town Boutique Hotel"]


def _nights(check_in: str, check_out: str) -> int:
    d1 = date.fromisoformat(check_in)
    d2 = date.fromisoformat(check_out)
    return max((d2 - d1).days, 1)


def search_hotels(destination: str, check_in: str, check_out: str, budget_per_night: float | None = None) -> list[dict]:
    """MOCK PROVIDER: deterministic synthetic hotel offers, seeded by
    (destination, check_in, check_out). See tools/flight_tools.py for the
    rationale (reproducibility, swap-in real API later).
    """
    rng = seed_for(destination, check_in, check_out)
    nights = _nights(check_in, check_out)
    offers = []
    for name in rng.sample(HOTEL_NAMES, k=3):
        star_rating = rng.choice([3, 4, 4, 5])
        price_per_night = rng.randint(60, 60 + star_rating * 70)
        offers.append({
            "name": name,
            "destination": destination,
            "star_rating": star_rating,
            "price_per_night": price_per_night,
            "nights": nights,
            "total_price": round(price_per_night * nights, 2),
            "currency": "USD",
        })
    offers.sort(key=lambda o: o["total_price"])
    if budget_per_night:
        within_budget = [o for o in offers if o["price_per_night"] <= budget_per_night]
        offers = within_budget or offers
    return offers
