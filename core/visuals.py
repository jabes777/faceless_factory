"""Stage 3 — Visual plan: storyboard, stock search queries, image prompts, captions."""
import re

from . import util


def _segments(script_text):
    parts = [p.strip() for p in script_text.split("\n\n") if p.strip() and not p.startswith("[")]
    return parts


def _keywords(paragraph, lang):
    # crude keyword pull for stock search; good enough to drive Pexels/Pixabay queries
    words = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{5,}", paragraph)
    stop = {"porque", "cuando", "tienes", "puedes", "vamos", "mucho", "sobre", "donde"}
    uniq = [w.lower() for w in words if w.lower() not in stop]
    return list(dict.fromkeys(uniq))[:3] or ["finance", "hope"]


def generate(config, script_text):
    segs = _segments(script_text)
    lang = config["channel"]["language"]
    storyboard = []
    for i, seg in enumerate(segs):
        kw = _keywords(seg, lang)
        storyboard.append({
            "shot": i + 1,
            "narration_excerpt": seg[:120] + ("…" if len(seg) > 120 else ""),
            "stock_query": " ".join(kw),
            "image_prompt": f"cinematic, warm light, {', '.join(kw)}, no text, {config['visuals']['aspect_ratio']}",
            "on_screen_caption": config["visuals"]["captions"],
            "duration_hint_sec": max(4, len(seg.split()) // 2),
        })
    util.log("visuals", f"{len(storyboard)}-shot storyboard, captions={config['visuals']['captions']}")
    return {"storyboard": storyboard, "stock_provider": config["visuals"]["stock_provider"]}
