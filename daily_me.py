"""The Daily Me: a private morning edition.

Inbox + calendar + news -> a one-page newspaper and a ~3 minute audio briefing.
Mail is read and summarised by Gemma 4 running locally through Ollama.
Only the finished briefing script leaves the machine (for text-to-speech).
"""
import argparse
import datetime as dt
import email
import email.utils
import html
import imaplib
import json
import os
import re
import smtplib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.header import decode_header, make_header
from email.message import EmailMessage
from pathlib import Path

import icalendar
import recurring_ical_events
from dotenv import load_dotenv

load_dotenv()
OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("MODEL", "gemma4:e4b")
UA = {"User-Agent": "Mozilla/5.0 (TheDailyMe)"}


# ---------- fetch ----------

def _header(value):
    return str(make_header(decode_header(value or "")))


def _text(msg):
    """First text/plain part, else text/html with tags stripped, collapsed to one line."""
    parts = list(msg.walk()) if msg.is_multipart() else [msg]
    for kind in ("text/plain", "text/html"):
        for part in parts:
            if part.get_content_type() == kind and not part.get_filename():
                body = part.get_payload(decode=True) or b""
                text = body.decode(part.get_content_charset() or "utf-8", "replace")
                if kind == "text/html":
                    text = re.sub(r"(?s)<(style|script).*?</\1>|<[^>]+>", " ", text)
                    text = html.unescape(text)
                return " ".join(text.split())
    return ""


def fetch_mail(user, password, hours=24, limit=40):
    """Read-only: BODY.PEEK never marks anything as read."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    since = cutoff.strftime("%d-%b-%Y")
    mails = []
    with imaplib.IMAP4_SSL("imap.gmail.com") as m:
        m.login(user, password)
        m.select("INBOX", readonly=True)
        _, ids = m.search(None, f'(SINCE "{since}")')
        for i in ids[0].split()[-limit:]:  # ponytail: newest 40 keeps the prompt small; raise with a bigger num_ctx
            _, data = m.fetch(i, "(FLAGS BODY.PEEK[])")
            msg = email.message_from_bytes(data[0][1])
            date = email.utils.parsedate_to_datetime(msg["Date"]) if msg["Date"] else cutoff
            if date.tzinfo is None:
                date = date.replace(tzinfo=dt.timezone.utc)
            if date < cutoff:
                continue
            mails.append({
                "from": _header(msg["From"]),
                "subject": _header(msg["Subject"]),
                "received": date.astimezone().strftime("%a %H:%M"),
                "snippet": _text(msg)[:300],
                "flags": [f.decode() for f in imaplib.ParseFlags(data[0][0])],
            })
    return mails


def fetch_calendar(url, day):
    cal = icalendar.Calendar.from_ical(urllib.request.urlopen(url, timeout=30).read())
    events = []
    for ev in recurring_ical_events.of(cal).at(day):
        start = ev["DTSTART"].dt
        timed = isinstance(start, dt.datetime)
        events.append({
            "time": start.astimezone().strftime("%H:%M") if timed else "all day",
            "title": str(ev.get("SUMMARY", "")),
            "where": str(ev.get("LOCATION", "")),
        })
    return sorted(events, key=lambda e: (e["time"] != "all day", e["time"]))


def fetch_news(interests, per_topic=4):
    """Google News RSS, no key needed. 'top' = front page headlines."""
    news = []
    for topic in interests:
        base = "https://news.google.com/rss"
        q = {"hl": "en-US", "gl": "US", "ceid": "US:en"}
        if topic.strip().lower() != "top":
            base += "/search"
            q["q"] = f"{topic.strip()} when:1d"
        req = urllib.request.Request(f"{base}?{urllib.parse.urlencode(q)}", headers=UA)
        root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
        for item in list(root.iter("item"))[:per_topic]:
            source = item.findtext("source", "")
            news.append({
                "n": len(news),
                "topic": topic.strip(),
                "title": item.findtext("title", "").removesuffix(f" - {source}"),
                "source": source,
                "link": item.findtext("link", ""),
            })
    return news


# ---------- write (local Gemma 4) ----------

_STR = {"type": "string"}
SCHEMA = {
    "type": "object",
    "properties": {
        "headline": _STR,
        "lede": _STR,
        "must_do_today": {"type": "array", "items": _STR},
        "needs_reply": {"type": "array", "items": {
            "type": "object",
            "properties": {"from": _STR, "about": _STR, "why": _STR},
            "required": ["from", "about", "why"]}},
        "fyi": {"type": "array", "items": _STR},
        "news": {"type": "array", "items": {
            "type": "object",
            "properties": {"n": {"type": "integer"}, "summary": _STR},
            "required": ["n", "summary"]}},
        "podcast_script": _STR,
    },
    "required": ["headline", "lede", "must_do_today", "needs_reply", "fyi", "news", "podcast_script"],
}

EDITOR = """You are the editor of "The Daily Me", a private one-page morning newspaper with exactly one reader: {name}.
Today is {date}. Use ONLY the facts in the input. Never invent emails, events, people, times or numbers.
Newsletters, promotions and automated notifications are noise unless they hold a deadline, a bill or a security alert.
- headline: the single most important thing about {name}'s day, newspaper style, max 10 words.
- lede: 2 sentences that set up the day.
- must_do_today: concrete actions for today from the calendar and emails, most urgent first (max 6).
- needs_reply: emails a real person is waiting on {name} to answer (max 5).
- fyi: things worth knowing that need no action (max 5).
- news: pick the 4 most relevant stories by their "n" and write one plain sentence each.
- podcast_script: about 400 words, spoken aloud while {name} brushes their teeth. Warm, crisp, a little witty.
  Greet with the date, walk through the schedule, what needs action, what can wait, then the news, then a short kind sign-off.
  Plain spoken sentences only: no lists, no markdown, no URLs, no email addresses."""


def write_edition(name, day, mail, events, news):
    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "format": SCHEMA,
        "options": {"temperature": 0.3, "num_ctx": 16384},
        "messages": [
            {"role": "system", "content": EDITOR.format(name=name, date=day.strftime("%A, %B %-d, %Y"))},
            {"role": "user", "content": json.dumps({"calendar": events, "emails": mail, "news": news}, ensure_ascii=False)},
        ],
    }
    req = urllib.request.Request(f"{OLLAMA}/api/chat", json.dumps(payload).encode(), {"Content-Type": "application/json"})
    reply = json.load(urllib.request.urlopen(req, timeout=900))
    ed = json.loads(reply["message"]["content"])
    by_n = {item["n"]: item for item in news}
    ed["news"] = [{**by_n[s["n"]], "summary": s["summary"]} for s in ed["news"] if s["n"] in by_n]
    return ed


# ---------- voice ----------

def speak(text, path):
    from elevenlabs.client import ElevenLabs  # reads ELEVENLABS_API_KEY

    audio = ElevenLabs().text_to_speech.convert(
        text=text,
        voice_id=os.getenv("VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),
        model_id=os.getenv("TTS_MODEL", "eleven_flash_v2_5"),
        output_format="mp3_44100_128",
    )
    path.write_bytes(b"".join(audio))


# ---------- render + deliver ----------

CSS = """
body{margin:0;background:#f4efe6;color:#1a1a1a;font-family:Georgia,'Times New Roman',serif}
.paper{max-width:960px;margin:0 auto;padding:24px 16px 48px}
.mast{text-align:center;border-bottom:4px double #1a1a1a;padding-bottom:8px}
.mast h1{font-size:clamp(40px,9vw,76px);margin:0;letter-spacing:-1px;font-weight:900}
.dateline{display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;font:12px/1.4 Helvetica,Arial,sans-serif;
 text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #1a1a1a;padding:6px 0;margin-bottom:20px}
.lead h2{font-size:clamp(28px,5vw,44px);line-height:1.1;margin:0 0 10px}
.lead p{font-size:19px;line-height:1.5;margin:0 0 16px}
audio{width:100%;margin:8px 0 20px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px}
section{border-top:2px solid #1a1a1a;padding-top:8px}
h3{font:700 13px/1.4 Helvetica,Arial,sans-serif;text-transform:uppercase;letter-spacing:2px;margin:0 0 8px}
ul{padding-left:18px;margin:0}li{margin:0 0 8px;line-height:1.45}
a{color:#7a1f1f}.src{font:11px Helvetica,Arial,sans-serif;color:#666;text-transform:uppercase}
footer{margin-top:32px;border-top:1px solid #1a1a1a;padding-top:8px;font:12px Helvetica,Arial,sans-serif;color:#555;text-align:center}
"""


def render_html(name, day, ed, events, audio_src=None):
    e = html.escape
    li = lambda items: "".join(f"<li>{x}</li>" for x in items) or "<li>Nothing here. Enjoy it.</li>"
    schedule = [f"<b>{e(ev['time'])}</b> {e(ev['title'])}" + (f" <span class=src>{e(ev['where'])}</span>" if ev["where"] else "") for ev in events]
    replies = [f"<b>{e(r['from'])}</b>: {e(r['about'])}<br><span class=src>{e(r['why'])}</span>" for r in ed["needs_reply"]]
    world = [f"<a href=\"{e(n['link'])}\">{e(n['title'])}</a><br>{e(n['summary'])}" for n in ed["news"]]
    player = f'<audio controls src="{e(audio_src)}"></audio>' if audio_src else ""
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>The Daily Me</title><style>{CSS}</style></head>
<body><div class=paper>
<div class=mast><h1>The Daily Me</h1></div>
<div class=dateline><span>{e(day.strftime('%A, %B %-d, %Y'))}</span><span>Edition for {e(name)}</span><span>Written on-device by Gemma 4</span></div>
<div class=lead><h2>{e(ed['headline'])}</h2><p>{e(ed['lede'])}</p>{player}</div>
<div class=cols>
<section><h3>Today</h3><ul>{li(schedule)}</ul></section>
<section><h3>Must do</h3><ul>{li(map(e, ed['must_do_today']))}</ul></section>
<section><h3>Waiting on you</h3><ul>{li(replies)}</ul></section>
<section><h3>Worth knowing</h3><ul>{li(map(e, ed['fyi']))}</ul></section>
<section><h3>The world</h3><ul>{li(world)}</ul></section>
</div>
<footer>Your inbox was read by an open model on your own machine. Nothing in it left the laptop.</footer>
</div></body></html>"""


def deliver(user, password, to, subject, page, mp3=None):
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    msg.set_content("Your morning edition is here. Open in an HTML-capable mail app; the audio is attached.")
    msg.add_alternative(page, subtype="html")
    if mp3 and mp3.exists():
        msg.add_attachment(mp3.read_bytes(), maintype="audio", subtype="mpeg", filename="the-daily-me.mp3")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, password)
        s.send_message(msg)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Make today's edition of The Daily Me.")
    ap.add_argument("--demo", action="store_true", help="use demo_inbox.json and write the public site/")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--no-send", action="store_true")
    a = ap.parse_args()

    day = dt.date.today()
    interests = os.getenv("INTERESTS", "top,technology").split(",")
    if a.demo:
        demo = json.loads(Path("demo_inbox.json").read_text())
        name, mail, events = demo["name"], demo["emails"], demo["calendar"]
        out = Path("site")
    else:
        user, pw = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"]
        name = os.getenv("READER_NAME", user.split("@")[0])
        mail = fetch_mail(user, pw)
        events = fetch_calendar(os.environ["ICAL_URL"], day) if os.getenv("ICAL_URL") else []
        out = Path("editions") / day.isoformat()
    news = fetch_news(interests)
    print(f"{len(mail)} emails, {len(events)} events, {len(news)} stories -> {MODEL}")

    out.mkdir(parents=True, exist_ok=True)
    ed = write_edition(name, day, mail, events, news)
    (out / "edition.json").write_text(json.dumps(ed, indent=2, ensure_ascii=False))
    mp3 = out / "edition.mp3"
    if not a.no_audio:
        speak(ed["podcast_script"], mp3)
    page = render_html(name, day, ed, events, "edition.mp3" if mp3.exists() else None)
    (out / "index.html").write_text(page)
    print(f"wrote {out}/index.html")

    if not a.demo and not a.no_send:
        to = os.getenv("SEND_TO", user)
        deliver(user, pw, to, f"The Daily Me · {day.strftime('%a %b %-d')}: {ed['headline']}",
                render_html(name, day, ed, events), mp3)
        print(f"sent to {to}")


if __name__ == "__main__":
    main()
