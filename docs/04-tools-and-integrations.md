# Tools and Integrations

Per the scoping decision for this iteration (mock/stub data sources with
clean swap-in interfaces — no external booking credentials configured),
tools fall into two categories. Every tool is a plain Python function with
a stable signature; agents depend only on that signature, never on how
the function is implemented, so any entry in the "mock" column below can
be replaced independently.

| Tool | File | Status | Notes |
|---|---|---|---|
| Weather | `tools/weather_tools.py` | **Real** (Open-Meteo, no API key) | Forecast + geocoding, both free public APIs |
| Multi-city routing | `tools/routing_tools.py` | **Real** (Open-Meteo geocoding + haversine) | Nearest-neighbor heuristic, not an exact TSP solver |
| Visa requirements | `tools/visa_tools.py` | **Static seed dataset** | ~14 nationality/destination pairs; explicitly labeled illustrative |
| Flights | `tools/flight_tools.py` | **Deterministic mock** | Seeded by `(origin, destination, date)` for reproducibility |
| Hotels | `tools/hotel_tools.py` | **Deterministic mock** | Seeded by `(destination, check_in, check_out)` |
| Budget aggregation | `tools/budget_tools.py` | **Real** (pure computation) | No external dependency by nature |
| Product/policy knowledge | `retrieval_db.py` (`rag` agent) | **Real** (existing Chroma + text-embedding-3-small) | Unchanged from the pre-refactor RAG pipeline |

## Weather (`get_weather_forecast`)

Wraps Open-Meteo's free geocoding + forecast APIs — no key required, so it
runs out of the box. Its forecast horizon is provider-limited (~16 days
ahead); if the requested `start_date` exceeds that, the function returns
a near-term forecast anyway but sets `forecast_horizon_exceeded: True` so
callers (and the LLM composing the final answer) don't present it as if
it covered the actual travel dates. This is a deliberate
uncertainty-communication design point, not an oversight — see
[research/RESEARCH-DIRECTION.md](research/RESEARCH-DIRECTION.md) on
grounding.

## Multi-city routing (`order_multi_city_route`)

Geocodes `origin` and each destination (same free API as weather), then
runs greedy nearest-neighbor over great-circle (haversine) distances to
produce a visiting order and total distance. This is a polynomial-time
approximation of the NP-hard Traveling Salesman Problem — acceptable at
the scale of a leisure itinerary (a handful of cities) but not
optimality-guaranteed; a real deployment with routinely large multi-city
trips would want an exact/ILP solver (e.g. OR-Tools) instead — see
[08-evaluation-methodology.md](08-evaluation-methodology.md).

## Visa requirements (`get_visa_requirement`)

Looks up `(nationality, destination)` in a small static JSON table
(`tools/visa_data.json`, ~14 entries covering common corridors). Any
unlisted pair returns `{"known": False, "message": "..."}` rather than
guessing — visa rules change and are jurisdiction-specific, so silent
fabrication here is a real correctness/safety risk, not just a data-
completeness gap. Swap-in path for a real provider (e.g. Sherpa, VisaHQ,
IATA Timatic) is to reimplement this function's body only; the
`(nationality, destination) -> dict` contract is unchanged.

## Flights / Hotels (mock providers)

Both use a SHA-256-seeded `random.Random` keyed by the query parameters,
so the same query always returns the same synthetic offers — this
determinism is intentional: it lets evaluation runs be repeatable (see
[research/EVALUATION-PROTOCOL.md](research/EVALUATION-PROTOCOL.md))
without depending on a live market. Each offer's shape (`airline`,
`price_per_traveler`, `total_price`, `stops`, `duration_minutes` for
flights; `name`, `star_rating`, `price_per_night`, `total_price` for
hotels) loosely mirrors what a real provider like Amadeus Self-Service
API returns, so swapping the mock for a real client is a same-file
replacement, not an agent-level change.

**To integrate a real flight/hotel provider:** replace the body of
`search_flights`/`search_hotels` with an HTTP client call, keep the
return shape (or update the two callers in
`agents/flight_agent.py`/`agents/hotel_agent.py` alongside it), and add
the provider's credentials to `.env`/`config.py` following the pattern
already used for `LLM_API_KEY`.

## Budget aggregation (`aggregate_budget`)

Pure computation, no external dependency: picks the cheapest gathered
flight and hotel offer, adds a flat per-traveler miscellaneous estimate,
and compares the total against `budget_total` if the user supplied one.
This is a greedy approximation of the underlying combinatorial selection
problem (choosing among multiple flight/hotel offers under a budget
constraint is a 0/1-knapsack-shaped problem) — see
[08-evaluation-methodology.md](08-evaluation-methodology.md) for the
formal framing and where an exact solver would matter (larger offer
sets, multiple constraints traded off simultaneously).
