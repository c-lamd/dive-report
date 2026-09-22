from pathlib import Path

from fetchers import beachcities

FIX = Path(__file__).parent / "fixtures" / "beachcities.html"


def test_parse_fixture():
    out = beachcities.parse(FIX.read_text(encoding="utf-8"))
    assert out["report_date"] == "2026-09-22"
    assert "Location: Shaw’s Cove, Laguna Beach, California" in out["text"]
    assert "Last Report Time: 9 am; Waves: 1-2ft; Surge: Light" in out["text"]
    assert "Visibility: 10ft +; Temperature: Water 78 °F-- Air 80 °F" in out["text"]
    assert "Navigation Menu" not in out["text"] and len(out["text"]) <= 3000
