from flask import Flask, request, jsonify
import sports_agent

app = Flask(__name__)

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "ok": True,
        "message": "Sports Agent API live. POST /run for JSON."
    })

@app.route("/run", methods=["POST"])
def run():
    data = request.get_json() or {}
    sport = data.get("sport", "nfl")
    allow_api = data.get("allow_api", True)
    log_full = data.get("log_full", False)

    try:
        report, prev, surv = sports_agent.run_model(
            sport=sport,
            log_full=log_full,
            allow_api=allow_api
        )
        return jsonify({"status": "success", "report": report, "survivor": surv})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
