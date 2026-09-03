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
| 2 | Actividad gubernamental y diplomática | 🟡 3 fuentes activas |
| 3 | Compromiso económico privado | ✅ 4 fuentes activas |
| 4 | Visibilidad mediática y relevancia pública | 🟡 1 fuente activa |

**14 fuentes de datos corriendo hoy**, automáticamente cada 3 meses vía
GitHub Actions:

- **Compromiso financiero oficial**: ForeignAssistance.gov, USAspending,
  DFC, EXIM, BID (proyectos), Banco Mundial (proyectos).
- **Actividad gubernamental y diplomática**: proyectos de ley y resoluciones
  del Congreso de EE.UU. que mencionan a Paraguay (GovInfo.gov + Congress.gov);
  reuniones del Consejo de Comercio e Inversión (TIFA/TIC) Paraguay-EE.UU.
  (USTR); tratados y acuerdos internacionales (TIAS) entre Paraguay y EE.UU.
  (State.gov).
- **Compromiso económico privado**: Comercio Exterior (BCP), Inversión
  Directa (BCP + BEA), Remesas Familiares (BCP).
- **Visibilidad mediática**: cobertura bilateral vía GDELT (regla "proxy B"),
  corrida a mano localmente y centralizada en Drive.

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
ingestion ya subió, aisla la cifra de EE.UU. de cada fuente, normaliza a
trimestres, y sube **un CSV por variable** (no un CSV combinado por
dimensión) a `02_limpias/{dimensión}_limpias/{variable}/` — ya cubre las 4
dimensiones, 17 variables en total. Todos los CSV comparten el mismo
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
pip install -r requirements.txt
# crear un .env con GOOGLE_APPLICATION_CREDENTIALS, SHEET_ID, BEA_API_KEY y CONGRESS_API_KEY
python run_pipeline.py
python run_processing.py
```

Necesitás una cuenta de servicio de Google Cloud con acceso de Editor al
Sheet de destino y rol Writer en la Unidad compartida de Drive del
proyecto. Ver sección 5 de [CLAUDE.md](CLAUDE.md) para el detalle completo.

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

## Estructura del repo

```
run_pipeline.py       # orquestador: descubre y corre cada módulo de ingestion
run_processing.py     # orquestador: descubre y corre cada módulo de processing
src/
  drive.py             # helpers de subida/lectura en Google Drive
  sheets.py             # registro de auditoría en Google Sheets
  ingestion/            # un script por variable/fuente de datos (solo extrae, sube crudo)
  processing/           # un script por dimensión (limpia y sube un CSV trimestral por variable)
gdelt_extraction/      # extractor de cobertura mediática GDELT (corre aparte, a mano)
CLAUDE.md              # contexto técnico completo del proyecto
```
