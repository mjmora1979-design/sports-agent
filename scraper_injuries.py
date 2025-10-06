import requests
from bs4 import BeautifulSoup
import datetime

def scrape_injuries():
    """Scrape NFL injury reports from CBS Sports."""
    url = "https://www.cbssports.com/nfl/injuries/"
    injuries = []
    try:
        html = requests.get(url, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")

        tables = soup.select("table")
        for table in tables:
            team_name = table.find_previous("h3").text.strip() if table.find_previous("h3") else "Unknown"
            for row in table.find_all("tr")[1:]:
                cols = [c.text.strip() for c in row.find_all("td")]
                if len(cols) >= 3:
                    player, position, status = cols[:3]
                    injuries.append({
                        "team": team_name,
                        "player": player,
                        "position": position,
                        "status": status,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    })

        print(f"[OK] Scraped {len(injuries)} injuries from CBS Sports")
    except Exception as e:
        print(f"[ERROR] scrape_injuries: {e}")
    return injuries
