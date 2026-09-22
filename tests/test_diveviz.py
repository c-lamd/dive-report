from pathlib import Path

from fetchers import diveviz

FIX = Path(__file__).parent / "fixtures" / "diveviz.atom"


def test_parse_fixture():
    out = diveviz.parse(FIX.read_text(encoding="utf-8"))
    assert out["report_date"] == "2019-09-07"
    assert out["url"] == "https://diveviz.com/blogs/la-and-oc-dive-conditions/saturdays-la-oc-dive-report"
    assert "Visibility: 10-20 feet Surf: 1-3 feet Water temp: 70-75 F" in out["text"]

