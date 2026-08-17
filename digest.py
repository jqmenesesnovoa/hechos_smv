"""
Arma el digest ordenado por tier y lo entrega: siempre lo imprime en consola y
lo guarda a un HTML; si hay config SMTP, tambien lo manda por correo.
"""
import datetime as dt
import smtplib
from email.mime.text import MIMEText

import config

TIER_LABEL = {1: "TIER 1 - Accionable", 2: "TIER 2 - Relevante", 3: "TIER 3 - Informativo"}


def _ordenar(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda x: (x.get("tier", 3), x.get("empresa", "")))


def render_texto(items: list[dict]) -> str:
    hoy = dt.date.today().strftime("%d/%m/%Y")
    if not items:
        return f"Hechos de importancia - cobertura - {hoy}\n\nSin hechos nuevos hoy."

    lineas = [f"Hechos de importancia - cobertura - {hoy}", ""]
    tier_actual = None
    for it in _ordenar(items):
        if it["tier"] != tier_actual:
            tier_actual = it["tier"]
            lineas.append("")
            lineas.append(TIER_LABEL.get(tier_actual, f"TIER {tier_actual}"))
            lineas.append("-" * 40)
        lineas.append("")
        if it.get("url_documento"):
            lineas.append(f"  {it['url_documento']}")
        fecha_hora = f"{it.get('fecha','')} {it.get('hora','')}".strip()
        lineas.append(f"- {it['empresa']} [{it.get('categoria','')}] ({fecha_hora})")
        lineas.append(f"  {it.get('resumen','')}")
    return "\n".join(lineas)


def render_html(items: list[dict], titulo: bool = True) -> str:
    hoy = dt.date.today().strftime("%d/%m/%Y")
    color = {1: "#A32D2D", 2: "#854F0B", 3: "#5F5E5A"}
    out = [f"<h2>Hechos de importancia - cobertura - {hoy}</h2>"] if titulo else []
    if not items:
        out.append("<p>Sin hechos nuevos hoy.</p>")
        return "".join(out)
    tier_actual = None
    for it in _ordenar(items):
        if it["tier"] != tier_actual:
            if tier_actual is not None:
                out.append("</ul>")
            tier_actual = it["tier"]
            out.append(f'<h3 style="color:{color.get(tier_actual,"#000")}">'
                       f'{TIER_LABEL.get(tier_actual)}</h3><ul>')
        nombre = (f'<a href="{it["url_documento"]}">{it["empresa"]}</a>'
                  if it.get("url_documento") else it["empresa"])
        fecha_hora = f"{it.get('fecha','')} {it.get('hora','')}".strip()
        out.append(f'<li style="margin-bottom:24px">'
                   f'<b>{nombre}</b> '
                   f'<i>[{it.get("categoria","")}]</i> '
                   f'<span style="color:#777">({fecha_hora})</span><br>'
                   f'{it.get("resumen","")}</li>')
    out.append("</ul>")
    return "".join(out)


def entregar(items: list[dict]):
    texto = render_texto(items)
    html = render_html(items)

    print(texto)  # siempre a consola

    with open("digest.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("\n[ok] digest guardado en digest.html")

    if config.SMTP_HOST and config.EMAIL_TO:
        # El Subject del correo ya trae el titulo/fecha, asi que el cuerpo va
        # sin el <h2> repetido (que si se guarda en digest.html, para cuando
        # se abre el archivo suelto sin ese contexto).
        _enviar_correo(render_html(items, titulo=False))
        print(f"[ok] correo enviado a {', '.join(config.EMAIL_TO)}")


def _enviar_correo(html: str):
    hoy = dt.date.today().strftime("%d/%m/%Y")
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = f"Hechos de importancia - cobertura - {hoy}"
    msg["From"] = config.EMAIL_FROM
    msg["To"] = ", ".join(config.EMAIL_TO)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.starttls()
        if config.SMTP_USER:
            s.login(config.SMTP_USER, config.SMTP_PASS)
        s.send_message(msg)
