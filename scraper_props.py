import time
import traceback
import requests
from bs4 import BeautifulSoup

# Define sites and their scraping logic
def _scrape_rotowire_props():
    url = "https://www.rotowire.com/betting/nfl/player-props.php"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    props = []
    # Example parsing – adjust to actual page structure
    for row in soup.select("table tr"):
        cols = row.find_all("td")
        if len(cols) >= 4:
            player = cols[0].get_text(strip=True)
            stat = cols[1].get_text(strip=True)
            line = cols[2].get_text(strip=True)
            # Only if numeric
            try:
                val = float(line.replace(",", "").split()[0])
                props.append({"player": player, "stat": stat, "line": val, "source": "rotowire"})
            except:
                continue
    return props

def _scrape_fantasypros_props():
    url = "https://www.fantasypros.com/nfl/props/"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/Anything"}, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    props = []
    for row in soup.select("table tbody tr"):
        cols = row.find_all("td")
        if len(cols) >= 3:
            player = cols[0].get_text(strip=True)
            stat = cols[1].get_text(strip=True)
            line = cols[2].get_text(strip=True)
            try:
                val = float(line.replace(",", "").split()[0])
                props.append({"player": player, "stat": stat, "line": val, "source": "fantasypros"})
            except:
                continue
    return props

def scrape_props_for_sport(sport: str, fresh: bool = False):
    """
    Return list of props (player + stat + line) for the given sport.
    fresh: if True, always re-scrape; else, cache/filter duplicates.
    """
    all_props = []
    # Try primary sites
    try:
        all_props.extend(_scrape_rotowire_props())
    except Exception as e:
        print("[WARN] rotowire scraping error:", traceback.format_exc())
    time.sleep(0.5)

    try:
        all_props.extend(_scrape_fantasypros_props())
    except Exception as e:
        print("[WARN] fantasypros scraping error:", traceback.format_exc())

    # Could add more scrapers (Covers, ActionNetwork, etc.)
    return all_props
