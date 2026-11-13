"""ElevenLabs voice for the WREL announcer. Optional, and the only script that uses the network.

It runs only when you ask for it (--voice elevenlabs) with your own key in the
ELEVENLABS_API_KEY environment variable. It sends the broadcast script text, and
nothing else, to ElevenLabs text to speech and caches each segment by a hash of
voice, model and text, so a re-run with the same data costs nothing and gives the
same audio. Raw data never leaves your machine.

Release Radio, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import hashlib
import json
import os
import struct
import urllib.request
from pathlib import Path

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_22050"
DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # an ElevenLabs premade voice; pick your own vintage announcer with --voice-id
DEFAULT_MODEL = "eleven_multilingual_v2"
SETTINGS = {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True}


def cache_key(voice_id, model, text):
    return hashlib.sha256(f"{voice_id}|{model}|{text}".encode()).hexdigest()[:16]


def request_for(text, voice_id, model, api_key):
    body = json.dumps({"text": text, "model_id": model, "voice_settings": SETTINGS}).encode()
    return urllib.request.Request(API.format(voice=voice_id), data=body, method="POST",
                                  headers={"xi-api-key": api_key, "Content-Type": "application/json",
                                           "Accept": "audio/pcm"})


def render(segments, cache_dir, voice_id=DEFAULT_VOICE, model=DEFAULT_MODEL, api_key=None, opener=urllib.request.urlopen):
    """Returns {segment id: path to 22.05 kHz 16-bit mono PCM}. Fetches only what is not cached."""
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    out, fetched = {}, 0
    for seg in segments:
        path = cache / f"{cache_key(voice_id, model, seg['text'])}.pcm"
        if not path.exists():
            if not api_key:
                raise SystemExit("ELEVENLABS_API_KEY is not set. Set it, or use --voice browser.")
            with opener(request_for(seg["text"], voice_id, model, api_key), timeout=120) as resp:
                path.write_bytes(resp.read())
            fetched += 1
        out[seg["id"]] = path
    print(f"Voice: {len(out)} segments ({fetched} from ElevenLabs, {len(out) - fetched} cached) in {cache}")
    return out


def load_pcm(path):
    data = Path(path).read_bytes()
    n = len(data) // 2
    return [v / 32768 for v in struct.unpack(f"<{n}h", data[:n * 2])]


def api_key_from_env():
    return os.environ.get("ELEVENLABS_API_KEY")
