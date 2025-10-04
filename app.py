from flask import Flask, request, jsonify
from sports_agent import build_payload, to_excel
import datetime

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "Sports Agent API running"})

@app.route("/run", methods=["POST"])
def run():
    """
    Accept JSON like:
    {
        "sport": "nfl",
        "allow_api": true,
        "game_filter": null,
        "max_games": null
    }
    """
    try:
        data = request.get_json(force=True)

        sport = data.get("sport", "nfl").lower()
        allow_api = data.get("allow_api", True)
        game_filter = data.get("game_filter", None)
        max_games = data.get("max_games", None)

        # Auto flags based on sport type
        pro_sports = ["nfl", "nba", "mlb", "nhl"]
        if sport in pro_sports:
            force_direct_odds = True
        else:
            force_direct_odds = False

        payload = build_payload(
            sport=sport,
            allow_api=allow_api,
            game_filter=game_filter,
            max_games=max_games,
            force_refresh=False,         # auto caching can be added later
            force_direct_odds=force_direct_odds
        )
        return jsonify(payload)

    except Exception as e:
        print("[ERROR] /run failed:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/excel", methods=["POST"])
def excel():
    """
    Accepts the payload JSON from /run and returns an Excel file.
    """
    try:
        data = request.get_json(force=True)
        excel_bytes = to_excel(data)
        response = app.response_class(excel_bytes, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response.headers.set("Content-Disposition", "attachment", filename=f"odds_{datetime.date.today()}.xlsx")
        return response
    except Exception as e:
        print("[ERROR] /excel failed:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
