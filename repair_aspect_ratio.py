#!/usr/bin/env python3
"""One-shot repair: re-render all final.mp4 files with aspect-ratio-corrected encoding.

The original encode used scale=W:H (force-stretching) and img.resize((W,H)) (same).
This script re-runs _render_local() — which now uses scale-to-cover + center-crop —
for every output directory that already has a final.mp4.

Audio: prefers voiceover.mp3; converts voiceover.aiff → .mp3 via ffmpeg if needed.
Clips: uses the cached Pexels clips in media/ or ~/.cache/faceless_factory/pexels_clips/.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import util, assemble

# Load .env so PEXELS_API_KEY etc. are available to _pexels_video_download
util.load_env()

OUTPUT_DIR = ROOT / "output"


def _ensure_mp3(odir, ffmpeg):
    """Return path to voiceover.mp3, converting .aiff if necessary."""
    mp3 = odir / "voiceover.mp3"
    if mp3.exists() and mp3.stat().st_size > 1000:
        return str(mp3)
    aiff = odir / "voiceover.aiff"
    if aiff.exists():
        util.log("repair", f"converting aiff→mp3: {aiff.name}")
        r = subprocess.run(
            [ffmpeg, "-y", "-i", str(aiff), "-b:a", "192k", str(mp3)],
            capture_output=True, text=True,
        )
        if r.returncode == 0 and mp3.exists():
            return str(mp3)
        util.log("repair", f"aiff→mp3 failed: {r.stderr[-120:]}")
    return None


def repair_one(config, odir):
    """Re-render final.mp4 for a single output directory."""
    sb_path = odir / "storyboard.json"
    if not sb_path.exists():
        util.log("repair", f"SKIP (no storyboard.json): {odir.name}")
        return False

    manifest_path = odir / "manifest.json"
    topic = None
    if manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        topic = m.get("topic")

    storyboard = json.loads(sb_path.read_text(encoding="utf-8"))
    # storyboard.json may be {"storyboard": [...]} or a bare list
    if isinstance(storyboard, dict):
        storyboard = storyboard.get("storyboard", storyboard)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        util.log("repair", "ffmpeg not found — skipping")
        return False

    audio_path = _ensure_mp3(odir, ffmpeg)
    if not audio_path:
        util.log("repair", f"SKIP (no usable audio): {odir.name}")
        return False

    util.log("repair", f"re-rendering: {odir.name}")
    ok = assemble._render_local(config, storyboard, audio_path, odir, topic=topic)
    if ok:
        util.log("repair", f"OK: {odir.name}")
    else:
        util.log("repair", f"FAILED: {odir.name}")
    return ok


def main():
    config = util.load_config()
    targets = sorted(
        d for d in OUTPUT_DIR.iterdir()
        if d.is_dir() and (d / "final.mp4").exists()
    )
    util.log("repair", f"Found {len(targets)} videos to repair")
    ok_count = 0
    for odir in targets:
        if repair_one(config, odir):
            ok_count += 1
    util.log("repair", f"Done: {ok_count}/{len(targets)} re-rendered successfully")


if __name__ == "__main__":
    main()
