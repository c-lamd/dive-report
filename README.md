# Spearo Brief

Daily 6 PM text with tomorrow-morning spearfishing conditions and a go / marginal / skip read for a preset list
of Orange County shore spots. One SMS, one markdown file. PRD: `spearo-brief-prd.md` (kept outside the repo).

**Laguna Beach is no-take** (Laguna Beach SMR and the adjacent SMCAs). It is deliberately not in `spots.yaml`;
Beach Cities Scuba's Shaw's Cove report is used only as a regional visibility signal.

## Run it locally

```
uv sync
cp .env.example .env            # fill in the four values
uv run --env-file .env main.py --collect-only   # fetch every source, print the JSON, no Claude, no SMS
uv run --env-file .env main.py --dry-run        # + Claude analysis + briefs/<date>.md, prints the SMS
uv run --env-file .env main.py                  # + sends the SMS, then writes briefs/<date>.sent so reruns are no-ops
uv run pytest                                   # fixture-based tests for every fetcher + the SMS formatter
```

`--day 2026-09-27` targets another morning (up to a week out). `--force` resends. Every fetcher returns `None` on failure and the
analysis is told what is missing, so a dead site degrades the brief instead of killing it.

## Free SMS (no Twilio)

`notify.py` emails the text to your carrier's email-to-SMS gateway from a Gmail account. Cost: zero.

| Carrier | `SMS_TO` |
|---|---|
| Verizon / Visible | `<10 digits>@vtext.com` (SMS, split at 160 chars) or `@vzwpix.com` (MMS, arrives as one bubble) |
| T-Mobile / Mint / Metro | `<10 digits>@tmomail.net` |
| Google Fi | `<10 digits>@msg.fi.google.com` |
| US Cellular | `<10 digits>@email.uscc.net` |
| AT&T / Cricket | gateway shut down in 2025. Use the ntfy.sh app instead: `curl -d "$SMS" ntfy.sh/<your-secret-topic>` |

`SMTP_USER` is the sending Gmail address, `SMTP_PASS` is a Gmail **App Password** (Google Account -> Security ->
2-Step Verification -> App passwords). Send yourself one `--dry-run` first and confirm the gateway address
before trusting the schedule. The text is forced to GSM-7 ASCII and 306 septets, so it arrives as two segments.

## Free hosting

`.github/workflows/brief.yml` runs the job daily on GitHub Actions (free on a private repo, ~1 minute a day) and
commits `briefs/` back so reruns are idempotent. The cron is fixed UTC: 6 PM PDT becomes 5 PM PST in winter; change
it to `0 2 * * *` in November if that matters. Add `ANTHROPIC_API_KEY`, `SMTP_USER`, `SMTP_PASS`, `SMS_TO` as
repository secrets. GitHub disables scheduled workflows after 60 days without a push, so commit something
occasionally or trigger it manually from the Actions tab. Any always-on box with cron works the same way:
`0 18 * * * cd ~/dive-report && uv run --env-file .env main.py`.

## Deviations from the PRD

- SpearFactor's per-spot model runs only in the browser, so the fetcher pulls their public diver-submitted OC
  reports (with the model's prediction at report time) instead. Still eyes-on, still per spot.
- DiveViz has not posted an LA/OC report since 2019-09-07; it is "no report" every day until they post again.
- Beach Cities Scuba reports Shaw's Cove, Laguna. It is used as a regional visibility proxy, never as a spot.
- Grunion runs are a moon-phase heuristic (4 nights after new/full, March to August), not the CDFW table.
- Twilio replaced by a carrier email gateway; `httpx` by `urllib`; Open-Meteo's `swell_wave_peak_period` is null
  on this coast, so the turbidity proxy uses mean swell period times swell height.
- About 600 non-test lines rather than 500; the extra is the five fetcher fixtures' parsing.

## Layout

```
spots.yaml       spots, bottom type, shelter notes, species, MPA note, buoy + tide station
fetchers/        one module per source; all return None on failure (contract in fetchers/__init__.py)
analyze.py       one Claude call (claude-sonnet-4-6, structured output) with the heuristics as the system prompt
notify.py        SMS formatting (320-char cap) + email-to-SMS delivery
main.py          collect -> analyze -> briefs/YYYY-MM-DD.{md,json} -> SMS
tests/           recorded fixtures per fetcher so a site redesign is a failing test, not a silent None
```
