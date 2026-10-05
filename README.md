# The Daily Me

A private morning newspaper with exactly one reader.

Every morning it reads your inbox, today's calendar and the news, then hands you a
one-page newspaper to read and a 3-minute audio briefing to listen to while you
brush your teeth. A friend asked for it. They wanted their day to fit on one page.

**Your inbox is read by Gemma 4 running on your own laptop.** Nothing in it is
sent to a cloud model. The only thing that leaves the machine is the finished
briefing script, which goes to text-to-speech.

Live demo (a made-up reader, Sam): see the Render link in the DEV post.

## How it works

```
Gmail (IMAP, read-only) ─┐
Google Calendar (iCal) ──┼─> Gemma 4 via Ollama, on-device ──> edition.json
Google News (RSS) ───────┘    (JSON-schema output, no invented facts)
                                         │
                     ┌───────────────────┼────────────────────┐
                     v                   v                    v
              index.html          edition.mp3            email to you
              (newspaper)     (ElevenLabs voice)    (page + audio attached)
```

One file, [`daily_me.py`](daily_me.py). Standard library for mail, news, HTML and SMTP.

## Run it

```bash
brew install ollama && ollama pull gemma4:e4b
cp .env.example .env      # Gmail app password, iCal URL, ElevenLabs key
uv run daily_me.py        # today's edition -> editions/<date>/ and your inbox
uv run daily_me.py --demo # demo reader -> site/ (what's deployed on Render)
```

Every morning at 7:

```
0 7 * * * cd /path/to/the-daily-me && /opt/homebrew/bin/uv run daily_me.py
```

Flags: `--no-audio` (skip text-to-speech), `--no-send` (don't email).

## Privacy model

| Data | Where it goes |
|---|---|
| Emails, calendar | Read on your laptop by Gemma 4 (Ollama). IMAP is opened read-only; nothing is marked as read. |
| Finished briefing script | ElevenLabs, to become audio. Use `--no-audio` to keep everything local. |
| The edition | Emailed to you through your own Gmail. |
| Demo site | A made-up inbox only. Real editions are never uploaded. |

## Built with

- [Gemma 4](https://ollama.com/library/gemma4), open-weight, local through [Ollama](https://ollama.com)
- [ElevenLabs](https://elevenlabs.io) text-to-speech
- [Render](https://render.com) static site for the public demo
- [Entire](https://entire.io) to keep the agent sessions behind the code

Built for the DEV Hacktoberfest 2026 Weekend Challenge, "Build for a Friend". MIT licensed.
