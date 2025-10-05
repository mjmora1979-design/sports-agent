import datetime
from typing import Any, Dict, List, Optional

from sportsbook_api import (
    find_competition_key_for_sport,
    fetch_events_with_markets_and_outcomes,
    list_advantages,
)


def build_payload(
    sport: str,
    allow_api: bool = True,
    max_games: int = 5,
    outcome_mode: str = "last",               # "last" or "closing"
    allowed_market_types: Optional[List[str]] = None,  # e.g. ["MONEYLINE","POINT_SPREAD","POINT_TOTAL"]
    include_advantages: bool = True,
) -> Dict[str, Any]:
    """
    Orchestrates a single snapshot payload:
      - competition key (by sport)
      - events + markets + outcomes
      - optional advantages
    """
    payload: Dict[str, Any] = {
        "sport": sport,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": "ok",
        "events_bundle": {},
        "advantages": None,
        "notes": {
            "outcome_mode": outcome_mode,
            "allowed_market_types": allowed_market_types or ["ALL"],
        }
    }

    if not allow_api:
        payload["status"] = "disabled"
        return payload

    comp_key = find_competition_key_for_sport(sport)
    if not comp_key:
        payload["status"] = "no_competition_for_sport"
        return payload

    bundle = fetch_events_with_markets_and_outcomes(
        competition_key=comp_key,
        max_events=max_games,
        outcome_mode=outcome_mode,
        allowed_market_types=allowed_market_types
    )
    payload["events_bundle"] = bundle

    if include_advantages:
        payload["advantages"] = list_advantages(type_str="ARBITRAGE")

    return payload
