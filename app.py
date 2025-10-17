from flask import Flask, request, jsonify
import os, json
from datetime import datetime
import pandas as pd
from monte_carlo_model import run_monte_carlo, calibrate_model, load_calibration

# ------------------------------------------------------------
# Initialize Flask app FIRST
# ------------------------------------------------------------
app = Flask(__name__)

# ------------------------------------------------------------
# Health check
# ------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Sports Agent API ready", "timestamp": datetime.utcnow().isoformat()})


# ------------------------------------------------------------
# Run model (main endpoint for ChatGPT & API)
# ------------------------------------------------------------
@app.route("/run_model", methods=["POST"])
def run_model():
    """
    Run the Monte Carlo EV model, optionally using calibration parameters.
    """
    try:
        data = request.get_json(force=True)
        snapshot_type = data.get("snapshot_type", "opening")
        n_sims = int(data.get("n_sims", 20000))
        top_k = int(data.get("top_k", 5))

        # Load calibration file if it exists
        calibration = load_calibration()

        df = run_monte_carlo(snapshot_type=snapshot_type, n_sims=n_sims, sim_confidence=0.8)
        top_df = (
            df.sort_values(by="home_EV_%", ascending=False)
            .drop_duplicates(subset=["home_team", "away_team"], keep="first")
            .head(top_k)
        )

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "snapshot": snapshot_type,
            "n_sims": n_sims,
            "top_k": top_k,
            "ev_field_used": "home_EV_%",
            "top_opportunities": top_df.to_dict(orient="records"),
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------
# Calibration endpoint
# ------------------------------------------------------------
@app.route("/calibrate", methods=["POST"])
def calibrate_endpoint():
    """
    Run calibration on the latest simulation output and update calibration file.
    """
    try:
        df = run_monte_carlo(snapshot_type="opening", n_sims=20000, sim_confidence=0.8)
        calib = calibrate_model(df)
        return jsonify({"message": "Calibration completed", "params": calib})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------
# OpenAPI schema for ChatGPT Actions
# ------------------------------------------------------------
@app.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """
    Returns a minimal OpenAPI schema so ChatGPT can integrate via 'Import from URL'.
    """
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Sports Agent API",
            "version": "1.0.0",
            "description": "Endpoints for running EV simulations and calibration",
        },
        "paths": {
            "/run_model": {
                "post": {
                    "summary": "Run Monte Carlo EV simulation",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "snapshot_type": {"type": "string", "example": "opening"},
                                        "n_sims": {"type": "integer", "example": 20000},
                                        "top_k": {"type": "integer", "example": 5},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful model run",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            "/calibrate": {
                "post": {
                    "summary": "Run calibration based on last simulation results",
                    "responses": {
                        "200": {
                            "description": "Calibration success",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
        },
    }
    return jsonify(spec)


# ------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
