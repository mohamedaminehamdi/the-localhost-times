"""Get the paper to the reader. Each delivery takes (env, edition) where edition has
headline, summary (plain text), html (email version), audio (Path or None) and subject."""
import json
import smtplib
import ssl
import urllib.parse
from email.message import EmailMessage

from . import net
from .sources import domain, host_port

SMTP_HOSTS = {
    "gmail.com": "smtp.gmail.com:465", "googlemail.com": "smtp.gmail.com:465",
    "icloud.com": "smtp.mail.me.com:587", "me.com": "smtp.mail.me.com:587", "mac.com": "smtp.mail.me.com:587",
    "fastmail.com": "smtp.fastmail.com:465", "fastmail.fm": "smtp.fastmail.com:465",
    "yahoo.com": "smtp.mail.yahoo.com:465", "zoho.com": "smtp.zoho.com:465",
    "aol.com": "smtp.aol.com:465", "gmx.com": "mail.gmx.com:465", "gmx.net": "mail.gmx.net:465",
}
AUDIO_TYPES = {".mp3": "audio/mpeg", ".m4a": "audio/mp4"}


def _audio(edition):
    path = edition["audio"]
    return (path.name, path.read_bytes(), AUDIO_TYPES.get(path.suffix, "application/octet-stream")) if path else None


def email(env, edition):
    user = env["MAIL_USER"]
    host, port = host_port(env.get("SMTP_HOST") or SMTP_HOSTS.get(domain(user), f"smtp.{domain(user)}:465"), 465)
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = edition["subject"], user, env.get("SEND_TO", user)
    msg.set_content(edition["summary"])
    msg.add_alternative(edition["html"], subtype="html")
    if audio := _audio(edition):
        _, data, ctype = audio
        maintype, subtype = ctype.split("/")
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=f"the-localhost-times{edition['audio'].suffix}")
    ctx = ssl.create_default_context()
    smtp = smtplib.SMTP_SSL(host, port, context=ctx) if port == 465 else smtplib.SMTP(host, port)
    with smtp:
        if port != 465:
            smtp.starttls(context=ctx)
        smtp.login(user, env["MAIL_PASSWORD"])
        smtp.send_message(msg)


def telegram(env, edition):
    api = f"https://api.telegram.org/bot{env['TELEGRAM_BOT_TOKEN']}"
    chat = env["TELEGRAM_CHAT_ID"]
    net.post_json(f"{api}/sendMessage", {"chat_id": chat, "text": edition["summary"][:4096]})
    if audio := _audio(edition):
        net.post_multipart(f"{api}/sendAudio", {"chat_id": chat, "title": edition["headline"][:64],
                                                "performer": "The Localhost Times"}, {"audio": audio})


def slack(env, edition):
    net.post_json(env["SLACK_WEBHOOK_URL"], {"text": edition["summary"]})


def discord(env, edition):
    payload = json.dumps({"content": edition["summary"][:2000]})
    audio = _audio(edition)
    net.post_multipart(env["DISCORD_WEBHOOK_URL"], {"payload_json": payload}, {"files[0]": audio} if audio else {})


def ntfy(env, edition):
    """Push notification (ntfy.sh or self-hosted), with the audio attached when there is one."""
    server = env.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    audio = _audio(edition)
    q = {"title": edition["headline"], "message": edition["summary"][:1000]}
    if audio:
        q["filename"] = audio[0]
    net.request(f"{server}/{env['NTFY_TOPIC']}?{urllib.parse.urlencode(q)}",
                data=audio[1] if audio else b"", method="PUT" if audio else "POST", timeout=120)
