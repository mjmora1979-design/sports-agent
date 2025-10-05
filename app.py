from flask import Flask, request, jsonify
import datetime
from sports_agent import build_payload
from gsheet_logger import log_to_sheets

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Sports Agent API is live and connected."

# --- TEST 1: Check that the API and Google Sheet are connected ---
@app.route("/test-sheets", methods=["GET"])
def test_sheets():
    try:
        data = {
            "test": "connection",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        log_to_sheets(data)
        return jsonify({"status": "success", "message": "Logged test row to Google Sheet", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- TEST 2: Simple debug to confirm API key and host setup ---
@app.route("/debug-api", methods=["GET"])
def debug_api():
    from sportsbook_api import test_api_connection
    result = test_api_connection()
    return jsonify(result)

# --- TEST 3: Run main payload builder ---
@app.route("/run", methods=["POST"])
def run():
    try:
        body = request.get_json(force=True)
        sport = body.get("sport", "nfl")
        allow_api = body.get("allow_api", True)
        max_games = body.get("max_games", 10)

        result = build_payload(sport, allow_api=allow_api, max_games=max_games)
        # Log a short summary to Sheets
        log_to_sheets({"run": sport, "game_count": len(result.get("events", []))})
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
