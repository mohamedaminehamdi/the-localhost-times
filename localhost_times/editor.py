"""The editor: an open-weight model that turns the morning's inputs into an edition.

Default: Gemma 4 through a local Ollama. Set LLM_BASE_URL to use any OpenAI-compatible
server instead (LM Studio, llama.cpp, vLLM, Jan, ...).
"""
import datetime as dt
import json

from . import net

_S = {"type": "string"}
SCHEMA = {
    "type": "object",
    "properties": {
        "headline": _S,
        "lede": _S,
        "must_do_today": {"type": "array", "items": _S},
        "needs_reply": {"type": "array", "items": {
            "type": "object", "properties": {"from": _S, "about": _S, "why": _S}, "required": ["from", "about", "why"]}},
        "fyi": {"type": "array", "items": _S},
        "news": {"type": "array", "items": {
            "type": "object", "properties": {"n": {"type": "integer"}, "summary": _S}, "required": ["n", "summary"]}},
        "podcast_script": _S,
    },
    "required": ["headline", "lede", "must_do_today", "needs_reply", "fyi", "news", "podcast_script"],
}

PROMPT = """You are the editor of "The Localhost Times", a private one-page morning newspaper with exactly one reader: {name}.
Today is {date}. Use ONLY the facts in the input. Never invent emails, events, people, times or numbers.
Rules:
1. An email received yesterday ({yesterday}) that says "tomorrow" means TODAY. Write "today", never "tomorrow", for those.
2. A security alert (new sign-in, password reset, card blocked) is ALWAYS the first item of must_do_today, never fyi.
3. Bills, rent and deadlines due today are must_do_today. Newsletters and promotions are noise: leave them out or put them in fyi.
4. The calendar is printed separately: must_do_today must NOT list meetings, lunches or other calendar events.
   It lists things {name} has to actively DO (send, pay, reply, check, book, buy).
- headline: the single most important thing about {name}'s day, newspaper style, max 10 words.
- lede: 2 warm, specific sentences that set up the day (mention the weather if given).
- must_do_today: concrete actions for today from emails and tasks, most urgent first, max 6, each starting with a verb.
- needs_reply: emails where a real person (not a company or a robot) is waiting on {name}, max 5.
- fyi: things worth knowing that need no action today, max 5.
- news: pick the 4 stories most relevant to {name} by their "n", preferring their own topics over general headlines; one plain sentence each.
- podcast_script: about 400 words read aloud while {name} brushes their teeth. Warm, crisp, a little witty.
  Greet with the date and weather, walk through the schedule, what needs action, what can wait, then the news, then a short kind sign-off.
  Plain spoken sentences only: no lists, no markdown, no URLs, no email addresses."""


def write(name, day, inputs, env):
    messages = [
        {"role": "system", "content": PROMPT.format(name=name, date=day.strftime("%A, %B %-d, %Y"),
                                                    yesterday=(day - dt.timedelta(days=1)).strftime("%A"))},
        {"role": "user", "content": json.dumps(inputs, ensure_ascii=False)},
    ]
    model = env.get("MODEL", "gemma4:e4b")
    if env.get("LLM_BASE_URL"):
        headers = {"Authorization": f"Bearer {env['LLM_API_KEY']}"} if env.get("LLM_API_KEY") else {}
        reply = net.post_json(env["LLM_BASE_URL"].rstrip("/") + "/chat/completions", {
            "model": model, "messages": messages, "temperature": 0.3,
            "response_format": {"type": "json_schema", "json_schema": {"name": "edition", "schema": SCHEMA}},
        }, headers, timeout=900)
        content = reply["choices"][0]["message"]["content"]
    else:
        reply = net.post_json(env.get("OLLAMA_URL", "http://localhost:11434") + "/api/chat", {
            "model": model, "messages": messages, "stream": False, "think": False, "format": SCHEMA,
            # Ollama's default context is small; without this, emails get silently cut off.
            "options": {"temperature": 0.3, "num_ctx": 16384},
        }, timeout=900)
        content = reply["message"]["content"]
    edition = json.loads(content)
    by_n = {story["n"]: story for story in inputs.get("news", [])}
    edition["news"] = [{**by_n[s["n"]], "summary": s["summary"]} for s in edition["news"] if s["n"] in by_n]
    return edition
