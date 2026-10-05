"""Everything the paper reads in the morning. Each fetcher takes (env, day) and returns a list."""
import datetime as dt
import email
import email.utils
import html
import imaplib
import re
import urllib.parse
import xml.etree.ElementTree as ET
from email.header import decode_header, make_header

import icalendar
import recurring_ical_events

from . import net

# Address domain -> IMAP host. Anything else: MAIL_HOST, or imap.<domain>.
IMAP_HOSTS = {
    "gmail.com": "imap.gmail.com", "googlemail.com": "imap.gmail.com",
    "icloud.com": "imap.mail.me.com", "me.com": "imap.mail.me.com", "mac.com": "imap.mail.me.com",
    "fastmail.com": "imap.fastmail.com", "fastmail.fm": "imap.fastmail.com",
    "yahoo.com": "imap.mail.yahoo.com", "zoho.com": "imap.zoho.com",
    "aol.com": "imap.aol.com", "gmx.com": "imap.gmx.com", "gmx.net": "imap.gmx.net",
}


def domain(address):
    return address.rsplit("@", 1)[-1].lower()


def host_port(value, default_port):
    host, _, port = value.partition(":")
    return host, int(port or default_port)


# ---------- mail (IMAP, read-only) ----------

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
                    text = html.unescape(re.sub(r"(?s)<(style|script).*?</\1>|<[^>]+>", " ", text))
                return " ".join(text.split())
    return ""


def mail(env, day, hours=24, limit=40):
    """Last 24 h of INBOX. Opened read-only and fetched with BODY.PEEK: nothing is marked as read."""
    user = env["MAIL_USER"]
    host, port = host_port(env.get("MAIL_HOST") or IMAP_HOSTS.get(domain(user), f"imap.{domain(user)}"), 993)
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    found = []
    with imaplib.IMAP4_SSL(host, port) as box:
        box.login(user, env["MAIL_PASSWORD"])
        box.select("INBOX", readonly=True)
        _, ids = box.search(None, f'(SINCE "{cutoff.strftime("%d-%b-%Y")}")')
        for i in ids[0].split()[-limit:]:  # ponytail: newest 40 keeps the prompt small; raise with a bigger num_ctx
            _, data = box.fetch(i, "(FLAGS BODY.PEEK[])")
            msg = email.message_from_bytes(data[0][1])
            date = email.utils.parsedate_to_datetime(msg["Date"]) if msg["Date"] else cutoff
            date = date if date.tzinfo else date.replace(tzinfo=dt.timezone.utc)
            if date < cutoff:
                continue
            found.append({
                "from": _header(msg["From"]),
                "subject": _header(msg["Subject"]),
                "received": date.astimezone().strftime("%a %H:%M"),
                "snippet": _text(msg)[:300],
                "flags": [f.decode() for f in imaplib.ParseFlags(data[0][0])],
            })
    return found


# ---------- calendar (any iCal link) ----------

def parse_ics(data, day):
    events = []
    for ev in recurring_ical_events.of(icalendar.Calendar.from_ical(data)).at(day):
        start = ev["DTSTART"].dt
        timed = isinstance(start, dt.datetime)
        events.append({
            "time": start.astimezone().strftime("%H:%M") if timed else "all day",
            "title": str(ev.get("SUMMARY", "")),
            "where": str(ev.get("LOCATION", "")),
        })
    return events


def calendars(env, day):
    events = []
    for url in filter(None, map(str.strip, env["ICAL_URLS"].split(","))):
        events += parse_ics(net.request(url.replace("webcal://", "https://", 1)), day)
    return sorted(events, key=lambda e: (e["time"] != "all day", e["time"]))


# ---------- tasks ----------

def todoist(env, day):
    data = net.get_json("https://api.todoist.com/api/v1/tasks/filter?query=" + urllib.parse.quote("today | overdue"),
                        {"Authorization": f"Bearer {env['TODOIST_TOKEN']}"})
    return [{"from": "Todoist", "task": t["content"], "due": (t.get("due") or {}).get("string", "")}
            for t in data.get("results", [])]


def github(env, day, limit=10):
    data = net.get_json("https://api.github.com/notifications",
                        {"Authorization": f"Bearer {env['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"})
    return [{"from": "GitHub", "task": f"{n['repository']['full_name']}: {n['subject']['title']}",
             "due": n["reason"].replace("_", " ")} for n in data[:limit]]


# ---------- weather (Open-Meteo, no key) ----------

WMO = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
       51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
       66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
       80: "Showers", 81: "Showers", 82: "Violent showers", 85: "Snow showers", 86: "Snow showers",
       95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, hail"}


def weather(env, day):
    q = urllib.parse.urlencode({"name": env["WEATHER_CITY"], "count": 1})
    place = net.get_json(f"https://geocoding-api.open-meteo.com/v1/search?{q}")["results"][0]
    q = urllib.parse.urlencode({
        "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto", "forecast_days": 1,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
    })
    d = net.get_json(f"https://api.open-meteo.com/v1/forecast?{q}")["daily"]
    return [{"city": place["name"], "sky": WMO.get(d["weather_code"][0], "Mixed"),
             "high": round(d["temperature_2m_max"][0]), "low": round(d["temperature_2m_min"][0]),
             "rain_chance": d["precipitation_probability_max"][0]}]


# ---------- news ----------

ATOM = "{http://www.w3.org/2005/Atom}"


def parse_feed(data, limit=4, topic=""):
    """RSS 2.0 or Atom -> [{title, source, link}]."""
    root = ET.fromstring(data)
    channel = root.findtext("channel/title") or root.findtext(f"{ATOM}title") or ""
    stories = []
    for item in root.iter("item"):
        source = item.findtext("source") or channel
        stories.append({"topic": topic, "title": (item.findtext("title") or "").removesuffix(f" - {source}"),
                        "source": source, "link": item.findtext("link") or ""})
    for entry in root.iter(f"{ATOM}entry"):
        link = entry.find(f"{ATOM}link")
        stories.append({"topic": topic, "title": entry.findtext(f"{ATOM}title") or "", "source": channel,
                        "link": link.get("href", "") if link is not None else ""})
    return stories[:limit]


def google_news(env, day):
    """NEWS_TOPICS, comma separated. "top" = the front page."""
    stories = []
    for topic in filter(None, map(str.strip, env.get("NEWS_TOPICS", "top,technology").split(","))):
        q = {"hl": "en-US", "gl": "US", "ceid": "US:en"}
        path = "rss"
        if topic.lower() != "top":
            path, q["q"] = "rss/search", f"{topic} when:1d"
        stories += parse_feed(net.request(f"https://news.google.com/{path}?{urllib.parse.urlencode(q)}"), 4, topic)
    return stories


def rss(env, day):
    stories = []
    for url in filter(None, map(str.strip, env["RSS_FEEDS"].split(","))):
        stories += parse_feed(net.request(url), 3, "feeds")
    return stories


def hackernews(env, day):
    ids = net.get_json("https://hacker-news.firebaseio.com/v0/topstories.json")[: int(env["HACKERNEWS"])]
    items = [net.get_json(f"https://hacker-news.firebaseio.com/v0/item/{i}.json") for i in ids]
    return [{"topic": "hacker news", "title": it.get("title", ""), "source": "Hacker News",
             "link": it.get("url") or f"https://news.ycombinator.com/item?id={it['id']}"} for it in items if it]
