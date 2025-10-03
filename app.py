# app.py
from flask import Flask, request, jsonify, send_file
from sports_agent import build_payload, to_excel
import io, os

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    """Simple health check."""
    return jsonify({"status": "ok"}), 200

@app.route("/config", methods=["GET"])
def config():
    """Echo non-sensitive config for debugging (never expose keys!)."""
    return jsonify({
        "SPORTSBOOK_RAPIDAPI_HOST": os.getenv("SPORTSBOOK_RAPIDAPI_HOST", ""),
        "BOOKS_DEFAULT": os.getenv("BOOKS_DEFAULT", ""),
        "CACHE_TTL_SEC": os.getenv("CACHE_TTL_SEC", ""),
        "SHEETS_ENABLED": os.getenv("SHEETS_ENABLED", "0"),
        "GSHEET_ID": os.getenv("GSHEET_ID", ""),
    }), 200

@app.route("/run", methods=["POST"])
def run():
    """Main endpoint: return JSON odds + summaries."""
    body = request.get_json(force=True, silent=True) or {}
    sport = (body.get("sport") or "nfl").lower()
    allow_api = bool(body.get("allow_api", False)) and (request.headers.get("X-ALLOW-API","") == "1")
    game_filter = body.get("game_filter")
    max_games = body.get("max_games")

    payload = build_payload(
        sport,
        allow_api=allow_api,
        game_filter=game_filter,
        max_games=max_games
    )
    return jsonify(payload), 200

@app.route("/excel", methods=["POST"])
def excel():
    """Optional: return flattened Excel file with games + survivor."""
    body = request.get_json(force=True, silent=True) or {}
    sport = (body.get("sport") or "nfl").lower()
    allow_api = bool(body.get("allow_api", False)) and (request.headers.get("X-ALLOW-API","") == "1")
    game_filter = body.get("game_filter")
    max_games = body.get("max_games")

    payload = build_payload(
        sport,
        allow_api=allow_api,
        game_filter=game_filter,
        max_games=max_games
    )

    xls = to_excel(payload)
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"{sport}_odds.xlsx"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","10000")))
