"""NOAA CO-OPS high/low tide predictions for one day (MLLW, feet, local standard/daylight time)."""
import json

from fetchers import safe
from fetchers._http import get

URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


@safe
def fetch(station_id, day):
    d = day.strftime("%Y%m%d")
    raw = get(URL, {"product": "predictions", "datum": "MLLW", "station": station_id, "time_zone": "lst_ldt",
                    "units": "english", "interval": "hilo", "format": "json", "begin_date": d, "end_date": d})
    return parse(json.loads(raw), station_id)


def parse(raw, station_id):
    events = [{"time": p["t"].replace(" ", "T"), "height_ft": float(p["v"]), "type": p["type"]}
              for p in raw["predictions"]]
    heights = [e["height_ft"] for e in events]
    return {"station": station_id, "events": events, "range_ft": round(max(heights) - min(heights), 2)}
