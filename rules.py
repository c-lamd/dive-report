"""Deterministic analysis: the PRD heuristics as a scoring rule set. Same Brief as analyze.py, no API key.

vis = eyes-on visibility (median of the fresh Laguna-area reports, or a 10 ft baseline; sand beaches take the
      baseline minus 2 and inherit a report only when it is worse) - swell energy reaching the bottom type
      - tide phase - onshore wind - lingering groundswell + slack-high / offshore-wind bonuses.
Hard gates (no-take, water closure, creek-mouth runoff) force a skip. Caps (bacteria warning, runoff advisory,
strong onshore wind, trashing groundswell on sand, no forecast) hold a spot at marginal.
Every knob is a module constant; tune them against briefs/*.md once real mornings come in."""
import math
import re
import statistics
from collections import Counter
from datetime import datetime, timedelta

from analyze import Brief, SpotVerdict

BASE_VIS = 10.0       # ft on an unremarkable OC reef morning with no eyes-on report
SAND_DISCOUNT = 2.0   # ft: sand beaches run dirtier than the Laguna reefs the reports describe
GO, MARGINAL = 10, 6  # ft thresholds
REPORT_AGE_DAYS = 3   # report lines older than this before the dive day are ignored (same as main.MAX_REPORT_AGE)
RUNOFF_IN = 0.1       # 72 h rain that makes a creek-mouth spot a skip
CALM_E = 12.0         # swell_ft x period_s that costs nothing (1 ft @ 12 s)
E_PER_FT = 0.3        # ft of vis lost per unit of swell energy above CALM_E on open sand
GROUNDSWELL_E = 24.0  # > 2 ft @ 12 s: the sand-trashing groundswell from the PRD
GALE_KN = 12          # mean onshore wind that caps a spot at marginal
BOTTOM = {"reef": 0.6, "kelp": 0.6, "mixed": 0.8, "sand": 1.0}  # share of swell energy that reaches the vis
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
DEG = {c: i * 22.5 for i, c in enumerate(COMPASS)}
VIS_RE = [re.compile(r"Visibility:\s*(\d+)(?:\s*-\s*(\d+))?\s*(?:ft|feet)", re.I),  # Beach Cities, DiveViz
          re.compile(r"(\d+)()\s*ft vis\b", re.I)]                                    # SpearFactor lines


def ang(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def compass(d):
    return COMPASS[int((d + 11.25) // 22.5) % 16]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def hm(t):
    return f"{t.hour}:{t.minute:02d}"


def fresh_lines(text, day):
    """Drop report lines whose leading MM/DD (SpearFactor) is older than REPORT_AGE_DAYS before the dive day."""
    keep = []
    for line in (text or "").splitlines():
        m = re.match(r"(\d\d)/(\d\d)", line)
        try:
            d = datetime(day.year, int(m[1]), int(m[2])) if m else None
        except ValueError:
            d = None
        if d and d > day:
            d = d.replace(year=day.year - 1)  # a December line read in January
        if d is None or (day - d).days <= REPORT_AGE_DAYS:
            keep.append(line)
    return "\n".join(keep)


def eyes_on(reports, day):
    """Median of every visibility number in the fresh eyes-on reports (ft), or None. All are Laguna-area proxies."""
    vals = [(int(a) + int(b or a)) / 2 for r in (reports or {}).values() if r
            for rx in VIS_RE for a, b in rx.findall(fresh_lines(r.get("text"), day))]
    return statistics.median(vals) if vals else None


def mentions(spot, items):
    """Does any water-quality posting name the spot ('Salt Creek', 'Doheny', 'San Juan Creek'...)?"""
    keys = [k.strip().lower() for k in re.split(r"[/()]", spot["name"]) if k.strip()] + [k.lower() for k in spot.get("wq_match") or []]
    return any(k in i.lower() for i in items or [] for k in keys)


def exposure(spot, direction):
    """Share of a swell from `direction` that reaches the beach: headland shadow and glancing angles cut it."""
    if direction is None:
        return 1.0
    arc = spot.get("shadow_deg")
    shadowed = bool(arc) and (direction - arc[0]) % 360 <= (arc[1] - arc[0]) % 360
    return (0.35 if shadowed else 1.0) * (0.6 if ang(direction, spot["facing_deg"]) > 80 else 1.0)


def tide_plan(tide, w0, w1):
    """(high, share of the window within 75 min of it, low near the window, share of the window that is mid-flood)."""
    if not tide or not tide.get("events"):
        return None, 0.0, None, 0.0
    ev = [(datetime.fromisoformat(e["time"]), e["type"]) for e in tide["events"]]
    ev = [(ev[0][0] - timedelta(hours=6, minutes=12), "L" if ev[0][1] == "H" else "H")] + ev  # ponytail: synthesized neighbour before the day's first event
    samples = [w0 + timedelta(minutes=15 * i) for i in range(int((w1 - w0) / timedelta(minutes=15)) + 1)]
    near, hour = timedelta(minutes=75), timedelta(hours=1)
    high = max((t for t, k in ev if k == "H"), key=lambda t: sum(abs(s - t) <= near for s in samples), default=None)
    slack = sum(abs(s - high) <= near for s in samples) / len(samples) if high else 0.0
    low = next((t for t, k in ev if k == "L" and w0 - timedelta(minutes=45) <= t <= w1 + timedelta(minutes=45)), None)

    def mid_flood(t):
        prev = max((e for e in ev if e[0] <= t), key=lambda e: e[0], default=None)
        nxt = min((e for e in ev if e[0] > t), key=lambda e: e[0], default=None)
        return bool(prev and nxt and prev[1] == "L" and t - prev[0] > hour and nxt[0] - t > hour)

    return high, slack, low, sum(map(mid_flood, samples)) / len(samples)


def wind(hours, spot):
    """(mean kn, mid-window direction, onshore kn above 4 weighted by angle, same offshore) over the window."""
    hs = [h for h in hours if h.get("wind_kn") is not None and h.get("wind_dir") is not None]
    if not hs:
        return None, None, 0.0, 0.0
    cos = [math.cos(math.radians(ang(h["wind_dir"], spot["facing_deg"]))) for h in hs]
    on = mean(max(0.0, h["wind_kn"] - 4) * max(0.0, c) for h, c in zip(hs, cos))
    off = mean(max(0.0, h["wind_kn"] - 4) * max(0.0, -c) for h, c in zip(hs, cos))
    return mean(h["wind_kn"] for h in hs), hs[len(hs) // 2]["wind_dir"], on, off


def judge(spot, data, w0, w1, eyes):
    """One spot -> SpotVerdict. Named gates, caps and penalties so the tag and why explain the verdict."""
    m = (data.get("marine") or {}).get(spot["name"]) or {}
    lo, hi = w0.strftime("%H:%M"), w1.strftime("%H:%M")
    hours = [h for h in m.get("hours") or [] if lo <= h["time"][11:] <= hi]
    wq = data.get("water_quality") or {}
    buoy = (data.get("buoys") or {}).get(spot["buoy"]) or {}
    moon = data.get("moon") or {}
    bt = spot.get("bottom") or []
    species = set(spot.get("species") or [])
    bottom = min((BOTTOM.get(b, 1.0) for b in bt), default=1.0)
    sandy = not {"reef", "kelp"} & set(bt)
    gates, caps, pen, bonus, why = [], [], {}, 0.0, []

    if not spot.get("spearfishing_allowed", True):
        gates.append("no-take")
    if mentions(spot, wq.get("closures")):
        gates.append("water closure")
    rain = m.get("rain_72h_in")
    if spot.get("creek_mouth"):
        if rain is not None and rain > RUNOFF_IN:
            gates.append("runoff")
            why.append(f"{rain:.2f}in rain/72h")
        elif mentions(spot, wq.get("advisories")):
            caps.append("runoff advisory")
    if mentions(spot, wq.get("warnings")):
        caps.append("bacteria warning")

    # swell: forecast energy over the window, replaced by the buoy when it runs hotter (forecast drifting)
    fc = [h for h in hours if None not in (h.get("swell_ft"), h.get("swell_period_s"), h.get("swell_dir"))]
    e, swell_dir = None, DEG.get(buoy.get("swell_dir"))
    if fc:
        mid = fc[len(fc) // 2]
        swell_dir = mid["swell_dir"]
        e = mean(h["swell_ft"] * h["swell_period_s"] * exposure(spot, h["swell_dir"]) for h in fc)
        why.append(f"{compass(swell_dir)} {mean(h['swell_ft'] for h in fc):.1f}ft@{mean(h['swell_period_s'] for h in fc):.0f}s"
                   + (" shadowed" if exposure(spot, swell_dir) < 1 else ""))
    if buoy.get("swell_ft") and buoy.get("swell_period_s"):
        be = buoy["swell_ft"] * buoy["swell_period_s"] * exposure(spot, DEG.get(buoy.get("swell_dir")))
        if e is None or be > 1.3 * e:
            e = be
            why.append(f"buoy {buoy['swell_ft']}ft@{buoy['swell_period_s']:.0f}s")
    label = "S swell" if swell_dir is not None and 150 <= swell_dir <= 235 else "swell"
    if e is not None and e > CALM_E:
        pen[label] = (e - CALM_E) * E_PER_FT * bottom
        if sandy and e > GROUNDSWELL_E:
            caps.append(label)  # a trashing groundswell keeps sand off the go list whatever the reefs report
    r = m.get("recent_swell_max") or {}
    if None not in (r.get("swell_ft"), r.get("swell_period_s"), r.get("time")) and r["swell_ft"] > 2 and r["swell_period_s"] > 12:
        recent = r["swell_ft"] * r["swell_period_s"] * exposure(spot, r.get("swell_dir"))
        if recent > GROUNDSWELL_E and recent > 1.3 * (e or 0):  # peaked already and not still in the forecast: no double count
            stirred = "sand still stirred" if sandy else "stirred"
            pen[stirred] = 3.0 if sandy else 1.0
            why.append(f"{stirred} by {r['swell_ft']:.1f}ft@{r['swell_period_s']:.0f}s {r['time'][5:10]}")
            if sandy:
                caps.append(stirred)
    wwd = DEG.get(buoy.get("wind_wave_dir"))
    if (buoy.get("wind_wave_ft") or 0) > 2 and wwd is not None and ang(wwd, spot["facing_deg"]) < 70:
        pen["wind chop"] = 1.5

    # wind: onshore costs, offshore (fall Santa Ana mornings) pays
    kn, wd, on, off = wind(hours, spot)
    if kn is not None:
        if kn >= 5:
            why.append(f"wind {kn:.0f}kn {compass(wd)}")
        if on > 0:
            pen["onshore wind"] = on * 0.6
        if on > GALE_KN - 4:
            caps.append("onshore wind")
        bonus += min(2.0, off * 0.5)

    # tide: slack high inside the window is best, spring mid-flood is worst
    high, slack, low, flood = tide_plan((data.get("tides") or {}).get(spot["tide_station"]), w0, w1)
    sn = moon.get("spring_neap")
    if sn:
        why.append(sn)
    if slack >= 0.25:  # at least an hour of the window within 75 min of the high
        bonus += (2.5 if sn == "neap" else 1.5) * min(1.0, slack / 0.6)
        window = f"{hm(max(w0, high - timedelta(minutes=75)))}-{hm(min(w1, high + timedelta(hours=1)))}, slack high {hm(high)}"
    elif low:
        window = f"{hm(max(w0, low - timedelta(minutes=45)))}-{hm(min(w1, low + timedelta(hours=1)))}, slack low {hm(low)}"
    else:
        window = f"{hm(w0)}-{hm(w0 + timedelta(hours=2))}, before the wind"
    if flood > 0.3:
        pen["spring flood" if sn == "spring" else "mid-flood"] = flood * (3.0 if sn == "spring" else 1.5)
        why.append(f"mid-flood {flood:.0%}")

    # baseline: the reports describe Laguna reefs; sand only inherits a bad one
    if eyes is None:
        vis0 = BASE_VIS
        why.append("no vis report")
    elif sandy:
        vis0 = min(BASE_VIS, eyes)
        if eyes < BASE_VIS:
            why.append(f"eyes-on {eyes:.0f}ft")
    else:
        vis0 = eyes
        why.append(f"eyes-on {eyes:.0f}ft")
    if sandy:
        vis0 -= SAND_DISCOUNT
    if not hours:
        caps.append("no forecast")

    vis = int(min(30.0, max(2.0, vis0 - sum(pen.values()) + bonus)) + 0.5)  # half-up
    verdict = "skip" if gates or vis < MARGINAL else "go" if vis >= GO else "marginal"
    capped = bool(caps) and verdict == "go"
    if capped:
        verdict = "marginal"
    why[:0] = gates + [c for c in caps if c not in pen]
    tag = (gates[0] if gates else "clean" if verdict == "go"
           else caps[0] if capped or (caps and not pen) else max(pen, key=pen.get, default="low vis"))
    note = ""
    if verdict != "skip":
        if moon.get("grunion_run_night_before") and "halibut" in species and "sand" in bt:
            note = "Grunion ran last night: work 5-15 ft sand for halibut"
        elif verdict == "go" and not sandy and {"calico", "sheephead"} & species:
            note = "Calico/sheephead on the reef edge"
    return SpotVerdict(spot=spot["name"], vis_estimate_ft=vis, verdict=verdict,
                       best_window="" if verdict == "skip" else window, why=", ".join(why), tag=tag, species_note=note)


def analyze(data, spots):
    w0, w1 = (datetime.fromisoformat(f"{data['target_date']}T{t}") for t in data["dive_window"])
    verdicts = [judge(s, data, w0, w1, eyes_on(data.get("vis_reports"), w0)) for s in spots]
    top = max((v for v in verdicts if v.verdict == "go"), key=lambda v: v.vis_estimate_ft, default=None)
    n = Counter(v.verdict for v in verdicts)
    tally = f"{n['go']} go, {n['marginal']} marginal, {n['skip']} skip."
    if top:
        summary = f"{top.spot} is the drive ({top.vis_estimate_ft}ft). {tally}"
    else:
        best = max((v for v in verdicts if v.verdict == "marginal"), key=lambda v: v.vis_estimate_ft, default=None)
        summary = f"Nothing worth the drive: {tally}" + (f" Best of a bad lot: {best.spot} ({best.tag})." if best else "")
    return Brief(spots=verdicts, top_pick=top.spot if top else "none", one_line_summary=summary)
