from flask import Flask, request, jsonify
from sports_agent import build_payload
import requests, os, datetime

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "service": "sports-agent",
        "endpoints": [
            "/healthz",
            "/test-api",
            "/debug-api",
            "/playground-proxy",
            "/run"
        ]
    })

@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()})

# -------------------------------------------------------------------
# /test-api : quick validation for known NFL endpoints
# -------------------------------------------------------------------
@app.route("/test-api", methods=["GET"])
def test_api():
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return jsonify({"status": "error", "message": "RAPIDAPI_KEY missing"}), 500

    tests = [
        ("v0/events/", {"sport": "americanfootball_nfl"}),
        ("v0/events", {"sport": "americanfootball_nfl"}),
        ("v1/events", {"sport": "americanfootball_nfl"}),
        ("api/v1/events", {"sport": "americanfootball_nfl"})
    ]

    results, working = [], None
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "sportsbook-api2.p.rapidapi.com",
    }

    for path, params in tests:
        url = f"https://sportsbook-api2.p.rapidapi.com/{path}"
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            data = r.json() if r.ok else {}
            count = len(data.get("events", [])) if isinstance(data, dict) else 0
            results.append({
                "url": url,
                "status": r.status_code,
                "count": count,
            })
            if r.ok and count > 0 and not working:
                working = url
        except Exception as e:
            results.append({"url": url, "error": str(e)})

    rec = {"message": "✅ FOUND WORKING ENDPOINT", "url": working} if working else {
        "message": "❌ No working endpoint found"}
    return jsonify({"status": "success", "results": results, "recommendation": rec})

# -------------------------------------------------------------------
# /debug-api : brute-force discovery of working API + sport combos
# -------------------------------------------------------------------
@app.route("/debug-api", methods=["GET"])
def debug_api():
    """
    Try all likely base paths and sport keys to detect which combination
    actually returns events. Helps identify correct API version.
    """
    host = os.getenv("RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
    key = os.getenv("RAPIDAPI_KEY")
    headers = {"X-RapidAPI-Host": host, "X-RapidAPI-Key": key}

    bases = [
        "https://sportsbook-api2.p.rapidapi.com/v0",
        "https://sportsbook-api2.p.rapidapi.com/api/v1",
        "https://sportsbook-api2.p.rapidapi.com/v1"
    ]
    sports = ["nfl", "americanfootball_nfl", "nba", "americanfootball_ncaaf"]

    results = []
    for base in bases:
        for sport in sports:
            url = f"{base}/events"
            try:
                r = requests.get(url, headers=headers, params={"sport": sport}, timeout=10)
                count = 0
                if r.ok:
                    data = r.json()
                    if isinstance(data, dict):
                        count = len(data.get("events", []))
                results.append({
                    "base": base,
                    "sport": sport,
                    "status": r.status_code,
                    "count": count
                })
            except Exception as e:
                results.append({
                    "base": base,
                    "sport": sport,
                    "error": str(e)
                })

    return jsonify({"status": "success", "results": results})

# -------------------------------------------------------------------
# /playground-proxy : mirror RapidAPI Playground calls directly
# -------------------------------------------------------------------
@app.route("/playground-proxy", methods=["GET"])
def playground_proxy():
    """
    Proxy any direct test from RapidAPI API Playground.
    Example usage:
      /playground-proxy?endpoint=v0/events&sport=americanfootball_nfl
    This lets you copy the playground request and test it here.
    """
    endpoint = request.args.get("endpoint", "v0/events")
    sport = request.args.get("sport", "americanfootball_nfl")
    host = os.getenv("RAPIDAPI_HOST", "sportsbook-api2.p.rapidapi.com")
    key = os.getenv("RAPIDAPI_KEY")

    url = f"https://{host}/{endpoint}"
    headers = {"X-RapidAPI-Host": host, "X-RapidAPI-Key": key}
    try:
        r = requests.get(url, headers=headers, params={"sport": sport}, timeout=10)
        return jsonify({
            "status": "success" if r.ok else "error",
            "url": url,
            "sport": sport,
            "http_status": r.status_code,
            "data": r.json() if r.ok else r.text
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------------------------------------------------
# /run : main ChatGPT endpoint
# -------------------------------------------------------------------
@app.route("/run", methods=["POST"])
def run():
    try:
        body = request.get_json(force=True)
        sport = body.get("sport", "nfl")
        allow_api = body.get("allow_api", False)
        max_games = body.get("max_games", 10)

        payload = build_payload(
            sport,
            allow_api=allow_api,
            max_games=max_games
        )

        return jsonify({
            "status": "success",
            "source": "sports-agent",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "endpoint": "/run",
            "input": body,
            "data": payload
        })

    except Exception as e:
        app.logger.error(f"/run failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------------------------------------------------
# Gunicorn entrypoint
# -------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
