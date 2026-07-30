# Hechos de importancia SMV - digest diario

Pipeline que cada dia trae los hechos de importancia que publica la SMV, filtra
solo los de las empresas que cubrimos, los clasifica por importancia con IA
(Haiku 4.5) y arma un digest ordenado.

Flujo: `scrape` -> `filtro por cobertura` -> `clasificacion IA` -> `digest`.

## Estructura

| Archivo | Que hace |
|---|---|
| `config.py` | Configuracion central (URL, modelo, correo). Todo lo sensible via variables de entorno. |
| `coverage.csv` | Universo de cobertura. Para agregar/quitar empresas, editas esto y nada mas. |
| `taxonomy.py` | Mapeo codigos SMV (L01-L40) -> tier. **Esto se afina con el equipo.** |
| `scraper.py` | Scraper Playwright del portal SMV. |
| `coverage.py` | Filtra los hechos por cobertura. |
| `classifier.py` | Clasificacion + resumen con Haiku 4.5 (configurable). |
| `digest.py` | Arma el digest y lo entrega (consola / HTML / correo). |
| `main.py` | Orquesta todo. |
| `.github/workflows/daily.yml` | Corre el pipeline solo, cada dia, en GitHub Actions. |

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
export ANTHROPIC_API_KEY="tu-api-key"
```

## Correr

```bash
python main.py
```

Imprime el digest en consola y lo guarda en `digest.html`. Si configuras SMTP
(ver abajo), tambien lo manda por correo.

## Lo primero que vas a tener que ajustar: los selectores

El portal de la SMV es ASP.NET viejo y la tabla de resultados se carga por AJAX,
por eso el scraper usa Playwright y no un `requests` simple. Deje los IDs de los
campos (fecha, boton buscar, filas) en `scraper.py` con los valores mas
probables, **pero no los pude verificar en vivo**, asi que casi seguro tengas
que corregir uno o dos. La forma facil:

```bash
playwright codegen "https://www.smv.gob.pe/simv/Frm_HechosDeImportancia?data=AEC85625CCC24CEF792DAE7794ED2132F7CFCB8B1C"
```

Eso abre el navegador y te va escribiendo el selector exacto de cada elemento
que clickeas. Copias esos selectores a las constantes `SEL_*` arriba de
`scraper.py`. Para ver que hace el scraper mientras corre:

```bash
HEADLESS=0 python scraper.py
```

Si algo falla en el paso de fechas, deja un `debug_*.png` y `debug_*.html` para
que puedas inspeccionar la pagina.

> Optimizacion opcional (nivel 2): en vez de manejar el DOM, podes abrir las
> DevTools, ver la llamada XHR que hace el formulario al buscar, y pegarle
> directo a ese endpoint. Es mas rapido y estable, pero el approach con
> Playwright ya funciona como baseline.

## Cobertura

`coverage.csv` trae 5 empresas de demo (Alicorp, Ferreycorp, Cementos Pacasmayo,
Engie Energia Peru, Volcan). El match es por razon social. Cuando quieras, carga
la columna `ruc` (la sacas de la ficha "Datos Generales" de cada empresa en la
SMV) para un match aun mas exacto. Reemplaza estas por tu cobertura real.

## Tiers (taxonomy.py)

El mapeo codigo -> tier es un **primer borrador**. Es justo lo que hay que
sentarse a definir con Karely: es criterio de research, no de codigo. El codigo
`L37` ("Otros") se deja sin tier fijo a proposito para que el modelo lo clasifique
caso por caso, porque ahi es donde se esconden cosas importantes mal etiquetadas.

## Correo (opcional)

Setea estas variables de entorno y el digest se manda solo:

```bash
export SMTP_HOST="smtp.tuservidor.com"
export SMTP_PORT="587"
export SMTP_USER="usuario"
export SMTP_PASS="clave"
export EMAIL_FROM="tu@correo.com"
export EMAIL_TO="karely@inteligo.com, tu@correo.com"
```

## Produccion (que corra solo)

`.github/workflows/daily.yml` ya lo deja corriendo cada dia en GitHub Actions.
Solo tienes que cargar los secrets en el repo (Settings -> Secrets and variables
-> Actions): `ANTHROPIC_API_KEY` y, si usas correo, los `SMTP_*` y `EMAIL_*`.
El horario del cron esta en 07:00 Lima; ajustalo segun cuando quieras el digest.

## Antes de ponerlo en produccion

Valida con IT / compliance dos cosas: (1) que se puede hacer scraping
automatizado del sitio de la SMV y mandar correos automaticos internos (suele
estar bien porque el hecho de importancia es informacion publica), y (2) cual es
el proveedor de LLM aprobado en Inteligo si no quieren que salga a la API publica
de Anthropic.
