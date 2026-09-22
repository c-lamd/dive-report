"""DiveViz 'LA - OC Dive Report'. diveviz.com/pages/daily-dive-report is a Shopify shell; the report is the newest post of
the la-and-oc-dive-conditions blog, read via its Atom feed. That blog's newest post is 2019-09-07 (checked 2026-09-22),
so main.fresh() drops it as stale every day; if they ever post again it starts working by itself."""
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from fetchers import _http, safe

URL = "https://www.diveviz.com/blogs/la-and-oc-dive-conditions.atom"
NS = {"a": "http://www.w3.org/2005/Atom"}


def parse(xml: str) -> dict:
    entry = ET.fromstring(xml).find("a:entry", NS)  # Shopify lists newest first
    body = BeautifulSoup(entry.findtext("a:content", "", NS), "html.parser").get_text(" ", strip=True)
    return {
        "source": "diveviz", "url": entry.find("a:link", NS).get("href"),
        "fetched_at": datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%dT%H:%M"),
        "report_date": entry.findtext("a:published", "", NS)[:10],
        "text": f"{entry.findtext('a:title', '', NS)}: {body}"[:3000],
    }


@safe
def fetch() -> dict | None:
    return parse(_http.get(URL))
