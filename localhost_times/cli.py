"""localhost-times: print today's edition.

Every integration switches on when its environment variables are set (see .env.example).
"""
import argparse
import datetime as dt
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from . import deliver, editor, render, sources, voice

log = logging.getLogger("localhost-times")

# name: (env vars that switch it on, fetch(env, day), which part of the paper it feeds)
SOURCES = {
    "mail": (("MAIL_USER", "MAIL_PASSWORD"), sources.mail, "emails"),
    "calendar": (("ICAL_URLS",), sources.calendars, "calendar"),
    "todoist": (("TODOIST_TOKEN",), sources.todoist, "tasks"),
    "github": (("GITHUB_TOKEN",), sources.github, "tasks"),
    "weather": (("WEATHER_CITY",), sources.weather, "weather"),
    "google news": ((), sources.google_news, "news"),
    "rss": (("RSS_FEEDS",), sources.rss, "news"),
    "hacker news": (("HACKERNEWS",), sources.hackernews, "news"),
}
# name: (env vars that switch it on, send(env, edition))
DELIVERIES = {
    "email": (("MAIL_USER", "MAIL_PASSWORD"), deliver.email),
    "telegram": (("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"), deliver.telegram),
    "slack": (("SLACK_WEBHOOK_URL",), deliver.slack),
    "discord": (("DISCORD_WEBHOOK_URL",), deliver.discord),
    "ntfy": (("NTFY_TOPIC",), deliver.ntfy),
}


def enabled(needs, env):
    return all(env.get(var) for var in needs)


def gather(env, day, only=None):
    """Run every enabled source. A broken source is logged and skipped, never fatal."""
    inputs = {"calendar": [], "emails": [], "tasks": [], "weather": [], "news": []}
    for name, (needs, fetch, part) in SOURCES.items():
        if (only and name not in only) or not enabled(needs, env):
            continue
        try:
            inputs[part] += fetch(env, day)
        except Exception as exc:  # one flaky source must not cancel the morning paper
            log.warning("skipped %s: %s", name, exc)
    for n, story in enumerate(inputs["news"]):
        story["n"] = n
    return inputs


def byline(env):
    model = env.get("MODEL", "gemma4:e4b")
    base = env.get("LLM_BASE_URL", "")
    local = not base or any(h in base for h in ("localhost", "127.0.0.1", "0.0.0.0"))
    return f"Written on-device by {model}" if local else f"Written by {model}"


def summary(ed, day):
    lines = [f"The Localhost Times · {day.strftime('%a %b %-d')}", "", ed["headline"].upper(), ed["lede"]]
    if ed["must_do_today"]:
        lines += ["", "MUST DO"] + [f"• {x}" for x in ed["must_do_today"]]
    if ed["needs_reply"]:
        lines += ["", "WAITING ON YOU"] + [f"• {r['from'].split('<')[0].strip()}: {r['about']}" for r in ed["needs_reply"]]
    return "\n".join(lines)


def show_integrations(env):
    rows = [(f"source  {name}", enabled(needs, env)) for name, (needs, _, _) in SOURCES.items()]
    rows += [(f"model   {env.get('MODEL', 'gemma4:e4b')} via {env.get('LLM_BASE_URL') or 'Ollama'}", True),
             (f"voice   {voice.engine(env)}", voice.engine(env) != "none")]
    rows += [(f"deliver {name}", enabled(needs, env)) for name, (needs, _) in DELIVERIES.items()]
    for label, on in rows:
        print(f"  [{'x' if on else ' '}] {label}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="localhost-times", description="Print today's edition of The Localhost Times.")
    ap.add_argument("--list", action="store_true", help="show which integrations are switched on and exit")
    ap.add_argument("--demo", action="store_true", help="use demo_inbox.json and print the public demo into site/demo/")
    ap.add_argument("--no-audio", action="store_true", help="skip the spoken briefing")
    ap.add_argument("--no-send", action="store_true", help="print locally only, deliver nowhere")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    load_dotenv()
    env = dict(os.environ)
    if args.list:
        show_integrations(env)
        return

    day = dt.date.today()
    if args.demo:  # a made-up inbox with real news and weather, safe to publish
        demo = json.loads(Path("demo_inbox.json").read_text())
        name, out = demo["name"], Path("site/demo")
        news_env = {"WEATHER_CITY": demo["city"], "NEWS_TOPICS": demo["topics"], "HACKERNEWS": "4"}
        inputs = gather(news_env, day, only={"weather", "google news", "hacker news"})
        inputs.update(calendar=demo["calendar"], emails=demo["emails"], tasks=demo["tasks"])
    else:
        name = env.get("READER_NAME") or env.get("MAIL_USER", "reader").split("@")[0]
        out = Path("editions") / day.isoformat()
        inputs = gather(env, day)

    counts = ", ".join(f"{len(v)} {k}" for k, v in inputs.items())
    log.info("read %s -> asking %s", counts, env.get("MODEL", "gemma4:e4b"))
    ed = editor.write(name, day, inputs, env)
    out.mkdir(parents=True, exist_ok=True)
    (out / "edition.json").write_text(json.dumps(ed, indent=2, ensure_ascii=False))

    audio = None if args.no_audio else voice.speak(ed["podcast_script"], out, env)
    page_bodies = render.pages(name, day, ed, inputs, byline(env))
    (out / "index.html").write_text(render.web(page_bodies, audio.name if audio else None))
    log.info("printed %s", (out / "index.html").resolve())

    if args.demo or args.no_send:
        return
    edition = {"headline": ed["headline"], "summary": summary(ed, day), "html": render.email(page_bodies), "audio": audio,
               "subject": f"The Localhost Times · {day.strftime('%a %b %-d')}: {ed['headline']}"}
    for target, (needs, send) in DELIVERIES.items():
        if enabled(needs, env):
            try:
                send(env, edition)
                log.info("delivered by %s", target)
            except Exception as exc:
                log.warning("could not deliver by %s: %s", target, exc)
