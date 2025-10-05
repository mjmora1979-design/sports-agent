from flask import Flask, jsonify, request
from sports_agent import build_payload
import os

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "Sports Agent API running successfully!"})

@app.route("/test-sheets", methods=["GET"])
def test_sheets():
    """
    Test connection to Google Sheets by logging a test entry.
    """
    from gsheet_logger import log_to_sheets
    test_data = {"test": "Render deployment", "status": "success"}
    try:
        log_to_sheets(test_data)
        return jsonify({"message": "Sheets test succeeded!", "data": test_data})
    except Exception as e:
        return jsonify({"error": str(e), "status": "failed"}), 500

@app.route("/run-model", methods=["POST"])
def run_model():
    """
    Trigger a model payload build and sheet log.
    """
    data = request.get_json(force=True)
    sport = data.get("sport", "nfl")
    payload = build_payload(sport)
    return jsonify({"payload": payload, "status": "success"})

@app.route("/debug-path", methods=["GET"])
def debug_path():
    """
    Debug Render directory and confirm credentials.json visibility.
    """
    cwd = os.getcwd()
    files = os.listdir(cwd)
    return jsonify({"cwd": cwd, "files": files})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
