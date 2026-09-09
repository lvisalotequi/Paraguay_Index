# gdelt_extraction — extractor de cobertura mediática Paraguay-EE.UU.

Actualizado: 2026-09-08. Único documento de referencia de esta carpeta —
reemplaza a `CONTEXTO_PORTABLE_PROXY_B.md`, `EJECUCION_PORTABLE.md` y
`WORKFLOW_EXTRACCION.md` (archivados fuera del repo, ver `CLAUDE.md`).
Solo tiene lo necesario para correr y entender el código; el detalle
histórico de cómo se llegó a la regla actual quedó fuera.

## Qué es

Extrae, vía BigQuery sobre GDELT 2.1 GKG, cobertura mediática bilateral
Paraguay-EE.UU. para la dimensión `4_Visibilidad_mediatica_y_relevancia_publica`
del proyecto. Corre a mano, en local (no en GitHub Actions — ver por qué en
`src/ingestion/gdelt_proxy_b.py`, el módulo que sube lo que esto produce al
resto del pipeline).

## Metodología ("proxy B", congelada 2026-08-27)

Selección = coocurrencia geográfica PY-US Y [D O (I Y (R O E))]:
- **D** — señales diplomáticas (embajadores, sanciones, tratados, cooperación).
- **I** — gobierno, instituciones, cargos públicos.
- **R** — comercio internacional, fronteras, inmigración.
- **E** — economía/impuestos (`EPU_ECONOMY`, `ECON_TAXATION`, `WB_1121_TAXATION`, `EPU_CATS_TAXES`).

Config exacta y versión aceptada: `proxy_b_config.json`
(`proxy_b_v1_accepted_2026_08_27`) — no modificarla para reproducir B.

**Límites de la metodología (repetir siempre al reportar resultados):** es
una aproximación de coocurrencia con señales institucionales/económicas,
**no** noticias validadas individualmente ni medición de calidad de
relaciones diplomáticas. El tono es del documento completo, no de la
relación bilateral. PY/US es país de fuente, no dirección de la
interacción. La serie GKG2 arranca el 19 de febrero de 2015 (antes de esa
fecha faltan datos, no son ceros reales) — este límite está *hardcodeado*
en el código (`GDELT_START` en `bilateral_media_extractor.py`, y el
`max(window.start, date(2015, 2, 19))` de `gdelt_queries.py`), no es solo
una nota.

**Qué significa la columna `month` (aclarado 2026-09-08, tras una confusión
real - ver `CLAUDE.md` sección 6):** en cada fila de los `monthly_*.csv`,
`month` es el **primer día del período que esa fila describe** — ej.
`month=2015-03-01` cubre el 1 al 31 de marzo de 2015 (`period_start`/
`period_end` en la misma fila lo confirman). **No** es una fecha de "corte"
que apunte al mes *anterior*. Esto es literal en `gdelt_queries.py`:
`SELECT DATE('{window.start.replace(day=1)}') month, ...` - el mes es el
propio inicio de la ventana que se está consultando, no el mes previo a
esa ventana.

Aparte, y sin relación directa con lo anterior, `bilateral_media_extractor.py`
sí tiene una función `last_complete_month()` que calcula "el mes anterior a
hoy" - pero es solo el valor por **default** de `--start`/`--end` cuando se
corre `bilateral_media_extractor.py gdelt` directamente **sin** pasar esas
fechas a mano. Ni `extraction_workflow.py` ni `historical_campaign.py` (las
formas normales de correr una extracción, ver más abajo) pasan por ese
default: siempre arman `--start`/`--end` explícitos. No confundir "cuándo
conviene correr la extracción" (a partir del mes calendario siguiente, para
tener el mes anterior ya completo) con "qué significa la columna `month`
del resultado" (el propio mes que describe, no el anterior).

## Archivos y para qué sirve cada uno

| Archivo | Rol |
| --- | --- |
| `historical_campaign.py` | Coordinador reanudable para correr el backlog histórico completo (llama a `extraction_workflow.py`). |
| `estimate_history.py` | Genera/actualiza la estimación de bytes por bloque de meses — correr antes de extender el rango histórico. |
| `extraction_workflow.py` | Workflow de un rango puntual: `plan` (dry run, congela el plan) → `execute` (corre solo ese plan). |
| `bilateral_media_extractor.py` | La consulta a BigQuery en sí (dry run por defecto; perfil `candidates_themes`). |
| `gdelt_queries.py` | Arma el SQL, incluido `build_proxy_b_metrics_query`. |
| `proxy_b.py` | Aplica la regla B localmente sobre un CSV ya descargado — no usa red. |
| `usage_ledger.py` | Reconstruye el registro de consumo acumulado desde los recibos (`*.complete.json`) para no perder cuenta del gasto entre corridas. |
| `proxy_b_config.json`, `workflow_config.json`, `historical_workflow_config.json` | Configuración (regla B, límites de `extraction_workflow.py`, proyecto/límites de `historical_campaign.py`). |
| `requirements.txt` | Dependencias (`google-cloud-bigquery`, `pandas`, etc.). |

## Preparación en una máquina nueva

0. Instalar [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (no
   viene con Python ni con el repo). Confirmar acceso al proyecto GCP
   `us-py-engagement-idx`.
1. **Windows, si el repo vive en una ruta larga** (carpetas con emoji, muchos
   niveles — como la Unidad compartida de este proyecto): habilitar rutas
   largas *antes* de crear el venv o correr nada (si no, `ensurepip` falla al
   crear el venv, y después `open()` falla con `FileNotFoundError` en
   archivos que sí existen). Una vez, en PowerShell como administrador:
   ```powershell
   New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
   ```
   Google Drive para escritorio no soporta symlinks/junctions, así que no
   sirve como atajo para evitar este paso. Si el checkout vive en una ruta
   corta (fuera de Drive), este paso no hace falta.
2. Crear el entorno virtual (preferible en una ruta corta si el repo está en
   una ruta larga, ej. `C:\Users\<usuario>\.venvs\gdelt_extraction`):
   ```powershell
   py -3.11 -m venv C:\Users\<usuario>\.venvs\gdelt_extraction
   C:\Users\<usuario>\.venvs\gdelt_extraction\Scripts\python.exe -m pip install -r requirements.txt
   gcloud init
   gcloud auth application-default login
   ```

## Cómo correr

**Dry run (siempre el default — no consume cuota real, solo estima):**
```powershell
python historical_campaign.py --prepare
```
Verifica y arma el plan sin consultar BigQuery de verdad.

**Ejecutar el backlog histórico** (después de revisar el plan):
```powershell
python historical_campaign.py --execute
```
Procesa bloques cronológicos, re-estima, comprueba que la facturación siga
deshabilitada antes de cada consulta, registra recibos, y escribe
`output/historical_campaign/CONTINUIDAD.md`. Se detiene si la suma
registrada + el siguiente bloque superaría el techo mensual.

**Para un rango puntual** (no backlog completo), usar `extraction_workflow.py`
en vez de `historical_campaign.py`:
```powershell
python extraction_workflow.py plan --start 2015-03 --end 2015-03
python extraction_workflow.py execute --plan RUTA_DEL_PLAN.json
```
`plan` nunca autoriza `execute` solo: son dos pasos separados a propósito.

**Reprocesar localmente un CSV ya descargado** (sin tocar BigQuery):
```powershell
python proxy_b.py RUTA_AL_CSV_CON_THEMES --output RUTA_NUEVA.json
```

## Límites y seguridad (no negociable)

- Techo preventivo acumulado por mes calendario: **850 GiB**.
- Límite por consulta: **20 GiB**. Límite por bloque/invocación: **100 GiB**.
- La facturación del proyecto GCP debe permanecer **deshabilitada**; el
  programa falla de forma cerrada (se detiene) si no puede comprobarlo antes
  y después de cada consulta. Nunca habilitarla ni vincular una tarjeta.
- No borrar los recibos (`output/**/*.complete.json`, `output/query_usage_ledger.json`):
  sin ellos, otra instalación no puede saber de forma confiable qué
  consultas ya se ejecutaron, y se corre el riesgo de repetir gasto.
- Copiar siempre la carpeta `output/` junto con el código al migrar de
  máquina (está en `.gitignore`, no viaja con git).
- No copiar/publicar `application_default_credentials.json`, archivos de
  cuenta de servicio, carpetas `gcloud` o el `venv`.

## Estado actual (actualizado 2026-09-08)

Cobertura histórica completa: **febrero 2015 a enero 2026**. Extendida el
2026-09-08 con un rango puntual vía `extraction_workflow.py` (no
`historical_campaign.py` — no hacía falta procesar backlog, solo un mes
suelto; por eso tampoco hizo falta correr `estimate_history.py` antes, ese
paso es específico de `historical_campaign.py`). Para sumar el próximo mes,
ver la receta paso a paso en `CLAUDE.md` sección 6 (nota de
`gdelt_extraction/`).

`src/ingestion/gdelt_proxy_b.py` (en la raíz del repo, fuera de esta
carpeta) sube los `monthly_*.csv` que esto produce a Drive
(`01_crudas/4_Visibilidad_mediatica_y_relevancia_publica/gdelt_proxy_b/`) —
correrlo después de una extracción nueva para que llegue al resto del
pipeline. Después, correr `src/processing/visibilidad_mediatica_y_relevancia_publica.py`
para que el mes nuevo llegue a `02_limpias/` (si ya se corrió processing
ese mismo día, hay que sobreescribir a mano el archivo del día en Drive -
el chequeo de idempotencia es por día).
