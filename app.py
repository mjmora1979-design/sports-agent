import os
import traceback
from flask import Flask, request, jsonify
from sports_agent import build_payload, to_excel

app = Flask(__name__)

# -------------------------
# Health check
# -------------------------
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "running"}), 200

# -------------------------
# Config endpoint
# -------------------------
@app.route("/config", methods=["GET"])
def get_config():
    return jsonify({
        "BOOKS_DEFAULT": os.getenv("BOOKS_DEFAULT", ""),
        "CACHE_TTL_SEC": os.getenv("CACHE_TTL_SEC", ""),
        "GSHEET_ID": os.getenv("GSHEET_ID", ""),
        "SHEETS_ENABLED": os.getenv("SHEETS_ENABLED", "0"),
        "SPORTSBOOK_RAPIDAPI_HOST": os.getenv("SPORTSBOOK_RAPIDAPI_HOST", "")
    })

# -------------------------
# Main run endpoint
# -------------------------
@app.route("/run", methods=["POST"])
def run():
    try:
        data = request.json or {}
        sport = data.get("sport", "nfl").lower()
        allow_api = data.get("allow_api", True)
        game_filter = data.get("filter")
        max_games = data.get("max_games")

        payload = build_payload(
            sport,
            allow_api=allow_api,
            game_filter=game_filter,
            max_games=max_games
        )
        return jsonify(payload)
    except Exception as e:
        print("[ERROR] in /run:", e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# Excel export endpoint
# -------------------------
@app.route("/export", methods=["POST"])
def export():
    try:
        data = request.json or {}
        payload = build_payload(data.get("sport", "nfl"), allow_api=True)
        excel_bytes = to_excel(payload)

        return (
            excel_bytes,
            200,
            {
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Content-Disposition": "attachment; filename=odds.xlsx",
            },
        )
    except Exception as e:
        print("[ERROR] in /export:", e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
