"""
Clasificacion con IA (Haiku 4.5, configurable en config.py).

Estrategia hibrida:
1. El tier base sale del codigo de la SMV (taxonomy.py). Eso ya resuelve la
   mayoria de los casos sin gastar tokens en lo obvio.
2. El modelo se encarga de:
   - narrar en un parrafo que dice el hecho (sin explicar su relevancia),
   - confirmar o corregir el tier en casos ambiguos (sobre todo L37 "Otros",
     que no tiene tier fijo).

El modelo recibe el tier sugerido y solo lo cambia si claramente corresponde,
asi mantenemos consistencia con el criterio del equipo.
"""
import json

import anthropic

import config
import taxonomy


SYSTEM_PROMPT = """Eres un analista de research de equity que clasifica hechos \
de importancia publicados por la SMV (Peru) para las empresas que cubre el area.

Para cada hecho recibes: empresa, codigo de tipo SMV, descripcion del tipo, \
descripcion resumida del hecho, y un tier sugerido (1=alta, 2=media, 3=baja) \
derivado del codigo.

Devuelve SOLO un objeto JSON, sin texto adicional, sin markdown, con las claves:
- "tier": entero 1, 2 o 3. Por defecto usa el tier sugerido. Solo cambialo si el \
TEXTO de la descripcion evidencia claramente que el hecho es mas o menos material \
de lo que el codigo sugiere (ej: un hecho marcado "Otros" que en el texto resulta \
ser un anuncio de cambio de control debe subir a tier 1). \
IMPORTANTE: la descripcion viene vacia o generica muy seguido, sobre todo en \
reportes de resultados (L10) donde la empresa solo adjunta el PDF sin resumen en \
texto - eso es normal y NO es evidencia de baja materialidad. Nunca bajes el tier \
sugerido solo porque no hay texto que analizar; en ese caso, respeta el tier \
sugerido tal cual.
- "categoria": etiqueta corta en espanol (ej: "Dividendos", "Resultados", "M&A", \
"Directorio", "Emision de deuda", "Litigios").
- "resumen": 3 a 5 oraciones en espanol, en un solo parrafo, que CUENTEN que dice \
el hecho de importancia: que se acordo o comunico, montos, fechas, nombres de \
personas o empresas involucradas, y demas detalles concretos que aparezcan en la \
descripcion original. Es una narracion del contenido del hecho, NO una explicacion \
de por que le importa a un analista ni de su impacto en resultados/valuacion/riesgo \
- omite ese tipo de comentario por completo. Si la descripcion original trae poco \
detalle, no inventes cifras ni contexto que no esten ahi; simplemente se mas breve.

Criterio de tiers:
- Tier 1 (accionable): resultados/EEFF, dividendos, cambios de rating, M&A/OPAs, \
emisiones, cambios de control, incumplimientos de pago, cambios en CEO/CFO/directorio, \
contingencias legales o regulatorias grandes.
- Tier 2 (relevante): convocatorias a junta, contratos/inversiones materiales, \
cambio de auditor, litigios en curso.
- Tier 3 (informativo): tramites administrativos, posicion mensual de derivados, \
comunicaciones de rutina."""


def _client() -> anthropic.Anthropic:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("Falta ANTHROPIC_API_KEY en el entorno.")
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def clasificar(hecho, client: anthropic.Anthropic) -> dict:
    tier_sugerido = taxonomy.tier_base(hecho.codigo)
    payload = {
        "empresa": hecho.empresa,
        "codigo_smv": hecho.codigo,
        "tipo": hecho.tipo,
        "descripcion": hecho.descripcion,
        "tier_sugerido": tier_sugerido if tier_sugerido is not None else "no definido",
    }

    msg = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=700,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )

    texto = "".join(b.text for b in msg.content if b.type == "text").strip()
    texto = texto.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(texto)
    except json.JSONDecodeError:
        # fallback seguro: si el modelo no devolvio JSON valido, no perdemos el hecho
        data = {
            "tier": tier_sugerido or 2,
            "categoria": taxonomy.categoria_base(hecho.codigo),
            "resumen": hecho.descripcion[:160],
        }

    # Adjuntamos los datos originales para el digest
    data["empresa"] = hecho.empresa
    data["fecha"] = hecho.fecha
    data["hora"] = hecho.hora
    data["url_documento"] = hecho.url_documento
    data["tier"] = int(data.get("tier", tier_sugerido or 2))
    return data


def clasificar_todos(hechos: list) -> list[dict]:
    client = _client()
    return [clasificar(h, client) for h in hechos]
