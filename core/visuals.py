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

# Photo queries — descriptive nouns for static Pexels images
_QUERY_MAP = {
    "dinero": "woman budgeting home", "deuda": "person stressed bills", "ahorro": "woman saving money",
    "familia": "latin family kitchen", "presupuesto": "budget notebook planning", "trabajo": "woman laptop professional",
    "mujer": "confident latina woman", "latina": "latina woman professional", "dios": "woman hands prayer",
    "iglesia": "church community worship", "casa": "family home warm interior", "niños": "mother children home",
    "ansiedad": "woman stressed anxiety", "paz": "woman peaceful calm", "negocio": "woman entrepreneur business",
    "tarjeta": "credit card payment", "banco": "woman banking online", "ingreso": "paycheck salary woman",
    "pareja": "couple discussing serious", "esposo": "couple conversation home", "hijos": "mother children homework",
    "fe": "woman faith prayer hope", "diezmo": "church offering giving", "gastos": "woman reviewing bills",
    "emergencia": "family savings emergency", "inversión": "woman financial planning", "meta": "woman goal writing",
    "crédito": "credit score financial woman", "salario": "woman paycheck work", "deudas": "woman eliminating debt",
    "pagos": "person paying bills phone", "herencia": "family legacy values", "divorcio": "strong woman rebuilding",
    "estrés": "woman stress relief breathe", "culpa": "woman reflection thinking", "prosperidad": "woman success thriving",
    "miedo": "woman courage confident", "cambiar": "woman transformation growth", "hablar": "women conversation talking",
    "pedir": "family difficult conversation", "libertad": "woman free happy confident", "valores": "family faith values",
    "cónyuge": "couple finances discussion", "salir": "woman walking determined", "construir": "woman building future",
    "oración": "woman praying kneeling", "efectivo": "woman paying cash", "hábitos": "woman journaling habits",
    "ingreso": "woman income paycheck", "ingresos": "woman multiple income streams",
}

# Video queries — ACTION-ORIENTED phrases (subject + verb + object) that return relevant motion clips
# Pexels video search needs human subjects doing something, not abstract nouns.
_VIDEO_QUERY_MAP = {
    # Finance / money actions
    "dinero": "woman counting money table",
    "deuda": "person stressed paperwork bills debt",
    "ahorro": "woman putting money piggy bank saving",
    "presupuesto": "person writing budget notebook planning",
    "gastos": "woman tracking expenses notebook pen",
    "facturas": "woman reviewing bills laptop kitchen",
    "pagos": "person paying bills online phone",
    "tarjeta": "woman using credit card payment",
    "banco": "woman banking phone online transaction",
    "inversión": "woman financial charts laptop investment",
    "crédito": "woman phone checking credit score app",
    "salario": "woman paycheck work desk salary",
    "ingreso": "woman receiving payment work income",
    "ingresos": "woman managing multiple income streams",
    "emergencia": "family planning emergency savings jar",
    "meta": "woman writing goals vision journal",
    "deudas": "woman cutting credit card debt free",
    "efectivo": "woman paying cash envelope budget",
    "hábitos": "woman journaling morning routine habits",
    # Family / relationships
    "familia": "latin family talking kitchen table",
    "pareja": "couple discussing finances home table",
    "esposo": "couple serious conversation living room",
    "hijos": "mother teaching children homework table",
    "niños": "children playing home family kitchen",
    "cónyuge": "couple disagreement talking kitchen calm",
    "herencia": "family sitting together discussion living room",
    "divorcio": "strong woman walking confident outdoors",
    # Faith / spiritual
    "dios": "woman praying hands bowed head",
    "fe": "woman hands folded prayer faith",
    "iglesia": "church service congregation worship singing",
    "diezmo": "person placing donation church offering",
    "oración": "woman kneeling prayer bedroom morning",
    "biblia": "woman reading bible morning light",
    "valores": "family around table talking faith",
    # Emotional / psychological
    "ansiedad": "woman anxious stressed holding head hands",
    "paz": "woman eyes closed peaceful calm nature",
    "estrés": "woman breathing deeply stress relief calm",
    "culpa": "woman looking down thoughtful reflection",
    "miedo": "woman looking up smiling brave confident",
    "prosperidad": "woman celebrating success arms raised happy",
    "libertad": "woman walking free outdoors smiling confident",
    "cambiar": "woman determined walking forward transformation",
    # Work / career
    "trabajo": "woman working laptop coffee shop professional",
    "negocio": "latina woman entrepreneur small business store",
    "mujer": "confident latina woman professional standing",
    "latina": "latina woman smiling professional confident",
    # Home / goals
    "casa": "family home warm living room",
    "hogar": "cozy family home kitchen cooking",
    "salir": "woman walking outdoors morning determined",
    "empezar": "woman opening notebook pen fresh start",
    # Conversation / communication
    "hablar": "two women talking coffee serious conversation",
    "pedir": "woman uncomfortable asking money family",
    "prestado": "family awkward money conversation table",
    "construir": "woman building future vision confident",
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
    """Photo query: returns first matching phrase from _QUERY_MAP."""
    for kw in keywords:
        if kw in _QUERY_MAP:
            return _QUERY_MAP[kw]
    return " ".join(keywords[:2])


# Rotating fallback pool — visually relevant to faith+finance content, always return Pexels results
_VIDEO_FALLBACKS = [
    "latina woman writing notebook morning",
    "woman reviewing financial documents home",
    "woman praying hands bowed head",
    "latin family kitchen table talking",
    "woman walking outdoors confident morning",
    "woman looking at phone smiling plan",
    "couple discussing plans kitchen table",
    "woman journaling coffee morning routine",
    "latina woman professional smiling office",
    "woman counting cash envelope budget",
    "mother children laughing home family",
    "woman closing eyes breathing peaceful",
    "woman opening bible reading morning",
    "person writing goals journal desk",
    "woman holding coffee thinking window",
    "latina woman entrepreneur laptop working",
    "woman calculating budget kitchen table",
    "family prayer hands together home",
    "woman determined walking street confident",
    "woman reviewing documents stressed desk",
]
_fallback_idx = 0
_query_slots: dict = {}  # {cache_key_base: next_slot} — rotated per render for clip variety


def _english_video_query(keywords, shot_index=0):
    """Video query: action-oriented phrase from _VIDEO_QUERY_MAP.

    Pexels video search works best with 'person doing something' phrases.
    Tries each keyword against the map; if nothing matches, cycles through
    a curated fallback pool of always-relevant queries for this channel.
    """
    global _fallback_idx
    for kw in keywords:
        if kw in _VIDEO_QUERY_MAP:
            return _VIDEO_QUERY_MAP[kw]
    # Cycle through fallbacks so consecutive unmatched shots get variety
    q = _VIDEO_FALLBACKS[_fallback_idx % len(_VIDEO_FALLBACKS)]
    _fallback_idx += 1
    return q


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
    """Download a Pexels video clip for the given query.

    Uses a per-render slot counter so repeated queries within the same video get
    DIFFERENT clips (slot 0, 1, 2 …) instead of the same cached clip every time.
    Cache is keyed {hash}_{slot}.mp4 so all slots persist across runs.

    License: Pexels Free License — royalty-free, commercial use OK, YouTube monetizable.
    Returns True on success.
    """
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        return False

    _CLIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve English query ONCE to avoid double-incrementing the fallback index
    eq = _english_video_query(query.split())
    cache_key_base = hashlib.md5(eq.lower().encode()).hexdigest()[:10]

    # Advance the slot for this query so the next call gets a different clip
    slot = _query_slots.get(cache_key_base, 0)
    _query_slots[cache_key_base] = slot + 1

    cached = _CLIP_CACHE_DIR / f"{cache_key_base}_{slot}.mp4"
    if cached.exists() and cached.stat().st_size > 50_000:
        import shutil as _sh
        _sh.copy2(str(cached), str(dest_path))
        util.log("visuals", f"  clip (cached s{slot}): '{eq}'")
        return True

    try:
        import requests
        util.log("visuals", f"  clip: '{query}' → '{eq}' (slot {slot})")
        headers = {
            "Authorization": key,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": eq, "per_page": 15, "size": "medium"},
            headers=headers, timeout=15,
        )
        r.raise_for_status()
        videos = r.json().get("videos", [])
        if not videos:
            return False

        # Score by duration preference (5-20 s loops cleanly)
        def _score(v):
            dur = v.get("duration", 0)
            return 2 if 5 <= dur <= 20 else (1 if dur > 20 else 0)
        videos.sort(key=_score, reverse=True)

        # Pick the slot-th video (wraps around if fewer results than slots used)
        target = videos[slot % len(videos)]

        def _best_file(vid):
            files = vid.get("video_files", [])
            cands = [f for f in files if 640 <= f.get("width", 0) <= 1920]
            if not cands:
                cands = [f for f in files if f.get("width", 0) >= 480]
            if not cands:
                return None
            cands.sort(key=lambda f: abs(f.get("width", 0) - 1280))
            return cands[0]["link"]

        url = _best_file(target)
        if not url:
            # Slot video has no usable file; scan other results
            for alt in videos:
                url = _best_file(alt)
                if url:
                    break
        if not url:
            return False

        resp = requests.get(url, headers={"User-Agent": headers["User-Agent"]},
                            timeout=60, stream=True)
        resp.raise_for_status()
        tmp = Path(str(dest_path) + ".tmp")
        with open(str(tmp), "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        if tmp.stat().st_size < 50_000:
            tmp.unlink()
            return False
        tmp.rename(dest_path)
        import shutil as _sh
        _sh.copy2(str(dest_path), str(cached))  # populate cache slot
        return True

    except Exception as e:
        util.log("visuals", f"Pexels video failed for '{query}': {e}")
        return False


def generate(config, script_text, topic=None):
    segs = _segments(script_text)
    # Extract topic-level keywords — these are blended into every shot so clips stay
    # on-theme even for paragraphs with generic words ("hablemos", "primero", etc.)
    topic_kw = _keywords(topic) if topic else []
    storyboard = []
    for i, seg in enumerate(segs):
        kw = _keywords(seg)
        # Paragraph keywords lead (topic-specific); topic_kw are fallback for generic paragraphs
        combined = list(dict.fromkeys(kw + topic_kw))[:4]
        storyboard.append({
            "shot": i + 1,
            "narration_excerpt": seg[:120] + ("…" if len(seg) > 120 else ""),
            "stock_query": " ".join(combined),
            "image_prompt": f"cinematic, warm light, {', '.join(combined)}, no text, {config['visuals']['aspect_ratio']}",
            "on_screen_caption": config["visuals"]["captions"],
            "duration_hint_sec": max(6, round(len(seg.split()) / 2.5)),
        })

    has_pexels = util.has_key("PEXELS_API_KEY")
    util.log("visuals", f"{len(storyboard)}-shot storyboard, captions={config['visuals']['captions']}, pexels={has_pexels}")
    return {"storyboard": storyboard, "stock_provider": config["visuals"]["stock_provider"],
            "pexels_available": has_pexels}
