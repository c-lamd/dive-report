"""OC Health Care Agency ocean/bay water closures, warnings and runoff advisories (ocbeachinfo.com, WordPress).
Each block is <div id="closures|warnings|advisories">: a blurb paragraph, then one <p> per posting or a
'No ... are currently in effect.' sentence."""
import re

from bs4 import BeautifulSoup

from fetchers import _http, safe

URL = "https://ocbeachinfo.com/"


def _items(block) -> list[str]:
    items = [p.get_text(" ", strip=True) for p in block.find_all(["p", "li"])]
    items = [t for t in items if t and "Click a" not in t]  # "Click a closure/posting/advisory when displayed..." = fixed blurb
    return [] if any(re.match(r"No .*currently in effect", t) for t in items) else items


def parse(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out = {k: _items(soup.select_one(f"#{k}")) for k in ("closures", "warnings", "advisories")}
    out["text"] = "\n".join(f"{k.upper()}: " + ("; ".join(v) or "none in effect") for k, v in out.items())[:3000]
    return out


@safe
def fetch() -> dict | None:
    return parse(_http.get(URL))
