"""Spearo Brief: collect -> analyze -> write briefs/ -> SMS.

    uv run --env-file .env main.py [--dry-run | --collect-only] [--day YYYY-MM-DD] [--force]
"""
import argparse
import json
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import rules
from analyze import analyze
from fetchers import beachcities, diveviz, marine, moon, ndbc, ocbeachinfo, spearfactor, tides
from notify import format_sms, send_sms

TZ = ZoneInfo("America/Los_Angeles")
ROOT = Path(__file__).parent
BRIEFS = ROOT / "briefs"
log = logging.getLogger("spearo")
MAX_REPORT_AGE = timedelta(days=3)  # an eyes-on report older than this is "no report", never a stale one


def fresh(report: dict | None, day: date) -> dict | None:
    """An eyes-on report older than MAX_REPORT_AGE before the dive day is no report at all."""
    if report and report.get("report_date") and date.fromisoformat(report["report_date"]) < day - MAX_REPORT_AGE:
        log.warning("%s report dated %s is stale -> dropped", report.get("source"), report["report_date"])
        return None
    return report


def collect(cfg: dict, day: date) -> dict:
    spots = cfg["spots"]
    data = {
        "target_date": day.isoformat(),
        "weekday": day.strftime("%A"),
        "dive_window": cfg["dive_window"],
        "generated_at": datetime.now(TZ).isoformat(timespec="minutes"),
        "marine": marine.fetch(spots, day),
        "buoys": {b: ndbc.fetch(b) for b in sorted({s["buoy"] for s in spots})},
        "tides": {t: tides.fetch(t, day) for t in sorted({s["tide_station"] for s in spots})},
        "moon": moon.info(day),
        "vis_reports": {m.__name__.rsplit(".", 1)[-1]: m.fetch() for m in (spearfactor, diveviz, beachcities)},
        "water_quality": ocbeachinfo.fetch(),
    }
    data["vis_reports"] = {k: fresh(r, day) for k, r in data["vis_reports"].items()}
    data["missing"] = [k for k, v in data.items() if v is None] + [
        f"{g}.{k}" for g in ("buoys", "tides", "vis_reports") for k, v in data[g].items() if v is None
    ]
    return data


def run_analysis(data: dict, spots: list[dict], engine: str):
    """engine: claude | rules | auto (claude when ANTHROPIC_API_KEY is set). Claude failures fall back to rules."""
    if engine == "auto":
        engine = "claude" if os.environ.get("ANTHROPIC_API_KEY") else "rules"
    if engine == "claude":
        try:
            return analyze(data, spots), "claude"
        except Exception as e:  # noqa: BLE001 - the brief must still go out
            log.warning("Claude analysis failed (%s: %s); falling back to rules", type(e).__name__, e)
            engine = "rules (claude failed)"
    return rules.analyze(data, spots), engine


def write_brief(day: date, data: dict, brief, sms: str, engine: str) -> None:
    BRIEFS.mkdir(exist_ok=True)
    (BRIEFS / f"{day}.json").write_text(json.dumps({"engine": engine, "data": data, "analysis": brief.model_dump()}, indent=1, default=str))
    rows = "\n".join(
        f"| {s.spot} | {s.verdict} | ~{s.vis_estimate_ft} ft | {s.best_window or '-'} | {s.why} | {s.species_note or '-'} |"
        for s in brief.spots
    )
    (BRIEFS / f"{day}.md").write_text(f"""# Spearo Brief - {day:%A %Y-%m-%d} AM

**SMS ({len(sms)} chars)**

```
{sms}
```

**Top pick:** {brief.top_pick} - {brief.one_line_summary}

| Spot | Verdict | Vis | Window | Why | Species |
|---|---|---|---|---|---|
{rows}

Engine: {engine}. Missing sources: {", ".join(data["missing"]) or "none"}. Raw inputs in `{day}.json`.
""")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--day", type=date.fromisoformat, help="dive morning (default: tomorrow)")
    ap.add_argument("--dry-run", action="store_true", help="everything except sending the SMS")
    ap.add_argument("--collect-only", action="store_true", help="fetch and print the data; no Claude call, no SMS")
    ap.add_argument("--force", action="store_true", help="rerun even if the brief for that day already exists")
    ap.add_argument("--engine", choices=["auto", "claude", "rules"], default="auto",
                    help="auto (default) = claude when ANTHROPIC_API_KEY is set, else the rules engine")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not (a.dry_run or a.collect_only):
        missing = [k for k in ("SMS_TO", "SMTP_USER", "SMTP_PASS") if not os.environ.get(k)]
        if missing:
            ap.error(f"cannot send without {', '.join(missing)} (see .env.example); use --dry-run to skip sending")
    day = a.day or datetime.now(TZ).date() + timedelta(days=1)
    cfg = yaml.safe_load((ROOT / "spots.yaml").read_text())
    sent = BRIEFS / f"{day}.sent"  # written only after a successful send, so dry runs and failed sends never block the real one
    if sent.exists() and not (a.force or a.dry_run or a.collect_only):
        log.info("brief for %s already sent, nothing to do (--force to resend)", day)
        return

    data = collect(cfg, day)
    if data["missing"]:
        log.warning("missing sources: %s", ", ".join(data["missing"]))
    if a.collect_only:
        print(json.dumps(data, indent=1, default=str))
        return

    brief, engine = run_analysis(data, cfg["spots"], a.engine)
    sms = format_sms(brief, day)
    write_brief(day, data, brief, sms, engine)
    print(f"--- SMS ({len(sms)} chars, engine {engine}) ---\n{sms}\n--- wrote {BRIEFS / f'{day}.md'}")
    if a.dry_run:
        return
    send_sms(sms)
    sent.touch()
    log.info("sent to %s", os.environ["SMS_TO"])


if __name__ == "__main__":
    main()
