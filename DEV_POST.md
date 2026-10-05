*This is a submission for the [Hacktoberfest Weekend Challenge: Build for a Friend](https://dev.to/challenges/hacktoberfest-weekend-2026-10-01)*

In 1995, Nicholas Negroponte imagined "The Daily Me": a newspaper edited for exactly one reader. Thirty years later we got the opposite: a dozen apps, each fighting for the first ten minutes of our morning.

## What I Built

My friend starts every day the same way, half awake with a toothbrush in hand. Open Gmail. Open the calendar. Check the weather. Scroll the news. By the time they've worked out what actually matters today, the coffee is cold. So they asked me for something simple: *read it all for me, and tell me what my day looks like.*

There was one condition: they didn't want to hand their entire inbox to yet another cloud AI.

So I built **The Localhost Times**: *All the news that's fit to print. Printed on your machine.*

Every morning it reads your inbox, today's calendar, your tasks, the weather and the news. Then an open-weight model **running on your own laptop** writes two things:

- 📰 **A one-page newspaper** you can flip through in the browser (it really turns pages) or read straight from your inbox.
- 🎧 **A 3-minute audio briefing**, written to be heard while you brush your teeth.

The paper has a front page with the headline of your day, then:

- **Today:** your calendar.
- **Must do:** actions pulled from your email and tasks.
- **Waiting on you:** people who need a reply.
- **Worth knowing:** things that need no action.
- **The world:** the four stories most relevant to you.

## Demo

- **Landing page:** https://mohamedaminehamdi.github.io/the-localhost-times/. It's a newspaper you flip through (drag a corner, swipe, or use the arrow keys), with a `.env` builder that runs entirely in your browser.
- **Today's demo edition:** https://mohamedaminehamdi.github.io/the-localhost-times/demo/. It was written by Gemma 4 for Sam, a made-up reader with a made-up inbox, using real news and real weather. Press play on the audio bar.

## Code

{% github mohamedaminehamdi/the-localhost-times %}

## How I Built It

**The editor is Gemma 4 (`gemma4:e4b`), running locally through Ollama.** The whole thing is one morning run:

```
mail (IMAP, read-only) ─┐
calendars (iCal) ───────┤
Todoist · GitHub ───────┼──> Gemma 4 on your laptop ──> edition.json ──┬─> flip-through newspaper
weather (Open-Meteo) ───┤    (Ollama, JSON schema)                     ├─> audio briefing
news (Google · RSS · HN)┘                                              └─> email · Telegram · Slack · Discord · ntfy
```

A few decisions made it work:

**1. The model answers in a schema, not in prose.** Ollama's structured outputs take a JSON schema (`headline`, `lede`, `must_do_today`, `needs_reply`, `fyi`, `news`, `podcast_script`). That way a 4B-class model on a fanless MacBook Air returns something I can lay out every single time. For the news it doesn't rewrite headlines. It picks stories by index, so every link in the paper is real.

**2. The prompt is mostly about not making things up.** It says "Use ONLY the facts in the input". My first test run then taught me three more rules:
- Gemma read Sunday night's "before our call tomorrow" on Monday morning and told the reader the call was tomorrow. Now: *an email received yesterday that says "tomorrow" means today.*
- It filed a bank's "new sign-in" alert under "worth knowing". Now: *a security alert is always the first must-do.*
- It padded "Must do" with calendar events. Now: *must-dos are things you actively do: send, pay, reply, check.*

A small model follows rules it is given explicitly, and stumbles on rules it's expected to infer.

**3. One setting that's easy to miss: Ollama's default context window is small.** Forty emails plus the news overflow it, and the model silently never sees the rest. `num_ctx: 16384` is the most important line in the project.

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

That gives 20+ integrations:

| | |
|---|---|
| **Mail** (IMAP) | Gmail, iCloud, Fastmail, Yahoo, Zoho, AOL, GMX, any IMAP server |
| **Calendars** | Any iCal link: Google, Outlook, Apple |
| **Tasks** | Todoist, GitHub notifications |
| **Weather** | Open-Meteo |
| **News** | Google News, any RSS feed, Hacker News |
| **Editor** | Ollama, or any OpenAI-compatible local server: LM Studio, llama.cpp, vLLM, Jan |
| **Delivery** | Email, Telegram, Slack, Discord, ntfy |

A broken source is logged and skipped, because one flaky API should never cancel the morning paper. `uv run localhost-times --list` shows what's switched on.

**5. Nearly everything is the standard library.** It uses `imaplib` (opened read-only with `BODY.PEEK`, so nothing gets marked as read), `smtplib`, `urllib` and `xml.etree`. There are only three runtime dependencies:
- `icalendar`
- `recurring-ical-events`, because your daily standup is a recurring event and a naive parser misses it
- `python-dotenv`

**6. The voice.** The briefing script is written for the ear: no lists, no URLs, no email addresses. By default macOS's built-in voice reads it aloud (that's what the demo uses), so the whole pipeline runs with the wifi off. Add an ElevenLabs key and it switches to ElevenLabs.

**7. The paper turns.** The demo edition and the landing page use [StPageFlip](https://github.com/Nodlik/StPageFlip): drag a corner and the page curls.
- Desktop shows two-page spreads sized to your window.
- Phones get a calm scrolling paper.
- So does anyone with `prefers-reduced-motion` turned on.
- The emailed edition is the same pages in one column, because mail clients strip scripts.

On my fanless M3 MacBook Air, Gemma 4 prints a full edition in 70 to 90 seconds, before the kettle boils.

## Why Does Open Innovation Matter?

Your inbox is the most private thing you own. It holds your bank's security alerts, your doctor, your landlord, your mum.

The AI morning briefings I tried all work the same way: connect your Google account, and their servers read your mail. For my friend that was a deal-breaker, and I think they're right.

Open-weight models change that deal:

- **It runs where the data already is.** Gemma 4 reads the mail on the laptop the mail is already on. Nothing is uploaded to be summarised. Every edition carries an honest byline, "Written on-device by gemma4:e4b". If you point it at a remote server, the byline says so.
- **It costs nothing per morning.** No API bill, no subscription, no rate limit, so it can run every day for years.
- **It can't be taken away.** No one can deprecate the model, change the terms or start training on my friend's mail. The weights are on the disk.
- **It works offline.** With the macOS voice, you can print your paper on a plane.
- **It's open all the way down:** Ollama, Gemma, StPageFlip, Open-Meteo, Hacker News's public API. The project is MIT licensed so anyone can print their own paper, and the README shows how to add an integration in three steps.

A closed API would have made this easier to demo and impossible to trust. Here, open *was* the feature.

## My Agent Session

I built this overnight with Claude Code as my pair programmer. Every commit is linked to the agent session that produced it with [Entire](https://entire.io). The checkpoints are pushed to the repo (`refs/entire/checkpoints/*`), so you can see *why* each piece of code exists, not just what it does.

## Prize Categories

- **Best Use of Gemma:** Gemma 4 (`gemma4:e4b`) is the editor. It runs locally through Ollama and writes every edition as schema-constrained JSON: the headline, the triage of your inbox, the news picks and the spoken script.
- **GitHub Copilot:** the project is automated with GitHub Actions. One workflow runs the offline test suite and the CLI on every push and pull request. Another publishes the landing page and the demo edition to GitHub Pages.
- **Entire:** the agent sessions behind the code are checkpointed with Entire and pushed alongside the repo.

*Thanks for reading! If you print your own paper, tell me what was on your front page.* 🗞️
