from flask import Flask, request, jsonify
import os, sports_agent

app = Flask(__name__)

@app.route("/run", methods=["POST"])
def run():
    data = request.get_json() or {}
    mode = data.get("mode","live")
    allow_api = data.get("allow_api", False) or request.headers.get("X-ALLOW-API","")=="1"
    try:
        report, prev = sports_agent.run_model(mode=mode, allow_api=allow_api)
        return jsonify({"status":"success","report":report})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}),500

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)
