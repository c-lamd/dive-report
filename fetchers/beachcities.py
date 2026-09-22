"""Beach Cities Scuba 'current conditions': a dive pro's eyes-on report from Shaw's Cove, Laguna Beach (Shopify page,
server-rendered; the report is the one <table> inside <main>, labels in the left cell, values in the right)."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from fetchers import _http, safe

URL = "https://beachcitiesscuba.com/pages/current-conditions"


def _row(tr) -> str:
    cells = [[d.get_text(" ", strip=True) for d in td.find_all(["div", "p"])] for td in tr.find_all("td")]
    if len(cells) < 2:
        return ""
    labels, values = ([x for x in c if x] for c in cells[:2])
    if len(labels) == len(values):
        return "; ".join(f"{k} {v}" for k, v in zip(labels, values))
    return " ".join(labels) + " " + " / ".join(values)  # ponytail: Location/Date cells hold extra lines (promo, flag); keep them in order


def parse(html: str) -> dict:
    main = BeautifulSoup(html, "html.parser").select_one("main")
    text = "\n".join(r for r in (_row(tr) for tr in main.select("table tr")) if r)[:3000]
    if "Visibility:" not in text:
        raise ValueError("report table not found (layout changed?)")
    m = re.search(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", text)
    return {
        "source": "beachcities", "url": URL,
        "fetched_at": datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%dT%H:%M"),
        "report_date": datetime.strptime(m.group(), "%b %d, %Y").strftime("%Y-%m-%d") if m else None,
        "text": text,
    }


@safe
def fetch() -> dict | None:
    return parse(_http.get(URL))
