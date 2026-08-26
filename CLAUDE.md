# CLAUDE.md — US-PY Engagement Index

Contexto del proyecto para Claude Code. Léelo antes de modificar cualquier script.
Documento simple: el proyecto recién está arrancando, se va a ir ampliando a medida
que se agreguen fuentes de datos reales.

## 1. Qué es el proyecto

Índice de las relaciones bilaterales entre Paraguay y Estados Unidos ("US-PY
Engagement Index"), construido a partir de **cuatro dimensiones**. Cada dimensión
se mide con varias variables, y cada variable se extrae con un script de
ingestion independiente. El resultado se centraliza en un Google Sheet.

Las cuatro dimensiones y sus variables todavía no están definidas en el repo —
se van a ir agregando como scripts en `src/ingestion/` a medida que se definan.

## 2. Arquitectura del pipeline

Flujo actual (simple, sin etapas de limpieza/enriquecimiento todavía):

```
src/ingestion/{variable}.py  →  run_pipeline.py  →  Google Sheets
```

- Cada módulo en `src/ingestion/` expone una función `run()` que devuelve un
  `pandas.DataFrame` con los datos de esa variable.
- `run_pipeline.py` es el orquestador: descubre automáticamente los módulos de
  `src/ingestion/` (con `pkgutil.iter_modules`, no hay que registrarlos a mano),
  corre cada `run()`, y escribe cada DataFrame en su propia pestaña del Google
  Sheet (nombre de pestaña = nombre del archivo).
- Cada corrida agrega una fila a la pestaña `pipeline_log` (timestamp, módulos
  corridos, errores) — es la forma de confirmar que una corrida ejecutó de
  punta a punta sin depender de leer logs de GitHub.
- Archivos que empiezan con `_` en `src/ingestion/` se ignoran (útiles para
  helpers compartidos entre módulos de ingestion).

No hay todavía etapas de `clean` / `enrichAI` / integración multi-fuente como
en otros proyectos del equipo — se evaluará agregarlas cuando haya más de una
fuente por dimensión y datos reales con qué probar el diseño.

## 3. Persistencia y ejecución

- **Sin almacenamiento intermedio todavía**: no hay GCS ni `.pkl`. Cada corrida
  extrae y escribe directo al Sheet. Se puede agregar persistencia intermedia
  más adelante si una fuente lo requiere (ej. detección de cambios por hash).
- **Salida**: un único Google Sheet, una pestaña por módulo de ingestion +
  `pipeline_log`.
- **Ejecución**: GitHub Actions, disparo manual (`workflow_dispatch`) desde la
  pestaña Actions del repo. No hay cron/scheduler todavía — se agregará cuando
  el pipeline tenga fuentes reales que valga la pena correr en automático.

## 4. Convenciones de código

- Cada script de ingestion: `src/ingestion/{nombre_variable}.py` con una
  función `def run() -> pd.DataFrame`. No hace falta tocar `run_pipeline.py`
  al agregar uno nuevo.
- Nombre de archivo = nombre de la variable/fuente = nombre de la pestaña en
  el Sheet. Evitar espacios y caracteres que Sheets no acepta en nombres de
  pestaña (`: \ / ? * [ ]`).
- Credenciales: nunca hardcodear rutas ni secrets en el código. Usar
  `os.environ["GOOGLE_APPLICATION_CREDENTIALS"]` y `os.environ["SHEET_ID"]`
  (ver `src/sheets.py`).

## 5. Entorno

- Python 3.11 (versión fijada en el workflow de GitHub Actions).
- Google Cloud: proyecto `us-py-engagement-idx`, cuenta de servicio en
  `config/credential_cloud.json` (**no está en git**, cubierta por
  `.gitignore`).
- Local: copiar `.env.example` a `.env` y completar `SHEET_ID`.
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
gspread          # cliente de Google Sheets
google-auth      # autenticación con la cuenta de servicio
pandas           # DataFrames que devuelve cada run()
python-dotenv    # cargar .env en local
```

## 6. Estado actual

- Pipeline maestro (`run_pipeline.py`) y helper de Sheets (`src/sheets.py`):
  probados de punta a punta, tanto en local como en GitHub Actions.
- `src/ingestion/` está **vacío**: todavía no se cargó ningún script de
  extracción real. El pipeline corre igual y solo escribe el log de la
  corrida.
- El repo tenía previamente un pipeline en R (`Paraguay_index_master_script.R`)
  y un workflow que corría un script de otro proyecto — eran archivos vacíos
  / de otra plantilla, se eliminaron.
- `SHEET_ID` apunta hoy a un Sheet de **prueba** (en Mi unidad personal, no en
  la Unidad compartida del proyecto) porque compartir con la cuenta de
  servicio falló dentro de la Unidad compartida (ver pendientes).

## 7. Pendientes

1. **Definir las cuatro dimensiones y sus variables** — es el bloqueante
   principal para empezar a escribir scripts de ingestion reales.
2. **Resolver el acceso a la Unidad compartida de Drive** para poder mover el
   Sheet definitivo ahí y compartirlo con la cuenta de servicio (hoy bloquea
   con `403 PERMISSION_DENIED`; requiere habilitar "compartir fuera de la
   organización" en esa unidad, o agregar la cuenta de servicio como miembro
   directo). Una vez resuelto, actualizar el secret `SHEET_ID` en GitHub.
3. Ir agregando un módulo en `src/ingestion/` por cada variable, siguiendo la
   convención de la sección 4.
4. Decidir si hace falta cron (`schedule` en el workflow) una vez que haya
   fuentes reales corriendo, o si el disparo manual alcanza por ahora.
5. Evaluar si con más de una fuente por dimensión hace falta una etapa de
   limpieza/homologación antes de escribir al Sheet (hoy cada `run()` escribe
   su DataFrame tal cual).
