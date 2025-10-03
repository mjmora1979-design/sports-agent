from flask import Flask, request, jsonify, send_file
import os, tempfile
import sports_agent

app = Flask(__name__)

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "ok": True,
        "message": "Sports Agent API is live. Use POST /run for JSON or POST /excel for Excel outputs."
    })

@app.route("/run", methods=["POST"])
def run():
    data = request.get_json() or {}
    mode = data.get("mode", "live")
    allow_api = data.get("allow_api", False) or request.headers.get("X-ALLOW-API", "") == "1"
    survivor = data.get("survivor", False)
    used = data.get("used", [])
    double_from = int(data.get("double_from", 13))
    game_filter = data.get("game_filter", None)
    max_games = data.get("max_games", None)
    sport = data.get("sport", "nfl")
    include_props = data.get("include_props", False)
    books = data.get("books", sports_agent.DEFAULT_BOOKS)
    debug = data.get("debug", False)

    try:
        result = sports_agent.run_model(
            mode=mode,
            allow_api=allow_api,
            survivor=survivor,
            used=used,
            double_from=double_from,
            game_filter=game_filter,
            max_games=max_games,
            sport=sport,
            include_props=include_props,
            books=books,
            debug=debug
        )
        if debug:
            report, prev, surv, skipped = result
            return jsonify({"status": "success", "report": report, "survivor": surv, "skipped_props": skipped})
        else:
            report, prev, surv = result
            return jsonify({"status": "success", "report": report, "survivor": surv})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/excel", methods=["POST"])
def excel():
    data = request.get_json() or {}
    mode = data.get("mode", "live")
    allow_api = data.get("allow_api", False) or request.headers.get("X-ALLOW-API", "") == "1"
    survivor = data.get("survivor", False)
    used = data.get("used", [])
    double_from = int(data.get("double_from", 13))
    game_filter = data.get("game_filter", None)
    max_games = data.get("max_games", None)
    sport = data.get("sport", "nfl")
    include_props = data.get("include_props", False)
    books = data.get("books", sports_agent.DEFAULT_BOOKS)

    try:
        report, prev, surv = sports_agent.run_model(
            mode=mode,
            allow_api=allow_api,
            survivor=survivor,
            used=used,
            double_from=double_from,
            game_filter=game_filter,
            max_games=max_games,
            sport=sport,
            include_props=include_props,
            books=books
        )
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        sports_agent.save_excel(report, prev, tmp.name, survivor=surv)
        tmp.flush()
        return send_file(
            tmp.name,
            as_attachment=True,
            download_name=f"report_{sports_agent.nowstamp()}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
