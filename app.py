from flask import Flask, request, jsonify
from sports_agent import build_payload
import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "sports-agent up", "ts": datetime.datetime.utcnow().isoformat()})

@app.route("/debug-api", methods=["GET"])
def debug_api():
    sport = request.args.get("sport", "nfl")
    props_flag = request.args.get("props", "true").lower() == "true"
    # optional param to force fresh scrape
    fresh = request.args.get("fresh", "false").lower() == "true"
    payload = build_payload(sport=sport, props=props_flag, fresh_props=fresh)
    return jsonify(payload)

@app.route("/run", methods=["POST"])
def run():
    data = request.get_json(force=True) or {}
    sport = data.get("sport", "nfl")
    props_flag = data.get("props", True)
    fresh = data.get("fresh_props", False)
    payload = build_payload(sport=sport, props=props_flag, fresh_props=fresh)
    return jsonify(payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
