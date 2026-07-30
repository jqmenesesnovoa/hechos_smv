"""
Scraper de hechos de importancia de la SMV.

Por que Playwright y no requests+BeautifulSoup:
la pagina de la SMV es ASP.NET WebForms y los resultados NO vienen en el HTML
inicial: se cargan por postback despues de elegir una empresa y darle click a
"Buscar". Un requests simple solo trae el formulario vacio. Playwright
renderiza la pagina como lo haria una persona, aplica los filtros, y recien
ahi lee los resultados.

IMPORTANTE - el sitio exige elegir una empresa puntual:
El campo "Empresa" (select #MainContent_cboDenominacionSocial) es obligatorio
para buscar; el portal no permite pedir "todos los hechos de un rango de
fechas" sin filtrar por emisor (la validacion JS del formulario lo rechaza
con "Ingrese/Seleccione nombre de la empresa"). Por eso este scraper hace un
query por cada empresa de coverage.csv, en vez de un query global filtrado
despues en Python.

Los resultados tampoco vienen en un <table> con filas homogeneas: cada hecho
es una tarjeta (div.card.card-custom) con el expediente, el tipo, la fecha de
acuerdo, la descripcion y el link al documento adjunto.
"""
import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, asdict

from playwright.sync_api import sync_playwright

import config
import coverage


SEL_EMPRESA = "#MainContent_cboDenominacionSocial"
SEL_FECHA_INICIO = "#txtFechDesde"
SEL_FECHA_FIN = "#txtFechHasta"
SEL_BOTON_BUSCAR = "#MainContent_btnBuscar"
SEL_LOADER = "img[src*='info-loader']"          # el gif "Cargando ..."
SEL_CARDS = "div.card.card-custom"              # una tarjeta = un hecho


@dataclass
class Hecho:
    empresa: str
    fecha: str              # fecha de acuerdo (se muestra en el digest)
    hora: str               # hora de emision/publicacion, ej. "07:40"
    fecha_publicacion: str  # fecha de emision (para filtrar por franja horaria; puede
                            # diferir de 'fecha' si el acuerdo es de un dia distinto)
    codigo: str        # p.ej. "L13"
    tipo: str          # descripcion del tipo
    descripcion: str   # descripcion resumida del hecho
    url_documento: str # link al PDF del hecho


def _rango_fechas():
    hoy = dt.date.today()
    inicio = hoy - dt.timedelta(days=config.LOOKBACK_DIAS)
    fmt = "%d/%m/%Y"  # la SMV usa dd/mm/aaaa
    return inicio.strftime(fmt), hoy.strftime(fmt)


def _norm(s: str) -> str:
    s = s or ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def _resolver_opcion_empresa(page, razon_social: str) -> str | None:
    """El nombre en coverage.csv puede no coincidir letra por letra con el
    combo del sitio (p.ej. 'ENGIE ENERGIA PERU S.A.' vs '...S.A.A.' en la
    SMV), asi que resolvemos por coincidencia normalizada en vez de exigir
    match exacto."""
    opciones = page.eval_on_selector_all(
        f"{SEL_EMPRESA} option",
        "els => els.map(e => ({value: e.value, texto: e.textContent}))",
    )
    objetivo = _norm(razon_social)
    for op in opciones:
        texto_norm = _norm(op["texto"])
        if texto_norm and (texto_norm == objetivo or objetivo in texto_norm or texto_norm in objetivo):
            return op["value"]
    return None


def _escribir_fecha(page, selector: str, valor: str):
    page.fill(selector, "")
    page.click(selector)
    page.keyboard.type(valor, delay=20)


def scrape_hechos(fecha_inicio: str | None = None, fecha_fin: str | None = None) -> list[Hecho]:
    """Hace un query por cada empresa de coverage.csv (el sitio no permite
    buscar por rango de fechas sin elegir emisor) y junta los resultados.

    Por defecto usa config.LOOKBACK_DIAS relativo a 'hoy' segun el reloj del
    sistema. Si se pasan fecha_inicio/fecha_fin (formato dd/mm/aaaa) se usan
    esas en su lugar, para no depender de la zona horaria del servidor donde
    corra (util para acotar por franja horaria, ver main.py)."""
    if fecha_inicio and fecha_fin:
        inicio, fin = fecha_inicio, fecha_fin
    else:
        inicio, fin = _rango_fechas()
    empresas = [c["razon_social"] for c in coverage.cargar_cobertura()]
    hechos: list[Hecho] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        page = browser.new_page()
        page.set_default_timeout(config.TIMEOUT_MS)

        for empresa in empresas:
            try:
                page.goto(config.SMV_HECHOS_URL, wait_until="domcontentloaded")

                valor_opcion = _resolver_opcion_empresa(page, empresa)
                if valor_opcion is None:
                    print(f"  [aviso] '{empresa}' no aparece en el combo de la SMV, se omite")
                    continue
                page.select_option(SEL_EMPRESA, value=valor_opcion)
                page.wait_for_load_state("networkidle")  # postback de DisplayText()

                _escribir_fecha(page, SEL_FECHA_INICIO, inicio)
                _escribir_fecha(page, SEL_FECHA_FIN, fin)
                page.keyboard.press("Tab")  # cierra el datepicker sin borrar el valor

                page.click(SEL_BOTON_BUSCAR, force=True)

                try:
                    page.wait_for_selector(SEL_LOADER, state="visible", timeout=5000)
                except Exception:
                    pass  # a veces carga tan rapido que no lo vemos, no es error
                page.wait_for_selector(SEL_LOADER, state="hidden")
                page.wait_for_load_state("networkidle")

                hechos.extend(_parsear_tarjetas(page, empresa))
            except Exception:
                _debug_dump(page, f"error_{_norm(empresa).replace(' ', '_')}")
                raise

        browser.close()

    return hechos


def _parsear_tarjetas(page, empresa: str) -> list[Hecho]:
    resultado = []
    for card in page.query_selector_all(SEL_CARDS):
        exp_el = card.query_selector("p.text-blue")
        exp_txt = exp_el.inner_text().strip() if exp_el else ""

        tipo_el = card.query_selector("h5.card-title")
        tipo = " ".join(tipo_el.inner_text().split()) if tipo_el else ""

        fecha_el = card.query_selector("span.small")
        fecha_txt = fecha_el.inner_text().strip() if fecha_el else ""
        fecha = fecha_txt.split(":", 1)[1].strip() if ":" in fecha_txt else exp_txt

        # ej. "EXP. 2026033497 DEL  24/07/2026 07:40" -> fecha y hora de publicacion
        pub_m = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", exp_txt)
        fecha_publicacion, hora = pub_m.groups() if pub_m else ("", "")

        desc_el = card.query_selector("p.card-text")
        descripcion = desc_el.inner_text().strip() if desc_el else ""

        link = card.query_selector("div.archivos-adjuntos a")
        url_doc = link.get_attribute("href") if link else ""

        resultado.append(Hecho(
            empresa=empresa,
            fecha=fecha,
            hora=hora,
            fecha_publicacion=fecha_publicacion,
            codigo=_extraer_codigo(tipo),
            tipo=tipo,
            descripcion=descripcion,
            url_documento=url_doc or "",
        ))
    return resultado


def _extraer_codigo(tipo: str) -> str:
    """El tipo viene como '1 - 10. INFORMACION FINANCIERA...' (el numero
    despues del guion es el codigo SMV, L10 en este ejemplo). Si no hay
    numero (p.ej. 'OTROS HECHOS DE IMPORTANCIA'), se deja vacio y el modelo
    clasifica caso por caso, igual que el L37 en taxonomy.py."""
    m = re.search(r"-\s*(\d{1,2})\.", tipo)
    if m:
        return f"L{int(m.group(1)):02d}"
    return ""


def _debug_dump(page, nombre: str):
    """Guarda screenshot + HTML cuando algo falla, para poder inspeccionar."""
    try:
        page.screenshot(path=f"debug_{nombre}.png", full_page=True)
        with open(f"debug_{nombre}.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"[debug] guardado debug_{nombre}.png y .html")
    except Exception:
        pass


if __name__ == "__main__":
    for h in scrape_hechos():
        print(asdict(h))
