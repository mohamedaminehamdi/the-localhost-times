# Contributing to The Localhost Times

Thanks for helping print better papers. Issues and pull requests are welcome.

## Setup

```bash
git clone https://github.com/mohamedaminehamdi/the-localhost-times && cd the-localhost-times
uv run pytest                       # offline tests, no model or network needed
ollama pull gemma4:e4b              # only to print real editions
uv run localhost-times --demo --no-audio
```

## Add an integration in 3 steps

1. **Write one function.**
   - A source goes in `localhost_times/sources.py`. It takes `(env, day)` and returns a list of small dicts.
   - A delivery goes in `localhost_times/deliver.py`. It takes `(env, edition)`.
   - Use the standard library and the helpers in `net.py`. Don't add a dependency unless it's unavoidable.
2. **Register it with one line** in `SOURCES` or `DELIVERIES` in `localhost_times/cli.py`. That line names the environment variables that switch it on and, for a source, the part of the paper it feeds: `emails`, `calendar`, `tasks`, `weather` or `news`.
3. **Document it.**
   - Add its variables to `.env.example` and a row to the README's integrations table.
   - If there is parsing logic, add a small offline test in `tests/` that uses an inline fixture rather than the network.

A broken source is logged and skipped, so one flaky API never cancels the morning paper. Keep it that way.

## Ideas

- Outlook.com mail (needs OAuth)
- CalDAV calendars, Things / Reminders / Linear tasks
- Local, open-weight text-to-speech (Kokoro, Piper)
- A "yesterday's paper" archive page
- Translations of the edition

## Ground rules

- **Private by default.** Nothing that reads personal data may send it anywhere except the reader's configured model, voice and delivery.
- **Facts only.** The editor must never invent emails, events or numbers. If you change the prompt, check a demo edition against `demo_inbox.json`.
- Be kind. This project was built for a friend.
