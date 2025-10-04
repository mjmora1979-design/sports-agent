from flask import Flask, request, jsonify, send_file
from sports_agent import build_payload, to_excel
import io, os

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "Sports Agent API running"}), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/config", methods=["GET"])
def config():
    return jsonify({
        "SPORTSBOOK_RAPIDAPI_HOST": os.getenv("SPORTSBOOK_RAPIDAPI_HOST", ""),
        "SPORTSBOOK_RAPIDAPI_KEY_SET": "yes" if os.getenv("SPORTSBOOK_RAPIDAPI_KEY") else "no",
        "BOOKS_DEFAULT": os.getenv("BOOKS_DEFAULT", ""),
        "CACHE_TTL_SEC": os.getenv("CACHE_TTL_SEC", ""),
        "SHEETS_ENABLED": os.getenv("SHEETS_ENABLED", "0"),
        "GSHEET_ID": os.getenv("GSHEET_ID", ""),
        "GOOGLE_CREDS_SET": "yes" if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON") else "no"
    }), 200

@app.route("/run", methods=["POST"])
def run():
    body = request.get_json(force=True, silent=True) or {}
    sport = (body.get("sport") or "nfl").lower()
    allow_api = bool(body.get("allow_api", False)) and (request.headers.get("X-ALLOW-API", "") == "1")
    game_filter = body.get("game_filter")
    max_games = body.get("max_games")
    force_direct_odds = bool(body.get("force_direct_odds", False))

    payload = build_payload(
        sport,
        allow_api=allow_api,
        game_filter=game_filter,
        max_games=max_games,
        force_direct_odds=force_direct_odds
    )
    return jsonify(payload), 200

@app.route("/excel", methods=["POST"])
def excel():
    body = request.get_json(force=True, silent=True) or {}
    sport = (body.get("sport") or "nfl").lower()
    allow_api = bool(body.get("allow_api", False)) and (request.headers.get("X-ALLOW-API", "") == "1")
    game_filter = body.get("game_filter")
    max_games = body.get("max_games")
    force_direct_odds = bool(body.get("force_direct_odds", False))

    payload = build_payload(
        sport,
        allow_api=allow_api,
        game_filter=game_filter,
        max_games=max_games,
        force_direct_odds=force_direct_odds
    )

    xls = to_excel(payload)
    return send_file(
        io.BytesIO(xls),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"{sport}_odds.xlsx"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
