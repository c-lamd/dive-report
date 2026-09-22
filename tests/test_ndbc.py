from pathlib import Path

from fetchers import ndbc

FIX = Path(__file__).parent / "fixtures"
KEYS = {"buoy", "time", "wvht_ft", "swell_ft", "swell_period_s", "swell_dir", "wind_wave_ft",
        "wind_wave_period_s", "wind_wave_dir", "apd_s", "mwd_deg", "steepness"}


def test_spec_46224():
    out = ndbc.parse((FIX / "ndbc.spec").read_text(), "46224")
    assert set(out) == KEYS
    assert out["time"] == "2026-09-22T10:26"  # 17:26 UTC
    assert (out["wvht_ft"], out["swell_ft"], out["swell_period_s"], out["swell_dir"]) == (3.0, 2.0, 16.7, "SSW")
    assert (out["wind_wave_dir"], out["steepness"], out["apd_s"], out["mwd_deg"]) == ("WNW", "SWELL", 7.0, 209)


def test_txt_fallback_46256():
    out = ndbc.parse((FIX / "ndbc.txt").read_text(), "46256")
    assert set(out) == KEYS
    assert (out["wvht_ft"], out["swell_period_s"], out["apd_s"], out["mwd_deg"]) == (2.0, 12, 5.6, 201)
    assert out["swell_ft"] is None and out["swell_dir"] is None and out["steepness"] is None
