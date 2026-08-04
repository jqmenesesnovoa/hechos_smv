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
| `.github/workflows/daily.yml` | Corre el pipeline en GitHub Actions cuando lo disparan (ver "Produccion" abajo). |

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

## Si la SMV cambia su web y el scraper se rompe

El portal de la SMV es ASP.NET viejo y los resultados se cargan por AJAX,
por eso el scraper usa Playwright y no un `requests` simple. Los selectores
(`SEL_*` en `scraper.py`) ya estan verificados contra el sitio real, pero si
la SMV les cambia el diseno en el futuro y el scraper empieza a fallar, la
forma facil de sacar los IDs nuevos:

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

`coverage.csv` es la unica lista que el equipo deberia necesitar tocar en el
dia a dia: una empresa por linea, con el nombre (razon social) tal como
aparece en el combo "Empresa" de la SMV. Para agregar o quitar un emisor,
edita ese archivo (se puede editar directo desde github.com sin saber git) y
listo.

Ojo: el nombre en la SMV a veces no es exactamente el nombre "comercial" (ej.
"Southern Peru Copper Corporation, Sucursal del Peru" en vez de "Southern", o
"Credicorp Ltd." en vez de "Credicorp" — a veces hay mas de una entidad
parecida registrada). `scraper.py` hace match flexible (sin tildes, mayus/minus,
substring), asi que no hace falta copiar el nombre letra por letra, pero si el
nombre que pongas no se parece a nada del combo real de la SMV, esa empresa se
va a saltar en silencio con un aviso `[aviso] '...' no aparece en el combo`.
Si agregas una empresa nueva, corre el pipeline una vez a mano despues y
revisa que no salga ese aviso.

Cuando quieras, carga tambien la columna `ruc` (la sacas de la ficha "Datos
Generales" de cada empresa en la SMV) para un match aun mas exacto.

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

## Produccion: 3 correos al dia (7am, 12pm, 4pm hora Lima)

`main.py` acepta una variable de entorno `FRANJA` (`manana` / `mediodia` /
`tarde`) que acota el digest a la ventana exacta desde el envio anterior, para
que el correo de las 12pm no repita lo que ya se mando a las 7am, y asi
sucesivamente (ver el modulo `main.py` para el detalle de cada ventana).

**Por que no usamos el `schedule` (cron) nativo de GitHub Actions**: lo
probamos primero y llegamos a ver retrasos de **3 a 11 horas** contra la hora
programada (es una limitacion conocida y documentada de GitHub: los triggers
`schedule` no tienen hora garantizada, sobre todo en horas "en punto" como
12:00/17:00/21:00 UTC, que son las mas congestionadas a nivel global). Por eso
`.github/workflows/daily.yml` ya no tiene `schedule`, solo `workflow_dispatch`
con un input `franja`.

En su lugar, un servicio externo gratuito (**cron-job.org**) llama a la API de
GitHub a la hora exacta para disparar el workflow. Esto SI llega a tiempo
(segundos de diferencia, no horas) porque no depende de la cola interna de
`schedule` de GitHub.

**Setup (una sola vez):**

1. Secrets del repo (Settings -> Secrets and variables -> Actions):
   `ANTHROPIC_API_KEY` y, si usas correo, los `SMTP_*` y `EMAIL_*`.
2. Un token de GitHub fine-grained (Settings -> Developer settings -> Personal
   access tokens -> Fine-grained tokens), scopeado SOLO a este repo, con el
   permiso "Actions: Read and write" (no necesita nada mas: no puede leer
   codigo, tocar secrets ni hacer push). **Le pusimos 1 ano de expiracion a
   proposito** — GitHub avisa por correo antes de que venza, para forzar que
   alguien lo renueve activamente en vez de que el pipeline se apague en
   silencio si queda huerfano. *(Ver fecha de vencimiento en el propio token,
   en la seccion de tokens de GitHub del dueno de la cuenta.)*
3. En cron-job.org, 3 cronjobs identicos salvo la hora y el body:

   | Franja | Hora (Lima, lun-vie) | Hora (UTC) | Body |
   |---|---|---|---|
   | manana | 07:00 | 12:00 | `{"ref":"main","inputs":{"franja":"manana"}}` |
   | mediodia | 12:00 | 17:00 | `{"ref":"main","inputs":{"franja":"mediodia"}}` |
   | tarde | 16:00 | 21:00 | `{"ref":"main","inputs":{"franja":"tarde"}}` |

   Todos con: URL
   `https://api.github.com/repos/<owner>/<repo>/actions/workflows/daily.yml/dispatches`,
   metodo `POST`, headers `Authorization: Bearer <token>` y
   `Accept: application/vnd.github+json`.

**Para probar/correr manualmente** cualquier franja sin esperar el horario:
GitHub -> pestana Actions -> "Hechos de importancia - 3x al dia" -> "Run
workflow" -> elige la franja. O por linea de comando:
`gh workflow run "Hechos de importancia - 3x al dia" -f franja=manana`.

## Cuando dejes el equipo (handoff)

Estas 3 cosas hoy estan atadas a cuentas personales; antes de irte, pasalas a
cuentas/servicio del equipo (cambiar 2-3 valores, no requiere tocar codigo):

- **Repo de GitHub**: agrega a tu equipo como colaboradores, o transfiere el
  repo a una cuenta/organizacion de Inteligo.
- **`ANTHROPIC_API_KEY`**: hoy es tu cuenta personal de Anthropic. Crea una a
  nombre del equipo y actualiza el secret en GitHub.
- **Correo (`SMTP_*`/`EMAIL_FROM`)**: hoy sale de un Gmail personal. Idealmente
  pasar a un correo institucional.
- **Token de cron-job.org**: cuando venza (a 1 ano de creado) o si te vas antes,
  alguien tiene que generar uno nuevo (paso 2 arriba) y actualizar los 3
  cronjobs en cron-job.org.

## Antes de ponerlo en produccion

Valida con IT / compliance dos cosas: (1) que se puede hacer scraping
automatizado del sitio de la SMV y mandar correos automaticos internos (suele
estar bien porque el hecho de importancia es informacion publica), y (2) cual es
el proveedor de LLM aprobado en Inteligo si no quieren que salga a la API publica
de Anthropic.
