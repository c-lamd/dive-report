"""One Claude call: structured ocean data + spot config in, per-spot verdicts out as validated JSON."""
import json
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

MODEL = "claude-sonnet-4-6"  # from the PRD. claude-sonnet-5 is newer and cheaper if you want to switch.

SYSTEM = """You are the nightly conditions analyst for one shore-diving spearfisher in Orange County, California.
The diver works early-morning windows only, drives from Irvine, and will hit exactly one spot, so rank honestly.
You receive the spot list and structured data for tomorrow morning: Open-Meteo swell/wind forecast for the
dive window, the latest NDBC buoy observation (ground truth for whether the forecast is drifting), NOAA tide
events, moon/spring-neap, 72 h rain, scraped eyes-on visibility reports, and OC water-quality closures.

Heuristics to apply:
- Long-period S/SSW groundswell (> 12 s and > 2 ft) stirs sand-bottom spots for 2-3 days; reef-adjacent sand
  recovers faster. Turbidity proxy for sand: swell_ft x swell_period_s. Compare the buoy's swell to the forecast.
- Spring tides + mid-flood = worst vis. Neap + slack high early in the window = best.
- Onshore wind builds after ~11 AM; earlier is better. > 10 kn in the window hurts. Offshore NE/E (Santa Ana)
  mornings in fall are the best vis of the year.
- Creek-mouth spots (creek_mouth: true) after > 0.1 in of rain in 72 h = skip.
- Grunion run the night before -> shallow sand (5-15 ft) is worth working for halibut.
- A water-quality CLOSURE covering a spot is an automatic skip; a bacteria WARNING makes it marginal at best;
  a runoff ADVISORY at a creek or storm-drain outlet applies to the creek_mouth spots near it.
- Never recommend a spot whose spearfishing_allowed is false. Never suggest drifting or moving south of Abalone
  Point from Crystal Cove: the Laguna Beach SMR / no-take SMCA runs 5.5 mi from Abalone Point to 3rd Ave in
  South Laguna. Lobster only in season (roughly early Oct to mid-Mar), by hand.
- Eyes-on reports are the strongest signal when fresh and nearby; weigh them over the forecast. Beach Cities
  Scuba reports Shaw's Cove and SpearFactor reports are diver-submitted, mostly Laguna coves: both are a
  visibility proxy for the reef spots to the north and south (Crystal Cove, Little Corona, Salt Creek), not
  for the sand beaches. Each SpearFactor line shows the diver's number and what their model predicted; the
  diver's number is the eyes-on value. DiveViz is usually null. If a report is null say "no vis report" and
  lower confidence. Never invent a report.
- `missing` lists dead sources. Lower confidence; do not fill gaps.
- Direction shorthand: 180-215 = S/SSW, 215-260 = SW/WSW, 260-300 = W/WNW. Buoy directions are compass strings.
- Data quirks: the forecast's wind_wave_ft is always 0 near shore, so judge wind chop from wind_kn / gust_kn and
  the buoy. At Crystal Cove and Little Corona the forecast's swell/wind-sea split is unstable; trust buoy 46256
  and wave_period_s (total sea) there. Buoy rows are ~30-60 min old at run time and describe now, not tomorrow.

Output rules: spot names exactly as configured. best_window is a clock range inside the dive window with the
tide state ("7:15-9:00, slack high 7:40"); empty for skips. why <= 25 words in the terse style
"SSW 1.5ft@9s fading, neap, slack high 7:40". tag = 2-4 words for the SMS ("sand still stirred", "runoff",
"S swell"). species_note <= 15 words and only when a target species is genuinely in play. top_pick is the one
spot worth the drive, or "none". one_line_summary <= 30 words."""


class SpotVerdict(BaseModel):
    spot: str = Field(description="exact spot name from the config")
    vis_estimate_ft: int
    verdict: Literal["go", "marginal", "skip"]
    best_window: str = Field(description='clock range + tide state inside the dive window, e.g. "7:15-9:00, slack high 7:40"; empty for skip')
    why: str = Field(description="<= 25 words")
    tag: str = Field(description="2-4 word reason for the SMS, e.g. 'sand still stirred', 'runoff', 'S swell'")
    species_note: str = Field(default="", description="<= 15 words; empty unless a target species is genuinely in play")


class Brief(BaseModel):
    spots: list[SpotVerdict]
    top_pick: str = Field(description="exact spot name, or 'none'")
    one_line_summary: str = Field(description="<= 30 words")


def analyze(data: dict, spots: list[dict]) -> Brief:
    client = anthropic.Anthropic()
    user = "SPOTS:\n" + json.dumps(spots, indent=1) + "\n\nDATA:\n" + json.dumps(data, indent=1, default=str)
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": user}],
        output_format=Brief,
    )
    if resp.parsed_output is None:
        raise RuntimeError(f"no structured output (stop_reason={resp.stop_reason})")
    return resp.parsed_output
