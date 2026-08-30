import hashlib
import random

AIRLINES = ["AeroLink", "SkyBridge", "TransGlobal", "Meridian Air", "NorthWind Airways"]


def seed_for(*parts: str) -> random.Random:
    key = "|".join(parts)
    seed = int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2 ** 32)
    return random.Random(seed)


def search_flights(origin: str, destination: str, date: str, travelers: int = 1) -> list[dict]:
    """MOCK PROVIDER: deterministic synthetic flight offers, seeded by
    (origin, destination, date) so results are reproducible across runs -
    important for evaluation/regression testing (docs/08-evaluation-methodology.md).

    Swap this module's implementation with a real GDS/API client (e.g.
    Amadeus Flight Offers Search) without changing any agent code, since
    callers only depend on this function's signature and return shape.
    """
    rng = seed_for(origin, destination, date)
    offers = []
    for airline in rng.sample(AIRLINES, k=3):
        stops = rng.choice([0, 0, 1])
        base_price = rng.randint(120, 900)
        price_per_traveler = round(base_price + stops * rng.randint(-40, 20), 2)
        offers.append({
            "airline": airline,
            "origin": origin,
            "destination": destination,
            "date": date,
            "stops": stops,
            "duration_minutes": rng.randint(90, 780),
            "price_per_traveler": price_per_traveler,
            "total_price": round(price_per_traveler * travelers, 2),
            "currency": "USD",
        })
    offers.sort(key=lambda o: o["total_price"])
    return offers
