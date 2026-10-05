---
title: The Localhost Times: a private morning newspaper, printed on your laptop by Gemma 4
published: false
tags: devchallenge, weekendchallenge, hf26challenge
cover_image: TODO(you): screenshot of the front page (site/demo/), 1000x420
---

*This is a submission for the [Hacktoberfest Weekend Challenge: Build for a Friend](https://dev.to/challenges/hacktoberfest-weekend-2026-10-01)*

In 1995, Nicholas Negroponte imagined "The Daily Me": a newspaper edited for exactly one reader. Thirty years later we got the opposite: twelve apps, each fighting for the first ten minutes of our morning.

## What I Built

My friend TODO(you: first name) starts every day the same way, half awake and toothbrush in hand. Open Gmail. Open the calendar. Check the weather. Scroll the news. By the time they've worked out what actually matters today, the coffee is cold. They asked me for something simple:

> TODO(you): their words, e.g. "Can't something just read it all and tell me what my day looks like?"

There was one condition: they didn't want to hand their entire inbox to yet another cloud AI.

So I built **The Localhost Times**: *All the news that's fit to print. Printed on your machine.*

Every morning at 7, it reads your inbox, today's calendar, your tasks, the weather and the news. Then an open-weight model **running on your own laptop** writes two things:

- 📰 **A one-page newspaper** you can flip through in the browser (it really turns pages), or read straight from your inbox.
- 🎧 **A 3-minute audio briefing**, written to be heard while you brush your teeth.

The paper has a front page with the headline of your day, then **Today** (your calendar), **Must do** (actions pulled from email and tasks), **Waiting on you** (people who need a reply), **Worth knowing** (things that need no action), and **The world** (the four stories most relevant to you).

TODO(you): screenshot of the front page and one inside spread

## Demo

- **Landing page:** https://the-localhost-times.onrender.com. It's also a newspaper you flip through, with a `.env` builder that runs entirely in your browser.
- **Today's demo edition**, for a made-up reader called Sam (with real news and weather): https://the-localhost-times.onrender.com/demo/. Press play on the audio bar.

TODO(you): 30–60 s screen recording, flipping the paper with the briefing playing

## Code

{% github mohamedaminehamdi/the-localhost-times %}

## How I Built It

**The editor is Gemma 4, running locally through Ollama.** The whole pipeline is one morning run:

```
mail (IMAP, read-only) ─┐
calendars (iCal) ───────┤
Todoist · GitHub ───────┼──> Gemma 4 on your laptop ──> edition.json ──┬─> flip-through newspaper
weather (Open-Meteo) ───┤    (Ollama, JSON schema)                     ├─> audio briefing
news (Google · RSS · HN)┘                                              └─> email · Telegram · Slack · Discord · ntfy
```

A few decisions that made it work:

**1. The model answers in a schema, not in prose.** Ollama's structured outputs let me pass a JSON schema (`headline`, `lede`, `must_do_today`, `needs_reply`, `fyi`, `news`, `podcast_script`), so a 4B-class model on a fanless MacBook Air returns something I can lay out every single time. For news, it doesn't rewrite headlines. It picks stories by index, so every link in the paper is real.

**2. The prompt is mostly about not making things up.** "Use ONLY the facts in the input." "Security alerts, bills and deadlines are urgent; newsletters are noise." And one rule I only added after the first test run: emails say "tomorrow" relative to *when they were received*. Gemma had read Sunday night's "before our call tomorrow" literally on Monday morning. One sentence in the prompt fixed it.

**3. One small thing will bite you: Ollama's default context window.** It is small. Forty emails plus news overflow it, and the model silently never sees the rest. Setting `num_ctx: 16384` is the most important line in the project.

**4. Integrations are one function plus one line.** Every source and delivery is a plain function, switched on by its environment variables in a small registry:

```python
SOURCES = {
    "mail":     (("MAIL_USER", "MAIL_PASSWORD"), sources.mail,      "emails"),
    "calendar": (("ICAL_URLS",),                 sources.calendars, "calendar"),
    "todoist":  (("TODOIST_TOKEN",),             sources.todoist,   "tasks"),
    "weather":  (("WEATHER_CITY",),              sources.weather,   "weather"),
    # ...
}
```

It covers about 25 services:
- **Mail:** Gmail, iCloud, Fastmail, Yahoo and others, over IMAP.
- **Calendars:** any iCal link (Google, Outlook, Apple).
- **Tasks:** Todoist and GitHub notifications.
- **Weather:** Open-Meteo.
- **News:** Google News, any RSS feed, Hacker News.
- **Delivery:** email, Telegram, Slack, Discord and ntfy.

A broken source is logged and skipped. One flaky API should never cancel the morning paper. `uv run localhost-times --list` shows what's switched on.

**5. Nearly everything is the standard library.** `imaplib` (opened read-only with `BODY.PEEK`, so nothing gets marked as read), `smtplib`, `urllib`, `xml.etree`. The only runtime dependencies are `icalendar`, `recurring-ical-events` (your daily standup is a recurring event, and a naive parser misses it) and `python-dotenv`.

**6. The voice.** The briefing script is written for the ear: no lists, no URLs, no email addresses. ElevenLabs reads it aloud (`eleven_flash_v2_5`). With `VOICE=say`, macOS's built-in voice does it instead, so the whole pipeline runs with the wifi off.

**7. The paper turns.** The web edition and the landing page use [StPageFlip](https://github.com/Nodlik/StPageFlip): drag a corner and the page curls. You get two-page spreads on desktop, swipe on a phone and arrow keys everywhere. With `prefers-reduced-motion` it becomes a calm scrolling page. The emailed edition is the same set of pages as one column, because mail clients strip scripts.

On my M3 MacBook Air, Gemma 4 (`gemma4:e4b`) prints a full edition in about a minute.

## Why Does Open Innovation Matter?

Your inbox is the most private thing you own. It holds your bank's security alerts, your doctor, your landlord, your mum.

Every "AI morning briefing" product I could find works the same way: connect your Google account, and their servers read your mail. For my friend, that was a deal-breaker, and I think they're right.

Open-weight models change that deal:

- **It runs where the data already is.** Gemma 4 reads the mail on the laptop the mail is already on. Nothing gets uploaded to be summarised. Every edition carries an honest byline: "Written on-device by gemma4:e4b". If you point it at a remote server, it says so.
- **It costs nothing per morning.** No API bill, no subscription and no rate limit, so it can run every day for years.
- **It can't be taken away.** No one can deprecate the model, change the terms or start training on my friend's mail. The weights are on the disk.
- **It works offline.** With the macOS voice, the whole thing runs on a plane.
- **It's open all the way down.** Ollama, Gemma, StPageFlip, Open-Meteo, Hacker News's public API. The project is MIT-licensed so anyone can print their own paper, and the README explains how to add an integration in three steps.

A closed API would have made this easier to demo and impossible to trust. Here, open was the feature.

## My Agent Session

I built this overnight with Claude Code as my pair. The session is saved with DevRelay:

TODO(you): DevRelay `agent_session` embed

Every commit is also linked to the agent session that produced it, using [Entire](https://entire.io). The checkpoints are pushed to the repo, so you can see *why* each piece of code exists.

## Handing It Over

TODO(you): what happened when your friend got their first edition at 7:00. What did they say? What did the paper catch that they would have missed?

## Prize Categories

- **Best Use of Gemma:** Gemma 4 (`gemma4:e4b`) is the editor. It runs locally through Ollama and writes every edition as schema-constrained JSON: headline, triage, news picks and the spoken script.
- **Best Use of Render:** the landing page and the live demo edition are a static site on Render, deployed from a `render.yaml` blueprint.
- **ElevenLabs:** gives the open-source agent its voice. The daily briefing is narrated with ElevenLabs text-to-speech.
- **Entire:** the agent sessions behind the code are checkpointed with Entire and pushed alongside the repo.
- **GitHub Copilot:** the project is automated with GitHub Actions. CI runs the offline test suite and the CLI on every push and pull request.

*Thanks for reading. If you print your own paper, tell me what was on your front page.*
