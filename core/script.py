"""Stage 1 — Script generation. Live: Claude/OpenAI. Dry-run: structured local draft."""
import json
import os
import urllib.request

from . import util

SYSTEM = (
    "You are the head writer for a faceless YouTube channel. Write a retention-optimized "
    "narration script. RULES: (1) Cold-open hook in the first 2 sentences that restates the "
    "title's promise and opens a curiosity loop. (2) Materially original substance — a SPECIFIC, "
    "concrete lesson, not a generic template (YouTube July-2025 inauthentic-content compliance). "
    "(3) Conversational, spoken cadence. (4) End with a clear CTA. Output plain narration only, "
    "no stage directions, no headers."
)


def _prompt(config, idea):
    wpm = config["script"]["words_per_minute"]
    minutes = config["channel"]["target_length_minutes"]
    words = wpm * minutes
    return (
        f"Channel: {config['channel']['name']}\n"
        f"Language: {config['channel']['language']}\n"
        f"Audience: {config['channel']['audience']}\n"
        f"Tone: {config['channel']['tone']}\n"
        f"Title: {idea['chosen_title']}\n"
        f"{idea['angle']}\n"
        f"Write ~{words} words (~{minutes} min at {wpm} wpm)."
    )


def _anthropic(config, idea):
    body = json.dumps({
        "model": config["script"]["model"],
        "max_tokens": 4000,
        "system": SYSTEM,
        "messages": [{"role": "user", "content": _prompt(config, idea)}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["content"][0]["text"].strip()


def _openai(config, idea):
    body = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": _prompt(config, idea)},
        ],
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=body,
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"].strip()


def _dry(config, idea):
    """Deterministic, demonstrative script so the pipeline runs with zero keys."""
    topic = idea["topic"]
    name = config["channel"]["name"]
    return (
        f"¿Y si te dijera que la razón por la que {topic} se siente imposible no es la falta de "
        f"dinero… sino una sola decisión que estás evitando? Quédate, porque al final te voy a dar "
        f"el primer paso exacto que puedes dar hoy.\n\n"
        f"Bienvenida a {name}. Hoy no vamos a hablar de teoría. Vamos a hablar de tu vida real: tu "
        f"familia, tu fe, y la paz que mereces mientras construyes tu libertad financiera.\n\n"
        f"Primero, la verdad incómoda. La mayoría de los consejos sobre {topic} fueron escritos para "
        f"alguien que no se parece a ti. No toman en cuenta la culpa de querer más, la presión de la "
        f"familia, ni el miedo de perder quién eres. Por eso no funcionan.\n\n"
        f"Paso uno: nombra el número. No el sueño, el número exacto que necesitas este mes. Lo que no "
        f"se mide, no se transforma.\n\n"
        f"Paso dos: elige una sola fuente de fuga. Una suscripción, una deuda, un hábito. Ciérrala "
        f"esta semana. Una victoria concreta cambia tu identidad más que diez metas abstractas.\n\n"
        f"Paso tres: aparta el diez por ciento antes de gastar, no después. Esto no es un truco "
        f"financiero; es un acto de fe en tu propio futuro.\n\n"
        f"Recuerda: Dios no te llamó a encogerte. Te llamó a ser completa, clara, y fructífera. "
        f"Puedes prosperar sin perder tu suavidad, tu fe, ni los valores de tu familia.\n\n"
        f"Si esto te habló hoy, suscríbete y deja en los comentarios cuál de los tres pasos vas a "
        f"dar primero. Nos vemos en el próximo video.\n\n"
        f"[DRY-RUN DRAFT — add an API key in .env to generate a full ~"
        f"{config['script']['words_per_minute'] * config['channel']['target_length_minutes']}-word original script.]"
    )


def generate(config, idea):
    if util.has_key("ANTHROPIC_API_KEY"):
        util.log("script", "generating with Anthropic…")
        text = _anthropic(config, idea)
    elif util.has_key("OPENAI_API_KEY"):
        util.log("script", "generating with OpenAI…")
        text = _openai(config, idea)
    else:
        util.log("script", "DRY-RUN structured draft (no API key)")
        text = _dry(config, idea)
    words = len(text.split())
    util.log("script", f"{words} words (~{words // config['script']['words_per_minute']} min)")
    return {"text": text, "word_count": words}
