"""Read the edition aloud. ElevenLabs if a key is set, else the offline macOS voice, else silence."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from . import net


def engine(env):
    if env.get("VOICE"):
        return env["VOICE"]
    if env.get("ELEVENLABS_API_KEY"):
        return "elevenlabs"
    return "say" if sys.platform == "darwin" else "none"


def speak(text, out_dir, env):
    """Write the briefing audio into out_dir and return its path (None when VOICE=none)."""
    kind = engine(env)
    if kind == "elevenlabs":
        voice = env.get("VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
        audio = net.request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
            data=json.dumps({"text": text, "model_id": env.get("TTS_MODEL", "eleven_flash_v2_5")}).encode(),
            headers={"xi-api-key": env["ELEVENLABS_API_KEY"], "Content-Type": "application/json"},
            timeout=300,
        )
        path = Path(out_dir) / "edition.mp3"
        path.write_bytes(audio)
        return path
    if kind == "say":  # fully offline: macOS speech synthesis + Apple's AAC encoder
        path = Path(out_dir) / "edition.m4a"
        with tempfile.TemporaryDirectory() as tmp:
            script, aiff = Path(tmp) / "script.txt", Path(tmp) / "edition.aiff"
            script.write_text(text)
            subprocess.run(["say", "-f", script, "-o", aiff], check=True)
            subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", aiff, path], check=True)
        return path
    return None
