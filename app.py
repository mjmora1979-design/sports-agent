from flask import Flask, request, jsonify
from sports_agent import build_payload
from sportsbook_api import (
    list_competitions,
    get_events_for_competition,
    get_markets
)
import requests
import os
import datetime

app = Flask(__name__)

# ----------------------------
# Basic route
# ----------------------------
@app.route('/')
def home():
    return "🏈 Sports Agent Flask API is running on Render."

# ----------------------------
# Test RapidAPI credentials
# ----------------------------
@app.route('/test-api')
def test_api():
    """
    Simple RapidAPI connectivity test using /v0/competitions.
    """
    url = "https://sportsbook-api2.p.rapidapi.com/v0/competitions"
    headers = {
        "x-rapidapi-key": os.environ.get("RAPIDAPI_KEY", ""),
        "x-rapidapi-host": "sportsbook-api2.p.rapidapi.com"
    }

    resp = requests.get(url, headers=headers)
    return jsonify({
        "status": resp.status_code,
        "length": len(resp.text),
        "sample": resp.text[:500]
    })

# ----------------------------
# Debug across possible endpoints
# ----------------------------
@app.route('/debug-api')
def debug_api():
    """
    Tests multiple possible base URLs and sport keys to detect the correct working route.
    """
    bases = [
        "https://sportsbook-api2.p.rapidapi.com/v0",
        "https://sportsbook-api2.p.rapidapi.com/v1",
        "https://sportsbook-api2.p.rapidapi.com/api/v1"
    ]
    sports = ["nfl", "americanfootball_nfl", "nba", "americanfootball_ncaaf"]
    headers = {
        "x-rapidapi-key": os.environ.get("RAPIDAPI_KEY", ""),
        "x-rapidapi-host": "sportsbook-api2.p.rapidapi.com"
    }

    results = []
    for base in bases:
        for sport in sports:
            url = f"{base}/events/{sport}"
            try:
                resp = requests.get(url, headers=headers)
                results.append({
                    "base": base,
                    "sport": sport,
                    "status": resp.status_code,
                    "count": len(resp.text)
                })
            except Exception as e:
                results.append({
                    "base": base,
                    "sport": sport,
                    "error": str(e)
                })

    return jsonify({"results": results, "status": "success"})

# ----------------------------
# Primary POST endpoint for model pipeline
# ----------------------------
@app.route('/run', methods=['POST'])
def run():
    """
    POST /run
    Example body:
    {
        "sport": "nfl",
        "allow_api": true,
        "max_games": 5
    }
    """
    data = request.get_json(force=True)
    sport = data.get("sport", "nfl")
    allow_api = data.get("allow_api", True)
    max_games = data.get("max_games", 5)

    print(f"[INFO] Running payload for sport={sport}, allow_api={allow_api}, max_games={max_games}")
    payload = build_payload(sport=sport, allow_api=allow_api, max_games=max_games)
    return jsonify(payload)

# ----------------------------
# Health check for debugging
# ----------------------------
@app.route('/health')
def health_check():
    now = datetime.datetime.utcnow().isoformat()
    return jsonify({"status": "healthy", "timestamp": now})

# ----------------------------
# Run Flask app
# ----------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
