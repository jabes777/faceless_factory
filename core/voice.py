"""Stage 2 — Voiceover.
Live:    ElevenLabs (best quality, needs key)
Offline: edge-tts   (free Microsoft neural TTS, very natural, no key needed)
Fallback: macOS `say`
"""
import asyncio
import json
import os
import shutil
import subprocess
import urllib.request

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
    return str(out_path)


def _edge_tts(text, out_path):
    """Free Microsoft neural TTS via edge-tts — no API key required."""
    try:
        import edge_tts

        async def _run():
            communicate = edge_tts.Communicate(text, _EDGE_VOICE)
            await communicate.save(str(out_path))

        asyncio.run(_run())
        return str(out_path)
    except Exception as e:
        util.log("voice", f"edge-tts failed ({e}); falling back to macOS say")
        return None


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
    if util.has_key("ELEVENLABS_API_KEY") and not config["voice"]["voice_id"].startswith("REPLACE"):
        util.log("voice", "synthesizing with ElevenLabs…")
        audio = _elevenlabs(config, script_text, odir / "voiceover.mp3")
    else:
        util.log("voice", f"synthesizing with edge-tts ({_EDGE_VOICE})…")
        audio = _edge_tts(script_text, odir / "voiceover.mp3")
        if not audio and shutil.which("say"):
            util.log("voice", "falling back to macOS say")
            audio = _macos_say(config, script_text, odir)

    ssml = "<speak>\n" + script_text.replace("\n\n", '\n<break time="700ms"/>\n') + "\n</speak>"
    util.write_text(odir / "voiceover.ssml", ssml)
    util.log("voice", f"audio={'written' if audio else 'SSML only'}")
    return {"audio_path": audio, "ssml_path": str(odir / "voiceover.ssml")}
