"""Print the edition: a flip-through newspaper for the browser, one scrolling page for email."""
import html

e = html.escape
MOTTO = "All the news that's fit to print.<br>Printed on your machine."
FONTS = ("https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Libre+Caslon+Text:ital,wght@0,400;0,700;1,400"
         "&family=Oswald:wght@500;600&display=swap")
PAGEFLIP = "https://cdn.jsdelivr.net/npm/page-flip@2.0.7/dist/js/page-flip.browser.js"

CSS = """
:root{--paper:#f4efe6;--ink:#1a1a1a;--muted:#5b554c;--accent:#7a1f1f;--table:#2b2723}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--table:#121110}}
*{box-sizing:border-box}
body{margin:0;background:var(--table);color:var(--ink);font:17px/1.5 'Libre Caslon Text',Georgia,serif}
.bar{display:flex;gap:12px;align-items:center;justify-content:center;flex-wrap:wrap;padding:14px 16px;color:#eee;
 font:600 13px/1 Oswald,Helvetica,Arial,sans-serif;letter-spacing:1.5px;text-transform:uppercase}
.bar audio{height:36px;max-width:100%}
.bar button{font:inherit;letter-spacing:inherit;background:none;color:#eee;border:1px solid #777;padding:9px 14px;cursor:pointer}
.bar button:focus-visible,a:focus-visible{outline:2px solid #e9c46a;outline-offset:2px}
.desk{max-width:min(1180px,calc((100vh - 84px) * 1.418));margin:0 auto 24px;padding:0 16px}
.page{background:var(--paper);background-image:radial-gradient(rgba(0,0,0,.035) 1px,transparent 1px);background-size:3px 3px}
.inner{padding:clamp(18px,4vw,34px);height:100%;overflow:auto}
body:not(.flip) .page{max-width:760px;margin:0 auto 18px;box-shadow:0 10px 30px rgba(0,0,0,.35)}
body:not(.flip) .bar .turn{display:none}
.mast{text-align:center;border-bottom:4px double var(--ink);padding-bottom:6px}
.mast h1{white-space:nowrap;font:400 clamp(28px,4.2vw,58px)/1.05 UnifrakturMaguntia,'Old English Text MT',Georgia,serif;margin:6px 0}
.ears{display:flex;justify-content:space-between;gap:12px;font-size:11px;font-style:italic;color:var(--muted);text-align:left}
.ears span:last-child{text-align:right}
.dateline{display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;border-top:1px solid var(--ink);margin-top:6px;
 padding-top:5px;font:500 11px/1.3 Oswald,Helvetica,Arial,sans-serif;letter-spacing:1px;text-transform:uppercase}
.lead h2{font-size:clamp(26px,4.4vw,40px);line-height:1.08;margin:18px 0 10px}
.lede:first-letter{float:left;font-size:3.3em;line-height:.85;padding:4px 6px 0 0;font-weight:700}
.inside{border-top:1px solid var(--ink);margin-top:18px;padding-top:8px;font:500 12px Oswald,Helvetica,Arial,sans-serif;
 letter-spacing:1px;text-transform:uppercase;color:var(--muted)}
section{border-top:2px solid var(--ink);padding-top:6px;margin-bottom:22px}
h3{font:600 13px/1.4 Oswald,Helvetica,Arial,sans-serif;text-transform:uppercase;letter-spacing:2px;margin:0 0 8px}
ul{padding-left:18px;margin:0}li{margin:0 0 9px}
.src{font:500 11px Oswald,Helvetica,Arial,sans-serif;letter-spacing:.5px;color:var(--muted);text-transform:uppercase}
a{color:var(--accent)}.quiet{color:var(--muted);font-style:italic}
footer{border-top:1px solid var(--ink);padding-top:8px;font-size:12px;color:var(--muted);text-align:center}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

FLIP_JS = """
const book = document.getElementById('paper');
const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
// Phones get a calm scrolling paper; spreads need room.
if (window.St && !calm && innerWidth >= 760) {
  document.body.classList.add('flip');
  const pf = new St.PageFlip(book, {width: 560, height: 790, size: 'stretch', minWidth: 300, maxWidth: 820,
    minHeight: 430, maxHeight: 1160, showCover: false, maxShadowOpacity: 0.45, mobileScrollSupport: true});
  pf.loadFromHTML(book.querySelectorAll('.page'));
  document.getElementById('prev').onclick = () => pf.flipPrev();
  document.getElementById('next').onclick = () => pf.flipNext();
  addEventListener('keydown', ev => {
    if (ev.key === 'ArrowRight') pf.flipNext();
    if (ev.key === 'ArrowLeft') pf.flipPrev();
  });
}
"""


def _list(items):
    rows = "".join(f"<li>{x}</li>" for x in items)
    return f"<ul>{rows or '<li class=quiet>Nothing here. Enjoy it.</li>'}</ul>"


def _section(title, items):
    return f"<section><h3>{e(title)}</h3>{_list(items)}</section>"


def weather_line(inputs):
    w = (inputs.get("weather") or [None])[0]
    return f"{w['city']}: {w['sky']}, {w['low']}–{w['high']}°, {w['rain_chance']}% rain" if w else ""


def pages(name, day, ed, inputs, byline):
    """The edition as a list of page bodies, shared by the web and email versions."""
    schedule = [f"<b>{e(ev['time'])}</b> {e(ev['title'])}" + (f" <span class=src>{e(ev['where'])}</span>" if ev.get("where") else "")
                for ev in inputs.get("calendar", [])]
    replies = [f"<b>{e(r['from'].split('<')[0].strip(' \"') or r['from'])}</b>: {e(r['about'])}<br><span class=src>{e(r['why'])}</span>" for r in ed["needs_reply"]]
    world = [f"<a href=\"{e(n['link'])}\">{e(n['title'])}</a> <span class=src>{e(n['source'])}</span><br>{e(n['summary'])}"
             for n in ed["news"]]
    front = f"""<header class=mast>
<div class=ears><span>{e(weather_line(inputs))}</span><span>{MOTTO}</span></div>
<h1>The Localhost Times</h1>
<div class=dateline><span>{e(day.strftime('%A, %B %-d, %Y'))}</span><span>Edition for {e(name)}</span><span>{e(byline)}</span></div>
</header>
<article class=lead><h2>{e(ed['headline'])}</h2><p class=lede>{e(ed['lede'])}</p></article>
{_section("Top of the list", map(e, ed["must_do_today"][:3])) if ed["must_do_today"] else ""}
<div class=inside>Inside: Today · Must do · Waiting on you · Worth knowing · The world</div>"""
    return [
        front,
        _section("Today", schedule) + _section("Must do", map(e, ed["must_do_today"])),
        _section("Waiting on you", replies) + _section("Worth knowing", map(e, ed["fyi"])),
        _section("The world", world)
        + "<footer>Read and written by an open model on your own machine. Nothing in your inbox left the laptop.</footer>",
    ]


def web(page_bodies, audio_src=None):
    player = f'<audio controls preload=none src="{e(audio_src)}" aria-label="Listen to this edition"></audio>' if audio_src else ""
    sheets = "".join(f'<div class=page><div class=inner>{body}</div></div>' for body in page_bodies)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>The Localhost Times</title>
<link rel=preconnect href="https://fonts.gstatic.com" crossorigin><link rel=stylesheet href="{FONTS}"><style>{CSS}</style></head>
<body><nav class=bar aria-label="Edition controls"><button id=prev class=turn>&larr; Prev</button>{player}<button id=next class=turn>Next &rarr;</button></nav>
<main class=desk><div id=paper>{sheets}</div></main>
<script src="{PAGEFLIP}"></script><script>{FLIP_JS}</script></body></html>"""


def email(page_bodies):
    """Mail clients strip scripts and web fonts, so: one column, inline-friendly CSS, no flipping."""
    body = "".join(f"<div class=inner>{b}</div>" for b in page_bodies)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8><style>{CSS}</style></head>
<body style="background:#f4efe6"><div class=page style="max-width:760px;margin:0 auto">{body}</div></body></html>"""
