"""Print the edition: a modern briefing page for the browser, and a light version for email."""
import html
from string import Template
from urllib.parse import urlparse

e = html.escape
FONTS = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Instrument+Serif:ital@1&display=swap"
AUDIO_SLOT = "<!--audio-->"

DARK = {"scheme": "dark", "bg": "#0a0a0b", "surface": "#111114", "surface2": "#17171b", "border": "rgba(255,255,255,.08)",
        "text": "#ededef", "muted": "#a1a1aa", "accent": "#f5b947", "glow": "rgba(245,185,71,.14)"}
LIGHT = {"scheme": "light", "bg": "#fafaf9", "surface": "#ffffff", "surface2": "#f4f4f5", "border": "rgba(0,0,0,.09)",
         "text": "#18181b", "muted": "#52525b", "accent": "#a8701a", "glow": "rgba(245,185,71,.20)"}

CSS = Template("""
:root{color-scheme:$scheme}
*{box-sizing:border-box}
body{margin:0;background:$bg;color:$text;font:16px/1.6 Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:880px;margin:0 auto;padding:28px 16px 64px}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:24px}
.mark{font:italic 400 26px/1 'Instrument Serif',Georgia,serif;color:$text;text-decoration:none;white-space:nowrap}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:$accent;margin-right:10px;vertical-align:middle;
 box-shadow:0 0 14px $accent}
.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border:1px solid $border;border-radius:999px;
 font-size:12px;font-weight:500;color:$muted;background:$surface}
.chip svg{width:12px;height:12px}
.hero{padding:clamp(22px,4vw,34px);border:1px solid $border;border-radius:22px;
 background:radial-gradient(120% 140% at 0% 0%,$glow,transparent 60%),$surface}
.date{font-size:12px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:$accent}
h1{font-size:clamp(28px,5.4vw,46px);line-height:1.08;letter-spacing:-.03em;margin:10px 0 12px;font-weight:700}
.lede{color:$muted;font-size:18px;margin:0;max-width:62ch}
.meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}
audio{display:block;width:100%;margin-top:22px;border-radius:12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
.card{padding:22px 24px;border:1px solid $border;border-radius:18px;background:$surface}
.full{margin-top:16px}
h2{display:flex;align-items:center;gap:10px;font-size:12px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
 color:$muted;margin:0 0 12px}
h2 b{color:$accent;font-weight:600}
ul{list-style:none;margin:0;padding:0}
li{padding:11px 0;border-top:1px solid $border}
li:first-child{border-top:0;padding-top:2px}
.time{display:inline-block;min-width:66px;font-variant-numeric:tabular-nums;font-weight:600}
.sub{display:block;color:$muted;font-size:13px;margin-top:2px}
.todo li{display:flex;gap:12px;align-items:flex-start}
.todo li:before{content:"";flex:none;width:16px;height:16px;margin-top:4px;border:1.5px solid $accent;border-radius:50%}
.who{display:flex;gap:12px;align-items:flex-start}
.av{flex:none;width:32px;height:32px;border-radius:50%;background:$surface2;border:1px solid $border;text-align:center;
 line-height:30px;font-weight:600;font-size:13px;color:$accent}
.news a{color:$text;font-weight:600;text-decoration:none}
.news a:hover{text-decoration:underline;text-decoration-color:$accent}
.quiet{color:$muted;font-style:italic}
footer{margin-top:28px;text-align:center;color:$muted;font-size:13px}
a:focus-visible{outline:2px solid $accent;outline-offset:2px;border-radius:4px}
@media (max-width:680px){.grid{grid-template-columns:1fr}}
""")

LOCK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
        '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>')


def safe_href(url):
    """Feed links are untrusted: only http(s) may become a link (no javascript: URLs)."""
    return url if urlparse(url or "").scheme.lower() in ("http", "https") else "#"


def weather_line(inputs):
    w = (inputs.get("weather") or [None])[0]
    return f"{w['city']} · {w['sky']} · {w['low']}–{w['high']}° · {w['rain_chance']}% rain" if w else ""


def _name(sender):
    return sender.split("<")[0].strip(' "') or sender


def _card(title, items, cls="", count=False):
    rows = "".join(f"<li>{x}</li>" for x in items) or "<li class=quiet>Nothing here. Enjoy it.</li>"
    badge = f" <b>{len(items)}</b>" if count and items else ""
    return f'<section class="card {cls}"><h2>{e(title)}{badge}</h2><ul>{rows}</ul></section>'


def pages(name, day, ed, inputs, byline):
    """The edition as a list of HTML blocks, shared by the web and email versions."""
    schedule = [f"<span class=time>{e(ev['time'])}</span>{e(ev['title'])}" + (f"<span class=sub>{e(ev['where'])}</span>" if ev.get("where") else "")
                for ev in inputs.get("calendar", [])]
    replies = [f"<div class=who><span class=av>{e(_name(r['from'])[:1].upper())}</span><div><b>{e(_name(r['from']))}</b> · {e(r['about'])}"
               f"<span class=sub>{e(r['why'])}</span></div></div>" for r in ed["needs_reply"]]
    world = [f"<a href=\"{e(safe_href(n['link']))}\" rel=\"noopener noreferrer\">{e(n['title'])}</a>"
             f"<span class=sub>{e(n['source'])} · {e(n['summary'])}</span>" for n in ed["news"]]
    weather = weather_line(inputs)
    chips = ([f"<span class=chip>{e(weather)}</span>"] if weather else []) + [
        f"<span class=chip>{len(ed['must_do_today'])} to do</span>",
        f"<span class=chip>{len(ed['needs_reply'])} waiting on you</span>"]
    hero = f"""<header class=top><span class=mark><span class=dot></span>The Localhost Times</span>
<span class=chip>{LOCK}{e(byline)}</span></header>
<section class=hero><div class=date>{e(day.strftime('%A, %B %-d'))} · Edition for {e(name)}</div>
<h1>{e(ed['headline'])}</h1><p class=lede>{e(ed['lede'])}</p><div class=meta>{''.join(chips)}</div>{AUDIO_SLOT}</section>"""
    return [
        hero,
        f"<div class=grid>{_card('Today', schedule)}{_card('Must do', list(map(e, ed['must_do_today'])), 'todo', True)}</div>",
        f"<div class=grid>{_card('Waiting on you', replies, count=True)}{_card('Worth knowing', list(map(e, ed['fyi'])))}</div>",
        _card("The world", world, "news full")
        + "<footer>Read and written by an open model on your own machine. Nothing in your inbox left the laptop.</footer>",
    ]


def _vars(tokens):
    return ";".join(f"--{k}:{v}" for k, v in tokens.items())


def web(blocks, audio_src=None):
    css = (f":root{{{_vars(DARK)}}}@media (prefers-color-scheme:light){{:root{{{_vars(LIGHT)}}}}}"
           + CSS.substitute({k: f"var(--{k})" for k in DARK}))
    player = f'<audio controls preload=none src="{e(audio_src)}" aria-label="Listen to this edition"></audio>' if audio_src else ""
    body = "".join(blocks).replace(AUDIO_SLOT, player)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>The Localhost Times</title>
<link rel=preconnect href="https://fonts.gstatic.com" crossorigin><link rel=stylesheet href="{FONTS}"><style>{css}</style></head>
<body><main class=wrap>{body}</main></body></html>"""


def email(blocks):
    """Mail clients drop scripts, web fonts and CSS variables: light theme, literal colors."""
    note = '<div class=meta><span class=chip>Your audio briefing is attached</span></div>'
    body = "".join(blocks).replace(AUDIO_SLOT, note)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8><style>{CSS.substitute(LIGHT)}</style></head>
<body style="background:{LIGHT['bg']}"><div class=wrap>{body}</div></body></html>"""
