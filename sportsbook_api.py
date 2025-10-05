import os
import time
import traceback
from typing import Any, Dict, List, Optional

import requests

# ---- RapidAPI config (env-driven) ----
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

# Known base variants used by the API docs/playground
BASE_URLS = [
    "https://sportsbook-api2.p.rapidapi.com/v0",
    "https://sportsbook-api2.p.rapidapi.com/v1",
    "https://sportsbook-api2.p.rapidapi.com/api/v1",
]

DEFAULT_TIMEOUT = float(os.getenv("RAPIDAPI_TIMEOUT_SEC", "20"))
RATE_SLEEP = float(os.getenv("RAPIDAPI_SLEEP_SEC", "0.15"))  # tiny pause to avoid 429s


def _headers() -> Dict[str, str]:
    return {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
    }


def _get_with_fallback(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Try each known base prefix with `path`. Return first 200 JSON response.
    Logs non-200s and exceptions for visibility.
    """
    for base in BASE_URLS:
        url = f"{base}{path}"
        try:
            resp = requests.get(url, headers=_headers(), params=params or {}, timeout=DEFAULT_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            print(f"[WARN] {url} -> {resp.status_code}")
        except Exception:
            print(f"[ERROR] {url}\n{traceback.format_exc()}")
        time.sleep(RATE_SLEEP)
    return None


# ---------------- Core GETs ----------------

def list_competitions() -> Optional[Dict[str, Any]]:
    """GET /competitions"""
    return _get_with_fallback("/competitions")


def list_competition_events(competition_key: str, event_type: str = "MATCH") -> Optional[Dict[str, Any]]:
    """GET /competitions/{competitionKey}/events?eventType=MATCH"""
    return _get_with_fallback(f"/competitions/{competition_key}/events", params={"eventType": event_type})


def get_event(event_key: str) -> Optional[Dict[str, Any]]:
    """GET /events/{eventKey}"""
    return _get_with_fallback(f"/events/{event_key}")


def list_event_markets(event_key: str) -> Optional[Dict[str, Any]]:
    """GET /events/{eventKey}/markets"""
    return _get_with_fallback(f"/events/{event_key}/markets")


def get_market(market_key: str) -> Optional[Dict[str, Any]]:
    """GET /markets/{marketKey} (meta for a market)"""
    return _get_with_fallback(f"/markets/{market_key}")


def list_market_outcomes_last(market_key: str) -> Optional[Dict[str, Any]]:
    """GET /markets/{marketKey}/outcomes/last (latest quotes)"""
    return _get_with_fallback(f"/markets/{market_key}/outcomes/last")


def list_market_outcomes_closing(market_key: str) -> Optional[Dict[str, Any]]:
    """GET /markets/{marketKey}/outcomes/closing (closing line)"""
    return _get_with_fallback(f"/markets/{market_key}/outcomes/closing")


def list_participant_events(participant_key: str, event_type: str = "MATCH") -> Optional[Dict[str, Any]]:
    """GET /participants/{participantKey}/events?eventType=MATCH"""
    return _get_with_fallback(f"/participants/{participant_key}/events", params={"eventType": event_type})


def list_advantages(type_str: str = "ARBITRAGE") -> Optional[Dict[str, Any]]:
    """GET /advantages?type=ARBITRAGE"""
    return _get_with_fallback("/advantages", params={"type": type_str})


# ---------------- Convenience helpers ----------------

def find_competition_key_for_sport(sport: str) -> Optional[str]:
    """
    Map a broad sport like 'nfl' to the competitionKey, if present.
    Fallback to NFL key if nothing obvious is found (keeps the pipeline alive).
    """
    data = list_competitions() or {}
    comps = data.get("competitions", []) if isinstance(data, dict) else []
    sport_l = (sport or "").lower()

    for c in comps:
        name = (c.get("name") or "").lower()
        key = (c.get("competitionKey") or "").lower()
        if sport_l in name or sport_l in key:
            return c.get("competitionKey")

    # safe fallback (2025-26 NFL instance from your successful calls)
    if sport_l in ("nfl", "football", "americanfootball", "american_football"):
        return "Q63E-wddv-ddp4"
    return None


def fetch_events_with_markets_and_outcomes(
    competition_key: str,
    max_events: int = 5,
    outcome_mode: str = "last",
    allowed_market_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    High-level aggregator:
      competition -> events -> markets -> outcomes(last/closing)

    outcome_mode: "last" (default) or "closing"
    allowed_market_types: if provided, filter markets by m["type"] (e.g. ["MONEYLINE","POINT_SPREAD","POINT_TOTAL"])
    """
    ev_resp = list_competition_events(competition_key) or {}
    events = ev_resp.get("events", []) if isinstance(ev_resp, dict) else []
    events = events[:max_events]

    result = {"event_count": len(events), "items": []}

    for ev in events:
        ev_key = ev.get("key")
        m_resp = list_event_markets(ev_key) or {}
        markets = m_resp.get("markets", []) if isinstance(m_resp, dict) else []

        if allowed_market_types:
            markets = [m for m in markets if (m.get("type") in allowed_market_types)]

        enriched_markets = []
        for m in markets:
            mk = m.get("key")
            if not mk:
                continue

            if outcome_mode == "closing":
                outcomes = list_market_outcomes_closing(mk)
                fallback = list_market_outcomes_last(mk) if outcomes is None else None
            else:
                outcomes = list_market_outcomes_last(mk)
                fallback = list_market_outcomes_closing(mk) if outcomes is None else None

            enriched_markets.append({
                "marketKey": mk,
                "market": m,
                "outcomes_primary": outcomes,      # last or closing
                "outcomes_fallback": fallback,     # whichever we didn't try first (or None)
            })
            time.sleep(RATE_SLEEP)

        result["items"].append({
            "event": ev,
            "markets": enriched_markets
        })
        time.sleep(RATE_SLEEP)

    return result
