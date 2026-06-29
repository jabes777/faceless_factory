"""Stage 3 — Visual plan: storyboard, stock queries, and Pexels image downloads."""
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from . import util

# English search terms that return better Pexels results than Spanish keywords
_QUERY_MAP = {
    "dinero": "money", "deuda": "debt", "ahorro": "savings", "familia": "family",
    "presupuesto": "budget", "trabajo": "work", "mujer": "woman", "latina": "latina woman",
    "dios": "faith prayer", "iglesia": "church", "casa": "house home", "niños": "children",
    "ansiedad": "anxiety stress", "paz": "peace calm", "negocio": "business entrepreneur",
    "tarjeta": "credit card", "banco": "bank", "ingreso": "income salary",
}


def _segments(script_text):
    return [p.strip() for p in script_text.split("\n\n") if p.strip() and not p.startswith("[")]


def _keywords(paragraph):
    words = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{5,}", paragraph)
    stop = {"porque", "cuando", "tienes", "puedes", "vamos", "mucho", "sobre", "donde",
            "perder", "misma", "ellos", "ellas", "nunca", "siempre", "manera", "manera"}
    uniq = [w.lower() for w in words if w.lower() not in stop]
    return list(dict.fromkeys(uniq))[:3] or ["family", "hope"]


def _english_query(keywords):
    for kw in keywords:
        if kw in _QUERY_MAP:
            return _QUERY_MAP[kw]
    return " ".join(keywords[:2])


def _pexels_download(query, dest_path, orientation="landscape"):
    """Download one Pexels photo for the given query. Returns True on success."""
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        return False
    try:
        import requests
        eq = _english_query(query.split())
        headers = {
            "Authorization": key,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": eq, "per_page": 3, "orientation": orientation},
            headers=headers, timeout=15,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            return False
        img_url = photos[0]["src"]["large2x"]
        img_data = requests.get(img_url, headers={"User-Agent": headers["User-Agent"]}, timeout=30)
        img_data.raise_for_status()
        Path(dest_path).write_bytes(img_data.content)
        return True
    except Exception as e:
        util.log("visuals", f"Pexels fetch failed for '{query}': {e}")
        return False


def generate(config, script_text):
    segs = _segments(script_text)
    storyboard = []
    for i, seg in enumerate(segs):
        kw = _keywords(seg)
        storyboard.append({
            "shot": i + 1,
            "narration_excerpt": seg[:120] + ("…" if len(seg) > 120 else ""),
            "stock_query": " ".join(kw),
            "image_prompt": f"cinematic, warm light, {', '.join(kw)}, no text, {config['visuals']['aspect_ratio']}",
            "on_screen_caption": config["visuals"]["captions"],
            "duration_hint_sec": max(6, round(len(seg.split()) / 2.5)),
        })

    has_pexels = util.has_key("PEXELS_API_KEY")
    util.log("visuals", f"{len(storyboard)}-shot storyboard, captions={config['visuals']['captions']}, pexels={has_pexels}")
    return {"storyboard": storyboard, "stock_provider": config["visuals"]["stock_provider"],
            "pexels_available": has_pexels}
