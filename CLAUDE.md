# CLAUDE.md — US-PY Engagement Index

Contexto del proyecto para Claude Code. Léelo antes de modificar cualquier script.
Documento simple: el proyecto recién está arrancando, se va a ir ampliando a medida
que se agreguen fuentes de datos reales.

## 1. Qué es el proyecto

Índice de las relaciones bilaterales entre Paraguay y Estados Unidos ("US-PY
Engagement Index"), construido a partir de **cuatro dimensiones**. Cada dimensión
se mide con varias variables, y cada variable se extrae con un script de
ingestion independiente. El resultado se centraliza en un Google Sheet.

Las cuatro dimensiones, ya nombradas en la carpeta de Drive del proyecto:

1. `1.Compromiso_financiero_oficial`
2. `2.Actividad_gubernamental_y_diplomática`
3. `3.Compromiso_economico_privado`
4. `4.Visibilidad_mediática_y_relevancia_publica`

Las variables de cada dimensión todavía se van definiendo sobre la marcha
(el usuario pasa una fuente + qué extraer, sección 8 tiene el detalle de las
que ya existen). Repo público desde 2026-08-26 (ver sección 7, auditoría de
seguridad previa).

## 2. Arquitectura del pipeline

```
src/ingestion/{fuente}.py  →  Drive: 2.Datos_recolectados/01_crudas/{dimensión}/{fuente}/  (archivos crudos)
                    │
                    └──  run_pipeline.py  →  pestaña pipeline_log del Sheet (solo auditoria)
```

La carpeta de Drive tiene 3 etapas (`01_crudas`, `02_limpias`, `03_final`);
por ahora **solo existe `01_crudas`** — las otras dos etapas todavía no
tienen ningún script que las llene (ver sección 7, pendiente #4).

**Regla central: los scripts de `src/ingestion/` SOLO extraen datos y los
suben a Drive.** No escriben nada a disco local, no limpian, no transforman,
no consolidan, y no escriben a Google Sheets. Eso es trabajo de una etapa
futura (`clean` / integración / export) que todavía no existe en este repo
— se agrega cuando haga falta.

- Cada módulo en `src/ingestion/` expone una función `run()` sin argumentos.
  Efecto esperado: descarga cada archivo **en memoria** y lo sube directo a
  su carpeta de Drive vía `src/drive.py` (convención: nombre de la carpeta
  de Drive = nombre del archivo del módulo, dentro de la carpeta de la
  dimensión correspondiente). No hace falta que devuelva nada.
- **Idempotente**: antes de subir un archivo, se revisa si ya existe uno con
  ese nombre en la carpeta de Drive de destino (`drive.existe_archivo`). Si
  ya está, se saltea; si no, se sube (`drive.subir_archivo`). Ver
  `bcp_comercio_exterior.py` como referencia (`_procesar_archivo()`).
- `run_pipeline.py` es el orquestador: descubre automáticamente los módulos de
  `src/ingestion/` (con `pkgutil.iter_modules`, no hay que registrarlos a
  mano) y llama `run()` de cada uno. No espera ningún valor de retorno.
- Cada corrida agrega una fila a la pestaña `pipeline_log` del Sheet
  (timestamp, módulos corridos, errores) — es la única escritura a Sheets que
  hace el pipeline hoy, y sirve para confirmar que una corrida ejecutó de
  punta a punta sin depender de leer logs de GitHub.
- Archivos que empiezan con `_` en `src/ingestion/` se ignoran como módulos
  (convención para helpers compartidos entre módulos de una misma fuente/
  sitio — ej. `_bcp_common.py`, que usan los tres módulos de bcp.gov.py para
  no repetir el bypass de Cloudflare y el manejo de nombres de archivo).

## 3. Persistencia y ejecución

- **Datos crudos**: viven en Google Drive, no en git y no en disco local.
  `src/drive.py` tiene `DRIVE_ROOT_ID`, el id de la carpeta de Drive
  `2.Datos_recolectados` (Unidad compartida del proyecto), y `CARPETA_CRUDAS`
  (`"01_crudas"`). Cada fuente sube a
  `DRIVE_ROOT_ID/01_crudas/{dimensión}/{fuente}/` — ej. Comercio Exterior del
  BCP va en `2.Datos_recolectados/01_crudas/3.Compromiso_economico_privado/bcp_comercio_exterior/`.
  `resolve_ingestion_folder(dimension, fuente)` arma esa ruta y crea las
  subcarpetas que falten (atajo sobre `resolve_folder()`, que acepta
  cualquier lista de segmentos si hiciera falta apuntar a otro lado).
- La cuenta de servicio tiene rol **Writer** en esa Unidad compartida (puede
  crear/editar archivos, no puede borrarlos — no hace falta para ingestion).
- Como la subida es por API (no por disco montado), **esto ya corre igual en
  local o en GitHub Actions** — no depende de tener la Unidad compartida
  montada en ninguna letra de unidad.
- **Salida a Sheets**: solo la pestaña `pipeline_log` (auditoría de que corrió).
  Ninguna fuente escribe datos a Sheets todavía.
- **Ejecución**: GitHub Actions, disparo manual (`workflow_dispatch`) desde la
  pestaña Actions del repo, y programado cada 12 horas (`schedule` cron
  `0 */12 * * *`, UTC).

## 4. Convenciones de código

- Cada script de ingestion: `src/ingestion/{nombre_fuente}.py` con una función
  `def run()`. No hace falta tocar `run_pipeline.py` al agregar uno nuevo.
- Carpeta de Drive: `carpeta_id = resolve_ingestion_folder("{dimensión}", "{nombre_fuente}")`
  desde `src/drive.py`, una sola vez al principio de `run()`. Por archivo:
  `existe_archivo(nombre, carpeta_id)` para chequear, `subir_archivo(bytes,
  nombre, carpeta_id, mime_type=...)` para subir.
- Si la fuente está detrás de Cloudflare y `requests` normal da `403`, usar
  `curl_cffi` con `impersonate="chrome"` en vez de `requests`. Si ya hay un
  helper `_{sitio}_common.py` para ese dominio (ej. `_bcp_common.py` para
  cualquier fuente de bcp.gov.py), reusarlo en vez de repetir el bypass y el
  manejo de nombres de archivo.
- Los archivos que un sitio publica como serie completa en un solo Excel (no
  uno por año) se suben tal cual, con su nombre original saneado — no hace
  falta iterar años. Ejemplo: `bcp_inversion_directa.py`, `bcp_remesas_familiares.py`.
- **Filtrar a Paraguay/EE.UU. en el origen siempre que se pueda** (política
  2026-08-27, aplica a toda fuente nueva): antes de bajar un dataset global,
  buscar si la fuente tiene un filtro server-side por país (parámetro de API,
  `filters` de un datastore CKAN, etc.) y usarlo — ver `bid_proyectos.py`
  (CKAN `filters={"cntry_nm":"Paraguay"}`), `bancomundial_proyectos.py`
  (`countrycode_exact=PY`) o `fa_gov_asistencia_oficial.py` (`PRY` en la
  URL) en vez de bajar el archivo/dataset completo (que puede pesar GBs para
  todos los países del mundo). Si la fuente NO tiene filtro server-side pero
  el archivo es grande, descargarlo igual pero filtrar las filas a Paraguay
  **antes de subir** (con pandas) — ver `exim_autorizaciones.py`. Si el
  archivo es chico (unos pocos MB) igual sin filtro server-side, subirlo
  completo sin filtrar es aceptable — ver `dfc_proyectos_activos.py`.
- Credenciales: nunca hardcodear rutas ni secrets en el código. Usar
  `os.environ["GOOGLE_APPLICATION_CREDENTIALS"]` (ver `src/sheets.py` y
  `src/drive.py`) y `os.environ["SHEET_ID"]` (solo `src/sheets.py`).

## 5. Entorno

- Python 3.11 (versión fijada en el workflow de GitHub Actions).
- Google Cloud: proyecto `us-py-engagement-idx`, cuenta de servicio en
  `config/credential_cloud.json` (**no está en git**, cubierta por
  `.gitignore`). Mismo archivo de credenciales para Sheets y para Drive —
  cada módulo pide el scope de OAuth que necesita al construir sus propias
  `Credentials`.
- Local: variables de entorno en `.env` (no versionado) —
  `GOOGLE_APPLICATION_CREDENTIALS`, `SHEET_ID`, `BEA_API_KEY`.
- GitHub Actions: secrets `GOOGLE_SHEETS_CREDENTIALS` (JSON completo de la
  cuenta de servicio), `SHEET_ID` y `BEA_API_KEY`, en Settings > Secrets and
  variables > Actions.
- El Sheet de destino debe estar compartido como **Editor** con el
  `client_email` de la cuenta de servicio. Si el Sheet vive dentro de una
  Unidad compartida de Google Workspace, puede bloquear compartir con cuentas
  externas al dominio (una cuenta de servicio cuenta como externa) — ver el
  punto pendiente en la sección 7.

### Dependencias (`requirements.txt`)

```
gspread                    # cliente de Google Sheets (solo pipeline_log)
google-auth                # autenticación con la cuenta de servicio
google-api-python-client   # src/drive.py (subida de archivos crudos)
pandas                     # queda declarado para cuando exista una etapa de limpieza
python-dotenv               # cargar .env en local
beautifulsoup4              # parseo de HTML en ingestion
curl_cffi                   # requests que bypasea Cloudflare (fuentes que lo necesiten)
requests                    # fuentes que exponen una API normal (ej. bea_inversion_directa.py)
```

## 6. Estado actual

- Pipeline maestro (`run_pipeline.py`), helper de Sheets (`src/sheets.py`) y
  helper de Drive (`src/drive.py`): probados de punta a punta, en local y en
  GitHub Actions.
- Cuatro scripts de ingestion reales, todos de la dimensión
  `3.Compromiso_economico_privado`:
  - `bcp_comercio_exterior.py` — Importación/Exportación por año, desde 2010
    en adelante (34 archivos hoy).
  - `bcp_inversion_directa.py` — anexo estadístico único de Inversión
    Directa (1995-actualidad); trae un cuadro con flujos trimestrales por
    país del inversionista, incluida una fila "ESTADOS UNIDOS".
  - `bcp_remesas_familiares.py` — Excel único de remesas familiares, con
    columna "EE.UU." y desglose mensual.
  - Estos tres comparten `_bcp_common.py` (bcp.gov.py está detrás de
    Cloudflare, requiere `curl_cffi`, ver sección 4).
  - `bea_inversion_directa.py` — API pública de BEA (dataset `MNE`,
    `DirectionOfInvestment=outward`, país Paraguay = código `216`), fuente
    complementaria a `bcp_inversion_directa.py` desde el lado de EE.UU. Sube
    la respuesta JSON cruda tal cual, con la fecha de la corrida en el
    nombre del archivo (idempotente por día). **A diferencia de la fuente
    del BCP, esta viene ANUAL, no trimestral** — es el corte más fino que
    expone la API para datos por país. Requiere `BEA_API_KEY` (gratuita,
    el usuario la generó en `apps.bea.gov/API/signup`).
  - Los cuatro probados con datos reales: suben bien y una segunda corrida
    saltea lo que ya está (idempotente).
- Seis scripts de ingestion reales de la dimensión `1.Compromiso_financiero_oficial`
  (2015-actualidad; ver política de filtrado a Paraguay/EE.UU. en sección 4):
  - `fa_gov_asistencia_oficial.py` — API del dashboard de ForeignAssistance.gov,
    ya filtrada a Paraguay por la URL (`.../PRY/...`); un JSON por año+medida
    (Obligations/Disbursements). Evita el dump global de 3.75 GB.
  - `usaspending_obligaciones.py` — API de descarga masiva de USAspending,
    filtrada a Paraguay por `place_of_performance_locations`; un ZIP por año
    (la API solo acepta rangos de hasta 1 año, y es asíncrona: se pide, se
    consulta el estado, se descarga cuando está listo).
  - `dfc_proyectos_activos.py` — Excel único de DFC (todos los países, pero
    pesa poco, ~300 KB, no hace falta filtrar). Es **anual**, no mensual.
  - `exim_autorizaciones.py` — CSV único de EXIM (~19 MB, todos los países);
    se descarga completo y se sube solo filtrado a Paraguay (~60 de ~52.700
    filas). Es **trimestral**, no mensual.
  - `bid_proyectos.py` — API CKAN de datos abiertos del BID (`data.iadb.org`,
    mismo portal que usa el equipo para otra fuente de BID), filtrada a
    Paraguay server-side.
  - `bancomundial_proyectos.py` — API pública de proyectos del Banco Mundial,
    filtrada a Paraguay server-side (`countrycode_exact=PY`).
  - `bid_proyectos.py` y `bancomundial_proyectos.py` son fuentes complementarias
    para "Desembolsos multilaterales atribuibles a EE.UU." — el cálculo
    ponderado por cuota de capital de EE.UU. es trabajo de una etapa
    posterior, acá solo se extraen los proyectos crudos de cada banco.
  - Los seis probados con datos reales: suben bien (confirmado con datos
    reales) y una segunda corrida saltea lo que ya está.
- Repo limpiado de artefactos que ya no aplican: el pipeline en R, el
  workflow de otro proyecto, todo lo de RStudio, y `.env.example` — el
  proyecto es 100% Python.
- **Incidente de seguridad resuelto (2026-08-26):** una clave de la cuenta
  de servicio quedó expuesta en el historial de git desde el primer commit
  (adentro de archivos de sesión de RStudio, `.Rproj.user/`, ya eliminados).
  Google la detectó y notificó. Se investigó el alcance completo (dos claves
  de esta cuenta de servicio + una clave ajena de otro proyecto +
  contraseñas en texto plano, todo dentro de `.Rproj.user/`), se purgó del
  historial completo con `git filter-repo` + force-push, se rotaron todas
  las credenciales afectadas, y se auditó de nuevo el historial ya limpio
  antes de hacer público el repo. Queda como recordatorio permanente: repetir
  esta auditoría completa antes de cualquier futuro cambio de visibilidad.
- `SHEET_ID` apunta hoy a un Sheet de **prueba** (en Mi unidad personal, no en
  la Unidad compartida del proyecto) porque compartir con la cuenta de
  servicio falló dentro de la Unidad compartida (ver pendientes).
- Repo público desde 2026-08-26, con el workflow disparándose cada 12 horas
  además de manual.

## 7. Pendientes

1. **Definir el resto de las variables de cada dimensión** — las cuatro
   dimensiones ya tienen nombre (sección 1); `3.Compromiso_economico_privado`
   y `1.Compromiso_financiero_oficial` ya tienen variables/fuentes definidas,
   faltan `2.Actividad_gubernamental_y_diplomática` y
   `4.Visibilidad_mediática_y_relevancia_publica`.
2. **Resolver el acceso a la Unidad compartida de Drive para el Sheet**
   (distinto del acceso a la carpeta de datos, que ya funciona). Compartir
   el Sheet definitivo con la cuenta de servicio dentro de esa Unidad
   compartida da `403 PERMISSION_DENIED`; requiere habilitar "compartir
   fuera de la organización" en esa unidad, o agregar la cuenta de servicio
   como miembro directo. Una vez resuelto, actualizar el secret `SHEET_ID`
   en GitHub.
3. **Anuncios de proyectos de inversión de EE.UU. hacia Paraguay** (REDIEX):
   el link dado (`rediex.gov.py/inversiones/`) es solo una página de menú,
   sin ningún dataset ni archivo descargable — se revisaron las subpáginas
   relacionadas (Dirección de Atracción de Inversiones, Inteligencia,
   Herramientas para Inversionistas) y tampoco hay nada. Falta un link más
   específico o confirmar si esta variable existe como dataset en otro lado.
4. Diseñar las etapas `02_limpias` y `03_final` que lean los datos crudos de
   `01_crudas` y armen lo que finalmente va al Sheet (limpieza, homologación
   entre fuentes, qué campos importan) — todavía no existen, ni en Drive ni
   en el repo.

*(Resuelto 2026-08-26: `bea_inversion_directa.py` escrito y probado en local
con la `BEA_API_KEY` que generó el usuario — falta confirmar que el secret
`BEA_API_KEY` ya esté cargado en GitHub para que corra igual en Actions.)*
