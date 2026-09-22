"""SpearFactor community diver reports for Orange County spots: the 'Recent Reports' panel of conditions.spearfactor.com,
one GET to its workers.dev API. The per-spot viz/fish model itself runs in the browser: /predict {action:"viz"} needs
~20 browser-computed inputs (turbidity, chlorophyll, wave energy, wind, tide state...) and answers result=null without
them, so the model's forecast is not reachable server-side; each report does carry the model's prediction at the time."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from fetchers import _http, safe

URL = "https://spearfactor-api.whitmanbret.workers.dev/reports/public?region=orange&days=3&limit=20"
TZ = ZoneInfo("America/Los_Angeles")
SPOTS = {  # OC spot ids -> names, from the page's LOCATIONS table
    "danapoint": "Dana Point / Salt Creek", "treasureisland": "Goff / Treasure Island (Laguna)",
    "woodscove": "Woods Cove (Laguna)", "laguna": "Laguna Beach (Shaw's / Diver's Cove)", "crescent": "Crescent Bay",
    "emerald": "Emerald Bay", "brooksstreet": "Brooks Street", "crystalcove": "Crystal Cove",
    "newport": "Newport / Corona del Mar", "huntington": "Huntington Cliffs",
}


def _line(r: dict) -> str:
    when = datetime.fromisoformat(r["ts"]).astimezone(TZ).strftime("%m/%d %H:%M")
    temp = f", water {r['waterTemp']}F" if r.get("waterTemp") else ""
    note = f" - {r['notes']}" if r.get("notes") else ""
    return f"{when} {SPOTS.get(r.get('spotId'), r.get('spotId'))}: {r.get('viz')} ft vis (model said {r.get('predictedViz')}){temp}{note}"


def parse(raw: str) -> dict:
    reports = json.loads(raw)["reports"]  # newest first
    return {
        "source": "spearfactor", "url": URL, "fetched_at": datetime.now(TZ).strftime("%Y-%m-%dT%H:%M"),
        "report_date": datetime.fromisoformat(reports[0]["ts"]).astimezone(TZ).strftime("%Y-%m-%d") if reports else None,
        "text": "\n".join(_line(r) for r in reports)[:3000] or "No diver reports for Orange County spots in the past 3 days.",
    }


@safe
def fetch() -> dict | None:  # ponytail: one request per run; the page itself caches this call for 15 min
    return parse(_http.get(URL))
