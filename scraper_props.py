import requests
from bs4 import BeautifulSoup
import datetime

def scrape_props(max_players=50):
    """Scrape popular player prop lines from CBS Sports (passing, rushing, receiving, TDs)."""
    url = "https://www.cbssports.com/nfl/props/"
    props = []
    try:
        html = requests.get(url, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")

        rows = soup.select("tr")[:max_players]
        for row in rows:
            cols = [c.text.strip() for c in row.find_all("td")]
            if len(cols) >= 4:
                player, team, prop_type, line = cols[:4]
                if any(k in prop_type.lower() for k in ["pass", "rush", "receiv", "touchdown"]):
                    props.append({
                        "player": player,
                        "team": team,
                        "market": prop_type,
                        "line": line,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    })

        print(f"[OK] Scraped {len(props)} props from CBS Sports")
    except Exception as e:
        print(f"[ERROR] scrape_props: {e}")
    return props
