"""Stage 5 — Thumbnail: generates a real 1280x720 PNG + spec JSON."""
import textwrap
from pathlib import Path

from . import util

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFNS.ttf",
]

_W, _H = 1280, 720


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


def _fetch_background(topic, odir):
    """Try Pexels for a relevant background; fall back to gradient."""
    from core.visuals import _pexels_download
    dest = odir / "thumbnail_bg.jpg"
    terms = ["woman finance", "latina family", "faith money", "success woman"]
    for t in terms:
        if _pexels_download(t, dest, orientation="landscape"):
            return dest
    return None


def _make_thumbnail_png(title, overlay_text, bg_path, out_path):
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    import textwrap as tw

    if bg_path and Path(bg_path).exists():
        img = Image.open(str(bg_path)).convert("RGB")
        img = img.resize((_W, _H), Image.LANCZOS)
        img = ImageEnhance.Brightness(img).enhance(0.35)
        # Gradient overlay (left side darker for text)
        overlay = Image.new("RGBA", (_W, _H), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        for x in range(_W // 2):
            alpha = int(180 * (1 - x / (_W // 2)))
            draw_ov.line([(x, 0), (x, _H)], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    else:
        img = Image.new("RGB", (_W, _H), (15, 52, 96))

    draw = ImageDraw.Draw(img)

    # Channel label (small, top-left)
    small_font = _get_font(32)
    if small_font:
        draw.text((60, 50), "Dinero con Propósito", font=small_font, fill=(255, 200, 80))

    # Main hook text (large, centered-left)
    hook_font = _get_font(88)
    lines = tw.wrap(overlay_text, width=14)[:3]
    y = _H // 2 - len(lines) * 55
    for line in lines:
        if hook_font:
            # Shadow
            draw.text((62, y + 4), line, font=hook_font, fill=(0, 0, 0, 200))
            draw.text((60, y), line, font=hook_font, fill=(255, 255, 255))
        y += 110

    # Accent bar
    draw.rectangle([(55, _H - 100), (55 + len(overlay_text) * 28, _H - 88)],
                   fill=(255, 180, 0))

    img.save(str(out_path), "JPEG", quality=95)
    return out_path


def generate(config, idea, odir):
    topic = idea["topic"]
    overlay_text = _hook_words(idea["chosen_title"])

    spec = {
        "image_prompt": (
            f"high-contrast YouTube thumbnail, single emotive subject, warm gold + deep teal palette, "
            f"shallow depth of field, dramatic rim light, copy-space on the left third, theme: {topic}, "
            f"no text in the image, 1280x720"
        ),
        "overlay_text": overlay_text,
        "overlay_rules": {
            "max_words": 4,
            "font": "bold condensed sans (Anton / Montserrat ExtraBold)",
            "color": "#FFFFFF with #1A1A1A stroke",
            "position": "left third, vertically centered",
        },
        "ab_variants": 2,
    }
    util.write_json(odir / "thumbnail_spec.json", spec)

    # Generate actual PNG
    try:
        bg = _fetch_background(topic, odir)
        _make_thumbnail_png(idea["chosen_title"], overlay_text, bg, odir / "thumbnail.jpg")
        util.log("thumbnail", f"PNG written, overlay: {overlay_text!r}")
    except Exception as e:
        util.log("thumbnail", f"PNG failed ({e}); spec written, overlay: {overlay_text!r}")

    return spec


def _hook_words(title):
    cleaned = title.replace("(", "").replace(")", "").replace("…", "")
    words = cleaned.split()
    return " ".join(words[:4]).upper()
