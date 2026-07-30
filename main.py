"""
Orquestador del pipeline:
  1. scrape  -> trae los hechos de la SMV
  2. filtro  -> se queda con los de nuestra cobertura
  3. IA      -> clasifica por tier + resumen
  4. digest  -> arma y entrega el resumen ordenado

Correr:  python main.py
  -> usa config.LOOKBACK_DIAS (relativo a 'hoy' segun el reloj del sistema).

Correr acotado a una franja horaria fija (para mandar 3 correos al dia sin
repetir hechos entre uno y otro), con la env var FRANJA:
  FRANJA=manana    python main.py   # hechos entre las 16:01 de ayer y las 07:00 de hoy
  FRANJA=mediodia  python main.py   # hechos entre las 07:01 y las 12:00 de hoy
  FRANJA=tarde     python main.py   # hechos entre las 12:01 y las 16:00 de hoy
Las franjas son siempre en hora de Lima, sin importar la zona horaria del
servidor donde corra (por eso se usa zoneinfo en vez de datetime.now() a secas).
"""
import datetime as dt
import os
import sys
from zoneinfo import ZoneInfo

import scraper
import coverage
import classifier
import digest

TZ_LIMA = ZoneInfo("America/Lima")

# (hora_inicio, hora_fin) de cada franja, en hora de Lima. "manana" cruza
# medianoche: empieza a las 16:01 del dia anterior.
FRANJAS = {
    "manana": (dt.time(16, 1), dt.time(7, 0)),
    "mediodia": (dt.time(7, 1), dt.time(12, 0)),
    "tarde": (dt.time(12, 1), dt.time(16, 0)),
}


def _ventana(franja: str, ahora: dt.datetime) -> tuple[dt.datetime, dt.datetime]:
    hora_ini, hora_fin = FRANJAS[franja]
    hoy = ahora.date()
    fin = dt.datetime.combine(hoy, hora_fin, tzinfo=TZ_LIMA)
    dia_inicio = hoy - dt.timedelta(days=1) if hora_ini > hora_fin else hoy
    inicio = dt.datetime.combine(dia_inicio, hora_ini, tzinfo=TZ_LIMA)
    return inicio, fin


def _momento_publicacion(hecho) -> dt.datetime | None:
    if not hecho.fecha_publicacion:
        return None
    momento = dt.datetime.strptime(hecho.fecha_publicacion, "%d/%m/%Y")
    if hecho.hora:
        hh, mm = hecho.hora.split(":")
        momento = momento.replace(hour=int(hh), minute=int(mm))
    return momento.replace(tzinfo=TZ_LIMA)


def run():
    franja = os.environ.get("FRANJA", "").strip().lower()

    print("[1/4] Scrapeando hechos de la SMV...")
    if franja:
        if franja not in FRANJAS:
            raise SystemExit(f"FRANJA invalida: {franja!r}. Usa: {', '.join(FRANJAS)}")
        ahora = dt.datetime.now(TZ_LIMA)
        inicio, fin = _ventana(franja, ahora)
        print(f"      franja={franja}: {inicio.strftime('%d/%m/%Y %H:%M')} -> {fin.strftime('%d/%m/%Y %H:%M')} (hora Lima)")
        hechos = scraper.scrape_hechos(
            fecha_inicio=inicio.strftime("%d/%m/%Y"),
            fecha_fin=fin.strftime("%d/%m/%Y"),
        )
        hechos = [h for h in hechos if (m := _momento_publicacion(h)) and inicio <= m <= fin]
    else:
        hechos = scraper.scrape_hechos()
    print(f"      {len(hechos)} hechos en la ventana.")

    print("[2/4] Filtrando por cobertura...")
    de_cobertura = coverage.filtrar_por_cobertura(hechos)
    print(f"      {len(de_cobertura)} hechos de empresas cubiertas.")

    if not de_cobertura:
        digest.entregar([])
        return

    print("[3/4] Clasificando con IA...")
    clasificados = classifier.clasificar_todos(de_cobertura)

    print("[4/4] Armando digest...\n")
    digest.entregar(clasificados)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
