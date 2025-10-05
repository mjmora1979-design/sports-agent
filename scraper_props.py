import requests
from bs4 import BeautifulSoup
from gsheet_logger import log_to_sheets

def scrape_props_example():
    """
    Example placeholder scraper.
    Replace with live sources for props or lines.
    """
    url = "https://www.espn.com/nfl/lines"
    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    props = []
    for game in soup.select("section.GameCell"):
        title = game.select_one("a.AnchorLink").get_text(strip=True)
        props.append({"source": "espn", "game": title})

    if props:
        log_to_sheets(props)
        print(f"[OK] Logged {len(props)} props to Sheets.")
    else:
        print("[WARN] No props found on page.")

if __name__ == "__main__":
    scrape_props_example()
