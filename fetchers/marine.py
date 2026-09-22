"""Open-Meteo marine + forecast (wind, rain): one multi-coordinate call each for every spot."""
import json

from fetchers import safe
from fetchers._http import get

MARINE = "https://marine-api.open-meteo.com/v1/marine"
WX = "https://api.open-meteo.com/v1/forecast"
TZ = "America/Los_Angeles"
WINDOW = ("05:00", "11:00")  # local, inclusive
# output key -> Open-Meteo hourly variable (swell_wave_peak_period is null on this coast, so not asked for)
SEA = {"wave_ft": "wave_height", "wave_period_s": "wave_period", "swell_ft": "swell_wave_height", "swell_period_s": "swell_wave_period",
       "swell_dir": "swell_wave_direction", "wind_wave_ft": "wind_wave_height"}
AIR = {"wind_kn": "wind_speed_10m", "wind_dir": "wind_direction_10m", "gust_kn": "wind_gusts_10m"}


@safe
def fetch(spots, day):
    coords = {"latitude": ",".join(str(s["lat"]) for s in spots),
              "longitude": ",".join(str(s["lon"]) for s in spots), "timezone": TZ, "forecast_days": 7}  # --day up to a week out
    sea = get(MARINE, {**coords, "hourly": ",".join(SEA.values()), "length_unit": "imperial"})
    air = get(WX, {**coords, "hourly": ",".join(AIR.values()), "daily": "precipitation_sum", "past_days": 3,
                   "wind_speed_unit": "kn", "precipitation_unit": "inch"})
    return parse(json.loads(sea), json.loads(air), spots, day)


def parse(sea, air, spots, day):
    """sea/air: Open-Meteo responses in spot order (a bare dict when only one coordinate was asked for)."""
    if isinstance(sea, dict):
        sea, air = [sea], [air]
    out = {}
    for spot, s, a in zip(spots, sea, air):
        sh, ah = s["hourly"], a["hourly"]
        at = {t: i for i, t in enumerate(ah["time"])}
        hours = [{"time": t, **{k: sh[v][i] for k, v in SEA.items()}, **{k: ah[v][at[t]] for k, v in AIR.items()}}
                 for i, t in enumerate(sh["time"]) if t[:10] == day.isoformat() and WINDOW[0] <= t[11:] <= WINDOW[1]]
        # the three calendar days before `day`: with day = tomorrow that is d-2, d-1 and today
        rain = [p or 0 for t, p in zip(a["daily"]["time"], a["daily"]["precipitation_sum"]) if t < day.isoformat()]
        out[spot["name"]] = {"hours": hours, "rain_72h_in": round(sum(rain[-3:]), 2)}
    return out
