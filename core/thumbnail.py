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
    from PIL import Image, ImageDraw, ImageEnhance
    import textwrap as tw

    if bg_path and Path(bg_path).exists():
        img = Image.open(str(bg_path)).convert("RGB")
        # Scale-to-cover: preserve aspect ratio, center-crop excess (no stretching)
        src_w, src_h = img.size
        scale = max(_W / src_w, _H / src_h)
        nw, nh = int(src_w * scale), int(src_h * scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        left, top = (nw - _W) // 2, (nh - _H) // 2
        img = img.crop((left, top, left + _W, top + _H))
        img = ImageEnhance.Brightness(img).enhance(0.28)
        # Full vignette: dark edges, slightly lighter center
        overlay = Image.new("RGBA", (_W, _H), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        for y in range(_H):
            alpha = int(100 * (y / _H))
            draw_ov.line([(0, y), (_W, y)], fill=(0, 0, 0, alpha))
        for x in range(_W // 3):
            alpha = int(160 * (1 - x / (_W // 3)))
            draw_ov.line([(x, 0), (x, _H)], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    else:
        # Rich vertical gradient: deep navy top → dark teal bottom
        img = Image.new("RGB", (_W, _H))
        draw_bg = ImageDraw.Draw(img)
        for y in range(_H):
            r = int(10 + (15 - 10) * y / _H)
            g = int(14 + (52 - 14) * y / _H)
            b = int(40 + (96 - 40) * y / _H)
            draw_bg.line([(0, y), (_W, y)], fill=(r, g, b))

    draw = ImageDraw.Draw(img)

    # --- Gold brand bar across the top ---
    draw.rectangle([(0, 0), (_W, 9)], fill=(255, 180, 0))

    # --- Channel label (small, top-left, gold) ---
    small_font = _get_font(34)
    if small_font:
        draw.text((52, 24), "DINERO CON PROPÓSITO", font=small_font, fill=(255, 200, 80))

    # --- Main hook text — large, CENTERED, 2 lines max ---
    hook_font = _get_font(112)
    lines = tw.wrap(overlay_text, width=13)[:2]
    line_h = 130
    total_h = len(lines) * line_h
    y = (_H - total_h) // 2 - 18  # slightly above center

    for line in lines:
        if hook_font:
            try:
                bbox = draw.textbbox((0, 0), line, font=hook_font)
            except Exception:
                bbox = (0, 0, len(line) * 60, 100)
            tw_px = bbox[2] - bbox[0]
            x = (_W - tw_px) // 2
            # Multi-pass shadow/outline (8 directions)
            for ox, oy in [(-5, -5), (5, -5), (-5, 5), (5, 5),
                            (0, 6), (6, 0), (-6, 0), (0, -6)]:
                draw.text((x + ox, y + oy), line, font=hook_font, fill=(0, 0, 0))
            # White main text
            draw.text((x, y), line, font=hook_font, fill=(255, 255, 255))
        y += line_h

    # --- Gold accent bar centered below text ---
    bar_w = 440
    bar_h = 11
    bar_x = (_W - bar_w) // 2
    bar_y = y + 12
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], fill=(255, 180, 0))

    # --- Subtitle line (channel + CTA) at bottom ---
    cta_font = _get_font(28)
    if cta_font:
        cta_text = "▶  Mira el video completo  •  @DineroConProposito"
        try:
            bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
            cta_w = bbox[2] - bbox[0]
        except Exception:
            cta_w = len(cta_text) * 16
        cx = (_W - cta_w) // 2
        draw.text((cx + 1, _H - 48 + 1), cta_text, font=cta_font, fill=(0, 0, 0))
        draw.text((cx, _H - 48), cta_text, font=cta_font, fill=(200, 200, 200))

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
            "position": "centered, 2 lines max",
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
