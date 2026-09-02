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
  BCP va en `2.Datos_recolectados/01_crudas/3.Compromiso_economico_privado/bcp_comercio_exterior/`.
  `resolve_ingestion_folder(dimension, fuente)` arma esa ruta y crea las
  subcarpetas que falten (atajo sobre `resolve_folder()`, que acepta
  cualquier lista de segmentos si hiciera falta apuntar a otro lado).
- La cuenta de servicio tiene rol **Writer** en esa Unidad compartida (puede
  crear/editar archivos, no puede borrarlos — no hace falta para ingestion).
- Como la subida es por API (no por disco montado), **esto ya corre igual en
  local o en GitHub Actions** — no depende de tener la Unidad compartida
  montada en ninguna letra de unidad.
- **Salida a Sheets**: `pipeline_log` (auditoría de que corrió) y
  `catalogo_fuentes` (trazabilidad — de dónde sale cada fuente, ver sección
  4). Ninguna fuente escribe sus *datos* a Sheets todavía, solo estos dos
  metadatos de auditoría.
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

## 5. Entorno

- Python 3.11 (versión fijada en el workflow de GitHub Actions).
- Google Cloud: proyecto `us-py-engagement-idx`, cuenta de servicio en
  `config/credential_cloud.json` (**no está en git**, cubierta por
  `.gitignore`). Mismo archivo de credenciales para Sheets y para Drive —
  cada módulo pide el scope de OAuth que necesita al construir sus propias
  `Credentials`.
- Local: variables de entorno en `.env` (no versionado, `run_pipeline.py` lo
  carga solo con `python-dotenv`) — `GOOGLE_APPLICATION_CREDENTIALS`,
  `SHEET_ID`, `BEA_API_KEY`, `CONGRESS_API_KEY`.
- GitHub Actions: secrets `GOOGLE_SHEETS_CREDENTIALS` (JSON completo de la
  cuenta de servicio), `SHEET_ID`, `BEA_API_KEY` y `CONGRESS_API_KEY`, en
  Settings > Secrets and variables > Actions.
- El Sheet de destino debe estar compartido como **Editor** con el
  `client_email` de la cuenta de servicio. Si el Sheet vive dentro de una
  Unidad compartida de Google Workspace, puede bloquear compartir con cuentas
  externas al dominio (una cuenta de servicio cuenta como externa) — ver el
  punto pendiente en la sección 7.

### Dependencias (`requirements.txt`)

```
google-api-python-client   # src/drive.py (subida de archivos crudos)
google-auth                # autenticación con la cuenta de servicio
gspread                     # src/sheets.py (pestañas pipeline_log y catalogo_fuentes)
python-dotenv                # carga .env en local (run_pipeline.py)

beautifulsoup4   # parseo de HTML en ingestion
curl_cffi         # requests que bypasea Cloudflare/bot-blocking (bcp.gov.py, state.gov)
ddgs               # búsqueda en DuckDuckGo (state_gov_tias_paraguay.py — state.gov no tiene índice navegable de TIAS)
openpyxl           # escribir .xlsx con pandas (congreso_menciones_paraguay.py, state_gov_tias_paraguay.py)
pandas              # filtrado local / armar excel (exim_autorizaciones.py, congreso_menciones_paraguay.py, state_gov_tias_paraguay.py)
requests             # fuentes que exponen una API normal (BEA, ForeignAssistance.gov, USAspending, BID, Banco Mundial, DFC, Congreso EE.UU.)
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
- Tres fuentes reales de la dimensión `2.Actividad_gubernamental_y_diplomática`
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
    APIs). **Columna de verificación (2026-09-02, a pedido del usuario)**:
    cada fila incluye `extracto_mencion_paraguay`, un fragmento real del
    texto del proyecto centrado en la primera mención de "Paraguay" — se
    descarga el contenido de la misma versión que GovInfo ya encontró que
    lo menciona (`/packages/{packageId}/htm`), no un snippet inventado, así
    se puede confirmar de un vistazo que el hit es real y en qué contexto
    aparece, sin abrir el proyecto entero.
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
  - `state_gov_tias_paraguay.py` — publicaciones TIAS (Treaties and Other
    International Acts Series) entre Paraguay y EE.UU., desde el Office of
    Treaty Affairs de state.gov. state.gov no tiene un índice navegable de
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
- Primera fuente real de la dimensión `4.Visibilidad_mediática_y_relevancia_publica`
  (2026-09-01):
  - `gdelt_proxy_b.py` — sube a Drive los CSV mensuales ya extraídos por
    `gdelt_extraction/` (ver más abajo), cobertura mediática bilateral PY-US
    según la regla "proxy B" sobre GDELT 2.1 GKG (coocurrencia geográfica
    PY-US + señales temáticas D/I/R/E — diplomáticas, gobierno/instituciones,
    comercio/fronteras/inmigración, economía/impuestos; ver
    `gdelt_extraction/proxy_b_config.json`, versión aceptada 2026-08-27). Es
    una aproximación de coocurrencia con señales institucionales, **no**
    noticias validadas individualmente ni medición de calidad de relaciones
    diplomáticas — ver los límites documentados en la propia config y en
    `gdelt_extraction/README.md`.
  - `gdelt_extraction/` — el extractor en sí (`historical_campaign.py` y
    soporte), corrido a mano localmente contra el proyecto GCP
    `us-py-engagement-idx` (sandbox de BigQuery sin facturación, techo
    preventivo mensual 850 GiB). No es un módulo de `src/ingestion/` — ver
    la excepción documentada en la sección 4. Cobertura completa feb-2015 a
    dic-2025 (falta ene-2026 en adelante — requiere generar un estimado
    nuevo con `estimate_history.py` antes de seguir); el detalle exacto de
    qué meses están cubiertos vive en
    `gdelt_extraction/output/historical_campaign/CONTINUIDAD.md` (se
    reescribe en cada corrida, no confiar en esta nota para el estado
    exacto). **Para correrlo en otra computadora**, ver
    `gdelt_extraction/README.md` — necesita Google Cloud SDK
    instalado y autenticado aparte (no viene con el repo ni con Python), y
    en Windows puede requerir habilitar rutas largas si el checkout queda en
    una ruta profunda (ver esa misma guía).
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

## 7. Pendientes

1. **Definir el resto de las variables de cada dimensión** — las cuatro
   dimensiones ya tienen nombre (sección 1) y las cuatro tienen ya al menos
   una fuente real; `3.Compromiso_economico_privado` y
   `1.Compromiso_financiero_oficial` tienen variables/fuentes definidas.
   `4.Visibilidad_mediática_y_relevancia_publica` y
   `2.Actividad_gubernamental_y_diplomática` tienen cada una una primera
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
4. Diseñar las etapas `02_limpias` y `03_final` que lean los datos crudos de
   `01_crudas` y armen lo que finalmente va al Sheet (limpieza, homologación
   entre fuentes, qué campos importan) — todavía no existen, ni en Drive ni
   en el repo.

*(Resuelto 2026-08-26: `bea_inversion_directa.py` escrito y probado en local
con la `BEA_API_KEY` que generó el usuario — falta confirmar que el secret
`BEA_API_KEY` ya esté cargado en GitHub para que corra igual en Actions.)*
