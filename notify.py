"""Format the two-segment SMS and send it for free through the carrier's email-to-SMS gateway."""
import os
import smtplib
from datetime import date
from email.message import EmailMessage

CAP = 306  # two concatenated SMS segments = 2 x 153 GSM-7 septets
EXT = "~[]{}\\^|"  # GSM-7 extension chars cost two septets
ASCII = str.maketrans({"\u2014": "-", "\u2013": "-", "\u00b0": "", "\u2026": "...", "\u2019": "'", "\u2018": "'",
                       "\u201c": '"', "\u201d": '"', "`": "'", "\u00d7": "x"})


def septets(text: str) -> int:
    return len(text) + sum(text.count(c) for c in EXT)


def _sent(s: str) -> str:
    return s.strip().rstrip(".") + "."


def format_sms(brief, day: date) -> str:
    by = {s.spot: s for s in brief.spots}
    top = by.get(brief.top_pick) or next((s for s in brief.spots if s.verdict == "go"), None)
    wd = day.strftime("%a")
    if top is None or top.verdict == "skip":
        top = None
        head = f"{wd} AM: SKIP. {_sent(brief.one_line_summary)}"
    else:
        head = f"{wd} AM: {top.verdict.upper()} - {top.spot}. Vis ~{top.vis_estimate_ft}ft. {_sent(top.why)}"
        if top.species_note:
            head += f" {_sent(top.species_note)}"
    rest = [s for s in brief.spots if s is not top]
    parts = []
    for label, v in (("Also go", "go"), ("Marginal", "marginal"), ("Skip", "skip")):
        group = [f"{s.spot} ({s.tag})" if v != "go" else s.spot for s in rest if s.verdict == v]
        if group:
            parts.append(f"{label}: {', '.join(group)}.")
    # one non-GSM char (em dash, degree sign, curly quote) would flip the whole text to UCS-2 and halve capacity
    text = (head + "\n" + " ".join(parts)).translate(ASCII).encode("ascii", "ignore").decode()
    if septets(text) > CAP and top and top.species_note:  # ponytail: drop species note first, then hard cut
        text = text.replace(f" {_sent(top.species_note)}", "", 1)
    while septets(text) > CAP:
        text = text[: CAP - 3].rstrip() + "..." if septets(text) > CAP + 20 else text[:-4].rstrip() + "..."
    return text


def send_sms(text: str) -> None:
    to, user, pw = os.environ["SMS_TO"], os.environ["SMTP_USER"], os.environ["SMTP_PASS"]
    msg = EmailMessage()
    msg["From"], msg["To"] = user, to
    msg.set_content(text, cte="7bit")  # no Subject on purpose: gateways prepend it; 7bit avoids quoted-printable "=\n" line breaks
    with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"), 465) as s:
        s.login(user, pw)
        s.send_message(msg)
