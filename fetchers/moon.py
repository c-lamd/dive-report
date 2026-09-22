"""Moon phase, spring/neap label, grunion-run flag. Pure computation, never None."""
import math
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

SYNODIC = 29.530588853  # ponytail: mean month from one reference new moon; real syzygies drift up to ~0.5 day
REF_NEW = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
HALF = SYNODIC / 2
TZ = ZoneInfo("America/Los_Angeles")
PHASES = ["new", "waxing crescent", "first quarter", "waxing gibbous",
          "full", "waning gibbous", "last quarter", "waning crescent"]


def age(dt):
    """Days since the last new moon at instant dt."""
    return ((dt - REF_NEW).total_seconds() / 86400) % SYNODIC


def info(day):
    a = age(datetime.combine(day, time(8), TZ))  # dive time
    syzygy = min(a % HALF, HALF - a % HALF)  # days from nearest new/full
    quarter = min((a + HALF / 2) % HALF, HALF - (a + HALF / 2) % HALF)  # days from nearest quarter
    # ponytail: ignores the ~1 day tidal lag; tides.range_ft is the real spring/neap signal
    label = "spring" if syzygy <= 2 else "neap" if quarter <= 2 else "mid"
    night = datetime.combine(day - timedelta(days=1), time(20), TZ)  # the night that ends on `day`
    last_syzygy = (night - timedelta(days=age(night) % HALF)).date()
    # ponytail: heuristic - 4 nights from each new/full moon, Mar-Aug; swap in CDFW's published table if it matters
    grunion = night.month in range(3, 9) and (night.date() - last_syzygy).days <= 3
    return {"phase": PHASES[int(a / SYNODIC * 8 + 0.5) % 8],
            "illumination": round((1 - math.cos(2 * math.pi * a / SYNODIC)) / 2, 2),
            "spring_neap": label, "days_from_syzygy": round(syzygy, 1),
            "grunion_run_night_before": grunion}
