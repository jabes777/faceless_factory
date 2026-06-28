"""Stage 6 — SEO metadata: title, description, tags, chapters, pinned comment, AI disclosure."""
import re

from . import util


def _tags(config, idea):
    base = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{4,}", idea["topic"].lower())
    niche = ["finanzas personales", "libertad financiera", "dinero", "fe y dinero",
             "ahorro", "presupuesto", "latinas", "emprender", "mentalidad de riqueza"]
    tags = list(dict.fromkeys(base + niche))
    return tags[: config["seo"]["tags_count"]]


def _chapters(storyboard):
    # group storyboard into rough chapters by cumulative time
    chapters, t = ["00:00 Introducción"], 0
    labels = ["La verdad incómoda", "Paso 1", "Paso 2", "Paso 3", "Cierre"]
    li = 0
    for shot in storyboard:
        t += shot["duration_hint_sec"]
        if shot["shot"] % 2 == 0 and li < len(labels):
            chapters.append(f"{t//60:02d}:{t%60:02d} {labels[li]}")
            li += 1
    return chapters


def generate(config, idea, visuals, odir):
    name = config["channel"]["name"]
    desc = (
        f"{idea['chosen_title']}\n\n"
        f"En este video de {name} te comparto pasos prácticos sobre {idea['topic']} "
        f"para construir libertad financiera sin perder tu fe, tu familia, ni tu paz.\n\n"
        f"⏱️ Capítulos:\n" + "\n".join(_chapters(visuals["storyboard"])) + "\n\n"
        f"🔔 Suscríbete para más: {config['channel']['handle']}\n\n"
        f"📌 Recursos y enlaces (afiliados):\n- [Tu lead magnet aquí]\n- [Tu producto digital aquí]\n\n"
        + ("🤖 Divulgación: este video usa herramientas de IA en su producción "
           "(guion/voz) con dirección y edición original.\n" if config["upload"]["self_certification_ai_disclosure"] else "")
        + "\n#FinanzasPersonales #LibertadFinanciera #FeYDinero"
    )
    meta = {
        "title": idea["chosen_title"],
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
