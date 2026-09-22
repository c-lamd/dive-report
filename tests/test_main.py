from datetime import date

from main import fresh

DAY = date(2026, 9, 23)


def test_fresh_gate():
    ok = {"source": "x", "report_date": "2026-09-20", "text": "t"}
    assert fresh(ok, DAY) is ok
    assert fresh({"source": "x", "report_date": "2026-09-19", "text": "t"}, DAY) is None
    assert fresh({"source": "x", "report_date": None, "text": "t"}, DAY)["text"] == "t"
    assert fresh(None, DAY) is None
