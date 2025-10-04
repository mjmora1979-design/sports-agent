from flask import Flask, request, jsonify
from sports_agent import build_payload, to_excel

app = Flask(__name__)

@app.route("/")
def home():
    return "Sports Agent API is live!"

@app.route("/run", methods=["POST"])
def run():
    try:
        body = request.get_json(force=True)

        sport = body.get("sport", "nfl")
        allow_api = body.get("allow_api", False)
        game_filter = body.get("game_filter")
        max_games = body.get("max_games")

        payload = build_payload(
            sport,
            allow_api=allow_api,
            game_filter=game_filter,
            max_games=max_games
        )

        return jsonify(payload)

    except Exception as e:
        app.logger.error(f"/run failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/excel", methods=["POST"])
def excel():
    try:
        body = request.get_json(force=True)
        payload = build_payload(
            body.get("sport", "nfl"),
            allow_api=body.get("allow_api", False),
            game_filter=body.get("game_filter"),
            max_games=body.get("max_games")
        )

        excel_bytes = to_excel(payload)
        return excel_bytes, 200, {
            "Content-Disposition": "attachment; filename=output.xlsx",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }

    except Exception as e:
        app.logger.error(f"/excel failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
