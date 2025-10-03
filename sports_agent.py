# -------------------------------
# Odds API (with debug logging)
# -------------------------------
def get_global_odds(allow_api: bool = False, sport_id: str = SPORT_ID):
    files = sorted(glob.glob("catalog_global_nfl_*.json"))
    if files:
        latest = files[-1]
        ts = datetime.strptime(
            latest.replace("catalog_global_nfl_", "").replace(".json", ""),
            "%Y%m%d_%H%M%S"
        )
        age_hours = (datetime.utcnow() - ts).total_seconds() / 3600.0
        if age_hours < 2:
            return json.load(open(latest, "r"))

    if not _is_api_allowed(allow_api):
        raise RuntimeError("API disabled")
    if not API_KEY or API_KEY.startswith("PASTE_"):
        raise RuntimeError("No API key set")

    url = f"{BASE_URL}/{sport_id}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": FEATURED_MARKETS,
        "oddsFormat": "american"
    }

    # 🔎 Debug logging
    print(f"[DEBUG] Requesting global odds")
    print(f"[DEBUG] URL: {url}")
    print(f"[DEBUG] Params: {params}")

    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        print(f"[ERROR] Global odds API failed: {r.status_code} {r.text}")
        raise RuntimeError(f"API error {r.status_code} {r.text}")

    data = r.json()
    out_file = f"catalog_global_nfl_{nowstamp()}.json"
    json.dump(data, open(out_file, "w"), indent=2)
    return data


def get_event_props(event_id: str, allow_api: bool = False, sport_id: str = SPORT_ID):
    if not _is_api_allowed(allow_api):
        return []
    if not API_KEY or API_KEY.startswith("PASTE_"):
        return []

    url = f"{BASE_URL}/{sport_id}/events/{event_id}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": PROP_MARKETS,
        "oddsFormat": "american"
    }

    # 🔎 Debug logging
    print(f"[DEBUG] Requesting props for event {event_id}")
    print(f"[DEBUG] URL: {url}")
    print(f"[DEBUG] Params: {params}")

    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        print(f"[ERROR] Event props API failed: {r.status_code} {r.text}")
        return []

    return r.json()
