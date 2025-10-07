import requests
from bs4 import BeautifulSoup
import datetime

def scrape_props(max_props=150):
    """Scrape QB/RB/WR/TE props from Rotowire and Action Network."""
    props = []
    timestamp = datetime.datetime.utcnow().isoformat()

    try:
        # ROTOWIRE
        rw_html = requests.get("https://www.rotowire.com/betting/nfl/prop-bets.php", timeout=20).text
        rw = BeautifulSoup(rw_html, "html.parser")

        rows = rw.select("tr")[:max_props]
        for r in rows:
            cols = [c.text.strip() for c in r.find_all("td")]
            if len(cols) >= 4:
                player, team, market, line = cols[:4]
                if any(k in market.lower() for k in ["pass", "rush", "receiv", "touchdown"]):
                    props.append({
                        "player": player,
                        "team": team,
                        "market": market,
                        "line": line,
                        "source": "Rotowire",
                        "timestamp": timestamp
                    })

        # ACTION NETWORK
        an_html = requests.get("https://www.actionnetwork.com/nfl/player-prop-bets", timeout=20).text
        an = BeautifulSoup(an_html, "html.parser")
        tables = an.select("div.player-prop-row")

        for t in tables[:max_props]:
            name = t.select_one("div.player-prop-name")
            stat = t.select_one("div.player-prop-stat")
            val = t.select_one("div.player-prop-line")
            if name and stat and val:
                stat_text = stat.text.lower()
                if any(k in stat_text for k in ["passing", "rushing", "receiving", "touchdown"]):
                    props.append({
                        "player": name.text.strip(),
                        "team": None,
                        "market": stat.text.strip(),
                        "line": val.text.strip(),
                        "source": "ActionNetwork",
                        "timestamp": timestamp
                    })

        print(f"[OK] Scraped {len(props)} player props from Rotowire + Action Network.")

    except Exception as e:
        print(f"[ERROR] scrape_props: {e}")

    return props
