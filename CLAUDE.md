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
En la Unidad compartida del proyecto (`2. Implementación/2.Datos_recolectados/`,
fuera de este repo) ya existen carpetas por dimensión — hoy: `1.Dimensión_1`,
`2.Dimensión_2` y `3.Compromiso_economico_privado` (nombrada; las otras dos
todavía no). Cada fuente que se agregue a `src/ingestion/` va a guardar sus
datos crudos dentro de la carpeta de la dimensión a la que pertenece (ver
sección 3).

## 2. Arquitectura del pipeline

```
src/ingestion/{fuente}.py  →  DATA_ROOT/{dimensión}/{fuente}/  (archivos crudos)
                    │
                    └──  run_pipeline.py  →  pestaña pipeline_log del Sheet (solo auditoria)
```

**Regla central: los scripts de `src/ingestion/` SOLO extraen datos y los
guardan en disco.** No limpian, no transforman, no consolidan, y no escriben
a Google Sheets. Eso es trabajo de una etapa futura (`clean` / integración /
export) que todavía no existe en este repo — se agrega cuando haga falta.

- Cada módulo en `src/ingestion/` expone una función `run()` sin argumentos.
  Efecto esperado: deja archivos crudos en su propia carpeta bajo
  `DATA_ROOT/{dimensión}/{fuente}/` (convención: el nombre de la carpeta
  coincide con el nombre del archivo del módulo; `DATA_ROOT` sale de
  `src/paths.py`). No hace falta que devuelva nada.
- **Idempotente**: antes de descargar un archivo, revisa si ya existe en la
  carpeta de destino. Si ya está, lo saltea; si no, lo descarga. Cada módulo
  implementa este chequeo (ver `bcp_comercio_exterior.py` como referencia:
  `_descargar_archivo()` hace `if os.path.exists(ruta): return ruta, False`).
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

- **Datos crudos**: viven FUERA del repo, en la Unidad compartida del
  proyecto, no en git. Ruta base = `DATA_ROOT` (definida en `src/paths.py`,
  hoy apunta a `2. Implementación/2.Datos_recolectados/`, con opción de
  sobreescribir vía la variable de entorno `DATA_ROOT` si otra máquina monta
  la Unidad compartida en otra letra). Cada fuente cuelga de
  `DATA_ROOT/{dimensión}/{fuente}/` — ej. Comercio Exterior del BCP va en
  `.../3.Compromiso_economico_privado/bcp_comercio_exterior/`.
- Por las dudas, `.gitignore` también excluye `data/` y `*.xls*` dentro del
  repo (por si algún módulo llegara a escribir ahí durante pruebas).
- **Ojo con GitHub Actions**: el runner es efímero y NO tiene montada la
  Unidad compartida. Si un módulo de ingestion corre ahí, los archivos que
  descarga se pierden al terminar el job. Por ahora la ingestion real se
  corre en local (donde la Unidad compartida sí está montada); ver
  pendientes.
- **Salida a Sheets**: solo la pestaña `pipeline_log` (auditoría de que corrió).
  Ninguna fuente escribe datos a Sheets todavía.
- **Ejecución**: GitHub Actions, disparo manual (`workflow_dispatch`) desde la
  pestaña Actions del repo. No hay cron/scheduler todavía.

## 4. Convenciones de código

- Cada script de ingestion: `src/ingestion/{nombre_fuente}.py` con una función
  `def run()`. No hace falta tocar `run_pipeline.py` al agregar uno nuevo.
- Carpeta de salida: `DATA_ROOT/{dimensión}/{nombre_fuente}/` (importar
  `DATA_ROOT` desde `src/paths.py`), creada por el propio módulo
  (`os.makedirs(..., exist_ok=True)`).
- Si la fuente está detrás de Cloudflare y `requests` normal da `403`, usar
  `curl_cffi` con `impersonate="chrome"` en vez de `requests` (bypasea el
  bloqueo por huella TLS). Ejemplo: `bcp_comercio_exterior.py`.
- Credenciales: nunca hardcodear rutas ni secrets en el código. Usar
  `os.environ["GOOGLE_APPLICATION_CREDENTIALS"]` y `os.environ["SHEET_ID"]`
  (ver `src/sheets.py`) — hoy solo lo usa `append_log_row`.

## 5. Entorno

- Python 3.11 (versión fijada en el workflow de GitHub Actions).
- Google Cloud: proyecto `us-py-engagement-idx`, cuenta de servicio en
  `config/credential_cloud.json` (**no está en git**, cubierta por
  `.gitignore`).
- Local: variables de entorno en `.env` (no versionado) —
  `GOOGLE_APPLICATION_CREDENTIALS`, `SHEET_ID`, y opcionalmente `DATA_ROOT`
  si hace falta sobreescribir la ruta de datos de `src/paths.py`.
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
gspread          # cliente de Google Sheets (solo pipeline_log)
google-auth      # autenticación con la cuenta de servicio
pandas           # queda declarado para cuando exista una etapa de limpieza
python-dotenv    # cargar .env en local
beautifulsoup4   # parseo de HTML en ingestion
curl_cffi        # requests que bypasea Cloudflare (fuentes que lo necesiten)
```

## 6. Estado actual

- Pipeline maestro (`run_pipeline.py`) y helper de Sheets (`src/sheets.py`):
  probados de punta a punta, tanto en local como en GitHub Actions.
- Primer script de ingestion real: `src/ingestion/bcp_comercio_exterior.py`
  (Comercio Exterior, Banco Central del Paraguay). Descarga los archivos
  Importación/Exportación por año, **desde 2010 en adelante** (34 archivos
  hoy), a `DATA_ROOT/3.Compromiso_economico_privado/bcp_comercio_exterior/`.
  Probado en local: descarga bien (confirmado con archivos reales, algunos de
  hasta ~14 MB) y una segunda corrida los saltea (idempotente). El sitio está
  detrás de Cloudflare — requirió `curl_cffi` en vez de `requests` normal
  (ver sección 4).
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
2. **Resolver el acceso a la Unidad compartida de Drive** para poder mover el
   Sheet definitivo ahí y compartirlo con la cuenta de servicio (hoy bloquea
   con `403 PERMISSION_DENIED`; requiere habilitar "compartir fuera de la
   organización" en esa unidad, o agregar la cuenta de servicio como miembro
   directo). Una vez resuelto, actualizar el secret `SHEET_ID` en GitHub.
3. **Decidir cómo persisten los datos crudos si la ingestion corre en la
   nube.** Hoy `DATA_ROOT` es la Unidad compartida montada en local; en
   GitHub Actions no está montada, así que ahí se perdería al terminar el
   job (runner efímero). Ya hay una carpeta de Google Drive con acceso dado
   a la cuenta de servicio (https://drive.google.com/drive/folders/1iFJsRRCMSa7u4-GpYNbl7BE2HnvDGxrL)
   pensada para esto — falta decidir si se sube ahí vía API de Drive desde
   Actions, o si por ahora la ingestion real se sigue corriendo solo en
   local.
4. Ir agregando un módulo en `src/ingestion/` por cada variable, siguiendo la
   convención de la sección 4.
5. Diseñar la etapa que lee los datos crudos de `DATA_ROOT` y arma lo que
   finalmente va al Sheet (limpieza, homologación entre fuentes, qué campos
   importan) — todavía no existe.
6. Decidir si hace falta cron (`schedule` en el workflow) una vez que haya
   fuentes reales corriendo, o si el disparo manual alcanza por ahora.
