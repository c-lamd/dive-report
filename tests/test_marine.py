import json
from datetime import date
from pathlib import Path

from fetchers import marine

FIX = Path(__file__).parent / "fixtures"
SPOTS = [{"name": "Salt Creek", "lat": 33.476, "lon": -117.722}]


def test_parse_fixture():
    sea = json.loads((FIX / "marine.json").read_text())
    air = json.loads((FIX / "marine.wx.json").read_text())
    out = marine.parse(sea, air, SPOTS, date(2026, 9, 23))
    sc = out["Salt Creek"]
    assert [h["time"] for h in sc["hours"]] == [f"2026-09-23T{h:02d}:00" for h in range(5, 12)]
    first = sc["hours"][0]
    assert set(first) == {"time", "wave_ft", "wave_period_s", "swell_ft", "swell_period_s", "swell_dir", "wind_wave_ft",
                          "wind_kn", "wind_dir", "gust_kn"}
    assert (first["wave_ft"], first["swell_ft"], first["swell_period_s"], first["swell_dir"]) == (2.756, 1.837, 12.05, 192)
    assert (first["wind_kn"], first["wind_dir"], first["gust_kn"]) == (3.5, 19, 3.9)
    assert sc["rain_72h_in"] == 0.0
