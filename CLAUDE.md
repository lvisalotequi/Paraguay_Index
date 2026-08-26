# CLAUDE.md — US-PY Engagement Index

Contexto del proyecto para Claude Code. Léelo antes de modificar cualquier script.
Documento simple: el proyecto recién está arrancando, se va a ir ampliando a medida
que se agreguen fuentes de datos reales.

## 1. Qué es el proyecto

Índice de las relaciones bilaterales entre Paraguay y Estados Unidos ("US-PY
Engagement Index"), construido a partir de **cuatro dimensiones**. Cada dimensión
se mide con varias variables, y cada variable se extrae con un script de
ingestion independiente. El resultado se centraliza en un Google Sheet.

Las cuatro dimensiones y sus variables todavía no están definidas del todo.
En la Unidad compartida del proyecto (carpeta de Drive `2.Datos_recolectados`,
fuera de este repo) ya existen carpetas por dimensión — hoy: `1.Dimensión_1`,
`2.Dimensión_2` y `3.Compromiso_economico_privado` (nombrada; las otras dos
todavía no). Cada fuente que se agregue a `src/ingestion/` va a subir sus
datos crudos a la carpeta de Drive de la dimensión a la que pertenece (ver
sección 3).

## 2. Arquitectura del pipeline

```
src/ingestion/{fuente}.py  →  Drive: 2.Datos_recolectados/{dimensión}/{fuente}/  (archivos crudos)
                    │
                    └──  run_pipeline.py  →  pestaña pipeline_log del Sheet (solo auditoria)
```

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
  (convención para helpers/funciones internas dentro del propio módulo, no
  para compartir entre módulos).

## 3. Persistencia y ejecución

- **Datos crudos**: viven en Google Drive, no en git y no en disco local.
  `src/drive.py` tiene `DRIVE_ROOT_ID`, el id de la carpeta de Drive
  `2.Datos_recolectados` (Unidad compartida del proyecto). Cada fuente sube
  a `DRIVE_ROOT_ID/{dimensión}/{fuente}/` — ej. Comercio Exterior del BCP va
  en `2.Datos_recolectados/3.Compromiso_economico_privado/bcp_comercio_exterior/`.
  `resolve_folder()` crea las subcarpetas que falten.
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
- Carpeta de Drive: `carpeta_id = resolve_folder("{dimensión}", "{nombre_fuente}")`
  desde `src/drive.py`, una sola vez al principio de `run()`. Por archivo:
  `existe_archivo(nombre, carpeta_id)` para chequear, `subir_archivo(bytes,
  nombre, carpeta_id, mime_type=...)` para subir.
- Si la fuente está detrás de Cloudflare y `requests` normal da `403`, usar
  `curl_cffi` con `impersonate="chrome"` en vez de `requests` (bypasea el
  bloqueo por huella TLS). Ejemplo: `bcp_comercio_exterior.py`.
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
  `GOOGLE_APPLICATION_CREDENTIALS` y `SHEET_ID`.
- GitHub Actions: secrets `GOOGLE_SHEETS_CREDENTIALS` (JSON completo de la
  cuenta de servicio) y `SHEET_ID`, en Settings > Secrets and variables >
  Actions.
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
```

## 6. Estado actual

- Pipeline maestro (`run_pipeline.py`), helper de Sheets (`src/sheets.py`) y
  helper de Drive (`src/drive.py`): probados de punta a punta en local.
- Primer script de ingestion real: `src/ingestion/bcp_comercio_exterior.py`
  (Comercio Exterior, Banco Central del Paraguay). Sube los archivos
  Importación/Exportación por año, **desde 2010 en adelante** (34 archivos
  hoy), a `2.Datos_recolectados/3.Compromiso_economico_privado/bcp_comercio_exterior/`
  en Drive. Probado: sube bien (confirmado con archivos reales de hasta
  ~14 MB) y una segunda corrida los saltea (idempotente, chequeado por API
  contra Drive). El sitio está detrás de Cloudflare — requirió `curl_cffi`
  en vez de `requests` normal (ver sección 4).
- La primera versión de este script escribía a disco local (Unidad
  compartida montada en `G:`) — se migró a subir directo a Drive por API
  para poder correr igual en GitHub Actions. De paso se encontró y se
  descartó un workaround que ya no hace falta: el path local superaba el
  límite de 260 caracteres de Windows (MAX_PATH) por lo largo de la ruta de
  la Unidad compartida.
- Repo limpiado de artefactos que ya no aplican: el pipeline en R
  (`Paraguay_index_master_script.R`), el workflow que corría un script de
  otro proyecto, y todo lo de RStudio (`.Rproj`, `.Rproj.user/`, `.Rhistory`)
  — el proyecto es 100% Python. También se eliminó `.env.example` (era un
  ejemplo de referencia, no un archivo que el pipeline necesite leer; cada
  quien mantiene su propio `.env` local, no versionado).
- `SHEET_ID` apunta hoy a un Sheet de **prueba** (en Mi unidad personal, no en
  la Unidad compartida del proyecto) porque compartir con la cuenta de
  servicio falló dentro de la Unidad compartida (ver pendientes).

## 7. Pendientes

1. **Definir las cuatro dimensiones y sus variables** — sigue siendo el
   bloqueante principal para saber qué otras fuentes agregar.
2. **Resolver el acceso a la Unidad compartida de Drive para el Sheet**
   (distinto del acceso a la carpeta de datos, que ya funciona). Compartir
   el Sheet definitivo con la cuenta de servicio dentro de esa Unidad
   compartida da `403 PERMISSION_DENIED`; requiere habilitar "compartir
   fuera de la organización" en esa unidad, o agregar la cuenta de servicio
   como miembro directo. Una vez resuelto, actualizar el secret `SHEET_ID`
   en GitHub.
3. Ir agregando un módulo en `src/ingestion/` por cada variable, siguiendo la
   convención de la sección 4.
4. Diseñar la etapa que lee los datos crudos de Drive y arma lo que
   finalmente va al Sheet (limpieza, homologación entre fuentes, qué campos
   importan) — todavía no existe.

*(Resuelto 2026-08-26: `bcp_comercio_exterior.py` corrió en GitHub Actions y
subió/verificó los archivos en Drive sin depender de nada montado en local —
confirmado leyendo `pipeline_log`. También se agregó el cron de 12hs y se
auditó todo el historial de git antes de volver público el repo — sección 3.)*
