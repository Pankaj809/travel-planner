import json
import os

_DATA_PATH = os.path.join(os.path.dirname(__file__), "visa_data.json")
with open(_DATA_PATH, "r", encoding="utf-8") as f:
    _VISA_TABLE = {(row["nationality"], row["destination"]): row for row in json.load(f)}


def get_visa_requirement(nationality: str, destination: str) -> dict:
    """Static-dataset visa lookup, keyed by ISO country codes.

    This is illustrative seed data (~a dozen common corridors), NOT a
    substitute for an authoritative source, and is explicitly labeled as
    such in the returned payload. Swap in a real provider (e.g. Sherpa,
    VisaHQ, Timatic) behind this same function signature - see
    docs/04-tools-and-integrations.md.
    """
    row = _VISA_TABLE.get((nationality.upper(), destination.upper()))
    if row is None:
        return {
            "known": False,
            "message": (
                f"No offline data for {nationality} travelers to {destination}. "
                "Consult the destination's official immigration authority or embassy."
            ),
        }
    return {"known": True, "source": "static-seed-dataset", **row}
