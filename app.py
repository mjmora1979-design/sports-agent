# app.py — secure, rate-limited API for GPT Actions
from flask import Flask, request, jsonify
import os, json, time, threading
from datetime import datetime, date
import pandas as pd

from monte_carlo_model import run_monte_carlo, calibrate_model

app = Flask(__name__)

# ---------- Config (env with sensible defaults) ----------
API_KEY                = os.getenv("SPORTS_AGENT_KEY", "local-test-key")
MAX_SIMS               = int(os.getenv("MAX_SIMS", "20000"))
RUNS_DAILY_QUOTA       = int(os.getenv("RUNS_DAILY_QUOTA", "40"))
RUNS_PER_MINUTE        = int(os.getenv("RUNS_PER_MINUTE", "1"))
ODDS_DAILY_QUOTA       = int(os.getenv("ODDS_DAILY_QUOTA", "12"))
MODEL_CACHE_TTL_HOURS  = int(os.getenv("MODEL_CACHE_TTL_HOURS", "2"))

USAGE_STATE_PATH = "usage_state.json"
CACHE_ODDS_PATH  = "cached_odds.json"

state_lock = threading.Lock()

# ---------- Helpers: usage state & rate limiting ----------
def _today_str():
    return date.today().isoformat()

def load_state():
    if os.path.exists(USAGE_STATE_PATH):
        try:
            return json.load(open(USAGE_STATE_PATH))
        except Exception:
            pass
    return {
        "date": _today_str(),
        "counts": {"runs": 0, "odds_api_calls": 0},
        "recent": {"runs": []}
    }

def save_state(st):
    tmp = USAGE_STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=2)
    os.replace(tmp, USAGE_STATE_PATH)

def rotate_if_new_day(st):
    today = _today_str()
    if st.get("date") != today:
        st["date"] = today
        st["counts"] = {"runs": 0, "odds_api_calls": 0}
        st["recent"] = {"runs": []}

def within_daily_quota(st, key, limit):
    rotate_if_new_day(st)
    if st["counts"].get(key, 0) >= limit:
        return False
    st["counts"][key] = st["counts"].get(key, 0) + 1
    return True

def within_minute_throttle(st, key, per_minute):
    now = time.time()
    window_start = now - 60
    arr = st["recent"].get(key, [])
    arr = [t for t in arr if t >= window_start]
    if len(arr) >= per_minute:
        return False
    arr.append(now)
    st["recent"][key] = arr
    return True

# ---------- Security ----------
@app.before_request
def verify_api_key():
    if request.path in ("/", "/health"):
        return None
    key = request.headers.get("x-api-key")
    if key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

# ---------- Health ----------
@app.route("/", methods=["GET"])
def root():
    return jsonify({"service": "sports-agent", "status": "ok"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "time": datetime.utcnow().isoformat()})

# ---------- Force-refresh odds ----------
@app.route("/refresh_odds", methods=["POST"])
def refresh_odds():
    with state_lock:
        st = load_state()
        if not within_daily_quota(st, "odds_api_calls", ODDS_DAILY_QUOTA):
            save_state(st)
            return jsonify({"error": "Daily odds refresh quota reached"}), 429
        save_state(st)

    try:
        if os.path.exists(CACHE_ODDS_PATH):
            os.remove(CACHE_ODDS_PATH)
    except Exception as e:
        return jsonify({"error": f"Failed to clear cache: {e}"}), 500

    try:
        res = run_monte_carlo(snapshot_type="opening", n_sims=2000, sim_confidence=0.8)
        if isinstance(res, tuple):
            df, _ = res
        else:
            df = res

        return jsonify({
            "status": "refreshed",
            "games_detected": int(len(df.index.unique())),
            "note": "Odds cache refreshed and model lightly warmed."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- Run model ----------
@app.route("/run_model", methods=["POST"])
def run_model():
    with state_lock:
        st = load_state()
        if not within_minute_throttle(st, "runs", RUNS_PER_MINUTE):
            save_state(st)
            return jsonify({"error": "Too many requests per minute"}), 429
        if not within_daily_quota(st, "runs", RUNS_DAILY_QUOTA):
            save_state(st)
            return jsonify({"error": "Daily runs quota reached"}), 429
        save_state(st)

    data = request.get_json(force=True) if request.data else {}
    snapshot = data.get("snapshot_type", "opening")
    n_sims_req = int(data.get("n_sims", 20000))
    sim_conf  = float(data.get("sim_confidence", 0.8))
    top_k     = max(1, min(int(data.get("top_k", 10)), 50))
    n_sims = min(n_sims_req, MAX_SIMS)

    try:
        res = run_monte_carlo(snapshot_type=snapshot, n_sims=n_sims, sim_confidence=sim_conf)
        if isinstance(res, tuple):
            df, plays_df = res
        else:
            df = res
            plays_df = df.copy()

        ts = datetime.utcnow().isoformat()
        top_rows = (plays_df.sort_values(by="EV_%", ascending=False)
                             .head(top_k)
                             .to_dict(orient="records"))

        return jsonify({
            "timestamp": ts,
            "snapshot": snapshot,
            "n_sims": n_sims,
            "top_k": top_k,
            "top_opportunities": top_rows
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- Calibration & memory ----------
def summarize_for_memory(calib_df, week_tag="latest"):
    summary = {
        "week": week_tag,
        "games_evaluated": int(len(calib_df)),
        "accuracy": round(calib_df["correct"].mean() * 100, 2),
        "timestamp": datetime.utcnow().isoformat()
    }
    path = "memory_summary.json"
    try:
        mem = json.load(open(path)) if os.path.exists(path) else []
        mem.append(summary)
        json.dump(mem[-10:], open(path, "w"), indent=2)
    except Exception:
        pass

@app.route("/run_calibration", methods=["GET"])
def run_calibration_ep():
    try:
        df = pd.read_csv("sim_output_full.csv")
    except Exception:
        return jsonify({"error": "No simulation output available. Run /run_model at least once."}), 400
    try:
        calib = calibrate_model(df)
        if calib is None or calib.empty:
            return jsonify({"message": "No overlapping games for calibration"}), 200
        summarize_for_memory(calib, week_tag="latest")
        acc = round(calib['correct'].mean() * 100, 2)
        return jsonify({"accuracy": acc, "games_evaluated": int(len(calib))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/memory_summary", methods=["GET"])
def memory_summary():
    path = "memory_summary.json"
    if not os.path.exists(path):
        return jsonify([])
    try:
        return jsonify(json.load(open(path)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/usage_state", methods=["GET"])
def usage_state():
    try:
        st = load_state()
        rotate_if_new_day(st)
        return jsonify(st)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
