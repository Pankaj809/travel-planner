import math

from tools.weather_tools import geocode_city


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def order_multi_city_route(origin: str, destinations: list[str]) -> dict:
    """Greedy nearest-neighbor ordering of `destinations` starting from `origin`.

    This is a polynomial-time (O(n^2)) approximation of the NP-hard
    Traveling Salesman Problem, not an optimal solution. It is deliberately
    simple: leisure itineraries rarely involve more than a handful of
    cities, where nearest-neighbor is within a small constant factor of
    optimal and avoids pulling in a solver dependency (e.g. OR-Tools) for a
    small n. See docs/08-evaluation-methodology.md for the discussion of
    where an exact/ILP solver would be worth the added complexity.
    """
    places = [origin] + destinations
    points: dict[str, tuple[float, float]] = {}
    for place in places:
        geo = geocode_city(place)
        if geo:
            points[place] = (geo["latitude"], geo["longitude"])

    remaining = [d for d in destinations if d in points]
    unresolved = [d for d in destinations if d not in points]

    if origin not in points or not remaining:
        return {"ordered": destinations, "unresolved": unresolved, "total_km": None}

    route: list[str] = []
    current = origin
    total_km = 0.0
    while remaining:
        nearest = min(remaining, key=lambda d: _haversine_km(*points[current], *points[d]))
        total_km += _haversine_km(*points[current], *points[nearest])
        route.append(nearest)
        current = nearest
        remaining.remove(nearest)

    return {"ordered": route, "unresolved": unresolved, "total_km": round(total_km, 1)}
