from pathlib import Path

from fetchers import spearfactor

FIX = Path(__file__).parent / "fixtures" / "spearfactor.json"


def test_parse_fixture():
    out = spearfactor.parse(FIX.read_text(encoding="utf-8"))
    assert out["report_date"] == "2026-09-21"
    assert out["text"].startswith("09/21 15:30 Crescent Bay: 13 ft vis (model said 10-15 ft (deep 15-24)) - 9/21 3:30pm: 10-20 milky")
    assert "09/21 15:30 Laguna Beach (Shaw's / Diver's Cove): 20 ft vis" in out["text"]
    assert len(out["text"]) <= 3000


def test_parse_empty():
    assert spearfactor.parse('{"reports": []}')["text"].startswith("No diver reports")
