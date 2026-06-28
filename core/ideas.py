"""Stage 0 — Idea & title generation (curiosity-gap packaging)."""
from . import util


# Curiosity-gap title frames proven across the top-50 faceless channels.
TITLE_FRAMES = [
    "Cómo {topic} (sin perder tu fe ni tu paz)",
    "La verdad que nadie te dice sobre {topic}",
    "{topic}: lo que aprendí demasiado tarde",
    "Por qué {topic} te mantiene estancado (y cómo salir)",
    "El método de 3 pasos para {topic}",
    "Lo que las personas con dinero saben sobre {topic}",
]


def generate(config, topic):
    """Return ranked title candidates + the chosen original angle."""
    # Avoid "Cómo cómo…" when a topic already opens with an interrogative.
    clean = topic.strip()
    for lead in ("cómo ", "como ", "por qué ", "porque ", "qué ", "que ", "cuándo ", "cuando ", "cuánto ", "dónde ", "quién "):
        if clean.lower().startswith(lead):
            clean = clean[len(lead):]
            break
    titles = [f.format(topic=clean) for f in TITLE_FRAMES]
    maxc = config["seo"]["max_title_chars"]
    titles = [t if len(t) <= maxc else t[: maxc - 1] + "…" for t in titles]
    angle = (
        f"Original angle: tie '{topic}' to a specific, concrete decision the viewer "
        f"can make this week, framed for {config['channel']['audience']}. "
        f"Each episode must teach a DIFFERENT specific lesson (July-2025 compliance)."
    )
    util.log("ideas", f"{len(titles)} title candidates for topic: {topic!r}")
    return {"topic": topic, "title_candidates": titles, "chosen_title": titles[0], "angle": angle}
