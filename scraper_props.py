import requests
from bs4 import BeautifulSoup
import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def scrape_props(max_props=150):
    props = []
    timestamp = datetime.datetime.utcnow().isoformat()

    try:
        # Rotowire first
        rw_html = requests.get("https://www.rotowire.com/betting/nfl/prop-bets.php",
                               headers=HEADERS, timeout=25).text
        rw = BeautifulSoup(rw_html, "html.parser")

        for row in rw.select("tr")[:max_props]:
            cols = [c.text.strip() for c in row.find_all("td")]
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

        print(f"[OK] Found {len(props)} props from Rotowire.")

        # If Rotowire was blocked, fallback to Covers
        if len(props) == 0:
            covers_html = requests.get("https://www.covers.com/sport/football/nfl/player-props",
                                       headers=HEADERS, timeout=25).text
            cs = BeautifulSoup(covers_html, "html.parser")
            for item in cs.select("div.covers-CustomLink"):
                txt = item.get_text(" ", strip=True)
                if any(word in txt.lower() for word in ["yards", "touchdown", "passing", "rushing"]):
                    props.append({
                        "player": txt.split(" ")[0],
                        "team": None,
                        "market": " ".join(txt.split(" ")[1:]),
                        "line": None,
                        "source": "Covers",
                        "timestamp": timestamp
                    })

        print(f"[OK] Total props collected: {len(props)}")

    except Exception as e:
        print(f"[ERROR] scrape_props: {e}")

    return props
