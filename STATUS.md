# Spearo Brief - task board

Sessions on this machine: **orchestrator-1** (owns integration + this board), **worker-1**, **worker-2**.
Rules: edit only your own rows; flip Status to `doing` when you start and `done`/`blocked` when you stop;
SendMessage orchestrator-1 when you finish or get stuck. Nobody commits; orchestrator-1 reviews the diff.

| Task | Owner | Status | Notes |
|---|---|---|---|
| Skeleton: pyproject, spots.yaml, fetchers contract, _http helper | orchestrator-1 | done | contract in fetchers/__init__.py |
| fetchers/spearfactor.py + fixture + test | worker-1 | done | /predict needs ~20 browser-computed inputs (returns result=null without them); ships GET /reports/public?region=orange instead = real diver vis reports for OC spots, 3 days, with model prediction per report |
| fetchers/diveviz.py + fixture + test | worker-1 | done | report lives in blogs/la-and-oc-dive-conditions.atom; newest post is 2019-09-07 so fetch() returns None (>7 days old) - source is effectively dead; parse() tested on fixture |
| fetchers/beachcities.py + fixture + test | worker-1 | done | Shaw's Cove / Laguna only; labeled fields + report_date; works live |
| fetchers/ocbeachinfo.py + fixture + test | worker-1 | done | closures/warnings/advisories lists (extra `advisories` key: creek-outlet runoff postings, Doheny-relevant); live today: 1 warning at Dana Point Harbor Baby Beach |
| fetchers/marine.py + fixture + test | worker-2 | done | Open-Meteo marine + forecast, multi-coordinate |
| fetchers/ndbc.py + fixture + test | worker-2 | done | .spec then .txt fallback; 46242.spec is 404 today |
| fetchers/tides.py + fixture + test | worker-2 | done | CO-OPS hilo |
| fetchers/moon.py + test | worker-2 | done | pure compute incl. grunion heuristic |
| MPA verification (spots.yaml regulatory notes) | worker-2 | done | CDFW Title 14 §632 + MPA pages |
| analyze.py (Claude structured output) | orchestrator-1 | done | messages.parse + pydantic Brief; model claude-sonnet-4-6 |
| notify.py (free email-to-SMS gateway) | orchestrator-1 | done | smtplib -> carrier gateway; 320-char ASCII cap; tests/test_notify.py |
| main.py + briefs/ writer | orchestrator-1 | done | --dry-run, --collect-only, --day, --force; idempotent via briefs/<day>.md |
| README + GitHub Actions cron | orchestrator-1 | done | .github/workflows/brief.yml commits briefs back |
| Integration: live --collect-only | orchestrator-1 | done | 7.6 s, only diveviz missing (dead since 2019); payload ~11k chars |
| Integration: --dry-run (Claude) + real SMS | orchestrator-1 | blocked | needs ANTHROPIC_API_KEY, SMS_TO, SMTP_USER/PASS from user |
| Review of analyze/notify/main | worker-1 | done | 13 findings sent to orchestrator-1; top 3: dry-run blocks the real send, top_pick mismatch -> SKIP text, no GSM-7 sanitizing  -> all 13 applied by orchestrator-1 |
