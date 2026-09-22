"""Newest NDBC realtime2 row: <id>.spec (swell / wind-wave split), falling back to <id>.txt."""
import urllib.error
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fetchers import safe
from fetchers._http import get

URL = "https://www.ndbc.noaa.gov/data/realtime2/"
# output key -> NDBC column
COLS = {"wvht_ft": "WVHT", "swell_ft": "SwH", "swell_period_s": "SwP", "swell_dir": "SwD",
        "wind_wave_ft": "WWH", "wind_wave_period_s": "WWP", "wind_wave_dir": "WWD",
        "apd_s": "APD", "mwd_deg": "MWD", "steepness": "STEEPNESS"}
METRES = ("wvht_ft", "swell_ft", "wind_wave_ft")


@safe
def fetch(buoy_id):
    try:
        text = get(f"{URL}{buoy_id}.spec")
    except urllib.error.HTTPError:  # some buoys publish no .spec (46242 today)
        text = get(f"{URL}{buoy_id}.txt")
    return parse(text, buoy_id)


def num(v):
    """'MM' or 'N/A' -> None; numbers -> float; compass strings and STEEPNESS unchanged."""
    if v in (None, "MM", "N/A"):
        return None
    try:
        return float(v)
    except ValueError:
        return v


def parse(text, buoy_id):
    """Two '#' header lines, then rows newest first. Times are UTC, heights metres."""
    lines = text.splitlines()
    row = dict(zip(lines[0].lstrip("#").split(), lines[2].split()))
    row.setdefault("SwP", row.get("DPD"))  # ponytail: .txt has no swell split; dominant period stands in
    utc = datetime(*(int(row[k]) for k in ("YY", "MM", "DD", "hh", "mm")), tzinfo=timezone.utc)
    out = {"buoy": buoy_id, "time": utc.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%dT%H:%M")}
    for key, col in COLS.items():
        out[key] = num(row.get(col))
        if key in METRES and out[key] is not None:
            out[key] = round(out[key] * 3.28084, 1)
    return out
