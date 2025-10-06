from flask import Flask, request, jsonify
from sports_agent import build_payload

app = Flask(__name__)

@app.route("/")
def home():
    return "🏈 Sports-Agent CBS Hybrid System Ready"

@app.route("/debug-scrape")
def debug_scrape():
    sport = request.args.get("sport", "nfl")
    max_games = int(request.args.get("max_games", 10))
    data = build_payload(sport, max_games)
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
