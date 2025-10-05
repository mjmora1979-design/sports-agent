from flask import Flask, request, jsonify
from sports_agent import build_payload
import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return "Sports Agent API active"

@app.route("/debug-api", methods=["GET"])
def debug_api():
    sport = request.args.get("sport", "nfl")
    props = request.args.get("props", "true").lower() == "true"
    debug = build_payload(sport=sport, props=props, allow_api=True)
    return jsonify(debug)

@app.route("/build", methods=["POST"])
def build():
    data = request.get_json(force=True)
    sport = data.get("sport", "nfl")
    props = data.get("props", True)
    payload = build_payload(sport=sport, props=props, allow_api=True)
    return jsonify(payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
