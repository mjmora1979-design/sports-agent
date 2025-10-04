from flask import Flask, request, jsonify
import os, datetime, requests
from sports_agent import build_payload
from sportsbook_api import get_events, get_odds

app = Flask(__name__)

# === Root route ===
@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "timestamp": datetime.datetime.utcnow().isoformat()from flask import Flask, request, jsonify
from sports_agent import build_payload
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Sports Agent API is running."

@app.route('/api/events', methods=['GET'])
def get_events_endpoint():
    """
    Endpoint: /api/events?sport=nfl
    """
    sport = request.args.get('sport', 'nfl')
    allow_api = request.args.get('allow_api', 'true').lower() == 'true'
    max_games = int(request.args.get('max_games', 10))

    payload = build_payload(sport=sport, allow_api=allow_api, max_games=max_games)
    return jsonify(payload)

if __name__ == '__main__':
    # Bind to Render’s dynamic port, fallback to 10000 locally
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

    })


# === Check environment variable ===
@app.route("/check-key")
def check_key():
    key = os.getenv("RAPIDAPI_KEY") or os.getenv("SPORTSBOOK_RAPIDAPI_KEY")
    return jsonify({
        "key_present": bool(key),
        "key_length": len(key) if key else 0,
        "host": "sportsbook-api2.p.rapidapi.com"
    })


# === Simple RapidAPI test ===
@app.route("/test-api")
def test_api():
    """Lightweight connectivity test."""
    sport = request.args.get("sport", "nfl")
    url = "https://sportsbook-api2.p.rapidapi.com/v0/events"
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY") or os.getenv("SPORTSBOOK_RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "sportsbook-api2.p.rapidapi.com"
    }
    params = {"sport": sport}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        return jsonify({
            "sport": sport,
            "status": resp.status_code,
            "text": resp.text[:300]  # preview only
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === Multi-path debugger ===
@app.route("/debug-api")
def debug_api():
    """
    Cycle through a few possible base paths and sport keys
    to see which combination works.
    """
    bases = [
        "https://sportsbook-api2.p.rapidapi.com/v0",
        "https://sportsbook-api2.p.rapidapi.com/v1",
        "https://sportsbook-api2.p.rapidapi.com/api/v1"
    ]
    sports = ["nfl", "americanfootball_nfl", "nba", "americanfootball_ncaaf"]

    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY") or os.getenv("SPORTSBOOK_RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "sportsbook-api2.p.rapidapi.com"
    }

    results = []
    for base in bases:
        for sport in sports:
            url = f"{base}/events"
            params = {"sport": sport}
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                data = {"base": base, "sport": sport, "status": resp.status_code}
                try:
                    j = resp.json()
                    data["count"] = len(j.get("events", []))
                except Exception:
                    data["count"] = 0
                results.append(data)
            except Exception as e:
                results.append({"base": base, "sport": sport, "error": str(e)})

    return jsonify({"status": "success", "results": results})


# === Main logic endpoint ===
@app.route("/run", methods=["POST"])
def run_model():
    """
    POST body example:
    {"sport": "nfl", "allow_api": true, "max_games": 5}
    """
    try:
        data = request.get_json(force=True)
        sport = data.get("sport", "nfl")
        allow_api = data.get("allow_api", True)
        max_games = int(data.get("max_games", 10))

        payload = build_payload(sport, allow_api, max_games)
        return jsonify(payload)

    except Exception as e:
        print("[ERROR] /run exception:", e)
        return jsonify({"error": str(e)}), 500


# === Health route ===
@app.route("/ping")
def ping():
    return "pong"


# === Entry point ===
if __name__ == "__main__":
    # Render assigns an ephemeral port at runtime; default to 10000 if not set
    port = int(os.environ.get("PORT", 10000))
    print(f"[INFO] Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)
