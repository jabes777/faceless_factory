"""Stage 3 — Visual plan: storyboard, stock queries, and Pexels image/video downloads.

All assets sourced from Pexels (pexels.com/license/) — royalty-free, commercial use
permitted, no attribution required. Safe for YouTube monetization.
"""
import hashlib
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from . import util

# Global clip cache — shared across all videos so the same query isn't re-downloaded
_CLIP_CACHE_DIR = Path.home() / ".cache" / "faceless_factory" / "pexels_clips"

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


def _pexels_video_download(query, dest_path):
    """Download one Pexels video clip (SD quality) for the given query.

    Uses a global cache keyed by query hash so repeated topics don't re-download.
    License: Pexels Free License — royalty-free, commercial use OK, YouTube monetizable.
    Returns True on success.
    """
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        return False

    # Check global cache first
    _CLIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(query.lower().encode()).hexdigest()[:10]
    cached = _CLIP_CACHE_DIR / f"{cache_key}.mp4"
    if cached.exists() and cached.stat().st_size > 50_000:
        import shutil as _sh
        _sh.copy2(str(cached), str(dest_path))
        return True

    try:
        import requests
        eq = _english_query(query.split())
        headers = {
            "Authorization": key,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": eq, "per_page": 5, "size": "medium"},
            headers=headers, timeout=15,
        )
        r.raise_for_status()
        videos = r.json().get("videos", [])
        if not videos:
            return False

        # Prefer 5-20 s clips (loop cleanly); pick smallest SD file to stay fast
        def _score(v):
            dur = v.get("duration", 0)
            return 2 if 5 <= dur <= 20 else (1 if dur > 20 else 0)
        videos.sort(key=_score, reverse=True)

        for video in videos:
            files = video.get("video_files", [])
            sd_files = [f for f in files if f.get("quality") == "sd" and f.get("width", 0) >= 640]
            if not sd_files:
                sd_files = [f for f in files if f.get("width", 0) >= 480]
            if not sd_files:
                continue
            sd_files.sort(key=lambda f: f.get("width", 0))
            url = sd_files[0]["link"]  # smallest suitable file
            resp = requests.get(url, headers={"User-Agent": headers["User-Agent"]},
                                timeout=60, stream=True)
            resp.raise_for_status()
            tmp = Path(str(dest_path) + ".tmp")
            with open(str(tmp), "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
            if tmp.stat().st_size < 50_000:
                tmp.unlink()
                continue
            tmp.rename(dest_path)
            import shutil as _sh
            _sh.copy2(str(dest_path), str(cached))  # populate cache
            return True

        return False
    except Exception as e:
        util.log("visuals", f"Pexels video failed for '{query}': {e}")
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
