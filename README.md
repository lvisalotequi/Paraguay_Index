# US-PY Engagement Index

Pipeline de extracción de datos para construir un índice de las relaciones
bilaterales entre **Paraguay y Estados Unidos**, a partir de cuatro
dimensiones. Cada variable se extrae con un script independiente y se
centraliza en Google Drive, listo para una etapa posterior de limpieza y
análisis.

> Para el detalle técnico completo (arquitectura, convenciones de código,
> estado exacto de cada fuente) ver [CLAUDE.md](CLAUDE.md) — este README es
> la vista rápida.

## Las cuatro dimensiones

| # | Dimensión | Estado |
| --- | --- | --- |
| 1 | Compromiso financiero oficial | ✅ 6 fuentes activas |
| 2 | Actividad gubernamental y diplomática | 🟡 5 fuentes activas |
| 3 | Compromiso económico privado | ✅ 4 fuentes activas |
| 4 | Visibilidad mediática y relevancia pública | 🟡 2 fuentes activas |

**21 fuentes de datos corriendo hoy**, automáticamente cada 3 meses vía
GitHub Actions:

- **Compromiso financiero oficial**: ForeignAssistance.gov, USAspending,
  DFC, EXIM, BID (proyectos), Banco Mundial (proyectos), cuota de capital
  de EE.UU. en el BID y en el Banco Mundial/IBRD (para ponderar los
  aportes multilaterales atribuibles a EE.UU.).
- **Actividad gubernamental y diplomática**: proyectos de ley y resoluciones
  del Congreso de EE.UU. que mencionan a Paraguay (GovInfo.gov + Congress.gov);
  reuniones del Consejo de Comercio e Inversión (TIFA/TIC) Paraguay-EE.UU.
  (USTR); tratados y acuerdos internacionales (TIAS) entre Paraguay y EE.UU.
  (State.gov, en revisión — candidata a ser reemplazada por el listado más
  completo de abajo); TODOS los tratados y acuerdos bilaterales que siguen
  vigentes según "Treaties in Force" (TIF, la publicación oficial anual del
  Departamento de Estado); noticias del Ministerio de Relaciones Exteriores
  de Paraguay clasificadas por bilateralidad con EE.UU. (`mre_scraping/`,
  corrida a mano localmente igual que GDELT).
- **Compromiso económico privado**: Comercio Exterior (BCP), Inversión
  Directa (BCP + BEA), Remesas Familiares (BCP).
- **Visibilidad mediática**: cobertura bilateral vía GDELT (regla "proxy B"),
  corrida a mano localmente y centralizada en Drive; interés de búsqueda en
  Google (Google Trends, `geo=US`, 3 términos fijos: trade/tariffs/embassy).
- **Insumos transversales para el índice** (no pertenecen a ninguna de las 4
  dimensiones): IPC de EE.UU. (BLS, para deflactar) y población de Paraguay
  (INE, para expresar variables por habitante).

## Cómo funciona

```
src/ingestion/{fuente}.py    →  Google Drive: 01_crudas/{dimensión}/{fuente}/
                    │                              │
                    │                              ▼
                    │          src/processing/{dimensión}.py  →  02_limpias/{dimensión}_limpias/{variable}/
                    ▼
     run_pipeline.py → pestaña pipeline_log        run_processing.py → pestaña processing_log
```

Cada script de `src/ingestion/` extrae una variable de una fuente pública
(scraping, API, o CSV/Excel oficial), filtra a lo relevante para
Paraguay/EE.UU. cuando la fuente lo permite, y sube el archivo crudo a la
carpeta de Drive de su dimensión, sin transformarlo. Es idempotente: si el
archivo ya está subido, la corrida lo saltea. `run_pipeline.py` descubre y
corre todos los módulos automáticamente — agregar una fuente nueva no
requiere tocar nada más.

`src/processing/` es la etapa siguiente: lee los archivos crudos que
ingestion ya subió, aisla la cifra de EE.UU. (o de Paraguay/EE.UU. por
separado, en el caso de GDELT) de cada fuente, normaliza a trimestres, y
sube **un CSV por variable** (no un CSV combinado por dimensión) a
`02_limpias/{dimensión}_limpias/{variable}/` — ya cubre las 4 dimensiones,
29 variables en total (2 en integración, ver tabla abajo). Todos los CSV comparten el mismo
esquema (`trimestre, anio, trimestre_num, valor, unidad`), y las variables
de un mismo tipo (monetario/cantidad/índice) quedan en una unidad
consistente entre sí (ej. todo lo monetario en USD sin escalar, nunca
mezclando miles y millones). `run_processing.py` sigue el mismo patrón de
auto-descubrimiento que `run_pipeline.py` — se corre a mano, no está en el
schedule automático.

Los datos extraídos **no viven en este repo** (viven en Google Drive, fuera
de git) — acá solo está el código que los extrae y los procesa.

## Correrlo en local

```bash
git clone <url-del-repo>   # a una ruta corta, ver nota de Windows más abajo
cd Paraguay_Index
pip install -r requirements.txt
cp .env.example .env       # completar con los valores reales (pedirle las credenciales al dueño del proyecto)
python run_pipeline.py
python run_processing.py
```

Necesitás una cuenta de servicio de Google Cloud con acceso de Editor al
Sheet de destino y rol Writer en la Unidad compartida de Drive del
proyecto — el archivo JSON de esa cuenta es un secreto, no está en el
repo, hay que pedírselo al dueño del proyecto. Ver sección 5 de
[CLAUDE.md](CLAUDE.md) para el detalle completo.

**Windows**: cloná el repo a una ruta corta (ej. `C:\dev\Paraguay_Index`)
en vez de trabajar directo desde la Unidad compartida montada — esa ruta
es muy larga (nombres largos + emojis) y sumada a las rutas que crea un
entorno virtual de Python puede superar el límite de 260 caracteres que
Windows respeta por defecto, rompiendo la instalación de dependencias. El
código no necesita vivir dentro de la Unidad compartida: los datos se
leen/escriben por la API de Drive, no por disco local. Ver sección 5 de
[CLAUDE.md](CLAUDE.md) para la alternativa (habilitar rutas largas en
Windows).

## Automatización

GitHub Actions corre el pipeline cada 3 meses (`.github/workflows/run_pipeline.yml`),
además de disparo manual desde la pestaña Actions. Cada corrida queda
registrada en la pestaña `pipeline_log` del Google Sheet, con timestamp y
errores si los hubo.

## Trazabilidad

Cada corrida reescribe la pestaña `catalogo_fuentes` del Sheet: una fila por
fuente, con su dimensión, una descripción de qué extrae, la página pública
de origen, y el estado/timestamp de la última corrida — para saber de dónde
sale cada dato sin tener que leer el código.

## Variables en `02_limpias`

Las 29 variables ya consolidadas por `src/processing/`, con su estado de
revisión. "En revisión" significa que la metodología de cálculo (fuente,
fórmula, unidad) todavía no está validada como definitiva; "Validado"
significa que ya se revisó y se puede usar tal cual.

| Dimensión | Variable | Estado |
| --- | --- | --- |
| 1. Compromiso financiero oficial | **fa_gov_obligaciones** | **Validado** |
| 1. Compromiso financiero oficial | **fa_gov_desembolsos** | **Validado** |
| 1. Compromiso financiero oficial | **usaspending_obligaciones** | **Validado** |
| 1. Compromiso financiero oficial | **dfc_comprometido** | **Validado** |
| 1. Compromiso financiero oficial | **dfc_proyectos_vigentes** (stock acumulado) | **Validado** |
| 1. Compromiso financiero oficial | **exim_autorizado** | **Validado** |
| 1. Compromiso financiero oficial | **exim_desembolsado** | **Validado** |
| 1. Compromiso financiero oficial | **bid_proyectos_aprobados** | **Validado** |
| 1. Compromiso financiero oficial | **bid_proyectos_atribuible_eeuu** (ponderado por cuota de capital) | **Validado** |
| 1. Compromiso financiero oficial | **bancomundial_proyectos_aprobados** | **Validado** |
| 1. Compromiso financiero oficial | **bancomundial_proyectos_atribuible_eeuu** (ponderado por cuota anual) | **Validado** |
| 2. Actividad gubernamental y diplomática | congreso_proyectos_relevantes_paraguay | En revisión |
| 2. Actividad gubernamental y diplomática | congreso_menciones_totales_paraguay | En revisión |
| 2. Actividad gubernamental y diplomática | **ustr_hitos_consejo_comercio_inversion** | **Validado** |
| 2. Actividad gubernamental y diplomática | state_gov_tias_vigentes (stock acumulado) | En revisión (candidata a eliminarse — ver state_gov_tif_vigentes) |
| 2. Actividad gubernamental y diplomática | **state_gov_tif_vigentes** (stock acumulado, todo tipo de acuerdo vigente) | **Validado** |
| 2. Actividad gubernamental y diplomática | **mre_noticias_bilaterales** | **Validado** (2026-09-22) |
| 2. Actividad gubernamental y diplomática | **mre_menciones_totales_eeuu** | **Validado** (2026-09-22) |
| 3. Compromiso económico privado | **exportaciones** | **Validado** |
| 3. Compromiso económico privado | **importaciones** | **Validado** |
| 3. Compromiso económico privado | **inversion_directa_bcp** | **Validado** (datos completos hasta 2024; 2025 pendiente de que el BCP publique el desglose por país, esperado octubre 2026 — ver `src/processing/compromiso_economico_privado.py`) |
| 3. Compromiso económico privado | **remesas** (Remesas internacionales) | **Validado** |
| 3. Compromiso económico privado | **bea_inversion_directa** | **Validado** |
| 4. Visibilidad mediática y relevancia pública | **gdelt_proxy_articles** (BOTH = PY+US) | **Validado** |
| 4. Visibilidad mediática y relevancia pública | **gdelt_tone_promedio** (BOTH = PY+US) | **Validado** |
| 4. Visibilidad mediática y relevancia pública | **gdelt_proxy_articles_py** | **Validado** |
| 4. Visibilidad mediática y relevancia pública | **gdelt_tone_promedio_py** | **Validado** |
| 4. Visibilidad mediática y relevancia pública | **gdelt_proxy_articles_us** | **Validado** |
| 4. Visibilidad mediática y relevancia pública | **gdelt_tone_promedio_us** | **Validado** |
| 4. Visibilidad mediática y relevancia pública | **google_trends_paraguay_trade** | **Validado** (2026-09-22) |
| 4. Visibilidad mediática y relevancia pública | **google_trends_paraguay_tariffs** | **Validado** (2026-09-22) |
| 4. Visibilidad mediática y relevancia pública | **google_trends_paraguay_embassy** | **Validado** (2026-09-22) |

## Estructura del repo

```
Paraguay_Index/
│
├── .github/workflows/run_pipeline.yml         # Corre run_pipeline.py cada 3 meses (cron) + disparo manual
│
├── src/
│   ├── drive.py                               # Subida/lectura de archivos y carpetas en Google Drive
│   ├── sheets.py                               # Auditoría en Google Sheets (pipeline_log, processing_log, catalogo_fuentes)
│   │
│   ├── ingestion/                              # Un script por fuente: SOLO extrae y sube crudo a 01_crudas/{dimensión}/{fuente}/
│   │   ├── _bcp_common.py                      # Bypass de Cloudflare (curl_cffi), compartido por las 3 fuentes de bcp.gov.py
│   │   ├── bcp_comercio_exterior.py            # Boletín de Comercio Exterior del BCP                    (dimensión 3)
│   │   ├── bcp_inversion_directa.py            # Anexo Estadístico de Inversión Directa del BCP          (dimensión 3)
│   │   ├── bcp_remesas_familiares.py           # Excel de Remesas Familiares del BCP                      (dimensión 3)
│   │   ├── bea_inversion_directa.py            # API de BEA, dataset MNE                                  (dimensión 3)
│   │   ├── fa_gov_asistencia_oficial.py        # API de ForeignAssistance.gov                             (dimensión 1)
│   │   ├── usaspending_obligaciones.py         # API asíncrona de USAspending                             (dimensión 1)
│   │   ├── dfc_proyectos_activos.py            # Excel de proyectos activos de DFC                        (dimensión 1)
│   │   ├── exim_autorizaciones.py              # CSV de EXIM, filtrado a Paraguay antes de subir           (dimensión 1)
│   │   ├── bid_proyectos.py                    # API CKAN del BID, filtrada a Paraguay server-side         (dimensión 1)
│   │   ├── bancomundial_proyectos.py           # API del Banco Mundial, filtrada a Paraguay server-side    (dimensión 1)
│   │   ├── cuota_capital_bid.py                # Cuota de capital de EE.UU. en el BID (valor fijo)         (dimensión 1)
│   │   ├── cuota_capital_bancomundial.py       # Cuota de EE.UU. en IBRD, historico por año fiscal          (dimensión 1)
│   │   ├── congreso_menciones_paraguay.py      # GovInfo + Congress.gov: proyectos que mencionan Paraguay  (dimensión 2)
│   │   ├── ustr_consejo_comercio_inversion.py  # Scraping histórico + en vivo de ustr.gov                  (dimensión 2)
│   │   ├── state_gov_tias_paraguay.py          # Histórico + búsqueda en vivo (DuckDuckGo) de TIAS, en revisión (dimensión 2)
│   │   ├── state_gov_tif_vigentes.py           # Parsea el PDF anual "Treaties in Force" del DOS           (dimensión 2)
│   │   ├── mre_menciones_eeuu.py               # Sube lo ya producido por mre_scraping/                    (dimensión 2)
│   │   ├── gdelt_proxy_b.py                    # Sube los CSV ya extraídos por gdelt_extraction/           (dimensión 4)
│   │   └── google_trends_paraguay.py           # pytrends, geo=US, 3 términos fijos                       (dimensión 4)
│   │
│   └── processing/                             # Un script por dimensión: limpia y sube un CSV por variable a 02_limpias/
│       ├── _common.py                                     # Convención compartida de salida (subir_variable, reescalar)
│       ├── compromiso_financiero_oficial.py               # 12 variables                   (dimensión 1)
│       ├── actividad_gubernamental_y_diplomatica.py       # 7 variables                    (dimensión 2)
│       ├── compromiso_economico_privado.py                # 5 variables                    (dimensión 3)
│       └── visibilidad_mediatica_y_relevancia_publica.py  # 9 variables                    (dimensión 4)
│
├── gdelt_extraction/                    # Extractor de GDELT (dimensión 4) - corre aparte y a mano, no vía run_pipeline.py
│   ├── historical_campaign.py           # Extracción histórica completa contra BigQuery
│   ├── bilateral_media_extractor.py     # Lógica central de la regla "proxy B"
│   ├── extraction_workflow.py
│   ├── proxy_b.py
│   ├── gdelt_queries.py
│   ├── estimate_history.py              # Genera el estimado de los meses que todavía faltan
│   ├── usage_ledger.py                  # Control del techo mensual de cuota gratuita de BigQuery
│   ├── proxy_b_config.json              # Config aceptada de la regla "proxy B"
│   ├── historical_workflow_config.json
│   ├── workflow_config.json
│   ├── requirements.txt                 # Dependencias propias (Google Cloud SDK se instala aparte)
│   └── README.md                        # Cómo correrlo en otra computadora
│
├── mre_scraping/                        # Scraper de noticias del MRE (dimensión 2) - corre aparte y a mano
│   ├── scraper_mre.py                   # Recolección: archivo actual (curl_cffi) + Wayback Machine
│   ├── clasificar_bilateral.py          # Clasificación bilateral por reglas, sin IA
│   ├── reglas_bilaterales.json          # Señales, puntajes y umbrales de bilateralidad
│   ├── terminos_eeuu.json               # Variantes textuales de "Estados Unidos"
│   ├── requirements.txt
│   ├── test_scraper_mre.py / test_clasificar_bilateral.py
│   ├── CONTEXTO_ORIGINAL.md             # Diseño original tal como llegó (antes de integrarlo)
│   └── README.md                        # Cómo correrlo, y el bypass de Cloudflare agregado
│
├── run_pipeline.py                      # Orquestador: descubre (pkgutil) y corre cada módulo de src/ingestion/
├── run_processing.py                    # Orquestador: descubre (pkgutil) y corre cada módulo de src/processing/
│
├── requirements.txt                     # Dependencias del proyecto
├── CLAUDE.md                            # Contexto técnico completo del proyecto
├── config/
│   └── credential_cloud.json            # Credenciales de la cuenta de servicio de GCP (no se sube)
├── .env.example                         # Plantilla de variables de entorno (sí se sube, sin valores reales)
├── .env                                 # Variables de entorno reales (no se sube)
└── .gitignore
```

### `src/` — helpers compartidos

- **`drive.py`** — subida/lectura de archivos y carpetas en Google Drive.
  - `resolve_folder(*segmentos)` — arma/crea una ruta de carpetas a partir de `DRIVE_ROOT_ID`.
  - `resolve_ingestion_folder(dimension, fuente)` — carpeta de destino de un módulo de ingestion (usa el cache `FOLDER_IDS` si ya se conoce).
  - `resolve_variable_folder(dimension_limpia, variable)` — carpeta de destino de una variable de processing (usa el cache `VARIABLE_FOLDER_IDS`).
  - `existe_archivo(nombre, carpeta_id)` / `subir_archivo(contenido, nombre, carpeta_id, mime_type)` — chequeo de idempotencia y subida.
  - `listar_archivos(carpeta_id)` / `descargar_archivo(file_id)` — lectura (usada por `src/processing/`).
  - `_client()`, `_buscar_hijo()`, `_buscar_hijo_con_reintentos()` — helpers internos de autenticación y búsqueda por nombre.
- **`sheets.py`** — registro de auditoría en Google Sheets.
  - `write_dataframe(tab_name, df)` — sobrescribe/crea una pestaña con un DataFrame (usado para `catalogo_fuentes`).
  - `append_log_row(started, finished, modules_run, errors, tab_name)` — agrega una fila de auditoría (`pipeline_log` o `processing_log`).

### `src/ingestion/` — un script por fuente, solo extrae y sube crudo

- **`_bcp_common.py`** (helper, no es un módulo de ingestion) — bypass de Cloudflare (`curl_cffi`) y utilidades compartidas por las 3 fuentes de bcp.gov.py: `obtener_html()`, `descargar_bytes()`, `limpiar_nombre_archivo()`, `nombre_desde_url()`, `mime_de()`.
- **`bcp_comercio_exterior.py`** — Boletín de Comercio Exterior del BCP (`_obtener_archivo()` elige la versión más reciente por año+trimestre, `_es_boletin()` filtra el link correcto entre varios documentos de la página) → `run()`.
- **`bcp_inversion_directa.py`** — Anexo Estadístico de Inversión Directa del BCP (`_obtener_archivo()`) → `run()`.
- **`bcp_remesas_familiares.py`** — Excel de Remesas Familiares del BCP (`_obtener_archivo()`) → `run()`.
- **`bea_inversion_directa.py`** — API de BEA, dataset MNE (`_pedir_datos()`) → `run()`.
- **`fa_gov_asistencia_oficial.py`** — API de ForeignAssistance.gov, un JSON por año+medida (`_pedir_medida(anio, medida)`) → `run()`.
- **`usaspending_obligaciones.py`** — API asíncrona de USAspending, un ZIP por año (`_pedir_descarga(anio)`, `_esperar_archivo(file_name)`) → `run()`.
- **`dfc_proyectos_activos.py`** — Excel único de proyectos activos de DFC (`_obtener_archivo()`) → `run()`.
- **`exim_autorizaciones.py`** — CSV de EXIM, filtrado a Paraguay antes de subir (`_obtener_url_csv()`) → `run()`.
- **`bid_proyectos.py`** — API CKAN de datos abiertos del BID, filtrada a Paraguay (`_pedir_proyectos()`) → `run()`.
- **`bancomundial_proyectos.py`** — API de proyectos del Banco Mundial, filtrada a Paraguay (`_pedir_proyectos()`) → `run()`.
- **`cuota_capital_bid.py`** — cuota de capital/poder de voto de EE.UU. en el BID (30,006%), valor fijo verificado a mano (la página oficial usa un widget de Power BI, no scrapeable) → `run()`.
- **`cuota_capital_bancomundial.py`** — cuota de poder de voto de EE.UU. en el IBRD, histórico fijo por año fiscal (a diferencia del BID, esta cuota sí cambia año a año) — cada fila viene de abrir a mano el "Information Statement" anual del IBRD y buscar el % en el texto (docstring del módulo explica paso a paso cómo agregar un año nuevo) → `run()`.
- **`congreso_menciones_paraguay.py`** — combina GovInfo (búsqueda de texto completo) + Congress.gov (datos estructurados): `_buscar_proyectos_govinfo()`, `_proyectos_unicos(hits)`, `_enriquecer_proyecto(...)`, `_menciones_paraguay(package_id)` (cuenta todas las menciones, no solo la primera), `_fila_desde_proyecto(...)` → `run()`.
- **`ustr_consejo_comercio_inversion.py`** — histórico fijo + revisión en vivo de ustr.gov: `_historico_verificado()`, `_verificar_evento_historico(evento)`, `_revisar_sitio_vivo()`, `_buscar_en_mes(anio, mes)`, `_fecha_del_comunicado(url)`, `_titulo_relevante(titulo)` → `run()`.
- **`state_gov_tias_paraguay.py`** — histórico fijo + búsqueda en vivo (DuckDuckGo) de TIAS en state.gov, en revisión: `_historico_verificado()`, `_buscar_candidatos_vivo(urls_conocidas)`, `_parsear_pagina_tias(url)`, `_anio_desde_tias(tias)`, `_normalizar_fecha(texto)` → `run()`.
- **`state_gov_tif_vigentes.py`** — descarga y parsea el PDF anual "Treaties in Force" del Departamento de Estado (todos los acuerdos bilaterales vigentes, no solo TIAS): `_url_pdf_vigente()`, `_descargar_pdf(url)`, `_paginas_de_texto(contenido_pdf)`, `_aislar_seccion_pais(paginas)`, `_parsear_acuerdos(seccion_texto)` → `run()`.
- **`mre_menciones_eeuu.py`** — sube a Drive lo que `mre_scraping/` ya produjo localmente (`noticias_clasificadas.csv`, `manifiesto.json`) → `run()`.
- **`bls_ipc_eeuu.py`** — IPC de EE.UU. (BLS, `CUUR0000SA0`), JSON crudo por tramos de 10 años → `run()`. Insumo transversal (`insumos_indice`), no una variable de dimensión.
- **`ine_poblacion_paraguay.py`** — población total de Paraguay por año (INE) → `run()`. Insumo transversal (`insumos_indice`), no una variable de dimensión.
- **`gdelt_proxy_b.py`** — sube a Drive los CSV que ya extrajo `gdelt_extraction/` (`_archivos_a_subir(carpeta_local)`) → `run()`.
- **`google_trends_paraguay.py`** — `pytrends`, `geo=US`, 3 términos fijos (`trade`/`tariffs`/`embassy`), reintenta 3 veces ante fallos: `_pedir_interes_con_reintentos()` → `run()`.

### `src/processing/` — un script por dimensión, limpia y sube un CSV por variable

- **`_common.py`** (helper, no es un módulo de processing) — convención compartida de salida: `subir_variable(dimension_limpia, variable, valores, unidad)` arma y sube el CSV (`trimestre, anio, trimestre_num, valor, unidad`); `reescalar(valores, factor)` convierte unidades nativas (miles/millones) a USD.
- **`compromiso_financiero_oficial.py`** (dimensión 1) — `_extraer_fa_gov()`, `_extraer_usaspending()`, `_extraer_dfc()`, `_extraer_exim()`, `_extraer_bid()`, `_extraer_bancomundial()`, más los helpers de fecha→trimestre `_sumar_por_trimestre()`/`_repetir_en_trimestres()` → `run()` (12 variables).
- **`actividad_gubernamental_y_diplomatica.py`** (dimensión 2) — `_extraer_congreso()` (devuelve dos series: relevantes y menciones totales), `_extraer_ustr()`, `_extraer_tias()` (stock acumulado, en revisión), `_extraer_tif()` (stock acumulado con base histórica pre-2015), `_extraer_mre()` (devuelve dos series: noticias bilaterales y menciones totales), `_contar_por_trimestre(fechas)`, `_acumular_por_trimestre(fechas)`, `_acumular_con_base_historica(fechas)` → `run()` (7 variables).
- **`compromiso_economico_privado.py`** (dimensión 3) — `_extraer_comercio_exterior()`, `_extraer_inversion_directa_bcp()`, `_extraer_remesas()`, `_extraer_bea_posicion()`, más los helpers de parseo del formato BCP `_mapear_columnas_trimestre()`/`_extraer_fila_pais_trimestral()`/`_sin_acentos()` → `run()` (5 variables).
- **`visibilidad_mediatica_y_relevancia_publica.py`** (dimensión 4) — `_extraer_gdelt()` (devuelve BOTH/PY/US por separado), `_extraer_google_trends()` (promedio trimestral por término, descarta el mes `isPartial`) → `run()` (9 variables: 6 de GDELT (cantidad y tono ×3 países) + 3 de Google Trends).
