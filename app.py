# app.py
# Flask backend for the Sports Agent app
# Integrates with sportsbook_api and sports_agent modules

from flask import Flask, request, jsonify
from sports_agent import build_payload
import os
import datetime

app = Flask(__name__)

# -------------------------------------------------------------
# 🔧 Root route for quick health checks
# -------------------------------------------------------------
@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "Sports Agent API is live!",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

# -------------------------------------------------------------
# 🧠 Debug API route
# Example: https://sports-agent.onrender.com/debug-api?sport=nfl
# -------------------------------------------------------------
@app.route("/debug-api", methods=["GET"])
def debug_api():
    sport = request.args.get("sport", "nfl")
    include_props = request.args.get("props", "true").lower() == "true"
    include_advantages = request.args.get("adv", "true").lower() == "true"

    print(f"[DEBUG] /debug-api called with sport={sport}, props={include_props}, adv={include_advantages}")

    try:
        payload = build_payload(
            sport_key=sport,
            allow_api=True,
            include_props=include_props,
            include_advantages=include_advantages,
            max_games=5
        )
        return jsonify(payload)
    except Exception as e:
        print(f"[ERROR] Exception in debug_api: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# -------------------------------------------------------------
# ⚙️ Environment check (API key + host validation)
# -------------------------------------------------------------
@app.route("/check-env", methods=["GET"])
def check_env():
    key = os.getenv("RAPIDAPI_KEY", "")
    host = os.getenv("RAPIDAPI_HOST", "")
    result = {
        "host": host or "missing",
        "key_present": bool(key),
        "key_length": len(key),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    return jsonify(result)

# -------------------------------------------------------------
# 🏁 Launch app with gunicorn in Render
# -------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[INFO] Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
