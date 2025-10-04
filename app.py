import os
from flask import Flask, request, jsonify
from sports_agent import build_payload, to_excel

app = Flask(__name__)

# -------------------------
# Healthcheck root
# -------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Sports Agent API is live"}), 200

# -------------------------
# Run payload builder
# -------------------------
@app.route("/run", methods=["POST"])
def run():
    try:
        data = request.get_json(force=True)

        sport = data.get("sport", "nfl")
        allow_api = data.get("allow_api", True)
        game_filter = data.get("game_filter")
        max_games = data.get("max_games")
        mode = data.get("mode", "open")   # ✅ new param to control open/closed odds

        payload = build_payload(
            sport,
            allow_api=allow_api,
            game_filter=game_filter,
            max_games=max_games,
            mode=mode
        )
        return jsonify(payload), 200
    except Exception as e:
        print("[ERROR] /run failed:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# Excel export
# -------------------------
@app.route("/export", methods=["POST"])
def export():
    try:
        data = request.get_json(force=True)
        payload = build_payload(
            data.get("sport", "nfl"),
            allow_api=data.get("allow_api", True),
            game_filter=data.get("game_filter"),
            max_games=data.get("max_games"),
            mode=data.get("mode", "open")
        )
        xlsx_bytes = to_excel(payload)

        from flask import Response
        response = Response(xlsx_bytes, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers.set("Content-Disposition", "attachment", filename="odds.xlsx")
        return response
    except Exception as e:
        print("[ERROR] /export failed:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# Main entrypoint
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
