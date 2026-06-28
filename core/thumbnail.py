"""Stage 5 — Thumbnail spec (CTR-driving). Emits an image prompt + text-overlay layout."""
from . import util


def generate(config, idea, odir):
    topic = idea["topic"]
    spec = {
        "image_prompt": (
            f"high-contrast YouTube thumbnail, single emotive subject, warm gold + deep teal palette, "
            f"shallow depth of field, dramatic rim light, copy-space on the left third, theme: {topic}, "
            f"no text in the image, 1280x720"
        ),
        "overlay_text": _hook_words(idea["chosen_title"]),
        "overlay_rules": {
            "max_words": 4,
            "font": "bold condensed sans (e.g., Anton / Montserrat ExtraBold)",
            "color": "#FFFFFF with #1A1A1A stroke",
            "position": "left third, vertically centered",
            "contrast_check": "must be legible at 168px wide (mobile feed)",
        },
        "ab_variants": 2,
    }
    util.write_json(odir / "thumbnail_spec.json", spec)
    util.log("thumbnail", f"spec written, overlay: {spec['overlay_text']!r}")
    return spec


def _hook_words(title):
    # pull the most clickable 2-4 words from the title
    cleaned = title.replace("(", "").replace(")", "").replace("…", "")
    words = cleaned.split()
    return " ".join(words[:4]).upper()
