import json
from pathlib import Path

from fetchers import tides

FIX = Path(__file__).parent / "fixtures"


def test_parse_fixture():
    out = tides.parse(json.loads((FIX / "tides.json").read_text()), "9410580")
    assert out["station"] == "9410580" and len(out["events"]) == 4
    assert out["events"][1] == {"time": "2026-09-23T08:29", "height_ft": 4.512, "type": "H"}
    assert out["range_ft"] == 5.35  # 5.515 - 0.169
