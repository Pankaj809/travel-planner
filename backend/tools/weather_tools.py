from datetime import date, timedelta

import requests

from logging_config import get_logger

logger = get_logger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_S = 10

# Open-Meteo's free forecast endpoint only covers this many days ahead of
# today. Leisure trips are frequently booked further out than that, so we
# surface the limitation explicitly instead of silently returning a forecast
# for the wrong dates.
FORECAST_HORIZON_DAYS = 16


def geocode_city(city: str) -> dict | None:
    """Returns None (rather than raising) on any network/parsing failure so
    callers can treat "API unreachable" the same as "location not found" -
    both mean the caller should degrade gracefully instead of crashing the
    graph node that invoked it."""
    try:
        resp = requests.get(GEOCODE_URL, params={"name": city, "count": 1, "language": "en"}, timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        results = resp.json().get("results")
        return results[0] if results else None
    except requests.RequestException as exc:
        logger.warning("Geocoding failed for %r: %s", city, exc)
        return None


def get_weather_forecast(city: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    """Real, free (no API key) weather lookup via Open-Meteo.

    Returns a daily forecast for `city`. If `start_date` falls beyond the
    provider's forecast horizon, returns a near-term forecast instead and
    flags `forecast_horizon_exceeded` so callers/LLMs don't present it as if
    it covered the actual travel dates.
    """
    location = geocode_city(city)
    if location is None:
        logger.info("No weather data for %r (geocoding failed or unknown location)", city)
        return {"city": city, "error": "Location not found"}

    horizon_exceeded = False
    if start_date:
        try:
            requested = date.fromisoformat(start_date)
            if requested > date.today() + timedelta(days=FORECAST_HORIZON_DAYS):
                horizon_exceeded = True
        except ValueError:
            pass

    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
        "timezone": "auto",
    }
    if start_date and not horizon_exceeded:
        params["start_date"] = start_date
        params["end_date"] = end_date or start_date

    try:
        resp = requests.get(FORECAST_URL, params=params, timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        daily = resp.json().get("daily", {})
    except requests.RequestException as exc:
        logger.warning("Forecast request failed for %r: %s", city, exc)
        return {"city": location.get("name", city), "country": location.get("country"), "error": "Forecast provider unreachable"}

    days = []
    for i, day in enumerate(daily.get("time", [])):
        days.append({
            "date": day,
            "temp_max_c": daily["temperature_2m_max"][i],
            "temp_min_c": daily["temperature_2m_min"][i],
            "precipitation_probability_pct": daily["precipitation_probability_max"][i],
            "weathercode": daily["weathercode"][i],
        })

    return {
        "city": location.get("name", city),
        "country": location.get("country"),
        "forecast_horizon_exceeded": horizon_exceeded,
        "days": days,
    }
