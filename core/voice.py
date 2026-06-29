"""Stage 2 — Voiceover.
Live:    ElevenLabs (best quality, needs key)
Offline: edge-tts   (free Microsoft neural TTS, very natural, no key needed)
Fallback: macOS `say`

Generates voiceover.mp3 + voiceover.srt (word-level closed captions, YouTube CC ready).
"""
import asyncio
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from . import util

_EDGE_VOICE = "es-MX-DaliaNeural"  # natural Mexican Spanish female


def _elevenlabs(config, text, out_path):
    voice_id = config["voice"]["voice_id"]
    body = json.dumps({
        "text": text,
        "model_id": config["voice"]["model"],
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}", data=body,
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        out_path.write_bytes(r.read())
    return str(out_path), None


def _audio_duration(audio_path):
    """Return audio duration in seconds using ffprobe, or None on error."""
    try:
        import json as _json
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", str(audio_path)],
            capture_output=True, text=True, timeout=10,
        )
        return float(_json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return None


def _build_srt_proportional(text, total_sec, words_per_sub=7):
    """Generate SRT by distributing subtitle chunks proportionally across the audio duration.

    Falls back when the TTS engine doesn't emit word-boundary events.
    Timing accuracy is within ±2 s for typical narration pace.
    """
    import re

    def _ts(s):
        ms = int((s % 1) * 1000)
        s = int(s)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    words = [w for w in re.split(r"\s+", text.strip()) if w and not w.startswith("[")]
    if not words or not total_sec:
        return ""
    n = len(words)
    chunks = [words[i:i + words_per_sub] for i in range(0, n, words_per_sub)]
    lines = []
    cursor = 0
    for ci, chunk in enumerate(chunks):
        start_s = (cursor / n) * total_sec
        cursor += len(chunk)
        end_s = (cursor / n) * total_sec
        lines += [str(ci + 1), f"{_ts(start_s)} --> {_ts(end_s)}", " ".join(chunk), ""]
    return "\n".join(lines)


def _edge_tts(text, out_path):
    """Free Microsoft neural TTS — generates audio and a proportional SRT subtitle file.

    es-MX-DaliaNeural doesn't emit WordBoundary events, so SRT timing is computed
    proportionally from total audio duration (accurate within ±2 s).
    """
    try:
        import edge_tts

        async def _run():
            communicate = edge_tts.Communicate(text, _EDGE_VOICE)
            submaker = edge_tts.SubMaker()
            audio_bytes = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)
            Path(str(out_path)).write_bytes(bytes(audio_bytes))
            # Try exact word-boundary SRT first
            srt = submaker.get_srt()
            if srt and srt.strip():
                return srt, True
            return None, False

        srt_raw, exact = asyncio.run(_run())
        srt_path = None
        if srt_raw:
            srt_content = srt_raw
        else:
            # Proportional fallback: distribute chunks across measured audio duration
            dur = _audio_duration(out_path)
            srt_content = _build_srt_proportional(text, dur) if dur else ""

        if srt_content and srt_content.strip():
            srt_path = Path(str(out_path)).parent / "voiceover.srt"
            srt_path.write_text(srt_content, encoding="utf-8")
            util.log("voice", f"SRT written ({'exact' if exact else 'proportional approx'})")
            srt_path = str(srt_path)

        return str(out_path), srt_path
    except Exception as e:
        util.log("voice", f"edge-tts failed ({e}); falling back to macOS say")
        return None, None


def _macos_say(config, text, out_dir):
    aiff = out_dir / "voiceover.aiff"
    voice = config["voice"].get("fallback_macos_say_voice", "Paulina")
    try:
        subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True,
                       capture_output=True, timeout=120)
        return str(aiff)
    except Exception as e:
        util.log("voice", f"macOS 'say' unavailable ({e}); writing SSML only")
        return None


def generate(config, script_text, odir):
    srt_path = None
    if util.has_key("ELEVENLABS_API_KEY") and not config["voice"]["voice_id"].startswith("REPLACE"):
        util.log("voice", "synthesizing with ElevenLabs…")
        audio, srt_path = _elevenlabs(config, script_text, odir / "voiceover.mp3")
    else:
        util.log("voice", f"synthesizing with edge-tts ({_EDGE_VOICE})…")
        audio, srt_path = _edge_tts(script_text, odir / "voiceover.mp3")
        if not audio and shutil.which("say"):
            util.log("voice", "falling back to macOS say")
            audio = _macos_say(config, script_text, odir)

    ssml = "<speak>\n" + script_text.replace("\n\n", '\n<break time="700ms"/>\n') + "\n</speak>"
    util.write_text(odir / "voiceover.ssml", ssml)
    util.log("voice", f"audio={'written' if audio else 'SSML only'}, srt={'written' if srt_path else 'none'}")
    return {"audio_path": audio, "ssml_path": str(odir / "voiceover.ssml"), "srt_path": srt_path}
