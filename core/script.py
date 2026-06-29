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
    """Full-length dry-run script (~1,350 words / 9 min) with proper hook → body → CTA structure."""
    topic = idea["topic"]
    name = config["channel"]["name"]
    audience = config["channel"]["audience"]
    return (
        # HOOK — first 30 sec, open the curiosity loop
        f"¿Y si la razón por la que {topic} se siente imposible "
        f"no tiene nada que ver con el dinero? Quédate, porque en los próximos minutos te voy a mostrar "
        f"exactamente por qué, y el primer paso concreto que puedes dar hoy — aunque tu cuenta bancaria "
        f"no lo refleje todavía.\n\n"

        f"Esto no es un video de motivación vacía. Es una lección específica, diseñada para ti: una mujer "
        f"que equilibra su fe, su familia, y su deseo de libertad financiera sin traicionar quién es. "
        f"Bienvenida a {name}.\n\n"

        # CONTEXTO — por qué este tema importa ahora
        f"Hablemos primero de por qué {topic} es tan difícil. No es porque te falte disciplina. "
        f"No es porque seas mala con el dinero. Es porque la mayoría de los consejos financieros fueron "
        f"escritos por personas que no se parecen a ti, para situaciones que no son las tuyas. Ignoraron "
        f"la presión familiar, la culpa de querer más, el peso de la cultura, y sobre todo — tu fe. "
        f"Eso cambia hoy.\n\n"

        f"Hace tres años, una mujer llamada Carmen — madre de dos hijos, trabajadora de tiempo completo, "
        f"profundamente creyente — me dijo: 'Sé que Dios quiere prosperidad para mí, pero cada vez que "
        f"intento avanzar, algo o alguien me detiene.' Lo que Carmen no sabía era que el obstáculo no "
        f"estaba afuera. Estaba en una sola creencia que nadie le había desafiado. Cuando la identificamos "
        f"y la reemplazamos, todo cambió en noventa días. Hoy te comparto lo que aprendió ella.\n\n"

        # CUERPO — tres pasos concretos
        f"Paso uno: nombra el número real, no el sueño.\n\n"

        f"La mayoría de nosotras tenemos metas financieras vagas. 'Quiero ahorrar más.' "
        f"'Quiero salir de deudas.' 'Quiero tener estabilidad.' Pero lo vago no se puede medir, "
        f"y lo que no se mide no cambia. El cerebro necesita especificidad para activarse. "
        f"Esta semana, escribe el número exacto: cuánto debes, cuánto necesitas ahorrar este mes, "
        f"cuánto pagarás en deuda esta quincena. No el número ideal. El número real, el de hoy. "
        f"Ese es el punto de partida. Sin punto de partida no hay camino.\n\n"

        f"Carmen hizo este ejercicio y descubrió que tenía cuatro deudas pequeñas que juntas sumaban "
        f"más de lo que pensaba — pero que podía liquidar la más pequeña en tres semanas. Esa primera "
        f"victoria le cambió la identidad. Dejó de verse como alguien atrapada y empezó a verse como "
        f"alguien que avanza. La identidad siempre precede al comportamiento.\n\n"

        f"Paso dos: cierra una sola fuente de fuga esta semana.\n\n"

        f"No te pido que transformes toda tu economía de golpe. Eso no funciona y genera culpa. "
        f"Te pido una sola cosa: identifica la fuente de gasto más fácil de eliminar esta semana. "
        f"Una suscripción que olvidaste. Una compra por ansiedad que se repite. Una transferencia "
        f"a alguien que en realidad no necesita tu dinero ahora mismo. Solo una. Ciérrala. "
        f"No porque seas tacaña — sino porque cada peso que desvías hacia tu libertad financiera "
        f"es un acto de amor propio y de fe en tu futuro.\n\n"

        f"La neurociencia del hábito nos dice que una victoria pequeña y concreta activa el circuito "
        f"de recompensa más que una meta grande y distante. No subestimes lo que parece pequeño. "
        f"Veinte dólares al mes parecen nada. En un año son doscientos cuarenta. En cinco años, "
        f"invertidos con un rendimiento moderado, son más de mil quinientos. El tiempo es el "
        f"ingrediente que nadie menciona en los consejos financieros de redes sociales.\n\n"

        f"Paso tres: aparta primero, gasta después — y trátalo como un acto de fe.\n\n"

        f"Hay una práctica que aparece en casi todas las tradiciones de sabiduría financiera — "
        f"y también en la fe cristiana: dar y apartar antes de gastar, no después. El diezmo no "
        f"es solo un principio espiritual. Es un sistema de priorización. Cuando apartas el diez "
        f"por ciento de cualquier ingreso — antes de pagar nada más — le estás diciendo a tu cerebro "
        f"que tú eres la primera prioridad. Que tu futuro importa. Que tienes suficiente para "
        f"prosperar y ser generosa.\n\n"

        f"Esto no es un truco de mentalidad. Es una instrucción de acción: abre una cuenta de "
        f"ahorro separada — muchos bancos lo permiten gratis — y configura una transferencia "
        f"automática el día que recibes tu ingreso. Aunque sea el cinco por ciento al principio. "
        f"El porcentaje importa menos que el hábito. El hábito importa más que el monto.\n\n"

        # PROFUNDIDAD — dimensión de fe
        f"Ahora quiero hablar de algo que pocas personas dicen en los videos de finanzas personales: "
        f"el componente espiritual de {topic}.\n\n"

        f"Si tu fe es parte de tu vida — y para muchas de ustedes lo es profundamente — entonces "
        f"separar lo financiero de lo espiritual no solo es artificial, es contraproducente. "
        f"La Biblia habla de administración, de generosidad, de no servir a dos señores. "
        f"No te está pidiendo que seas pobre. Te está pidiendo que seas íntegra — que tus "
        f"decisiones financieras estén alineadas con tus valores más profundos.\n\n"

        f"Cuando sientes culpa por querer más, pregúntate: ¿es esta culpa de Dios, o es de la "
        f"cultura? ¿Te enseñaron que el dinero es sucio, que querer prosperar es vanidad, que "
        f"una mujer buena no habla de dinero? Esas creencias tienen origen cultural y familiar — "
        f"no espiritual. Dios no te llamó a vivir estresada. Te llamó a ser buena administradora "
        f"de lo que te dio. Eso requiere claridad financiera, no ignorancia.\n\n"

        # ACCIÓN INMEDIATA
        f"Antes de cerrar este video, quiero que hagas una sola cosa. Solo una. Abre una hoja de "
        f"papel — o tu aplicación de notas — y escribe tres números: el total de lo que debes hoy, "
        f"el ingreso que esperas este mes, y el monto mínimo que podrías apartar esta semana. "
        f"No tiene que ser perfecto. Solo tiene que ser real.\n\n"

        f"Esos tres números son tu punto de partida. No tu condena. Tu punto de partida. "
        f"Y desde un punto de partida claro, cualquier camino es posible.\n\n"

        # CTA
        f"Si este video te habló hoy, suscríbete a {name} — publicamos cada semana una lección "
        f"específica, práctica, y con raíces en la fe para mujeres que quieren prosperar sin "
        f"perder su paz, su familia, ni sus valores. Y déjame saber en los comentarios: "
        f"¿cuál de los tres pasos vas a dar esta semana? Leo cada comentario. "
        f"Nos vemos en el próximo video.\n\n"

        f"[DRAFT — agrega ANTHROPIC_API_KEY en .env para un guion 100% original de Claude.]"
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
