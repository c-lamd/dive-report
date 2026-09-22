from datetime import date

from analyze import Brief, SpotVerdict
from notify import CAP, format_sms, septets

DAY = date(2026, 9, 23)  # a Wednesday


def _brief(top_pick="Salt Creek"):
    return Brief(
        spots=[
            SpotVerdict(spot="Salt Creek", vis_estimate_ft=12, verdict="go", best_window="7:15-9:00, slack high 7:40",
                        why="SSW 1.5ft@9s fading, neap, slack high 7:40", tag="clean reef",
                        species_note="Calico/sheephead on reef edge; skip sand"),
            SpotVerdict(spot="Calafia / Riviera", vis_estimate_ft=6, verdict="marginal", best_window="",
                        why="Sand still stirred from the weekend SSW.", tag="sand still stirred"),
            SpotVerdict(spot="Doheny", vis_estimate_ft=3, verdict="skip", best_window="", why="Creek runoff.", tag="runoff"),
        ],
        top_pick=top_pick,
        one_line_summary="Salt Creek is the drive; everything else is stirred.",
    )


def test_matches_prd_shape():
    sms = format_sms(_brief(), DAY)
    assert sms.startswith("Wed AM: GO - Salt Creek. Vis ~12ft. SSW 1.5ft@9s fading, neap, slack high 7:40. Calico")
    assert "\nMarginal: Calafia / Riviera (sand still stirred). Skip: Doheny (runoff)." in sms
    assert len(sms) <= CAP and sms.isascii()


def test_cap_enforced():
    b = _brief()
    b.spots[0].why = "word " * 100
    assert len(format_sms(b, DAY)) <= CAP


def test_all_skip():
    b = _brief(top_pick="none")
    for s in b.spots:
        s.verdict = "skip"
    sms = format_sms(b, DAY)
    assert sms.startswith("Wed AM: SKIP. Salt Creek is the drive")
    assert "Skip: Salt Creek (clean reef), Calafia / Riviera (sand still stirred), Doheny (runoff)." in sms


def test_gsm_sanitized_and_top_pick_fallback():
    b = _brief(top_pick="Crystal Cove")  # not an exact spot name -> fall back to the first "go"
    b.spots[0].why = "SSW 1.5ft@9s — fading… 78°F, “clean”"
    sms = format_sms(b, DAY)
    assert sms.startswith("Wed AM: GO - Salt Creek.")
    assert 'SSW 1.5ft@9s - fading... 78F, "clean".' in sms and sms.isascii()
    assert septets(sms) <= CAP
