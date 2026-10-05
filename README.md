# The Localhost Times

*All the news that's fit to print. Printed on your machine.*

A private morning newspaper with exactly one reader: you.

Every morning it reads your inbox, today's calendar, your tasks, the weather and the news.
Then an open-weight model **running on your own laptop** (Gemma 4 via Ollama) writes:

- a **one-page newspaper** you can flip through in the browser or read in your inbox, and
- a **3-minute audio briefing** to listen to while you brush your teeth.

A friend asked for it. They wanted their whole day to fit on one page, without handing their inbox to someone else's cloud.

**Live demo** (a made-up reader, Sam): https://mohamedaminehamdi.github.io/the-localhost-times/ · [demo edition](https://mohamedaminehamdi.github.io/the-localhost-times/demo/)

## How it works

```
 mail (IMAP, read-only) ─┐
 calendars (iCal) ───────┤
 Todoist · GitHub ───────┼──> Gemma 4 on your laptop ──> edition.json ──┬─> newspaper (flip-through web page)
 weather (Open-Meteo) ───┤    (Ollama, JSON schema,                     ├─> audio briefing (ElevenLabs or macOS voice)
 news (Google · RSS · HN)┘     never invents facts)                     └─> email · Telegram · Slack · Discord · ntfy
```

## Quick start

```bash
brew install ollama && ollama pull gemma4:e4b      # the editor, ~7 GB, runs locally
git clone https://github.com/mohamedaminehamdi/the-localhost-times
cd the-localhost-times
cp .env.example .env                                # switch integrations on
uv run localhost-times --list                       # see what is on
uv run localhost-times                              # print today's edition
```

The edition lands in `editions/<date>/` (open `index.html`) and is delivered wherever you configured.
Prefer clicking? The [landing page](https://mohamedaminehamdi.github.io/the-localhost-times/) has a `.env` builder that runs entirely in your browser.

Print it every morning at 7:

```cron
0 7 * * * cd ~/the-localhost-times && /opt/homebrew/bin/uv run localhost-times
```

Flags: `--list`, `--no-audio`, `--no-send`, `--demo` (prints the public demo into `site/demo/`).

## Integrations

Each one switches on when its variables are set in `.env`. See [`.env.example`](.env.example) for every option.

| | Integrations | Variables |
|---|---|---|
| **Mail** (IMAP, read-only) | Gmail, iCloud, Fastmail, Yahoo, Zoho, AOL, GMX, any IMAP server over SSL | `MAIL_USER`, `MAIL_PASSWORD`, `MAIL_HOST` |
| **Calendars** | Any iCal link: Google, Outlook / Microsoft 365, Apple iCloud, Fastmail | `ICAL_URLS` |
| **Tasks** | Todoist (today + overdue), GitHub notifications | `TODOIST_TOKEN`, `GITHUB_TOKEN` |
| **Weather** | Open-Meteo (no key) | `WEATHER_CITY` |
| **News** | Google News topics, any RSS/Atom feed, Hacker News | `NEWS_TOPICS`, `RSS_FEEDS`, `HACKERNEWS` |
| **Editor** (open models) | Ollama (default Gemma 4), or any OpenAI-compatible server: LM Studio, llama.cpp, vLLM, Jan | `MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` |
| **Voice** | ElevenLabs, macOS built-in voice (fully offline), none | `ELEVENLABS_API_KEY`, `VOICE` |
| **Delivery** | Email (SMTP), Telegram, Slack, Discord, ntfy push, local folder | `SEND_TO`, `TELEGRAM_*`, `SLACK_WEBHOOK_URL`, `DISCORD_WEBHOOK_URL`, `NTFY_TOPIC` |

Outlook.com mail isn't supported yet: Microsoft requires OAuth for IMAP. A good first contribution.

## Privacy model

| Data | Where it goes |
|---|---|
| Emails, calendar, tasks | Read on your machine by the local model. IMAP is opened read-only; nothing is marked as read. |
| The finished briefing script | To ElevenLabs for the voice, if you set a key. With `VOICE=say` (macOS) it never leaves the laptop. |
| The edition | Saved locally and delivered only through the accounts you configure. |
| News, weather | Public feeds, fetched by topic or city. |
| The demo site | A made-up inbox. Real editions are never uploaded anywhere. |

Point `LLM_BASE_URL` at a remote server and your mail goes there instead. The byline on every edition says honestly where it was written.

## Project layout

```
localhost_times/
  cli.py       the morning run, and the integration registry
  sources.py   mail, calendars, tasks, weather, news
  editor.py    the prompt, the JSON schema, Ollama / OpenAI-compatible call
  voice.py     ElevenLabs, macOS say
  render.py    flip-through web page + email version
  deliver.py   email, Telegram, Slack, Discord, ntfy
  net.py       small stdlib HTTP helpers
site/          landing page + demo edition (GitHub Pages)
tests/         offline tests: `uv run pytest`
```

Three runtime dependencies (`icalendar`, `recurring-ical-events`, `python-dotenv`). Everything else is the standard library.

## Contributing

New integrations are the best way in, usually one function and one line. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Built with

[Gemma 4](https://ai.google.dev/gemma) · [Ollama](https://ollama.com) · [ElevenLabs](https://elevenlabs.io) · [StPageFlip](https://github.com/Nodlik/StPageFlip) · [Open-Meteo](https://open-meteo.com)

Built for a friend, for the [DEV Hacktoberfest 2026 Weekend Challenge](https://dev.to/challenges/hacktoberfest-weekend-2026-10-01). MIT licensed.
