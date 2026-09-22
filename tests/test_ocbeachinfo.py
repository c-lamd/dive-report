from pathlib import Path

from fetchers import ocbeachinfo

FIX = Path(__file__).parent / "fixtures" / "ocbeachinfo.html"


def test_parse_fixture():
    out = ocbeachinfo.parse(FIX.read_text(encoding="utf-8"))
    assert out["closures"] == []
    assert out["warnings"] == ["Dana Point Harbor – East end of Baby Beach (updated on 9/18/2026)"]
    assert out["advisories"] == []
    assert out["text"] == ("CLOSURES: none in effect\nWARNINGS: Dana Point Harbor – East end of Baby Beach (updated on 9/18/2026)"
                           "\nADVISORIES: none in effect")
