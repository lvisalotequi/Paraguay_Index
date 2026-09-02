# gdelt_extraction — extractor de cobertura mediática Paraguay-EE.UU.

Actualizado: 2026-09-02. Único documento de referencia de esta carpeta —
reemplaza a `CONTEXTO_PORTABLE_PROXY_B.md`, `EJECUCION_PORTABLE.md` y
`WORKFLOW_EXTRACCION.md` (archivados fuera del repo, ver `CLAUDE.md`).
Solo tiene lo necesario para correr y entender el código; el detalle
histórico de cómo se llegó a la regla actual quedó fuera.

## Qué es

Extrae, vía BigQuery sobre GDELT 2.1 GKG, cobertura mediática bilateral
Paraguay-EE.UU. para la dimensión `4.Visibilidad_mediática_y_relevancia_publica`
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
fecha faltan datos, no son ceros reales).

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

## Estado actual (2026-09-02)

Cobertura histórica completa: **febrero 2015 a diciembre 2025**. Falta
**enero 2026 en adelante** — antes de correr `historical_campaign.py
--execute` para ese tramo, correr `estimate_history.py` para generar una
estimación nueva (la congelada solo cubre hasta diciembre 2025).

`src/ingestion/gdelt_proxy_b.py` (en la raíz del repo, fuera de esta
carpeta) sube los `monthly_*.csv` que esto produce a Drive
(`01_crudas/4.Visibilidad_mediática_y_relevancia_publica/gdelt_proxy_b/`) —
correrlo después de una extracción nueva para que llegue al resto del
pipeline.
