# app.py
# Flask backend for the Sports Agent app
# Integrates with sportsbook_api and sports_agent modules

from flask import Flask, request, jsonify
from sports_agent import build_payload
import os
import datetime
import traceback

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
# 🧠 Debug route to view sportsbook API results
# Example: /debug-api?sport=nfl
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
        print(f"[ERROR] Exception in /debug-api: {traceback.format_exc()}")
        return jsonify({"status": "error", "error": str(e)}), 500

# -------------------------------------------------------------
# ⚙️ Environment check route
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
# 🧩 Model API — “North Star” Integration
# -------------------------------------------------------------
# This will later serve your model analysis layer or ChatGPT custom GPT
# For now, it will return a combined package of:
#   - events
#   - odds
#   - props
#   - advantages (if available)
#   - metadata for model scoring
# -------------------------------------------------------------
@app.route("/model-api", methods=["POST"])
def model_api():
    try:
        data = request.get_json(force=True)
        sport = data.get("sport", "nfl")
        include_props = data.get("include_props", True)
        include_advantages = data.get("include_advantages", True)
        model_id = data.get("model_id", "default-v1")

        print(f"[INFO] /model-api request for sport={sport}, model={model_id}")

        # Pull the live payload
        payload = build_payload(
            sport_key=sport,
            allow_api=True,
            include_props=include_props,
            include_advantages=include_advantages,
            max_games=10
        )

        # Add a metadata block for downstream ML integration
        response = {
            "model_id": model_id,
            "sport": sport,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "payload": payload,
            "metadata": {
                "source": "sportsbook-api2",
                "integration": "north_star_v1",
                "description": "Unified data for modeling and ChatGPT integration"
            }
        }

        return jsonify(response)

    except Exception as e:
        print(f"[ERROR] Exception in /model-api: {traceback.format_exc()}")
        return jsonify({"status": "error", "error": str(e)}), 500

# -------------------------------------------------------------
# 🏁 Launch app with gunicorn in Render
# -------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[INFO] Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
