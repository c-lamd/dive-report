"""Data fetchers. One module per source, one public function per module.

CONTRACT (every module in this package)
  - Decorate the public function with @safe. It returns None on ANY failure and never raises.
    A dead source degrades the brief; it does not kill it. analyze.py is told what is missing.
  - Return only json.dumps-able values (dict/list/str/float/int/bool/None).
  - Imperial units: ft, knots, inches, degF. Directions in degrees true (0-360).
  - Times as local ISO strings "YYYY-MM-DDTHH:MM" in America/Los_Angeles unless noted.
  - All network I/O goes through fetchers._http (get / post_json). No other HTTP library.
  - Keep a recorded fixture of the raw upstream payload in tests/fixtures/<module>.* and a
    test that parses it, so a site layout change is a failing test, not a silent None.

SIGNATURES
  marine.fetch(spots: list[dict], day: date) -> dict | None
      Open-Meteo marine + forecast APIs (multi-coordinate: one call each). Keyed by spot name:
      {"<spot name>": {"hours": [{"time", "wave_ft", "wave_period_s", "swell_ft", "swell_period_s", "swell_dir",
                                  "wind_wave_ft", "wind_kn", "wind_dir", "gust_kn"}, ...],   # 05:00-11:00 local on `day`
                       "rain_72h_in": float}}
      Notes: swell_wave_peak_period is null for this coast; wind_wave_ft is 0.0 near shore (use wind_kn);
      the swell/wind-sea partition is unstable at the Newport spots, so wave_period_s (total sea) is included.
  ndbc.fetch(buoy_id: str) -> dict | None
      Newest row of https://www.ndbc.noaa.gov/data/realtime2/<id>.spec (fall back to .txt if .spec is 404).
      {"buoy", "time", "wvht_ft", "swell_ft", "swell_period_s", "swell_dir", "wind_wave_ft",
       "wind_wave_period_s", "wind_wave_dir", "apd_s", "mwd_deg", "steepness"}   # "MM" -> None
      swell_dir / wind_wave_dir are compass strings ("SSW"); mwd_deg is degrees. .txt rows have no swell split.
  tides.fetch(station_id: str, day: date) -> dict | None
      NOAA CO-OPS hi/lo predictions for `day`, MLLW, feet, lst_ldt.
      {"station", "events": [{"time", "height_ft", "type": "H"|"L"}], "range_ft"}
  moon.info(day: date) -> dict            # pure computation, never None
      {"phase", "illumination", "spring_neap": "spring"|"neap"|"mid", "days_from_syzygy",
       "grunion_run_night_before": bool}    # night preceding `day`
  spearfactor.fetch() -> dict | None
  diveviz.fetch() -> dict | None
  beachcities.fetch() -> dict | None
      {"source", "url", "fetched_at", "report_date": "YYYY-MM-DD" | None, "text": str}   # main.fresh() parses report_date
      text = cleaned visible report text relevant to LA/OC only, <= 3000 chars, no nav/menu chrome.
  ocbeachinfo.fetch() -> dict | None
      {"closures": [str], "warnings": [str], "advisories": [str], "text": str}   # empty lists when none in effect
      closures = sewage/hazard (automatic no-go), warnings = bacteria postings, advisories = runoff at creek mouths.
"""
import functools
import logging

log = logging.getLogger("spearo")


def safe(fn):
    """Any exception -> None plus one warning line. The single failure guard for all fetchers."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 - deliberate catch-all at the trust boundary
            log.warning("%s failed: %s: %s", fn.__module__, type(e).__name__, e)
            return None
    return wrapper
