"""Stage 4 — Assembly. Emits Shotstack JSON + ffmpeg.sh, then renders final.mp4 locally
when ffmpeg is available (using color-slide placeholders so no stock downloads are needed).
"""
import shutil
import subprocess

from . import util

# Warm brand gradient palette — one color per shot (cycles if > 8 shots)
_SLIDE_COLORS = [
    "0x1a1a2e", "0x16213e", "0x0f3460", "0x533483",
    "0x2d6a4f", "0x1b4332", "0x40916c", "0x52b788",
]


def _shotstack_json(config, storyboard, audio_path):
    w, h = config["assemble"]["resolution"].split("x")
    clips = []
    start = 0.0
    for shot in storyboard:
        dur = shot["duration_hint_sec"]
        clips.append({
            "asset": {"type": "image", "src": f"<<URL for stock: {shot['stock_query']}>>"},
            "start": round(start, 2), "length": dur,
            "effect": "zoomIn",
            "transition": {"in": "fade", "out": "fade"},
        })
        start += dur
    timeline = {
        "soundtrack": {"src": "<<music url>>", "effect": "fadeOut"} if config["assemble"]["background_music"] else None,
        "tracks": [{"clips": clips}],
    }
    return {
        "timeline": timeline,
        "output": {"format": "mp4", "size": {"width": int(w), "height": int(h)}, "fps": config["assemble"]["fps"]},
        "merge": [{"find": "voiceover", "replace": audio_path or "<<voiceover.mp3>>"}],
    }


def _render_local(config, storyboard, audio_path, odir):
    """Render final.mp4 using ffmpeg color slides + voiceover (no stock needed).

    Uses the concat demuxer (one segment per shot) to avoid filter_complex escaping
    issues with Spanish/Unicode text in drawtext.
    """
    res = config["assemble"]["resolution"]
    w, h = res.split("x")
    fps = config["assemble"]["fps"]
    ffmpeg = shutil.which("ffmpeg")
    media_dir = odir / "media"
    media_dir.mkdir(exist_ok=True)

    # Render each shot as a silent .mp4 color slide
    segment_paths = []
    for i, shot in enumerate(storyboard):
        color = _SLIDE_COLORS[i % len(_SLIDE_COLORS)]
        dur = shot["duration_hint_sec"]
        seg_path = str(media_dir / f"shot_{i:02d}.mp4")
        cmd = [
            ffmpeg, "-y",
            "-f", "lavfi",
            "-i", f"color=c={color}:s={w}x{h}:r={fps}:d={dur}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-t", str(dur),
            seg_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            util.log("assemble", f"slide {i} error: {r.stderr[-200:]}")
            return False
        segment_paths.append(seg_path)

    # Write concat list
    concat_list = media_dir / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p}'" for p in segment_paths), encoding="utf-8")

    out_path = str(odir / "final.mp4")
    cmd = [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-i", audio_path,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        util.log("assemble", f"ffmpeg concat error: {r.stderr[-300:]}")
        return False
    util.log("assemble", f"rendered -> {out_path}")
    return True


def generate(config, storyboard, audio_path, odir):
    plan = _shotstack_json(config, storyboard, audio_path)
    util.write_json(odir / "render_shotstack.json", plan)

    res = config["assemble"]["resolution"]
    fps = config["assemble"]["fps"]
    ff = (
        "# After downloading stock per render_shotstack.json into ./media as shot_1.jpg, shot_2.jpg ...\n"
        "# and exporting voiceover to voiceover.mp3, run:\n"
        f"ffmpeg -framerate {fps} -pattern_type glob -i 'media/shot_*.jpg' "
        f"-i voiceover.mp3 -c:v libx264 -pix_fmt yuv420p -s {res} -shortest "
        "-vf \"scale={res}:force_original_aspect_ratio=cover,zoompan=z='min(zoom+0.0005,1.1)'\" "
        "final.mp4\n"
    ).replace("{res}", res)
    util.write_text(odir / "render_ffmpeg.sh", ff)

    have_ffmpeg = bool(shutil.which("ffmpeg"))
    rendered = False
    if have_ffmpeg and audio_path and Path(audio_path).exists():
        rendered = _render_local(config, storyboard, audio_path, odir)

    util.log("assemble", f"render plan written (shotstack json + ffmpeg.sh); ffmpeg installed={have_ffmpeg}; rendered={rendered}")
    return {"shotstack_plan": str(odir / "render_shotstack.json"),
            "ffmpeg_script": str(odir / "render_ffmpeg.sh"),
            "ffmpeg_available": have_ffmpeg,
            "rendered": rendered}


# Allow Path usage in generate()
from pathlib import Path  # noqa: E402
