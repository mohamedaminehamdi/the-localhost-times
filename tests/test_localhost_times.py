"""Offline checks: no network, no model. Run with `uv run pytest`."""
import datetime as dt
from email.message import EmailMessage

from localhost_times import cli, render, sources

DAY = dt.date(2026, 10, 5)
EDITION = {"headline": "<script>alert(1)</script>", "lede": "A quiet day.", "must_do_today": ["Pay rent"],
           "needs_reply": [{"from": "Mom", "about": "Lunch", "why": "By Wednesday"}], "fyi": [], "news": [],
           "podcast_script": "Good morning."}


def test_mail_text_and_headers():
    msg = EmailMessage()
    msg["Subject"] = "=?utf-8?b?w4l0w6k=?="
    msg.set_content("<html><style>p{color:red}</style><p>Hello&nbsp;<b>Sam</b></p></html>", subtype="html")
    assert sources._text(msg) == "Hello Sam"
    assert sources._header(msg["Subject"]) == "Été"


def test_host_presets():
    assert sources.host_port("imap.example.com:1143", 993) == ("imap.example.com", 1143)
    assert sources.host_port("imap.example.com", 993) == ("imap.example.com", 993)
    assert sources.IMAP_HOSTS[sources.domain("Sam@iCloud.com")] == "imap.mail.me.com"


def test_rss_and_atom():
    rss = b"""<rss><channel><title>Daily</title><item><title>Big news - Wire</title><link>https://a</link>
              <source>Wire</source></item><item><title>Second</title><link>https://b</link></item></channel></rss>"""
    atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><title>Blog</title>
               <entry><title>Post</title><link href="https://c"/></entry></feed>"""
    assert sources.parse_feed(rss) == [
        {"topic": "", "title": "Big news", "source": "Wire", "link": "https://a"},
        {"topic": "", "title": "Second", "source": "Daily", "link": "https://b"},
    ]
    assert sources.parse_feed(atom, topic="feeds") == [{"topic": "feeds", "title": "Post", "source": "Blog", "link": "https://c"}]


def test_ics_includes_recurring_events():
    ics = b"""BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:1\r\nDTSTART;VALUE=DATE:20261005\r\nSUMMARY:Rent due\r\nEND:VEVENT\r
BEGIN:VEVENT\r\nUID:2\r\nDTSTART:20260901T093000\r\nDTEND:20260901T094500\r\nRRULE:FREQ=DAILY\r\nSUMMARY:Standup\r\nEND:VEVENT\r
END:VCALENDAR\r\n"""
    events = {e["title"]: e["time"] for e in sources.parse_ics(ics, DAY)}
    assert events == {"Rent due": "all day", "Standup": "09:30"}


def test_render_escapes_and_email_has_no_script():
    pages = render.pages("Sam", DAY, EDITION, {"calendar": [], "weather": []}, "Written on-device by gemma4:e4b")
    web, mail = render.web(pages, "edition.mp3"), render.email(pages)
    assert "<script>alert" not in web and "&lt;script&gt;" in web
    assert "<script" not in mail
    assert 'src="edition.mp3"' in web and "Pay rent" in mail


def test_broken_source_is_skipped(monkeypatch):
    def boom(env, day):
        raise OSError("imap down")

    monkeypatch.setattr(cli, "SOURCES", {
        "broken": ((), boom, "emails"),
        "fine": ((), lambda env, day: [{"title": "x"}], "news"),
        "off": (("NOT_SET",), boom, "emails"),
    })
    inputs = cli.gather({}, DAY)
    assert inputs["emails"] == [] and inputs["news"] == [{"title": "x", "n": 0}]


def test_byline_is_honest_about_where_the_model_runs():
    assert cli.byline({}).startswith("Written on-device")
    assert cli.byline({"LLM_BASE_URL": "http://localhost:1234/v1"}).startswith("Written on-device")
    assert cli.byline({"LLM_BASE_URL": "https://api.example.com/v1", "MODEL": "m"}) == "Written by m"
