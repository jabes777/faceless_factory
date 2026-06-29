"""Stage 4 — Assembly. Emits Shotstack JSON + ffmpeg.sh, then renders final.mp4 locally
when ffmpeg is available (using Pillow-generated caption slides so no stock downloads needed).
"""
import shutil
import subprocess
import textwrap

from . import util

# Warm brand gradient palette — one color per shot (cycles if > 8 shots)
_SLIDE_COLORS = [
    (26, 26, 46), (22, 33, 62), (15, 52, 96), (83, 52, 131),
    (45, 106, 79), (27, 67, 50), (64, 145, 108), (82, 183, 136),
]

# System fonts that render Spanish correctly on macOS
_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/SFNSDisplay.ttf",
]


def _get_font(size):
    try:
        from PIL import ImageFont
        for path in _FONT_CANDIDATES:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()
    except Exception:
        return None


def _draw_subtitle(draw, width, height, caption, font):
    """Draw Netflix-style subtitle: 2 lines max, bottom-third, semi-transparent bar."""
    from PIL import Image, ImageDraw
    lines = textwrap.wrap(caption, width=42)[:2]
    text = "\n".join(lines)
    if not font:
        return
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=8)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 20
    bar_y = height - th - pad * 2 - 60
    # Semi-transparent black bar
    bar = Image.new("RGBA", (tw + pad * 2 + 20, th + pad * 2), (0, 0, 0, 160))
    x = (width - bar.width) // 2
    draw._image.paste(bar, (x, bar_y), bar)
    # Text
    tx = (width - tw) // 2
    draw.multiline_text((tx + 2, bar_y + pad + 2), text, font=font,
                        fill=(0, 0, 0, 200), spacing=8, align="center")
    draw.multiline_text((tx, bar_y + pad), text, font=font,
                        fill=(255, 255, 255), spacing=8, align="center")


def _make_slide_photo(width, height, photo_path, caption, out_path):
    """Real photo bg + subtitle-style caption at the bottom."""
    from PIL import Image, ImageDraw, ImageEnhance
    img = Image.open(str(photo_path)).convert("RGBA")
    img = img.resize((width, height), Image.LANCZOS)
    # Slight darken only at the bottom for subtitle legibility
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gradient)
    for y in range(height // 2, height):
        alpha = int(140 * (y - height // 2) / (height // 2))
        gd.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, gradient)
    draw = ImageDraw.Draw(img)
    _draw_subtitle(draw, width, height, caption, _get_font(54))
    img.convert("RGB").save(str(out_path), "PNG")
    return out_path


def _make_slide(width, height, color_rgb, caption, out_path):
    """Color-bg slide + subtitle-style caption (fallback when no Pexels photo)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (width, height), (*color_rgb, 255))
    draw = ImageDraw.Draw(img)
    _draw_subtitle(draw, width, height, caption, _get_font(54))
    img.convert("RGB").save(str(out_path), "PNG")
    return out_path


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

    # Generate PNG slides with Pillow (Pexels photo bg if key present, else color)
    from core.visuals import _pexels_download
    segment_paths = []
    for i, shot in enumerate(storyboard):
        color_rgb = _SLIDE_COLORS[i % len(_SLIDE_COLORS)]
        dur = shot["duration_hint_sec"]
        caption = shot.get("narration_excerpt", "")
        png_path = media_dir / f"shot_{i:02d}.png"
        seg_path = str(media_dir / f"shot_{i:02d}.mp4")

        # Try Pexels photo background, fall back to color slide
        stock_path = media_dir / f"stock_{i:02d}.jpg"
        have_stock = _pexels_download(shot.get("stock_query", ""), stock_path)
        if have_stock:
            _make_slide_photo(int(w), int(h), stock_path, caption, png_path)
        else:
            _make_slide(int(w), int(h), color_rgb, caption, png_path)

        cmd = [
            ffmpeg, "-y",
            "-loop", "1", "-i", str(png_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-t", str(dur), "-r", str(fps),
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
