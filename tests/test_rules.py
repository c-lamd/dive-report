from datetime import datetime

import rules
from analyze import Brief

DAY = "2026-09-25"
W0 = datetime.fromisoformat(f"{DAY}T06:00")
REEF = {"name": "Reefy", "lat": 0, "lon": 0, "facing_deg": 225, "bottom": ["reef", "sand"], "species": ["calico", "sheephead"],
        "spearfishing_allowed": True, "creek_mouth": False, "buoy": "46224", "tide_station": "9410580"}
SAND = {**REEF, "name": "Sandy", "bottom": ["sand"], "species": ["halibut"], "creek_mouth": True}
SHADOW = {**SAND, "name": "Shadowed", "shadow_deg": [165, 215], "creek_mouth": False}


def hours(swell_ft=1.0, period=10.0, sdir=200, wind_kn=2.0, wind_dir=40):
    return [{"time": f"{DAY}T{h:02d}:00", "wave_ft": swell_ft, "wave_period_s": period, "swell_ft": swell_ft,
             "swell_period_s": period, "swell_dir": sdir, "wind_wave_ft": 0.0, "wind_kn": wind_kn, "wind_dir": wind_dir,
             "gust_kn": wind_kn} for h in range(5, 12)]


def data(**over):
    d = {"target_date": DAY, "dive_window": ["06:00", "10:00"],
         "marine": {s["name"]: {"hours": hours(), "rain_72h_in": 0.0, "recent_swell_max": None} for s in (REEF, SAND, SHADOW)},
         "buoys": {"46224": None},
         "tides": {"9410580": {"station": "9410580", "range_ft": 4.0, "events": [
             {"time": f"{DAY}T01:30", "height_ft": 1.0, "type": "L"}, {"time": f"{DAY}T07:45", "height_ft": 4.5, "type": "H"},
             {"time": f"{DAY}T13:30", "height_ft": 1.5, "type": "L"}, {"time": f"{DAY}T19:45", "height_ft": 5.0, "type": "H"}]}},
         "moon": {"phase": "first quarter", "spring_neap": "neap", "grunion_run_night_before": False},
         "vis_reports": {"beachcities": {"text": "Visibility: 15ft +", "report_date": DAY},
                         "spearfactor": {"text": "09/24 19:00 Shaw's: 14 ft vis (model said 13-18 ft)", "report_date": DAY}, "diveviz": None},
         "water_quality": {"closures": [], "warnings": [], "advisories": []}}
    d.update(over)
    return d


def one(d, spot):
    return rules.analyze(d, [spot]).spots[0]


def test_glassy_neap_slack_high_is_go():
    b = rules.analyze(data(), [REEF, SAND])
    assert isinstance(b, Brief) and b.top_pick == "Reefy"
    reef = b.spots[0]
    assert reef.verdict == "go" and reef.vis_estimate_ft >= 14 and reef.best_window == "6:30-8:45, slack high 7:45"
    assert reef.species_note.startswith("Calico") and reef.tag == "clean" and "eyes-on 14ft" in reef.why


def test_eyes_on_parser_and_staleness():
    assert rules.eyes_on(data()["vis_reports"], W0) == 14.5
    assert rules.eyes_on({"d": {"text": "Visibility: 10-20 feet Surf: 1-3 feet"}}, W0) == 15
    assert rules.eyes_on({"x": None, "y": {"text": "Waves: 2-3ft; Surge: Light"}, "z": {"text": None}}, W0) is None
    stale = "09/20 15:30 Crescent Bay: 25 ft vis\n09/24 19:59 Shaw's: 6 ft vis\n09/13 10:00 Emerald: 30 ft vis"
    assert rules.eyes_on({"sf": {"text": stale}}, W0) == 6


def test_hard_gates_lead_the_why():
    d = data()
    d["marine"]["Sandy"]["rain_72h_in"] = 0.4
    d["water_quality"]["closures"] = ["Reefy State Beach - sewage spill"]
    b = rules.analyze(d, [REEF, SAND])
    assert [(s.verdict, s.tag) for s in b.spots] == [("skip", "water closure"), ("skip", "runoff")]
    assert b.spots[0].why.startswith("water closure") and b.spots[1].why.startswith("runoff, 0.40in rain/72h")
    assert b.top_pick == "none" and b.spots[0].best_window == "" and "Best of a bad lot" not in b.one_line_summary
    assert one(data(), {**REEF, "spearfishing_allowed": False}).tag == "no-take"


def test_advisory_and_warning_cap_at_marginal():
    d = data(); d["water_quality"]["advisories"] = ["Dana Point - 75 feet either side of Sandy Creek outlet"]
    s = one(d, SAND)
    assert (s.verdict, s.tag) == ("marginal", "runoff advisory") and s.why.startswith("runoff advisory")
    d = data(); d["water_quality"]["warnings"] = ["Reefy State Beach - bacteria"]
    s = one(d, REEF)
    assert (s.verdict, s.tag) == ("marginal", "bacteria warning") and s.best_window


def test_groundswell_trashes_sand_but_shadow_and_reef_help():
    d = data()
    for n in d["marine"]:
        d["marine"][n]["hours"] = hours(swell_ft=3.0, period=16.0, sdir=195)
    reef, sand, shadow = rules.analyze(d, [REEF, SAND, SHADOW]).spots
    assert sand.verdict == "skip" and sand.tag == "S swell"
    assert shadow.vis_estimate_ft > sand.vis_estimate_ft and "shadowed" in shadow.why
    assert reef.vis_estimate_ft > sand.vis_estimate_ft
    d["vis_reports"]["beachcities"]["text"] = "Visibility: 25ft +"  # a great Laguna report must not lift open sand to go
    d["vis_reports"]["spearfactor"] = None
    assert one(d, SAND).verdict != "go"


def test_buoy_override_and_lingering_groundswell():
    calm = one(data(), SAND)
    d = data(); d["buoys"]["46224"] = {"swell_ft": 3.5, "swell_period_s": 17.0, "swell_dir": "SSW", "wind_wave_ft": 0.5, "wind_wave_dir": "WNW"}
    hot = one(d, SAND)
    assert hot.vis_estimate_ft < calm.vis_estimate_ft and "buoy 3.5ft@17s" in hot.why
    d = data(); d["marine"]["Sandy"]["recent_swell_max"] = {"time": "2026-09-24T03:00", "swell_ft": 3.0, "swell_period_s": 15.0, "swell_dir": 200}
    s = one(d, SAND)
    assert "sand still stirred" in s.why and s.verdict != "go" and s.vis_estimate_ft < calm.vis_estimate_ft
    d["marine"]["Sandy"]["recent_swell_max"] = {"time": "2026-09-24T03:00", "swell_ft": 2.5, "swell_period_s": 8.0, "swell_dir": 200}
    assert "stirred" not in one(d, SAND).why  # short-period wind swell does not linger
    d["marine"]["Sandy"]["recent_swell_max"] = {"time": None, "swell_ft": None, "swell_period_s": 15.0, "swell_dir": 200}
    assert one(d, SAND).vis_estimate_ft == calm.vis_estimate_ft


def test_north_wind_wave_is_offshore_not_chop():
    d = data(); d["buoys"]["46224"] = {"swell_ft": 0.5, "swell_period_s": 8.0, "swell_dir": "SSW", "wind_wave_ft": 3.0, "wind_wave_dir": "N"}
    assert one(d, REEF).vis_estimate_ft == one(data(), REEF).vis_estimate_ft
    d["buoys"]["46224"]["wind_wave_dir"] = "SW"
    assert one(d, REEF).vis_estimate_ft < one(data(), REEF).vis_estimate_ft


def test_spring_flood_and_onshore_wind_hurt():
    d = data()
    d["moon"]["spring_neap"] = "spring"
    d["tides"]["9410580"]["events"] = [{"time": f"{DAY}T04:30", "height_ft": -0.5, "type": "L"}, {"time": f"{DAY}T11:15", "height_ft": 6.5, "type": "H"},
                                       {"time": f"{DAY}T17:00", "height_ft": 1.0, "type": "L"}, {"time": f"{DAY}T23:00", "height_ft": 5.5, "type": "H"}]
    for n in d["marine"]:
        d["marine"][n]["hours"] = hours(wind_kn=14.0, wind_dir=230)
    s = one(d, REEF)
    assert s.verdict != "go" and s.tag in ("onshore wind", "spring flood") and s.best_window == "6:00-8:00, before the wind"
    assert "wind 14kn SW" in s.why and "mid-flood 100%" in s.why
    d = data()
    for n in d["marine"]:
        d["marine"][n]["hours"] = hours(wind_kn=8.0, wind_dir=45)  # offshore NE: Santa Ana morning
    assert one(d, REEF).vis_estimate_ft > one(data(), REEF).vis_estimate_ft


def test_everything_missing_still_produces_a_brief():
    d = {"target_date": DAY, "dive_window": ["06:00", "10:00"], "marine": None, "buoys": {"46224": None},
         "tides": {"9410580": None}, "moon": {}, "vis_reports": {}, "water_quality": None}
    b = rules.analyze(d, [REEF, SAND, {**REEF, "name": "Bare", "species": None, "bottom": None, "wq_match": None}])
    assert b.top_pick == "none"
    assert all(s.verdict == "marginal" and s.tag == "no forecast" and s.why.startswith("no forecast") and "no vis report" in s.why for s in b.spots)
    assert b.one_line_summary.startswith("Nothing worth the drive")


def test_species_notes():
    d = data(); d["moon"]["grunion_run_night_before"] = True
    assert one(d, SAND).species_note.startswith("Grunion")
    d["marine"]["Sandy"]["rain_72h_in"] = 0.5
    assert one(d, SAND).species_note == ""  # never on a skip
    assert one(data(), {**REEF, "species": []}).species_note == ""
