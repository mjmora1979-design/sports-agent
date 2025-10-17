# ... everything above unchanged ...

from monte_carlo_model import run_monte_carlo, calibrate_model, load_calibration  # ← add load_calibration

# ---------- Run model (rate-limited) ----------
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

    n_sims = min(n_sims_req, MAX_SIMS)  # hard cap per run

    try:
        # NEW: load calibration (if present)
        calib = load_calibration()

        df, plays_df = run_monte_carlo(
            snapshot_type=snapshot,
            n_sims=n_sims,
            sim_confidence=sim_conf,
            calibration=calib
        )
        ts = datetime.utcnow().isoformat()

        # Prefer EV_% column for both sides
        ev_field = "EV_%"
        if ev_field not in plays_df.columns:
            # fallback to home-only
            ev_field = "home_EV_%"

        top_rows = (plays_df.sort_values(by=ev_field, ascending=False)
                             .head(top_k)
                             .to_dict(orient="records"))

        return jsonify({
            "timestamp": ts,
            "snapshot": snapshot,
            "n_sims": n_sims,
            "top_k": top_k,
            "ev_field_used": ev_field,
            "top_opportunities": top_rows
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
