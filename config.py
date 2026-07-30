"""
Configuracion central del pipeline de hechos de importancia SMV.
Todo lo sensible (API key, credenciales de correo) se lee de variables
de entorno, nunca se hardcodea.
"""
import os

# --- Fuente SMV ---------------------------------------------------------------
# Seccion Emisores > Mercado Principal > Hechos de Importancia.
# Si algun dia cambian el parametro 'data', se actualiza solo aca.
SMV_HECHOS_URL = (
    "https://www.smv.gob.pe/simv/Frm_HechosDeImportancia"
    "?data=AEC85625CCC24CEF792DAE7794ED2132F7CFCB8B1C"
)

# Cuantos dias hacia atras revisar. 0 = solo hoy. 1 = hoy y ayer, etc.
# Util para el primer arranque o si el job no corrio un dia (feriado, caida).
LOOKBACK_DIAS = 0

# --- Cobertura ----------------------------------------------------------------
COVERAGE_CSV = os.path.join(os.path.dirname(__file__), "coverage.csv")

# --- Modelo de IA -------------------------------------------------------------
# Haiku 4.5: el modelo eficiente para clasificar y resumir. 5x mas barato que
# Opus y de sobra para esta tarea. Si algun dia ves que falla en casos raros
# (p.ej. L37 "Otros"), sube solo esos a Sonnet 5 con la env var ANTHROPIC_MODEL.
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")  # requerido

# --- Entrega por correo (opcional) --------------------------------------------
# Si SMTP_HOST esta vacio, el digest solo se imprime en consola y se guarda a HTML.
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", SMTP_USER)
EMAIL_TO = [x.strip() for x in os.environ.get("EMAIL_TO", "").split(",") if x.strip()]

# --- Scraper ------------------------------------------------------------------
# Poner HEADLESS=0 para ver el navegador mientras corre (debug de selectores).
HEADLESS = os.environ.get("HEADLESS", "1") != "0"
TIMEOUT_MS = 45000  # el portal SMV es lento, damos margen
