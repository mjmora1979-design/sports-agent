"""
app.py
------
Flask service entrypoint for the sports model Odds API integration.

Endpoints:
    /odds?snapshot=opening   -> Fetches odds snapshot (opening or cached)
    /odds?snapshot=closing   -> Fetches closing snapshot (manual or cached)
"""

from flask import Flask, jsonify, request
from sports_agent import build_payload

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({
        "message": "Sports Odds API Service",
        "endpoints": {
            "/odds?snapshot=opening": "Fetch opening odds",
            "/odds?snapshot=closing": "Fetch closing odds (Sunday batch)"
        }
    })

@app.route("/odds", methods=["GET"])
def get_odds():
    """
    Example:
        GET /odds?snapshot=opening
        GET /odds?snapshot=closing
    """
    snapshot = request.args.get("snapshot", "opening")
    result = build_payload("nfl", snapshot)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
