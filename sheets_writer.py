# sheets_writer.py
# Google Sheets logging helper with throttling + de-dupe.

import os, json, base64, time, logging
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

# ---- Env Vars ----
SHEETS_ENABLED = os.getenv("SHEETS_ENABLED", "0") == "1"
GSHEET_ID = os.getenv("GSHEET_ID", "")
GOOGLE_SA_JSON = os.getenv("GOOGLE_SA_JSON", "")

# Lazy imports
_gspread = None
_gc = None

# De-dupe tracker (in-memory, 2h window)
_last_seen: Dict[Tuple[str, str, str, str, str], float] = {}

def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _load_sa():
    """Authorize gspread client using Service Account JSON (raw or base64)."""
    global _gspread, _gc
    if not SHEETS_ENABLED:
        return
    if _gc:
        return
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        _gspread = gspread
        raw = GOOGLE_SA_JSON.strip()
        try:
            if raw.startswith("{"):
                sa = json.loads(raw)
            else:
                sa = json.loads(base64.b64decode(raw).decode("utf-8"))
        except Exception:
            sa = json.loads(base64.b64decode(raw).decode("utf-8"))
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(sa, scopes=scopes)
        _gc = gspread.authorize(creds)
    except Exception as e:
        logging.warning(f"[Sheets] SA init failed: {e}")

def _open_ws(sport: str):
    """Open or create worksheet tab for given sport (e.g. nfl_log)."""
    _load_sa()
    if not _gc:
        return None
    try:
        sh = _gc.open_by_key(GSHEET_ID)
        tab = f"{sport.lower()}_log"
        try:
            ws = sh.worksheet(tab)
        except Exception:
            ws = sh.add_worksheet(title=tab, rows=1000, cols=12)
            ws.append_row([
                "timestamp_utc","event_id","commence_time","home","away",
                "book","market","label","price","point_or_line"
            ])
        return ws
    except Exception as e:
        logging.warning(f"[Sheets] open worksheet failed: {e}")
        return None

def _should_write(key: Tuple[str,str,str,str,str]) -> bool:
    """De-dupe within ~2h based on key: (event_id, book, market, label, point)."""
    now = time.time()
    last = _last_seen.get(key)
    if last and now - last < 7200:  # 2h
        return False
    _last_seen[key] = now
    return True

def log_batch(sport: str, rows: List[Dict[str, Any]]):
    """
    Log odds rows to Google Sheets.
    rows must include: event_id, commence_time, home, away, book, market, label, price, point_or_line
    """
    if not SHEETS_ENABLED or not rows:
        return
    ws = _open_ws(sport)
    if not ws:
        return
    try:
        values = []
        now_iso = _now_iso()
        for r in rows:
            key = (
                r.get("event_id",""),
                r.get("book",""),
                r.get("market",""),
                r.get("label",""),
                str(r.get("point_or_line","")),
            )
            if not _should_write(key):
                continue
            values.append([
                now_iso,
                r.get("event_id",""),
                r.get("commence_time",""),
                r.get("home",""),
                r.get("away",""),
                r.get("book",""),
                r.get("market",""),
                r.get("label",""),
                r.get("price",""),
                r.get("point_or_line",""),
            ])
        if values:
            ws.append_rows(values, value_input_option="RAW")
    except Exception as e:
        logging.warning(f"[Sheets] append failed: {e}")
