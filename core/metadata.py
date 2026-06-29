"""Stage 6 — SEO metadata: title, description, tags, chapters, pinned comment, AI disclosure."""
import re

from . import util

# 25 Spanish personal-finance tags optimised for Latinas audience (Tier 3)
_NICHE_TAGS = [
    "finanzas personales", "libertad financiera", "dinero", "fe y dinero",
    "ahorro", "presupuesto", "latinas", "emprender", "mentalidad de riqueza",
    "mujeres y dinero", "dinero con propósito", "independencia financiera",
    "eliminar deudas", "invertir dinero", "salir de deudas", "administrar dinero",
    "finanzas para mujeres", "prosperidad financiera", "educación financiera",
    "inteligencia financiera", "ahorro inteligente", "presupuesto familiar",
    "finanzas en pareja", "hablar de dinero", "vida financiera sana",
]

# Hashtags for the description footer
_HASHTAGS = (
    "#FinanzasPersonales #LibertadFinanciera #FeYDinero #Latinas "
    "#DineroConPropósito #AhorroInteligente #EliminarDeudas "
    "#EmprendimientoFemenino #EducaciónFinanciera #MujeresYDinero"
)


def _tags(config, idea):
    """Return 20+ YouTube tags: topic words + curated niche tags."""
    base = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{4,}", idea["topic"].lower())
    tags = list(dict.fromkeys(base + _NICHE_TAGS))
    # Use at least 20 regardless of config
    count = max(20, config["seo"].get("tags_count", 20))
    return tags[:count]


def _chapters(storyboard):
    """Generate YouTube chapter timestamps from the storyboard."""
    chapter_labels = [
        "Intro — El Gancho",
        "El Problema",
        "Paso 1: Nombra el número",
        "Paso 2: Cierra la fuga",
        "Paso 3: Aparta primero",
        "Fe y Finanzas",
        "Tu Acción de Hoy",
    ]
    chapters = ["00:00 " + chapter_labels[0]]
    t = 0
    label_i = 1
    for shot in storyboard:
        t += shot["duration_hint_sec"]
        if shot["shot"] % 3 == 0 and label_i < len(chapter_labels):
            mins = int(t // 60)
            secs = int(t % 60)
            chapters.append(f"{mins:02d}:{secs:02d} {chapter_labels[label_i]}")
            label_i += 1
    return chapters


def _bullet_summary(idea):
    """Three-bullet summary of what the viewer will learn (Tier 3)."""
    return (
        "• Identifica y cierra las fugas de dinero más comunes en tu hogar\n"
        "• Pasos concretos para empezar a ahorrar — aunque estés al límite\n"
        "• Cómo alinear tus finanzas con tu fe, tu familia y tus valores"
    )


def generate(config, idea, visuals, odir):
    name = config["channel"]["name"]
    handle = config["channel"]["handle"]
    title = idea["chosen_title"]
    topic = idea["topic"]

    # Hook line (Tier 3 — first thing readers see in search results)
    hook_line = f"💰 {title}"

    # Chapter timestamps
    chapter_lines = "\n".join(_chapters(visuals["storyboard"]))

    # Three-bullet summary
    bullets = _bullet_summary(idea)

    # AI disclosure (conditional)
    ai_note = (
        "🤖 Divulgación IA: este video usa herramientas de inteligencia artificial "
        "(guion y voz) con dirección, edición y criterio editorial original.\n"
        if config["upload"]["self_certification_ai_disclosure"] else ""
    )

    desc = (
        f"{hook_line}\n\n"
        f"En este video de {name} te comparto pasos prácticos sobre {topic} "
        f"para construir libertad financiera sin perder tu fe, tu familia, ni tu paz.\n\n"
        f"Lo que aprenderás hoy:\n{bullets}\n\n"
        f"⏱️ Capítulos:\n{chapter_lines}\n\n"
        f"🔔 Suscríbete cada semana: {handle}\n\n"
        f"📌 Recursos mencionados:\n"
        f"- [Tu lead magnet aquí]\n"
        f"- [Tu producto digital aquí]\n\n"
        f"{ai_note}"
        f"\n{_HASHTAGS}"
    )

    meta = {
        "title": title,
        "description": desc,
        "tags": _tags(config, idea),
        "category_id": config["upload"]["category_id"],
        "privacy_status": config["upload"]["privacy_status"],
        "made_for_kids": config["upload"]["made_for_kids"],
        "pinned_comment": "¿Cuál de los 3 pasos vas a dar primero? Te leo 👇",
        "ai_disclosure": config["upload"]["self_certification_ai_disclosure"],
    }
    util.write_json(odir / "metadata.json", meta)
    util.log("metadata", f"title='{meta['title']}' tags={len(meta['tags'])}")
    return meta
