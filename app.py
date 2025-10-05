from flask import Flask, request, jsonify
import os
import datetime
import traceback

from sports_agent import build_payload

app = Flask(__name__)

@app.route("/")
def root():
    return jsonify({
        "status": "ok",
        "message": "sports-agent is live",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

@app.route("/check-env")
def check_env():
    key = os.getenv("RAPIDAPI_KEY", "")
    host = os.getenv("RAPIDAPI_HOST", "")
    return jsonify({
        "host": host or "missing",
        "key_present": bool(key),
        "key_length": len(key),
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

@app.route("/test-api")
def test_api():
    """Lightweight health + one simple fetch (competitions) to verify keys work."""
    try:
        from sportsbook_api import list_competitions
        data = list_competitions()
        count = len((data or {}).get("competitions", [])) if isinstance(data, dict) else 0
        return jsonify({
            "ok": bool(data),
            "competitions_count": count,
            "sample_keys": (data or {}).get("competitions", [])[:3],
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
    except Exception as e:
        print("[ERROR] /test-api\n", traceback.format_exc())
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/debug-api")
def debug_api():
    """
    Debug snapshot:
      /debug-api?sport=nfl&max=5&mode=last&markets=MONEYLINE,POINT_SPREAD,POINT_TOTAL&advantages=true
    """
    sport = request.args.get("sport", "nfl")
    max_games = int(request.args.get("max", "5"))
    outcome_mode = request.args.get("mode", "last").lower()
    include_advantages = request.args.get("advantages", "true").lower() == "true"

    markets_arg = request.args.get("markets")  # comma-separated or None
    allowed_market_types = None
    if markets_arg:
        allowed_market_types = [m.strip() for m in markets_arg.split(",") if m.strip()]

    try:
        payload = build_payload(
            sport=sport,
            allow_api=True,
            max_games=max_games,
            outcome_mode=outcome_mode if outcome_mode in ("last", "closing") else "last",
            allowed_market_types=allowed_market_types,
            include_advantages=include_advantages
        )
        return jsonify(payload)
    except Exception as e:
        print("[ERROR] /debug-api\n", traceback.format_exc())
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/run", methods=["POST"])
def run():
    """
    POST JSON:
      {
        "sport": "nfl",
        "allow_api": true,
        "max_games": 5,
        "outcome_mode": "last",    # or "closing"
        "markets": ["MONEYLINE","POINT_SPREAD","POINT_TOTAL"],
        "include_advantages": true
      }
    """
    try:
        data = request.get_json(force=True) or {}
        sport = data.get("sport", "nfl")
        allow_api = bool(data.get("allow_api", True))
        max_games = int(data.get("max_games", 5))
        outcome_mode = (data.get("outcome_mode", "last") or "last").lower()
        include_advantages = bool(data.get("include_advantages", True))
        allowed_market_types = data.get("markets")  # list or None

        payload = build_payload(
            sport=sport,
            allow_api=allow_api,
            max_games=max_games,
            outcome_mode=outcome_mode if outcome_mode in ("last", "closing") else "last",
            allowed_market_types=allowed_market_types,
            include_advantages=include_advantages
        )
        return jsonify({
            "status": "success",
            "sport": sport,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "payload": payload
        })
    except Exception as e:
        print("[ERROR] /run\n", traceback.format_exc())
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=True)
