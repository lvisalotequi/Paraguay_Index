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

1. `1_Compromiso_financiero_oficial`
2. `2_Actividad_gubernamental_y_diplomatica`
3. `3_Compromiso_economico_privado`
4. `4_Visibilidad_mediatica_y_relevancia_publica`

Las variables de cada dimensión todavía se van definiendo sobre la marcha
(el usuario pasa una fuente + qué extraer, sección 8 tiene el detalle de las
que ya existen). Repo público desde 2026-08-26 (ver sección 7, auditoría de
seguridad previa).

## 2. Arquitectura del pipeline

```
ETAPA 01 · src/ingestion/{fuente}.py   →  Drive: 01_crudas/{dimensión}_crudas/{fuente}/   (archivos crudos)
              │                                        │
              │  run_pipeline.py → pipeline_log        ▼
              │  (automatizado en GitHub Actions)
              │
ETAPA 02 · dos implementaciones que hacen LO MISMO (ver aviso abajo):
              │   src/processing/{dimensión}.py        → módulos con run(), orquestados por run_processing.py
              │   src/02_cleaning/02_clean_{dim}.py    → script lineal, se corre a mano en Positron
              │                                        │
              │                                        ▼
              │                          Drive: 02_limpias/{dimensión}_limpias/{variable}/  (1 CSV por variable)
              ▼
ETAPA 03 · src/03_integration/03_integration.py   →  Drive: 03_integracion/   (panel trimestral cuadrado,
              │                                        │      480 filas = 10 variables × 48 trimestres,
              │                                        │      un CSV largo + un CSV ancho)
              ▼                                        ▼
ETAPA 04 · src/04_analysis_index/04_analysis_index.qmd  →  Drive: 04_final/   (CSV largo + CSV ancho +
                                                            un Google Sheet de 2 pestañas para el dashboard)
                                                            + el documento Quarto renderizado
```

La carpeta de Drive tiene 4 etapas (`01_crudas`, `02_limpias`, `03_integracion`,
`04_final`), y desde el 2026-09-10 las cuatro tienen datos: las etapas 03 y 04
ya publican su salida (antes vivían solo en memoria y en el HTML renderizado).
Ojo con el nombre: la última carpeta se llama **`04_final`**, no `03_final`
como decía esta nota antes de que existieran las carpetas reales.

> **Las etapas 03 y 04 escriben distinto a las etapas 01 y 02 (2026-09-10).**
> Ingestion y processing acumulan un archivo por corrida con la fecha en el
> nombre y nunca pisan nada (idempotente por día). Las etapas 03 y 04 usan
> **nombre fijo y reemplazan el contenido del mismo archivo** en cada corrida
> (`subir_o_reemplazar()` en `src/drive.py`, que hace `files.update`). El
> motivo es que lo que publican no es una foto nueva de una fuente sino el
> estado vigente de la etapa, y hay cosas enganchadas por link a esos archivos
> (el `.qmd` lee el panel de `03_integracion`; un dashboard lee el Sheet de
> `04_final`). Con nombre fijo, el id del archivo no cambia nunca y el
> historial de versiones lo guarda igual Drive.

> ⚠️ **Duplicación conocida de la etapa 02 (2026-09-09).** La dimensión 1
> está implementada dos veces: como módulo (`src/processing/
> compromiso_financiero_oficial.py`, que `run_processing.py` autodescubre) y
> como script lineal (`src/02_cleaning/02_clean_compromiso_financiero_oficial.py`,
> con `SUBIR_A_DRIVE = False`). Las dos suben a las MISMAS carpetas de
> variable, y `subir_variable()` es idempotente **por día**: si se corren
> las dos el mismo día, gana la primera y la segunda se saltea en silencio.
> Hay que decidir cuál queda antes de activar la subida del script lineal.
> Las dimensiones 2, 3 y 4 siguen existiendo solo como módulo.

**Regla central: los scripts de `src/ingestion/` SOLO extraen datos y los
suben a Drive.** No escriben nada a disco local, no limpian, no transforman,
no consolidan, y no escriben a Google Sheets. Limpiar/consolidar es trabajo
de `src/processing/` (ver más abajo) — una etapa separada, corrida a mano,
no automatizada todavía.

- **`src/processing/{dimensión}.py`** (agregado 2026-09-02, rediseñado
  2026-09-03): a diferencia de ingestion, SI lee los archivos crudos que
  ingestion ya subio a Drive (via `src.drive.listar_archivos`/
  `descargar_archivo`), aisla la cifra especifica de EE.UU. de cada fuente
  de esa dimensión, normaliza a trimestres (sumando meses o repitiendo un
  valor anual segun la granularidad nativa de cada fuente — ver el
  docstring de cada módulo), y sube un CSV **por variable** (no un CSV
  combinado por dimensión) a `02_limpias/{dimensión}_limpias/{variable}/` —
  una carpeta por variable, política 2026-09-03 a pedido del usuario, para
  que cada variable se pueda leer/actualizar sola en una etapa posterior.
  Esquema fijo e igual en las 4 dimensiones: `trimestre, anio,
  trimestre_num, valor, unidad` — el helper `src/processing/_common.py`
  (`subir_variable()`/`reescalar()`) centraliza esta convención, así ningún
  módulo arma el CSV a mano. Todas las variables monetarias van en **USD
  sin escalar** (nunca miles/millones mezclados dentro de la misma
  dimensión); las de tipo "cantidad" (conteos) y "índice" quedan tal cual,
  sin conversión. Expone `run()`, igual que ingestion; `run_processing.py`
  los descubre automáticamente con `pkgutil.iter_modules` (mismo patrón que
  `run_pipeline.py`) y registra la corrida en la pestaña `processing_log`
  del Sheet (separada de `pipeline_log`). No forma parte del schedule
  automático de GitHub Actions todavía — se corre a mano cuando hace
  falta. Cubre las 4 dimensiones — ver sección 6.

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
- **Trazabilidad (política 2026-09-02)**: cada módulo declara, junto a
  `DIMENSION`/`FUENTE`, dos constantes más: `DESCRIPCION` (una línea, qué
  extrae) y `URL_FUENTE` (la página/portal público de origen — no
  necesariamente el endpoint de API que usa el código, sino donde una
  persona puede ir a verificar la fuente). `run_pipeline.py` lee estas
  cuatro constantes de cada módulo con `getattr` (con fallback si faltan) y
  arma la pestaña `catalogo_fuentes` del Sheet en cada corrida — una fila
  por módulo, con estado y timestamp de la última corrida. Es la forma de
  saber de dónde sale cada dato sin tener que leer el código.
- Cada corrida agrega una fila a la pestaña `pipeline_log` del Sheet
  (timestamp, módulos corridos, errores) y reescribe `catalogo_fuentes` —
  son las dos únicas escrituras a Sheets que hace el pipeline hoy, y sirven
  para confirmar que una corrida ejecutó de punta a punta sin depender de
  leer logs de GitHub.
- Archivos que empiezan con `_` en `src/ingestion/` se ignoran como módulos
  (convención para helpers compartidos entre módulos de una misma fuente/
  sitio — ej. `_bcp_common.py`, que usan los tres módulos de bcp.gov.py para
  no repetir el bypass de Cloudflare y el manejo de nombres de archivo).
- **Excepción a "solo extraen y suben, no tocan disco local":** `gdelt_proxy_b.py`
  (dimensión 4) no hace fetch en vivo. Lee CSV ya generados por
  `gdelt_extraction/` (ver sección 6) y los sube tal cual. La extracción real
  contra GDELT vía BigQuery consume cuota mensual de un sandbox sin
  facturación y necesita login OAuth personal (`gcloud auth application-default
  login`) para verificar antes de cada consulta que la facturación sigue
  deshabilitada — no tiene sentido automatizarla en GitHub Actions (no hay
  login humano ahí, y se fundiría la cuota gratuita rápido).
  Por eso la extracción corre a mano, localmente, desde `gdelt_extraction/`;
  `gdelt_proxy_b.py` solo centraliza en Drive lo que esa extracción ya
  produjo. En Actions, donde `gdelt_extraction/output/` no existe (está en
  `.gitignore`, nunca se clona), el módulo imprime un aviso y no sube nada —
  no es un error, es el comportamiento esperado.

## 3. Persistencia y ejecución

- **Datos crudos**: viven en Google Drive, no en git y no en disco local.
  `src/drive.py` tiene `DRIVE_ROOT_ID`, el id de la carpeta de Drive
  `2.Datos_recolectados` (Unidad compartida del proyecto), y `CARPETA_CRUDAS`
  (`"01_crudas"`). Cada fuente sube a
  `DRIVE_ROOT_ID/01_crudas/{dimensión}/{fuente}/` — ej. Comercio Exterior del
  BCP va en `2.Datos_recolectados/01_crudas/3_Compromiso_economico_privado/bcp_comercio_exterior/`.
  `resolve_ingestion_folder(dimension, fuente)` arma esa ruta y crea las
  subcarpetas que falten (atajo sobre `resolve_folder()`, que acepta
  cualquier lista de segmentos si hiciera falta apuntar a otro lado).
- La cuenta de servicio tiene rol **Writer** en esa Unidad compartida (puede
  crear/editar archivos, no puede borrarlos — no hace falta para ingestion).
- Como la subida es por API (no por disco montado), **esto ya corre igual en
  local o en GitHub Actions** — no depende de tener la Unidad compartida
  montada en ninguna letra de unidad.
- **Salida de las etapas 03 y 04**: `CARPETA_INTEGRACION` (`"03_integracion"`)
  y `CARPETA_FINAL` (`"04_final"`), las dos colgando directo de
  `DRIVE_ROOT_ID` (ids cacheados en `ETAPA_FOLDER_IDS`,
  `resolve_etapa_folder(carpeta)` los resuelve). A diferencia de ingestion y
  processing, escriben con `subir_o_reemplazar()` (nombre fijo, `files.update`
  sobre el mismo archivo) — ver el aviso de la sección 2.
- **Salida a Sheets**: tres pestañas de auditoría en el Sheet de `SHEET_ID`
  (`pipeline_log`, `processing_log` y `catalogo_fuentes` — trazabilidad de
  dónde sale cada fuente, ver sección 4), más, desde el 2026-09-10, el Sheet
  `us_py_engagement_index` que publica la etapa 04 dentro de `04_final`. Ese
  último es el único que lleva *datos* y no metadatos de auditoría, y vive en
  un archivo aparte (`write_dataframe(..., spreadsheet_id=...)`) porque lo
  consume un dashboard: nunca se borra ni se recrea, solo se reemplaza el
  contenido de sus dos pestañas.
- **Ejecución**: GitHub Actions, disparo manual (`workflow_dispatch`) desde la
  pestaña Actions del repo, y programado cada 3 meses (`schedule` cron
  `0 0 1 */3 *`, 1 de enero/abril/julio/octubre, UTC).

## 4. Convenciones de código

- Cada script de ingestion: `src/ingestion/{nombre_fuente}.py` con una función
  `def run()`. No hace falta tocar `run_pipeline.py` al agregar uno nuevo.
- **Obligatorio para trazabilidad**: además de `DIMENSION` y `FUENTE`, todo
  módulo nuevo declara `DESCRIPCION` (una línea, qué extrae) y `URL_FUENTE`
  (la página pública de origen, no el endpoint de API interno). Sin esto la
  fila del módulo en `catalogo_fuentes` queda vacía — no rompe el pipeline,
  pero rompe la trazabilidad.
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

### Estilo de las etapas 02 en adelante (política 2026-09-08/09)

A partir de `src/02_cleaning/`, el usuario pidió un estilo distinto al de
`src/ingestion/` y `src/processing/`. Las etapas nuevas **no son módulos con
`run()`**: son scripts lineales pensados para correrse por bloques en la
consola de Positron, dejando los objetos intermedios vivos para inspección.

- Cajón de encabezado con proyecto, responsable, fecha de creación, detalle,
  qué corre antes y cuál es la salida.
- Secciones numeradas (`# 0. SETUP`, `## 0.1. Entorno`, `## 0.2. Rutas y
  credenciales`, `## 0.3. Parametros configurables`, `#=== 1. ... ===#`).
- **Todos los parámetros en `0.3`**, nunca dispersos en el código: cambiar el
  comportamiento debe ser cambiar constantes.
- Objetos intermedios con nombre y sufijo que indique la etapa
  (`*_raw`, `*_limpiando`, `*_clean`, `*_limpia`), porque se abren de a uno
  en el panel de Variables de Positron.
- Validaciones impresas al cierre de cada bloque, y un interruptor tipo
  `SUBIR_A_DRIVE` para poder correr todo sin escribir nada mientras se revisa.
- Comentarios sin tildes (igual que el resto del repo, por encoding de
  consola); la prosa de los documentos Quarto sí lleva tildes.

### Estándar de documentación de la etapa 04 (política 2026-09-09)

El usuario rechazó un primer borrador del documento de análisis por dar por
sabido demasiado. El estándar acordado es **"calidad de paper, compartible
con el cliente"**, y en concreto exige:

- Nada de jerga sin explicar. Cada término técnico se define en lenguaje
  llano la primera vez que aparece, y hay un glosario desplegable.
- **Tabla de operacionalización** obligatoria: qué mide exactamente cada
  variable, fuente, unidad, y qué significa que suba.
- Cada decisión metodológica se escribe con: qué se decidió, **por qué**,
  **qué alternativa se descartó** y a qué costo.
- Declarar explícitamente qué del marco prometido **no** está en el
  resultado.
- Convención metodológica citada (OCDE/JRC) y mapeada paso por paso.
- Las cifras que aparecen en la prosa se calculan **en línea** (`` `{python}
  ...` ``) desde los mismos objetos que producen las tablas, para que no se
  desincronicen al reprocesar. Esto ya pasó una vez: cuatro cifras del texto
  quedaron desfasadas de la corrida final.

## 5. Entorno

- Python 3.11 (versión fijada en el workflow de GitHub Actions). **En local
  hoy se corre con Python 3.14.7** (verificado 2026-09-09): todas las
  dependencias tienen wheels para 3.14, incluidas `curl_cffi` y `lxml`, así
  que no hace falta instalar 3.11 para trabajar localmente.
- **`pandas` está fijado en `>=2.2,<3` (2026-09-09).** Sin ese techo, pip
  con Python 3.14 resuelve pandas 3.0.x, que cambia el dtype por defecto de
  los strings y hace obligatorio copy-on-write. Nada de este repo está
  probado con la serie 3.x. Subir el techo es una decisión aparte, con su
  propia verificación de las 4 dimensiones.
- **Entorno virtual local**: `.venv/` en la raíz del repo. Ojo: **`.venv/`
  NO está en `.gitignore`** (solo lo está `gdelt_extraction/.venv/`), así
  que aparece como untracked — conviene agregarlo.
  ```
  py -m venv .venv
  ./.venv/Scripts/python.exe -m pip install -r requirements.txt "pandas<3"
  ```
- **Positron es el IDE que usa el usuario** (no VS Code, no RStudio). Dos
  cosas de su configuración cambian los pasos: `python.createEnvironment.trigger`
  está en `"off"` (no ofrece crear el venv solo) y `python.languageServer`
  en `"None"` (sin autocompletado). Tras crear el venv hay que recargar la
  ventana (`Developer: Reload Window`) para que Positron lo detecte, y
  elegirlo en el selector de intérprete del panel de Consola.
- **Quarto** (necesario para la etapa 04) no se instala con pip: es un
  binario aparte. Positron ya lo trae en
  `resources/app/quarto/bin/`. **Usar `quarto.exe`, NO `quarto.cmd`** — el
  `.cmd` devuelve exit 0, no imprime nada y no genera el HTML (verificado
  2026-09-09, costó un rato descubrirlo). Para renderizar:
  ```powershell
  $env:QUARTO_PYTHON = "<repo>\.venv\Scripts\python.exe"
  & "<Positron>\resources\app\quarto\bin\quarto.exe" render "src\04_analysis_index\04_analysis_index.qmd" --to html
  ```
  El puente jupyter de Quarto necesita `pyyaml`, `ipykernel`, `nbclient` y
  `nbformat` en el venv; sin `pyyaml` el render falla con
  `ModuleNotFoundError` sin explicar por qué.
- Google Cloud: proyecto `us-py-engagement-idx`, cuenta de servicio en
  `config/credential_cloud.json` (**no está en git**, cubierta por
  `.gitignore`). Mismo archivo de credenciales para Sheets y para Drive —
  cada módulo pide el scope de OAuth que necesita al construir sus propias
  `Credentials`.
- Local: variables de entorno en `.env` (no versionado, `run_pipeline.py` lo
  carga solo con `python-dotenv`) — `GOOGLE_APPLICATION_CREDENTIALS`,
  `SHEET_ID`, `BEA_API_KEY`, `CONGRESS_API_KEY`. Hay una plantilla en
  `.env.example` (sí versionada, sin valores reales) para copiar y
  completar.
- GitHub Actions: secrets `GOOGLE_SHEETS_CREDENTIALS` (JSON completo de la
  cuenta de servicio), `SHEET_ID`, `BEA_API_KEY` y `CONGRESS_API_KEY`, en
  Settings > Secrets and variables > Actions.
- El Sheet de destino debe estar compartido como **Editor** con el
  `client_email` de la cuenta de servicio. Si el Sheet vive dentro de una
  Unidad compartida de Google Workspace, puede bloquear compartir con cuentas
  externas al dominio (una cuenta de servicio cuenta como externa) — ver el
  punto pendiente en la sección 7.
- **Windows: rutas largas (verificado 2026-09-03, a pedido del usuario —
  "que otra persona pueda correrlo en local sin problemas").** La ruta de
  esta carpeta dentro de la Unidad compartida mide ~190 caracteres ella
  sola (nombres largos + emojis); sumada a las rutas anidadas que crea un
  entorno virtual de Python al instalar paquetes, es fácil superar el
  límite de 260 caracteres que Windows respeta por defecto (falla la
  instalación de dependencias o la corrida misma, con errores confusos de
  archivo no encontrado — ya pasó en una sesión anterior de este proyecto).
  Dos soluciones, no excluyentes:
  1. **Recomendado**: clonar el repo de GitHub a una ruta corta (ej.
     `C:\dev\Paraguay_Index`) en vez de trabajar directo desde la Unidad
     compartida montada. El código no necesita vivir ahí — los datos se
     leen/escriben por la API de Drive, no por disco local (ver sección 2,
     "Regla central"), así que no hace falta tener la Unidad compartida
     montada para nada relacionado al código.
  2. Habilitar `LongPathsEnabled` en el registro de Windows (requiere
     permisos de administrador en esa máquina).

### Dependencias (`requirements.txt`)

```
google-api-python-client   # src/drive.py (subida y lectura de archivos en Drive)
google-auth                # autenticación con la cuenta de servicio
gspread                     # src/sheets.py (pestañas pipeline_log, catalogo_fuentes, processing_log)
python-dotenv                # carga .env en local (run_pipeline.py, run_processing.py)

beautifulsoup4   # parseo de HTML en ingestion
curl_cffi         # requests que bypasea Cloudflare/bot-blocking (bcp.gov.py, state.gov)
ddgs               # búsqueda en DuckDuckGo (state_gov_tias_paraguay.py — state.gov no tiene índice navegable de TIAS)
openpyxl           # escribir .xlsx con pandas (congreso_menciones_paraguay.py, state_gov_tias_paraguay.py)
pandas              # filtrado local / armar excel / processing (exim_autorizaciones.py, congreso_menciones_paraguay.py, state_gov_tias_paraguay.py, src/processing/)
pypdf                # leer texto del PDF "Treaties in Force" (state_gov_tif_vigentes.py) — no es escaneado, texto real extraible
pytrends              # scraping no oficial de Google Trends (google_trends_paraguay.py) — sin API oficial
requests             # fuentes que exponen una API normal (BEA, ForeignAssistance.gov, USAspending, BID, Banco Mundial, DFC, Congreso EE.UU.)
```

## 6. Estado actual

- Pipeline maestro (`run_pipeline.py`), helper de Sheets (`src/sheets.py`) y
  helper de Drive (`src/drive.py`): probados de punta a punta, en local y en
  GitHub Actions.
- Cuatro scripts de ingestion reales, todos de la dimensión
  `3_Compromiso_economico_privado`:
  - `bcp_comercio_exterior.py` — **cambiada de fuente el 2026-09-02** (a
    pedido del usuario, para poder alimentar `src/processing/`): antes
    bajaba un archivo por año desde `importaciones-partidas-p` (desglosado
    por PARTIDA ARANCELARIA — producto —, sin ninguna cifra por país
    socio, asi que no servia para aislar comercio con EE.UU.). Ahora baja
    el Boletín de Comercio Exterior único (serie completa 1961-actualidad,
    desde `comercio-externo-comex-mensual`) con las hojas "Exp./Imp. por
    países" — trimestral desde 1994, incluye fila "Estados Unidos de
    América"/"Estados Unidos de America" (el propio BCP la escribe sin
    tilde en la hoja de importaciones — ver `src/processing/` para el
    workaround). Si la página lista más de una versión del boletín (la
    vieja queda en cache junto a la actual), se elige la de año+trimestre
    más reciente por el propio nombre del archivo, no por orden de
    aparición. Los 34 archivos viejos (por partida) quedaron sin usarse
    tras el cambio — el usuario los borró a mano de Drive el 2026-09-08
    (el servicio no puede borrar, rol Writer), ya que ahora la fuente
    trabaja con un único archivo (el Boletín).
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
- Ocho scripts de ingestion reales de la dimensión `1_Compromiso_financiero_oficial`
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
  - `cuota_capital_bid.py` (2026-09-21, primer paso del pendiente #4 —
    ponderar BID/Banco Mundial por cuota de capital de EE.UU.): sube el %
    de capital/poder de voto de EE.UU. en el BID, **30,006%**, verificado a
    mano contra la página oficial del BID ("Capital Stock And Voting
    Power"). **Excepción real, no solo pragmática, a "todo se
    scrapea":** esa página no tiene la tabla en HTML — la renderiza un
    widget de Power BI embebido (confirmado inspeccionando la página con
    el navegador: carga `idb_powerbi-embed.js` y un iframe de
    `app.powerbi.com` con token de sesión), así que no hay HTML ni JSON
    estático que `requests`/`curl_cffi` puedan leer — automatizarlo en
    serio exigiría un navegador headless, una dependencia que el proyecto
    no usa en ningún otro lado. Se usa un **valor fijo verificado a mano**,
    justificado porque además se confirmó que el BID no tiene un aumento
    de capital desde "IDB-9" (2010) — el mismo 30,006% aplica a todo
    2015-2026. **Verificación (a pedido del usuario, dado que no se puede
    chequear en vivo):** es manual — hay que revisar la página del BID de
    vez en cuando y, si cambia (ej. un futuro aumento de capital),
    actualizar `PORCENTAJE_EEUU`/`FECHA_VERIFICACION` en el código; cada
    corrida solo sube un archivo nuevo si `FECHA_VERIFICACION` cambió, así
    el historial en Drive documenta cuándo se revisó por última vez, no
    un timestamp automático sin sentido. El Banco Mundial (IBRD) **sí**
    tuvo un cambio real de cuota en 2018 (Selective Capital Increase) — su
    ingestion (`cuota_capital_bancomundial.py`) queda pendiente, necesita
    una serie por año, no una constante (ver pendiente #4 actualizado en
    sección 7).
  - `cuota_capital_bancomundial.py` (2026-09-22, resuelve el resto del
    pendiente #4): histórico fijo, editado a mano, con el % de poder de
    voto de EE.UU. en el IBRD **por año fiscal** (2016, 2018, 2019, 2022,
    2023, 2024, 2025 — verificado 2026-09-22, cada valor sacado a mano del
    "Information Statement" oficial de ese año en `thedocs.worldbank.org`,
    buscando la oración "The United States is IBRD's largest shareholder,
    with XX.XX% of total voting power."). **A diferencia del BID, acá SÍ
    hace falta una serie por año**: el % se mueve de verdad (16,63% en
    FY2016 → 15,49% en FY2024, sin patrón simple, confirmado con evidencia
    real). **A diferencia de TIAS/USTR, no hay verificación en vivo en
    cada corrida** (a pedido del usuario, "no complicar tanto el scrapeo")
    — cada edición del "Information Statement" vive en una URL con un
    hash impredecible, sin página índice, así que agregar un año nuevo
    requiere buscarlo a mano (el propio docstring del módulo trae la
    receta paso a paso: buscar "IBRD Information Statement FY{año}" en
    Google, abrir el PDF, copiar el % de esa misma oración). Años sin dato
    todavía: FY2015, FY2017, FY2020, FY2021, FY2026 — `compromiso_financiero_oficial.py`
    arrastra el último valor confirmado hacia adelante (o hacia atrás para
    2015, anterior al primer año con dato) para esos huecos, mismo
    criterio que ya usa el proyecto para otras fuentes anuales.
  - Los ocho probados con datos reales: suben bien (confirmado con datos
    reales) y una segunda corrida saltea lo que ya está.
- Cuatro fuentes reales de la dimensión `2_Actividad_gubernamental_y_diplomatica`
  (2026-09-02):
  - `congreso_menciones_paraguay.py` — a diferencia de las demás fuentes, no
    existe como archivo descargable en ningún sitio: se **construye** acá
    combinando dos APIs. Busca texto completo por "Paraguay" en
    `api.govinfo.gov` (colección BILLS — HR, S, HRES, SRES, HJRES, SJRES,
    HCONRES, SCONRES), deduplica por proyecto (GovInfo devuelve una fila por
    cada versión publicada, no por proyecto), filtra a 2015-2025, y enriquece
    cada proyecto con datos estructurados de `api.congress.gov` (título,
    fechas, cámara, área de política, patrocinador). Sube un único `.xlsx`
    (una fila por proyecto), con fecha en el nombre (idempotente por día).
    Probado con datos reales: 49 proyectos en el rango. **Límite real de la
    fuente**: es búsqueda de texto completo, no un filtro temático — un
    proyecto puede aparecer solo por mencionar a Paraguay de paso (ver
    docstring del módulo). Requiere `CONGRESS_API_KEY` (gratuita, el usuario
    la generó en `api.congress.gov/sign-up` — la misma key sirve para ambas
    APIs). **Rediseñado 2026-09-10 (commit de `lvisalotequi`): cuenta TODAS
    las menciones, no solo detecta si aparece.** Cada fila incluye ahora
    `cantidad_menciones_paraguay` (cuántas veces aparece "Paraguay" en el
    texto completo) y `extractos_menciones_paraguay` (un fragmento real
    alrededor de CADA mención, unidos por `" ||| "` — antes solo se
    guardaba `extracto_mencion_paraguay`, un único fragmento de la primera
    mención). Se descargan del mismo documento que GovInfo ya encontró que
    contiene "Paraguay" (`/packages/{packageId}/htm`), no son snippets
    inventados. **Por qué contar en vez de solo detectar**: es un proxy de
    qué tan central es Paraguay en el proyecto (no de si la mención es
    positiva o negativa) — misma lógica que la *saliency theory* del
    Comparative Manifestos Project y el *expressed agenda model* de
    Grimmer (2013, "Text as Data"), que miden atención a un tema por
    frecuencia de mención en el texto, no por juicio de contenido. Piloto
    real (2026-09-10, 3 años: 2020/2021/2024): los proyectos con
    "Paraguay" en el título promediaron 12.0 menciones contra 1.14 de los
    que lo mencionan de paso — separación clara que valida el enfoque.
    **Límite reconocido explícitamente**: la frecuencia no mide intensidad
    de tono (una mención muy fuerte puede eclipsar a varias tibias);
    clasificar el tono de cada mención requeriría NLP/LLM, que se decidió
    no usar para que el pipeline siga siendo determinístico y sin depender
    de un servicio externo.
  - `ustr_consejo_comercio_inversion.py` — hitos del Consejo de Comercio e
    Inversión (TIFA/TIC) entre Paraguay y EE.UU., vía scraping de
    ustr.gov (el buscador propio del sitio no funciona — confirmado
    2026-09-02, cero resultados para cualquier término, sin API detrás). Es
    un diseño **híbrido**: un historico fijo con los 5 hitos 2015-2024
    (verificados a mano escaneando el archivo completo de USTR mes a mes —
    ese rango cerrado no se vuelve a escanear cada corrida) + una revisión
    liviana del sitio en vivo desde 2025 en adelante en cada corrida, para
    que futuras reuniones se agreguen solas. De los 5 hitos, solo 3 son
    literalmente "reuniones del Consejo" (2022/2023/2024, primera/segunda/
    tercera reunión); los otros 2 son hitos previos (MOU 2015, firma del
    TIFA 2017) — columna `tipo` para distinguirlos. Probado con datos
    reales: 5 eventos, 0 nuevos del chequeo en vivo (no hubo reunión en
    2025 todavía). **Verificación del histórico (2026-09-02, a pedido del
    usuario — "quiero poder verificar si la información histórica es
    real")**: en cada corrida se vuelve a pedir la URL de cada uno de los 5
    hitos fijos (solo 5 pedidos, no todo el archivo) y se confirma que la
    página siga existiendo, mencione a Paraguay, y que la fecha guardada
    aparezca en el texto — columnas `verificado`/`nota_verificacion` en el
    Excel. Al probarlo encontró un caso real: la página de 2017 (formato
    archivado pre-2018) no tiene ninguna fecha extraíble en el texto — la
    única fecha que aparece es "26 de septiembre de 2003", que es una
    mención real pero a un acuerdo *anterior* que este TIFA reemplaza
    ("Agreement Establishing the United States–Paraguay Bilateral Council
    on Trade and Investment"), no la fecha del comunicado. La verificación
    distingue esto de un error real (fecha que sí aparece pero no coincide)
    y lo marca como "no se pudo confirmar", no como "dato incorrecto".
  - `state_gov_tias_paraguay.py` — **en revisión desde 2026-09-22** (no
    Validado): ver `state_gov_tif_vigentes.py` más abajo, agregada el mismo
    día y candidata a reemplazarla más adelante (decisión pendiente,
    todavía no tomada — por ahora coexisten). Publicaciones TIAS (Treaties
    and Other International Acts Series) entre Paraguay y EE.UU., desde el
    Office of Treaty Affairs de state.gov. state.gov no tiene un índice navegable de
    TIAS por país ni un buscador propio que sirva para esto (confirmado
    2026-09-02) — la única forma de encontrarlas es buscando por texto. Es
    otro diseño **híbrido**, igual que `ustr_consejo_comercio_inversion.py`:
    un histórico fijo con los 3 TIAS de Paraguay ≥2015 encontrados y
    confirmados el 2026-09-02 (años de TIAS 2021, 2025 y 2026 — también
    existen TIAS de Paraguay más viejos, con numeración pre-2000 sin guion,
    que quedan fuera del rango a propósito) + una búsqueda en vivo vía
    DuckDuckGo (paquete `ddgs`) para detectar TIAS nuevos que todavía no
    estén en el histórico. Igual que USTR, en cada corrida se vuelve a pedir
    la página de cada uno de los hitos fijos para confirmar que los datos
    guardados sigan siendo reales (columnas `verificado`/`nota_verificacion`).
    **Riesgo distinto al resto de las fuentes**: la búsqueda de DuckDuckGo
    puede fallar o devolver menos resultados corriendo desde IPs compartidas
    (como las de GitHub Actions) que desde una IP residencial — si las tres
    consultas fallan, el módulo no rompe: sube igual el histórico fijo ya
    verificado y avisa por consola. state.gov está detrás de bot-blocking
    (403 con `requests` normal, confirmado 2026-09-02) — usa `curl_cffi` con
    `impersonate="chrome"`, igual que bcp.gov.py. El límite superior de años
    no es una constante fija sino "el año en curso" en cada corrida (con un
    tope fijo en 2025, el TIAS 26-317 — Status of Forces Agreement, vigente
    desde 2026-03-17 — se hubiera quedado afuera para siempre pese a estar
    ya verificado como real; encontrado y corregido el mismo 2026-09-02, en
    la primera corrida real del módulo). Adaptado de un script de referencia
    que pasó el usuario, simplificado a un único Excel en memoria sin
    dependencias de Node ni archivos intermedios en disco, siguiendo la
    convención del resto de `src/ingestion/`. Probado con datos reales: 3
    TIAS, 0 sin verificar. **Completitud del histórico verificada a mano
    (2026-09-02)**: además de los 3 hitos ya confirmados, se corrió una
    búsqueda separada por prefijo de año en state.gov para todo 2015-2024
    ("Paraguay (15-" ... "Paraguay (24-"), repetida dos veces de forma
    independiente para descartar ruido puntual de DuckDuckGo — en ambas
    corridas hubo hits sueltos pero ninguno matcheó el patrón real de URL
    de un TIAS de Paraguay. No hay ningún TIAS de Paraguay perdido en ese
    rango.
  - `state_gov_tif_vigentes.py` (2026-09-22, **Validado**): descarga el PDF
    anual "Treaties in Force" (TIF) del Departamento de Estado — la
    publicación oficial que lista TODOS los tratados y acuerdos bilaterales
    de EE.UU. que siguen vigentes a esa fecha (el propio DOS ya excluye lo
    terminado/reemplazado/superado). El link al PDF del año vigente se
    busca en `state.gov/treaties-in-force/` (no se hardcodea el año). **No
    es un PDF escaneado como imagen** — contra lo que se creía cuando se
    investigó `state_gov_tias_vigentes` (nota de la sección 6, más abajo);
    la edición 2026 se probó de nuevo y tiene texto real, extraíble con
    `pypdf` (551 páginas, ~5 MB). La sección bilateral de Paraguay se aísla
    usando la tabla de contenidos propia del documento (no números de
    página fijos, que cambian de edición a edición) y se parsea línea por
    línea (categoría, fecha de entrada en vigor, cita) — ver el docstring
    del módulo para el detalle completo de los casos raros que maneja
    (categorías en 2 líneas, fechas partidas en 2 líneas, enmiendas que no
    cuentan como acuerdo nuevo). Verificado a mano, entrada por entrada,
    contra el texto del PDF antes de escribir el parser: **39 acuerdos**
    para Paraguay, 1860-03-07 a 2025-08-14. **Por qué se agrega y no
    reemplaza a `state_gov_tias_paraguay.py`** (decisión del usuario,
    2026-09-22): esta fuente es mucho más completa (cualquier tipo de cita,
    cualquier fecha de firma, no solo TIAS post-2015), y un análisis de
    correlación confirmó que no es redundante con
    `ustr_consejo_comercio_inversion.py` (correlación en diferencias ~0,07,
    ver DICCIONARIO_VARIABLES.md) — pero la decisión de si `state_gov_tias_paraguay.py`
    queda obsoleta y se elimina se toma más adelante, no ahora.
  - `mre_menciones_eeuu.py` (2026-09-22, **Validado**): sube a
    Drive lo que `mre_scraping/` ya produjo localmente — noticias del MRE de
    Paraguay clasificadas por mención y bilateralidad con EE.UU. Misma
    excepción documentada que `gdelt_proxy_b.py`/`gdelt_extraction/`: el
    scraping (archivo actual + índice CDX de Wayback Machine, con demora
    entre pedidos) tarda horas para el rango completo 2015-2025, no tiene
    sentido en GitHub Actions — corre a mano, localmente, desde
    `mre_scraping/` (ver `mre_scraping/README.md`). **Origen**: el usuario
    trajo el scraper ya armado y probado (`mre_eeuu_scraper_portable.zip`,
    dos etapas — `scraper_mre.py` recolecta, `clasificar_bilateral.py`
    clasifica por reglas explícitas sin IA). Dos cambios hechos para
    integrarlo (2026-09-22):
    1. **Bypass de Cloudflare**: el sitio actual (`mre.gov.py`) devolvía 403
       con `requests` normal — mismo bloqueo que `bcp.gov.py`/`state.gov`,
       corregido con `curl_cffi` `impersonate="chrome"` en la clase
       `Fetcher`. Verificado: 403 → 200.
    2. **Bug real encontrado al cambiar de librería**: el manejo de errores
       capturaba `requests.RequestException` (nombre que no existe en
       `curl_cffi.requests` al mismo nivel — queda en
       `requests.exceptions.RequestException`) — con el cambio, un timeout
       real de red terminaba en `AttributeError` sin manejar en vez de
       reintentar; apareció en la práctica al correr la extracción completa
       (un timeout contra el CDX de Wayback tumbó el proceso). Corregido y
       verificado con un caso forzado.

    Corrida completa 2015-2025 terminada el 2026-09-22 (~5h14m, 9.304 URLs,
    exit 0). De esas, 7.494 quedaron `estado == "ok"` (el resto: sin fecha
    extraíble, fuera del período, error de descarga o texto insuficiente —
    descartadas antes de contar). Verificado con recálculo independiente
    antes de subir: 91 noticias bilaterales, 1.401 menciones totales de
    EE.UU., 0 diffs (ver `mre_scraping/README.md` y
    `DICCIONARIO_VARIABLES.md` para el detalle completo).
- Dos fuentes reales de la dimensión `4_Visibilidad_mediatica_y_relevancia_publica`
  (2026-09-01, segunda agregada 2026-09-22):
  - `gdelt_proxy_b.py` — sube a Drive los CSV mensuales ya extraídos por
    `gdelt_extraction/` (ver más abajo), cobertura mediática bilateral PY-US
    según la regla "proxy B" sobre GDELT 2.1 GKG (coocurrencia geográfica
    PY-US + señales temáticas D/I/R/E — diplomáticas, gobierno/instituciones,
    comercio/fronteras/inmigración, economía/impuestos; ver
    `gdelt_extraction/proxy_b_config.json`, versión aceptada 2026-08-27). Es
    una aproximación de coocurrencia con señales institucionales, **no**
    noticias validadas individualmente ni medición de calidad de relaciones
    diplomáticas — ver los límites documentados en la propia config y en
    `gdelt_extraction/README.md`. **Aclaración importante sobre la columna
    `month` (2026-09-08, tras una confusión real en conversación con el
    usuario):** `month` es el primer día del período que esa fila
    *describe* (`month=2015-03-01` → cubre 1-31 de marzo), **no** una fecha
    de corte que apunte al mes anterior — está hardcodeado así en
    `gdelt_extraction/gdelt_queries.py`
    (`DATE('{window.start.replace(day=1)}') month`). Es un concepto
    distinto de `last_complete_month()` en `bilateral_media_extractor.py`
    (que sí calcula "el mes anterior a hoy", pero solo como default de
    `--start`/`--end` cuando se corre ese script directo sin fechas
    explícitas — ni `extraction_workflow.py` ni `historical_campaign.py`,
    las formas normales de correr una extracción, pasan por ese default).
    Ver el detalle completo en `gdelt_extraction/README.md`. Sube dos tipos
    de archivo: 18 CSV `monthly_{desde}_{hasta}.csv` que tilan sin huecos
    ni superposición todo el rango feb-2015 a ene-2026 (son la fuente de
    verdad, los que usa `src/processing/`; se suma un `monthly_*` nuevo
    cada vez que se extiende la extracción, ver la nota de
    `gdelt_extraction/` más abajo), más **un
    único `historical_processed_{desde}_{hasta}.csv`** que es el
    conglomerado de esos mismos archivos en uno solo, para quien quiera
    bajar todo de una — no se genera aparte, es un `pd.concat()` de todos
    los monthly, y hay que regenerarlo (y volver a subir) cada vez que se
    suma un mes nuevo (la versión de un rango viejo queda huérfana en Drive
    — el servicio no puede borrar, rol Writer; hay que borrarla a mano
    cuando se pueda. Pasó primero el 2026-09-08: la versión original solo
    cubría feb-2015 a mar-2020, resabio de una corrida vieja).
    `src/processing/visibilidad_mediatica_y_relevancia_publica.py`
    ignora este archivo a propósito (solo lee los `monthly_*`, ver su
    docstring) para no contar cada mes dos veces.
  - `gdelt_extraction/` — el extractor en sí (`historical_campaign.py` y
    soporte), corrido a mano localmente contra el proyecto GCP
    `us-py-engagement-idx` (sandbox de BigQuery sin facturación, techo
    preventivo mensual 850 GiB). No es un módulo de `src/ingestion/` — ver
    la excepción documentada en la sección 4. Cobertura completa feb-2015 a
    **ene-2026** (extendido 2026-09-08, a pedido del usuario, con
    `extraction_workflow.py plan/execute --config historical_workflow_config.json`
    para el rango puntual ene-2026 — no `historical_campaign.py`, que
    procesaría todo el backlog pendiente en vez de un solo mes; ~7.77 GiB,
    dentro de los límites). El detalle exacto de qué meses están cubiertos
    vive en `gdelt_extraction/output/historical_campaign/CONTINUIDAD.md` (se
    reescribe en cada corrida, no confiar en esta nota para el estado
    exacto). **Para sumar un mes nuevo:** (1) `extraction_workflow.py plan
    --start AAAA-MM --end AAAA-MM --config historical_workflow_config.json`
    (dry run, sin costo) para congelar un plan; revisar el GiB estimado; (2)
    `extraction_workflow.py execute --plan RUTA_DEL_PLAN.json` — chequea
    que la facturación siga deshabilitada antes y después, si esa
    verificación falla el programa se detiene sin consultar nada (visto en
    la práctica: puede fallar por sesión de `gcloud auth login` vencida —
    reautenticar con `gcloud auth login`, o `gcloud.cmd auth login` desde
    PowerShell si la política de ejecución de scripts bloquea el `.ps1`);
    (3) regenerar `historical_processed_{desde}_{hasta}.csv` con un
    `pd.concat()` de todos los `monthly_*.csv` (no hay script dedicado
    todavía, se hizo a mano) y borrar la versión vieja local; (4) correr
    `gdelt_proxy_b.py` para subir el mes nuevo + el histórico regenerado a
    Drive; (5) correr `visibilidad_mediatica_y_relevancia_publica.py`
    (processing) para que el trimestre nuevo llegue a
    `02_limpias/4_Visibilidad_mediatica_y_relevancia_publica_limpias/` — si
    ya se corrió processing ese mismo día, hay que sobreescribir a mano el
    archivo del día en Drive (`files.update`), el chequeo de idempotencia
    es por día. **Para correrlo en otra computadora**, ver
    `gdelt_extraction/README.md` — necesita Google Cloud SDK
    instalado y autenticado aparte (no viene con el repo ni con Python), y
    en Windows puede requerir habilitar rutas largas si el checkout queda en
    una ruta profunda (ver esa misma guía).
  - `google_trends_paraguay.py` (2026-09-22, **Validado**): interés de
    búsqueda en Google (`pytrends`, librería no oficial — no hay API
    oficial de Google Trends) para 3 términos fijos (`Paraguay trade`,
    `Paraguay tariffs`, `Paraguay embassy`), `geo=US`. Complementa a GDELT:
    GDELT mide cobertura mediática (oferta), esto mide demanda (cuánto
    busca el público de EE.UU.) — no verificado todavía si son redundantes
    entre sí. **Dos decisiones tomadas con datos reales antes de construir
    el módulo, ver `DICCIONARIO_VARIABLES.md` para el detalle completo**:
    el filtro geográfico (`US` vs `global`, los números cambian de forma
    real) y la lista de términos (se probaron 9 candidatos; se descartó
    "Paraguay visa" pese a tener la mejor cobertura por ser conceptualmente
    ambiguo, se mantuvo "Paraguay tariffs" pese a ser disperso porque sus
    picos coinciden con hechos reales). **La lista de términos es FIJA**:
    Google Trends normaliza los términos de una misma consulta relativos
    entre sí (0-100 según cuál tuvo más búsquedas en todo el rango), así
    que agregar/sacar un término reescalaría retroactivamente la serie ya
    publicada de los demás. Para rangos largos (2015-2025) la fuente
    devuelve datos **mensuales**, no semanales. **Riesgo operativo
    documentado, no resuelto**: `pytrends` scrapea el mismo endpoint que la
    web de Trends, sin API oficial — Google puede bloquear/limitar el
    scraping, más todavía desde IPs compartidas como GitHub Actions (mismo
    tipo de riesgo que ya tiene `state_gov_tias_paraguay.py` con
    DuckDuckGo); el módulo reintenta 3 veces y, si falla igual, no sube
    nada y avisa por consola sin romper el pipeline. También se encontró un
    bug real de compatibilidad: la versión instalada de `pytrends` rompe
    con `urllib3>=2.0` si se le pasan `retries`/`backoff_factor` a
    `TrendReq` — el módulo no usa esos parámetros y reintenta a mano.
    Verificado con datos reales: 141 meses (2015-01 a 2026-09), subido a
    Drive y confirmado en `src/processing/`.
- **Dos fuentes de la pseudo-dimensión `insumos_indice` (2026-09-22)** —
  deflactores/escalas transversales que usa (o va a usar) la etapa de
  construcción del índice, no atados a ninguna de las 4 dimensiones reales
  del vínculo bilateral (ver el docstring de cada módulo para la
  justificación completa):
  - `bls_ipc_eeuu.py` — serie mensual `CUUR0000SA0` (IPC de EE.UU.) de la
    API pública del BLS, en tramos de 10 años calculados dinámicamente
    (límite de la API sin credencial) — JSON crudo, sin transformar, mismo
    criterio que `fa_gov_asistencia_oficial.py`/`bid_proyectos.py` (ver
    `feedback_json_raw_is_source_of_truth` en memoria). Probado con datos
    reales: 140 puntos mensuales, 2015-2026 (un 503 transitorio de la API
    del BLS en el primer intento, resuelto reintentando).
  - `ine_poblacion_paraguay.py` — Excel único "Estimaciones y Proyecciones
    de la Población Nacional... 1950-2050. Revisión 2024" del INE de
    Paraguay (post-Censo 2022), fila "Total País" de la hoja "Poblac a
    mitad de año 1950-2050". **Investigado si había corte trimestral (a
    pedido del usuario)**: no existe — es una estimación/proyección
    demográfica anual ("a mitad de año"), igual que la mayoría de los
    institutos de estadística de la región; se usa anual. Complementa (no
    reemplaza todavía) al `SP.POP.TOTL` del Banco Mundial que ya usa
    `04_construccion_indice.qmd` — es la fuente oficial paraguaya.
    Verificado con datos reales contra la propia fuente: 2015=5.912.082,
    2024=6.372.623, 2026=6.460.159 habitantes.
  - **Ninguna de las dos está conectada todavía a `04_construccion_indice.qmd`**
    (que sigue pidiendo IPC a la API del BLS y población a la API del Banco
    Mundial en tiempo de render) — no se tocó el `.qmd` porque esa sección
    está en pausa. Ver pendiente #7 (sección 7) para el detalle.
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
- Repo público desde 2026-08-26, con el workflow disparándose cada 3 meses
  además de manual.
- **Carpetas de dimensión renombradas a mano por el usuario (descubierto
  2026-09-02):** las 4 carpetas de dimensión dentro de `01_crudas` pasaron
  a llamarse `{dimensión}_crudas` (ej. `3_Compromiso_economico_privado_crudas`)
  — rename hecho directo en Drive, sin avisar en el momento. Las
  constantes `DIMENSION` de cada módulo NO llevan ese sufijo, así que
  `resolve_ingestion_folder()` (que buscaba/creaba por el nombre exacto de
  `DIMENSION`) dejó de encontrar las carpetas reales y creó **8 carpetas
  duplicadas vacías** (para las 4 dimensiones) antes de que el usuario
  avisara del rename. Las 8 quedaron en Drive (el servicio no puede
  borrarlas, rol Writer) — inofensivas, hay que borrarlas a mano cuando se
  pueda. Arreglado en dos partes en `src/drive.py`: (1)
  `resolve_ingestion_folder()` ahora arma la ruta con el sufijo
  `_crudas` agregado (`CARPETA_CRUDAS/{dimension}_crudas/{fuente}`) para
  que cualquier fuente nueva caiga en la carpeta real, no en una vacía
  nueva; (2) `FOLDER_IDS`/`VARIABLE_FOLDER_IDS`, un diccionario con los IDs
  ya confirmados de las 14 carpetas de ingestion + las 17 de processing
  — `resolve_ingestion_folder()`/`resolve_variable_folder()` los usan
  directo, sin buscar. Para una fuente/dimensión nueva (todavía sin
  entrada en el diccionario), sigue cayendo a la búsqueda por nombre, pero
  ahora con reintentos (`_buscar_hijo_con_reintentos`) — conviene agregar
  su ID al diccionario a mano después de la primera corrida exitosa.
- **Nombres de carpeta sin puntos ni tildes (política 2026-09-08, a pedido
  del usuario — pensando en que el código lo corra otra persona sin
  problemas):** las 4 constantes `DIMENSION` (y `DIMENSION_CRUDA`/
  `DIMENSION_LIMPIA` en processing) pasaron de `"N.Nombre_con_tildes"` a
  `"N_Nombre_sin_tildes"` — ej. `2.Actividad_gubernamental_y_diplomática` →
  `2_Actividad_gubernamental_y_diplomatica`. Motivo: un punto o una tilde
  en un nombre de carpeta puede dar problemas reales en otra máquina/SO
  (encoding de consola, herramientas que no esperan esos caracteres en
  rutas). Se corrigió con un reemplazo de texto en los 18 módulos que
  declaran la constante + `FOLDER_IDS`/`VARIABLE_FOLDER_IDS` en
  `src/drive.py` (mismas claves, mismos IDs — no se tocó ningún archivo),
  y se renombraron a mano las 8 carpetas de dimensión reales en Drive
  (`files.update` sobre el `name`, no crea IDs nuevos). Las 17 carpetas de
  variable y las 14 de fuente ya cumplían la regla, no se tocaron.
- **`src/processing/` cubre las 4 dimensiones (2026-09-02, rediseñado
  2026-09-03):** un módulo por dimensión, cada uno consolida sus fuentes
  crudas y sube **un CSV por variable** (no un CSV combinado por dimensión)
  a `02_limpias/{dimensión}_limpias/{variable}/` — esquema fijo en las 4
  dimensiones: `trimestre, anio, trimestre_num, valor, unidad`. **Política
  de carpetas y unidades (2026-09-03, a pedido del usuario — "quiero una
  carpeta por cada variable... en formatos iguales"):** cada variable tiene
  su propia carpeta (para poder leerse/actualizarse sola después), y dentro
  de cada tipo (monetario / cantidad / índice) las variables comparten
  unidad — todo lo monetario en USD sin escalar, nunca miles/millones
  mezclados. `src/processing/_common.py` centraliza esta convención
  (`subir_variable()`/`reescalar()`) para que ningún módulo arme el CSV a
  mano. Corridos con `run_processing.py` (auto-descubrimiento, ver sección
  2) — separado del schedule automático de GitHub Actions, se corre a
  mano. Probados con datos reales el 2026-09-03:
  - `compromiso_financiero_oficial.py` (dimensión 1, **12 variables** desde
    el 2026-09-22 — antes 7, ver historial en el módulo y en
    `DICCIONARIO_VARIABLES.md` —, todo **monetario en USD sin escalar**):
    obligaciones/desembolsos de ForeignAssistance.gov (anual, repetido en
    los 4 trimestres — la fuente no tiene fecha más fina que el año
    fiscal), obligaciones de USAspending (trimestral real, sumando
    `federal_action_obligation` por `action_date` de: TODAS las
    transacciones de Contracts, más solo las de Assistance cuya
    `awarding_agency_name` sea Social Security Administration, Railroad
    Retirement Board o Department of Veterans Affairs — **rediseñada
    2026-09-28, a pedido del usuario, "excluir toda la asistencia
    extranjera, quedarnos con el resto"**: el resto de Assistance (USAID,
    Departamento de Estado, USDA/Food for Progress, IAF, HHS, Interior —
    ~US$118,9M 2015-2026) se excluye porque ya lo mide `fa_gov_obligaciones`/
    `fa_gov_desembolsos`; las tres agencias que sí se mantienen no son
    asistencia extranjera pese a estar clasificadas como "Assistance" por
    USAspending — son pagos de beneficios individuales (jubilación, pensión,
    compensación por discapacidad) a personas que residen en Paraguay, sin
    relación con cooperación bilateral (~US$30,4M 2015-2026, ver
    `AGENCIAS_NO_ASISTENCIA_EXTRANJERA` en el código y
    `DICCIONARIO_VARIABLES.md` para el detalle completo con montos por
    agencia); total de la variable tras el cambio: ~US$313,5M, antes
    ~US$431,8M con Assistance completo, 47 trimestres, 2015-Q1 a 2026-Q3),
    comprometido de DFC + `dfc_proyectos_vigentes`
    (stock de vigencia, ver arriba), autorizado de EXIM + `exim_desembolsado`
    (trimestral real por `Decision Date`, solo `Decision == "Approved"`), y
    de BID/Banco Mundial: `bid_proyectos_aprobados`/
    `bancomundial_proyectos_aprobados` (trimestral real por fecha de
    aprobación del proyecto, monto total sin ponderar) más
    **`bid_proyectos_atribuible_eeuu`** y **`bancomundial_proyectos_atribuible_eeuu`**
    (nuevas, 2026-09-22 — pendiente #4 resuelto por completo, ver la nota
    de "Resuelto" al final de la sección 7 para el detalle). Rango 2015-Q1
    a 2027-Q1 (el Banco Mundial ya tiene un proyecto con aprobación futura
    anunciada) — varía por variable, cada una con su propio CSV.
  - `actividad_gubernamental_y_diplomatica.py` (dimensión 2, **7 variables**
    desde el 2026-09-22 — antes 4, ver más abajo —, todo **cantidad**):
    hitos del Consejo de Comercio e Inversión de USTR (por `fecha`, muy
    disperso — 5 trimestres con datos en 10 años, sin cambios), y TIAS de
    Paraguay (rediseñada, ver más abajo). **Congreso, rediseñado
    2026-09-10 (commit de `lvisalotequi`) — reemplaza a
    `congreso_proyectos_mencion_paraguay` con dos variables nuevas**, mismo
    patrón que fa_gov en la dimensión 1 (una fuente, dos series): (1)
    `congreso_proyectos_relevantes_paraguay` — cantidad de proyectos por
    trimestre con `cantidad_menciones_paraguay > UMBRAL_MENCIONES_RELEVANTE`
    (3), un proxy de que Paraguay es tema central del proyecto y no una
    mención de paso; (2) `congreso_menciones_totales_paraguay` — suma de
    menciones de TODOS los proyectos del trimestre, sin umbral, una medida
    continua de volumen. La variable vieja (conteo simple de proyectos, sin
    distinguir mención central de mención de paso) queda retirada — su
    carpeta de Drive quedó huérfana (el servicio no puede borrarla, rol
    Writer). **TIAS, política 2026-09-10**: `state_gov_tias_vigentes` pasó
    de contar TIAS *nuevos* por trimestre (disperso — 3 trimestres con
    datos, no calzaba con el propio nombre "vigentes") a un **stock
    acumulado** de TIAS vigentes (`_acumular_por_trimestre()` — mismo
    enfoque que usa el Departamento de Estado en su reporte anual
    "Treaties in Force" y el World Treaty Index para operacionalizar
    relaciones bilaterales). USTR no se cambió a stock a propósito: una
    reunión no tiene "vigencia" que persista después de ocurrir, a
    diferencia de un tratado. **Límite explícito y no verificado**: el
    stock de TIAS asume que ninguno se da de baja después de entrar en
    vigor — no hay ningún mecanismo que lo detecte. `state_gov_tias_vigentes`
    queda **en revisión** desde 2026-09-22 (no Validado) — ver
    `state_gov_tif_vigentes` justo abajo, que sí resuelve ese límite.

    **`state_gov_tif_vigentes` (agregada 2026-09-22, Validado — se AGREGA,
    no reemplaza a `state_gov_tias_vigentes`, decisión del usuario)**:
    stock acumulado de TODOS los tratados/acuerdos bilaterales vigentes
    según "Treaties in Force" (TIF), la publicación oficial anual del
    Departamento de Estado — resuelve directamente el límite de arriba,
    porque el propio DOS ya excluye lo terminado antes de publicar la
    lista, no hay que asumir nada. A diferencia de `state_gov_tias_vigentes`,
    no se limita a instrumentos con número TIAS ni a firmas posteriores a
    2015 (incluye acuerdos vigentes firmados desde 1860) — por eso usa
    `_acumular_con_base_historica()` en vez de `_acumular_por_trimestre()`:
    la base de 2015-Q1 ya arranca en 33 (lo firmado antes de 2015 que
    seguía vigente), no en 0. Verificado con datos reales: 47 trimestres
    (2015-Q1 a 2026-Q3), de 33 a 39 acuerdos vigentes, 0 diffs contra un
    recálculo independiente. **Verificación de que no es redundante con
    USTR**: correlación en niveles 0,86 (efecto de tendencia compartida,
    ambas series solo crecen) pero en primeras diferencias cae a 0,07 — son
    estadísticamente independientes (ver DICCIONARIO_VARIABLES.md para el
    detalle del análisis y la nota sobre la TIFA, que aparece en las dos
    fuentes con fechas distintas — firma en USTR, entrada en vigor en TIF —
    por diseño, no por error).

    Esta redirección hacia medidas continuas (menciones totales, stock
    acumulado) es directamente relevante para el
    pendiente #6 ("reemplazar conteos de eventos raros por alguna medida de
    intensidad continua") — sigue sin estar incorporada al índice, pero el
    insumo para intentarlo ya existe. **MRE, agregado y Validado 2026-09-22
    — ver `mre_menciones_eeuu.py` en la sección de ingestion más arriba
    para el detalle de origen y los dos cambios hechos**: mismo patrón de
    dos variables que Congreso — `mre_noticias_bilaterales` (cantidad por
    trimestre con `es_bilateral == 1`, clasificación ya calculada por
    reglas explícitas en `mre_scraping/clasificar_bilateral.py` — a
    diferencia de Congreso, el umbral de relevancia ya viene aplicado en el
    dato crudo, no se reaplica en processing) y `mre_menciones_totales_eeuu`
    (suma de `numero_menciones_eeuu` de todas las noticias válidas del
    trimestre, sin umbral). Es la contraparte del lado paraguayo de
    USTR/Congreso. Verificado con datos reales (corrida completa
    2015-2025, 9.304 URLs, terminada 2026-09-22): 91 noticias bilaterales
    (28 trimestres, 2017-Q2 a 2025-Q4) y 1.401 menciones totales (42
    trimestres, 2015-Q3 a 2025-Q4), 0 diffs contra recálculo independiente.
  - `compromiso_economico_privado.py` (dimensión 3, 5 variables, todo
    **monetario en USD sin escalar**): exportaciones/importaciones con
    EE.UU. del Boletín de Comercio Exterior, flujo de IED de EE.UU. del
    Cuadro 4 del anexo del BCP, remesas desde EE.UU. (sumando meses en
    trimestre), y posición de IED de BEA (anual repetido). Rango 2015-Q1
    a 2026-Q2 (varía por variable). **Bug de datos encontrado y corregido
    (2026-09-08, a pedido del usuario — "veo que jalas data desde el
    segundo trimestre"):** `exportaciones` venía sin el primer trimestre
    de 2015 y 2016 — no era un límite de la fuente, era un typo real del
    propio Boletín del BCP: en la hoja "Exp. por países", la fila de
    rótulos de trimestre tiene una **"l" minúscula en vez de "I" mayúscula**
    para el primer trimestre de varios años (23 años en total en esa hoja,
    6 en "Imp. por países" — todos anteriores a 2015 salvo los dos de
    exportaciones ya mencionados, así que no afectaban nada más dentro del
    rango del proyecto). `_mapear_columnas_trimestre()` solo reconocía
    "I"/"II"/"III"/"IV" exactos, así que esas columnas quedaban afuera en
    silencio. Se corrigió normalizando "l" → "I" antes de mapear. Confirmado
    con datos reales: `exportaciones` pasó de 44 a 46 trimestres, ahora
    2015-Q1 a 2026-Q2 igual que `importaciones`.
  - `visibilidad_mediatica_y_relevancia_publica.py` (dimensión 4, **9
    variables** desde el 2026-09-22 — 6 de GDELT + 3 nuevas de Google
    Trends, ver más abajo —, **cantidad + índice**) a partir de
    `gdelt_proxy_b` (CSV con prefijo `monthly_` —
    cualquier archivo `historical_processed_*.csv` queda afuera a propósito
    porque duplicaría esos mismos meses, ver docstring del módulo): por
    cada trimestre, cantidad de artículos proxy y tono promedio ponderado
    por cantidad de artículos (trimestres sin ningún artículo no tienen
    fila en la variable de tono — no se rellenan con 0). 45 trimestres,
    2015-Q1 a 2026-Q1 (actualizado 2026-09-08 tras sumar la extracción de
    enero 2026 — ver la nota de `gdelt_extraction/` más arriba).
    **Separación PY/US/BOTH (2026-09-09, a pedido del usuario — antes solo
    se usaba la fila `source_country == "BOTH"`, perdiendo la distinción de
    si la cobertura viene de medios paraguayos o estadounidenses):** ahora
    se suben 3 variantes de cada métrica, una por valor de `source_country`
    en el CSV crudo — `gdelt_proxy_articles`/`gdelt_tone_promedio` (BOTH,
    nombres sin cambios para no romper la carpeta de Drive ya existente),
    `gdelt_proxy_articles_py`/`gdelt_tone_promedio_py`, y
    `gdelt_proxy_articles_us`/`gdelt_tone_promedio_us`. **BOTH no es una
    tercera categoría de artículos, es la suma de PY + US** — verificado
    contra un CSV real (mes 2026-01: BOTH=241 artículos = PY(238) + US(3)
    exacto): en `gdelt_queries.py`, cada artículo seleccionado por la regla
    proxy B se cuenta una vez bajo su propio `source_country` (PY o US,
    según el país verificado del dominio de origen) y otra vez bajo "BOTH"
    (`CROSS JOIN UNNEST([s.source_country, 'BOTH'])`). El tono de BOTH
    tampoco es el promedio de tono(PY) y tono(US) — es el promedio pooled
    sobre todos los artículos de ambos países juntos, así que si un mes
    tiene muchos más artículos de un país que del otro, el tono de BOTH
    queda mucho más cerca del tono de ese país que de un promedio 50/50.
    **`google_trends_paraguay` (agregada 2026-09-22, 3 variables nuevas —
    ver `src/ingestion/google_trends_paraguay.py` y
    `DICCIONARIO_VARIABLES.md` para el detalle completo de las decisiones):**
    `google_trends_paraguay_trade`/`_tariffs`/`_embassy` — índice mensual
    (0-100, relativo) de interés de búsqueda en Google, `geo=US`,
    promediado (no sumado, a diferencia de GDELT) dentro de cada
    trimestre; se descarta el mes marcado `isPartial` (en curso). Lista de
    3 términos **fija** — Google Trends normaliza los términos de una
    misma consulta relativos entre sí, así que agregar/sacar un término
    reescalaría retroactivamente los ya publicados. No verificado todavía
    si es redundante con GDELT (a diferencia de la comparación TIF/USTR,
    que sí se hizo antes de construir esa variable) — pendiente una vez
    esta fuente esté validada con más corridas.

- **`src/02_cleaning/` — etapa 02 en formato script (2026-09-08/09).** Una
  reescritura de `src/processing/compromiso_financiero_oficial.py` en el
  estilo de script lineal que prefiere el usuario: cajón de encabezado con
  responsable y fecha, secciones numeradas (`0. SETUP`, `1. IMPORTAR DATA
  CRUDA`, `2. LIMPIEZA`, `3. EXPORTAR CLEAN`), objetos intermedios con
  nombre (`*_limpiando`, `*_clean`) que quedan vivos en la consola de
  Positron, y validaciones impresas al final de cada bloque. Tiene un
  interruptor `SUBIR_A_DRIVE` (hoy en `False`) para poder correrlo entero
  sin escribir nada mientras se revisa. **Solo cubre la dimensión 1** — ver
  el aviso de duplicación en la sección 2.
- **`src/03_integration/03_integration.py` (2026-09-09).** Lee de Drive el
  último CSV de cada variable limpia y arma **un panel trimestral cuadrado**:
  480 filas = 10 variables × 48 trimestres (2015-Q1 a 2026-Q4), con `NA`
  donde la fuente todavía no publicó. Puntos de diseño que hay que respetar
  si se lo modifica:
  - La grilla se arma primero (producto cartesiano variables × trimestres) y
    los valores se pegan encima con un left join, para que **el tamaño del
    panel no dependa de hasta dónde llegó cada fuente**.
  - `ANIO_MINIMO`/`ANIO_MAXIMO` son constantes declaradas, no deducidas de
    los datos. Hay una validación que cuenta las filas de los CSV que caen
    fuera del rango (hoy 0) para que el panel no las tire en silencio.
  - Columna `en_fuente` (bool): distingue "la fuente no publica ese
    trimestre" de "había fila con valor nulo". Hoy los 10 CSV vienen sin
    nulos, así que los 19 `NA` son todos de cola.
  - Columnas `grano_temporal` y `agregacion` se **declaran acá**, no vienen
    del CSV (el contrato de `02_limpias` son 5 columnas fijas). `agregacion`
    distingue `suma` / `no sumar` / `promedio ponderado` — el caso que la
    hace necesaria es el tono de GDELT, que es "trimestre real" y aun así no
    se puede sumar.
  - Expone `limpias_largo` (480 × 11) y `limpias_ancho` (48 × 10), más
    `catalogo_variables` y `trimestres_panel`.
  - **Publica los dos formatos en `03_integracion` (2026-09-10):**
    `panel_trimestral_largo.csv` (480 × 11, el que lee la etapa 04 — es el
    único que lleva `dimension`/`grano_temporal`/`agregacion`/`unidad`/
    `en_fuente`/`archivo_origen`) y `panel_trimestral_ancho.csv` (48 × 11,
    vista cómoda). Nombre fijo, se reemplaza el contenido en cada corrida
    (ver el aviso de la sección 2), con interruptor `SUBIR_A_DRIVE` (hoy en
    `True`). El largo se exporta en el **orden declarado** de las variables,
    no en el alfabético de `limpias_largo`: la etapa 04 reconstruye su
    catálogo con un `drop_duplicates` sobre ese orden, y hay una validación
    que lo verifica.
  - Las 10 variables del panel son 3 de la dimensión 1 (fa_gov ob/des,
    usaspending), 3 de la 3 (exportaciones, importaciones, remesas) y 4 de
    la 4 (gdelt articles/tone × py/us). **No se traen las variantes BOTH de
    GDELT a propósito**: BOTH = PY + US, incluirlas contaría los mismos
    artículos dos veces.
- **`src/04_analysis_index/04_analysis_index.qmd` (2026-09-09).** Documento
  Quarto (chunks `{python}`) que hace el diagnóstico de las series y
  construye el índice. Reescrito por completo el 2026-09-09 a pedido del
  usuario, que rechazó el primer borrador por dar por sabido demasiado; el
  estándar acordado quedó fijado en "calidad de paper, compartible con el
  cliente" (ver sección 4). Sigue los 10 pasos del *Handbook on Constructing
  Composite Indicators* de la OCDE/JRC, con una tabla que mapea cada paso a
  su sección.

  **Entrada y salida (2026-09-10).** El insumo es
  `03_integracion/panel_trimestral_largo.csv`, leído de Drive — **ya no
  ejecuta `03_integration.py` con `runpy`**. El motivo está escrito en el
  propio documento: ejecutando la etapa anterior, dos renders podían mirar
  paneles distintos y las cifras no eran reproducibles contra ningún archivo
  concreto. Consecuencia operativa: **hay que correr `03_integration.py`
  antes de renderizar**, si no el documento reporta el panel viejo sin
  avisar. La salida va a `04_final` y son tres cosas con el mismo contenido:
  `indice_us_py_ancho.csv` (45 × 29), `indice_us_py_largo.csv` (1.125 × 10) y
  el Google Sheet `us_py_engagement_index` con las pestañas `indice_ancho` y
  `indice_largo`. Las tres llevan los tres bloques de columnas: las 10
  originales (unidad nativa, sin deflactar), las 10 normalizadas (sufijo
  `_z`, que ya trae adentro deflactar + logaritmo + puntaje z contra la base)
  y los 5 índices (`indice_dim_1`/`3`/`4`, `indice_agregado`,
  `indice_agregado_suavizado`), más `trimestre`/`anio`/`trimestre_num`/
  `provisional`. Interruptor `PUBLICAR_RESULTADO` (hoy en `True`) para
  renderizar sin escribir nada. **El Sheet no se borra ni se recrea nunca**
  (lo consume un dashboard): se resuelve por nombre, se crea solo la primera
  vez, y de ahí en más se reemplaza únicamente el contenido de las dos
  pestañas — `write_dataframe()` en `src/sheets.py` limpia y reescribe, y
  solo **agranda** la grilla si hace falta (la grilla por defecto son 1.000 ×
  26 y el formato largo tiene 1.126 filas, así que sin ese `resize` la
  escritura fallaba con "exceeds grid limits"). Queda una pestaña `Sheet1`
  vacía de cuando se creó el archivo: se puede borrar a mano una vez, nada la
  vuelve a crear.

  **Las 11 decisiones que definen el índice** (cada una documentada en el
  .qmd con su alternativa descartada):

  | # | Tema | Decisión |
  |---|---|---|
  | 1 | Alcance | Se publica como índice de **3 de las 4 dimensiones**; la 2 no entra |
  | 2 | Faltantes | Recortar la ventana, no imputar |
  | 3 | Grano anual | fa_gov entra, pero el índice nunca se suma en el tiempo |
  | 4 | Año en curso | Escala estimada solo con trimestres firmes |
  | 5 | Precios | **Deflactar** por IPC de EE.UU. (BLS `CUUR0000SA0`) |
  | 6 | Distribuciones | log10 en dinero y conteos; nada en tono |
  | 7 | Estacionalidad | No desestacionalizar; leer con media móvil de 4T |
  | 8 | Ponderación | Jerárquica: 1/3 por dimensión, 2 bloques por dimensión, 1/6 cada bloque |
  | 9 | Comercio | Exportaciones+importaciones en un bloque; **la balanza NO entra** |
  | 10 | Tono | Entra con 1/6 de peso + reporte paralelo sin tono obligatorio |
  | 11 | Escala | **Base fija 2015-2019 = 100, desvío 10**; no se recalcula |

  **Hallazgos que hay que conocer antes de tocar nada:**
  - **El año fiscal en curso llega incompleto y contamina el último dato.**
    fa_gov 2026 registra 1.48 M (obligaciones) y 3.15 M (desembolsos) contra
    un rango histórico de 11-39 M: es el año fiscal en curso que
    ForeignAssistance.gov publica parcial y que ingestion congela. Sin
    tratarlo, el índice se desploma a 51 en 2026-Q1. Hay detección
    automática (un año por debajo de la mitad del mínimo histórico previo se
    marca provisional).
  - **Deflactar cambia el índice de verdad**: entre 22% y 24% del
    crecimiento aparente de las 6 series monetarias era inflación. La
    versión sin deflactar correlaciona 0.80 con la propuesta.
  - **La base fija resuelve las revisiones.** Con escala recalculada, un
    índice publicado a fines de 2019 se habría revisado 4.6 puntos en
    promedio (hasta 8.1) al entrar los años siguientes, porque 2020
    recalibraba toda la escala. Con base fija la revisión es **0.000**.
  - **Alfa de Cronbach = 0.34** (dim 1: 0.10, dim 3: −0.03, dim 4: 0.71). No
    invalida el índice porque es **formativo** y no reflectivo (el manual de
    la OCDE es explícito en que el alfa solo aplica a modelos reflectivos),
    pero sí implica que **el agregado comunica menos que sus partes**.
  - **La balanza comercial es negativa en 44 de 45 trimestres** — por eso el
    comercio entra como intensidad (X+M) y no como saldo.
  - **Ninguna de las 10 variables es prescindible**: sacar la menos
    influyente mueve el índice 2.7 puntos (escala de desvío 10).
  - **La dimensión 4 gobierna el agregado** (correlación 0.74) pese a pesar
    un tercio, porque es la que más se mueve.

  **Resultado actual**: 2015-2019 ≈ 100 (base), 2020 = 67.9, 2021-22 = 82-85,
  2023-24 = 97-103, 2025 = 92.3. El hallazgo del período es que 2025 esconde
  una divergencia de más de 4 desvíos: **dimensión 3 en 118.9 (máximo de la
  serie) contra dimensión 1 en 71.5 (mínimo de la serie)**.

  **Dependencia externa nueva**: el deflactor se descarga **en tiempo de
  render** desde la API pública de BLS (sin key). El IPC de **octubre 2025 no
  existe** — BLS lo marca "Data unavailable due to the 2025 lapse in
  appropriations" —, así que el deflactor de 2025-Q4 se calcula con dos
  meses. Trasladar esa descarga a `src/ingestion/` es un pendiente.

- **`src/04_analysis_index/04_construccion_indice.qmd` — reconstrucción del
  índice desde cero (2026-09-10 en adelante, en curso).** El usuario invalidó
  `04_analysis_index.qmd` como decisión: sus elecciones metodológicas se
  tomaron sin evaluar sistemáticamente las alternativas. El documento nuevo
  rehace el índice siguiendo los 10 pasos del manual OCDE/JRC en 13 etapas, y
  para cada pregunta explica todas las técnicas disponibles, las contrasta con
  evidencia real y recién ahí decide, dejando registrada la alternativa
  descartada.

  Parte del panel de `03_integracion` (12 series, 8 indicadores) y no de
  `02_limpias`. Ventana 2015-Q1 a 2026-Q1, 45 trimestres sin faltantes.

  **Estado: etapas 0 a 10 completas (44 decisiones registradas), etapas 11 a 13
  pendientes.** El índice ya existe como serie: 45 trimestres, entre 89,4 y 105,9, y
  resistió el análisis de sensibilidad sobre 324 combinaciones metodológicas. El documento viejo sigue en el repo pero no debe usarse como
  referencia.

  > **Todo el contexto para retomar está en
  > [`src/04_analysis_index/ESTADO_CONSTRUCCION_INDICE.md`](src/04_analysis_index/ESTADO_CONSTRUCCION_INDICE.md)**:
  > convenciones obligatorias de estructura y redacción, las 31 decisiones, lo
  > que quedó abierto, los hallazgos que no conviene perder y cómo renderizar.
  > Leerlo antes de tocar el `.qmd`.

## 7. Pendientes

1. **Definir el resto de las variables de cada dimensión** — las cuatro
   dimensiones ya tienen nombre (sección 1) y las cuatro tienen ya al menos
   una fuente real; `3_Compromiso_economico_privado` y
   `1_Compromiso_financiero_oficial` tienen variables/fuentes definidas.
   `4_Visibilidad_mediatica_y_relevancia_publica` y
   `2_Actividad_gubernamental_y_diplomatica` tienen cada una una primera
   fuente (`gdelt_proxy_b.py` y `congreso_menciones_paraguay.py`, ver
   sección 6) pero podrían sumar más variables.
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
4. ~~**Desembolsos de BID/Banco Mundial ponderados por cuota de capital de
   EE.UU.**~~ **Resuelto 2026-09-22** — ver la nota al final de esta
   sección para el detalle completo (qué se implementó, qué queda fuera del
   cálculo y por qué, y dónde vive el histórico editable de cada banco).

5. **Decidir la duplicación de la etapa 02** (ver el aviso de la sección 2).
   Hay dos implementaciones de la dimensión 1 que suben a las mismas
   carpetas de Drive y compiten por el idempotente-por-día. Si el script
   lineal reemplaza al módulo, hay que sacar
   `src/processing/compromiso_financiero_oficial.py` de la carpeta que
   `run_processing.py` autodescubre, y decidir si las dimensiones 2, 3 y 4
   se reescriben en el mismo estilo.
6. **Incorporar la dimensión 2 al índice** — es la limitación más importante
   del índice actual, que hoy cubre 3 de 4 dimensiones. Sus tres variables
   existen y están limpias, pero son conteos de eventos demasiado raros
   (los hitos de USTR aparecen en 5 trimestres de 45, los TIAS en 3) y al
   normalizarse producirían saltos enormes. La vía más prometedora es
   reemplazar conteos de eventos raros por alguna medida de intensidad
   continua.
7. ~~**Mover la descarga del IPC a `src/ingestion/`.**~~ **Resuelto
   2026-09-22** — `bls_ipc_eeuu.py` (ver sección 6) ya sube el JSON crudo de
   la serie a Drive. **Falta un paso más, no incluido en esto**: la etapa 04
   (`04_construccion_indice.qmd`) todavía pide la serie en vivo a la API del
   BLS en tiempo de render — no se tocó el `.qmd` porque esa sección está en
   pausa (ajuste metodológico en curso, a pedido del usuario). Cuando se
   retome, hay que cambiar `descargar_ipc()` para que lea de Drive en vez de
   llamar a la API. Mismo caso para la población: se agregó
   `ine_poblacion_paraguay.py` (fuente oficial del INE, alternativa/
   complemento al `SP.POP.TOTL` del Banco Mundial que ya usa el `.qmd`) —
   tampoco está conectada todavía, mismo motivo.
8. **Contrastar el índice con indicadores externos** — es el paso 9 del
   manual de la OCDE y el único de los diez que hoy no se cumple.
9. **Definir la política de re-basificación**: cada cuántos años se
   actualiza el período base 2015-2019 del índice y cómo se publica la
   transición (la práctica estándar es publicar ambas series durante un
   tiempo).
10. ~~**Higiene del repo**~~ **Resuelto 2026-09-22**: `.env.example`
    restaurado (las 4 variables reales confirmadas con
    `grep -rn "os\.environ\[" src/ *.py` — sin sorpresas respecto a lo que
    ya decía la sección 5), y `.venv/` agregado a `.gitignore` en la raíz
    (antes solo estaban `gdelt_extraction/.venv/` y `mre_scraping/.venv/`).

*(Resuelto 2026-08-26: `bea_inversion_directa.py` escrito y probado en local
con la `BEA_API_KEY` que generó el usuario — falta confirmar que el secret
`BEA_API_KEY` ya esté cargado en GitHub para que corra igual en Actions.)*

*(Resuelto 2026-09-10: era el pendiente "Materializar `03_final` en Drive".
Las etapas 03 y 04 ya publican — el panel en `03_integracion` y el resultado
del índice en `04_final`, este último como CSV largo + ancho y como Google
Sheet de dos pestañas para el dashboard. Se persisten las 10 columnas
originales, las 10 normalizadas y los 5 índices, todo probado de punta a
punta con datos reales. Ojo: la carpeta se llama `04_final`, no `03_final`
como suponía el pendiente. Ver secciones 2, 3 y 6.)*

*(Resuelto 2026-09-22: era el pendiente #4, "Desembolsos de BID/Banco Mundial
ponderados por cuota de capital de EE.UU.". El método (monto atribuible = %
de cuota de capital × monto al país) es el mismo que usa la OCDE/DAC para su
estadística de "imputed multilateral ODA" — no es un atajo del proyecto, es
una convención estadística reconocida.*

*BID: `_extraer_bid()` en `compromiso_financiero_oficial.py` devuelve
`bid_proyectos_aprobados` (sin cambios) y la nueva **`bid_proyectos_atribuible_eeuu`**
— 30,006% aplicado SOLO a `opertyp_nm` "Loan Operation" y "Container"
(préstamos y líneas de crédito de Capital Ordinario, ~98% del monto 2015-2026).
Motivo de la restricción: 69% de los 940 registros de Paraguay son "Technical
Cooperation", financiada mayormente por fondos fiduciarios específicos
(confirmado un caso real financiado por el Fund for Special Operations) que NO
salen de Capital Ordinario — aplicarles 30% habría sido inventar un número; el
dataset no identifica el fondo fiduciario exacto de cada TC como para
tratarlas caso por caso. Quedan deliberadamente fuera: Cooperación Técnica,
Multilateral Investment Fund/IDB Lab, IDB Invest (entidad legal separada,
cuota propia sin investigar), Garantías y Equity — por eso
`bid_proyectos_atribuible_eeuu` es un **piso** (mínimo atribuible), no el
total real. Impacto de esa exclusión (investigado 2026-09-22): en dólares
es marginal (1,9% del total 2015-2026, correlación 0,9999 con la serie sin
excluir), pero sí reduce la cobertura temporal (26 de 47 trimestres con
actividad, contra 47 de 47 sin excluir) — ver `DICCIONARIO_VARIABLES.md`
para el detalle completo. El % se lee en vivo del archivo más reciente de
`cuota_capital_bid` (no hardcodeado en processing). Verificado con datos
reales: 26 trimestres (2015-Q2 a 2026-Q1), 0 diffs contra un recálculo
independiente, US$1.761.829.295 acumulados.*

*Banco Mundial: los proyectos de Paraguay son 100% IBRD, cero IDA
(`idacommamt` da 0 en las 133 filas) — no hay que mezclar dos cuotas
distintas. A diferencia del BID, la cuota de EE.UU. en IBRD SÍ cambia año a
año de verdad (confirmado con 7 años reales: 16,63% en FY2016, 15,98% en
FY2018, 15,68% en FY2019, 15,79% en FY2022, 15,75% en FY2023, 15,49% en
FY2024, 15,79% en FY2025 — sin patrón simple). Se creó
`cuota_capital_bancomundial.py`: histórico fijo editado a mano (no scrapeado
en vivo, a pedido del usuario — "no complicar tanto el scrapeo"; cada
"Information Statement" anual del IBRD vive en una URL con hash impredecible
en `thedocs.worldbank.org`, sin página índice, así que agregar un año nuevo
requiere buscarlo a mano — el propio docstring del módulo trae la receta paso
a paso). Años sin dato todavía: FY2015, FY2017, FY2020, FY2021, FY2026 —
`_extraer_bancomundial()` arrastra el último valor confirmado hacia adelante
(o hacia atrás para 2015) para esos huecos. Se aplica el % a TODO
`bancomundial_proyectos_aprobados` sin restricción de tipo (a diferencia del
BID, acá no hay categorías con otra estructura de capital que excluir).
Nueva variable: **`bancomundial_proyectos_atribuible_eeuu`**. Verificado con
datos reales: 12 trimestres (2015-Q1 a 2027-Q1), 0 diffs contra un
recálculo independiente, US$278.313.250 acumulados.)*
