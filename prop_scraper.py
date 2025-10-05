import requests
from bs4 import BeautifulSoup

def get_nfl_props():
    """
    Scrapes NFL player prop lines from FantasyPros and Vegas Insider (fallback)
    Returns a standardized list of dicts
    """
    props = []
    try:
        print("[SCRAPER] Fetching FantasyPros props...")
        url = "https://www.fantasypros.com/nfl/prop-bets/"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        for row in soup.select("table tbody tr"):
            player = row.select_one("td:nth-child(1)").get_text(strip=True)
            stat = row.select_one("td:nth-child(2)").get_text(strip=True)
            line = row.select_one("td:nth-child(3)").get_text(strip=True)
            if line.replace('.', '', 1).isdigit():
                line_val = float(line)
                props.append({"player": player, "stat": stat, "line": line_val})
    except Exception as e:
        print(f"[WARN] FantasyPros failed: {e}")
    
    if not props:
        try:
            print("[SCRAPER] Fallback to Vegas Insider...")
            url = "https://www.vegasinsider.com/nfl/player-props/"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(response.text, "html.parser")

            for row in soup.select("tr"):
                cols = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cols) >= 3:
                    player, stat, line = cols[0], cols[1], cols[2]
                    if line.replace('.', '', 1).isdigit():
                        props.append({"player": player, "stat": stat, "line": float(line)})
        except Exception as e:
            print(f"[WARN] Vegas Insider failed: {e}")
    
    return props
