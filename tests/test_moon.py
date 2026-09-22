from datetime import date

from fetchers import moon


def test_known_phases():
    full = moon.info(date(2024, 1, 25))  # full moon 2024-01-25 17:54 UTC
    assert full["phase"] == "full" and full["spring_neap"] == "spring" and full["illumination"] > 0.98
    quarter = moon.info(date(2024, 1, 18))  # first quarter 2024-01-18 03:53 UTC
    assert quarter["phase"] == "first quarter" and quarter["spring_neap"] == "neap"
    assert moon.info(date(2024, 1, 21))["spring_neap"] == "mid"


def test_grunion():
    # new moon 2024-06-06 12:38 UTC -> run nights Jun 6-9 -> flagged on the mornings of Jun 7-10
    assert moon.info(date(2024, 6, 7))["grunion_run_night_before"]
    assert moon.info(date(2024, 6, 10))["grunion_run_night_before"]
    assert not moon.info(date(2024, 6, 11))["grunion_run_night_before"]
    assert not moon.info(date(2024, 1, 26))["grunion_run_night_before"]  # full moon, but off-season
