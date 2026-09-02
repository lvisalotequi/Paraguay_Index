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
| 2 | Actividad gubernamental y diplomática | ⏳ sin definir todavía |
| 3 | Compromiso económico privado | ✅ 4 fuentes activas |
| 4 | Visibilidad mediática y relevancia pública | 🟡 1 fuente activa |

**11 fuentes de datos corriendo hoy**, automáticamente cada 12 horas vía
GitHub Actions:

- **Compromiso financiero oficial**: ForeignAssistance.gov, USAspending,
  DFC, EXIM, BID (proyectos), Banco Mundial (proyectos).
- **Compromiso económico privado**: Comercio Exterior (BCP), Inversión
  Directa (BCP + BEA), Remesas Familiares (BCP).
- **Visibilidad mediática**: cobertura bilateral vía GDELT (regla "proxy B"),
  corrida a mano localmente y centralizada en Drive.

## Cómo funciona

```
src/ingestion/{fuente}.py  →  Google Drive: 01_crudas/{dimensión}/{fuente}/
                    │
                    └──  run_pipeline.py  →  pestaña pipeline_log del Sheet
```

Cada script de `src/ingestion/` extrae una variable de una fuente pública
(scraping, API, o CSV/Excel oficial), filtra a lo relevante para
Paraguay/EE.UU. cuando la fuente lo permite, y sube el archivo crudo a la
carpeta de Drive de su dimensión. Es idempotente: si el archivo ya está
subido, la corrida lo saltea. `run_pipeline.py` descubre y corre todos los
módulos automáticamente — agregar una fuente nueva no requiere tocar nada
más.

Los datos extraídos **no viven en este repo** (viven en Google Drive, fuera
de git) — acá solo está el código que los extrae.

## Correrlo en local

```bash
pip install -r requirements.txt
# crear un .env con GOOGLE_APPLICATION_CREDENTIALS, SHEET_ID y BEA_API_KEY
python run_pipeline.py
```

Necesitás una cuenta de servicio de Google Cloud con acceso de Editor al
Sheet de destino y rol Writer en la Unidad compartida de Drive del
proyecto. Ver sección 5 de [CLAUDE.md](CLAUDE.md) para el detalle completo.

## Automatización

GitHub Actions corre el pipeline cada 12 horas (`.github/workflows/run_pipeline.yml`),
además de disparo manual desde la pestaña Actions. Cada corrida queda
registrada en la pestaña `pipeline_log` del Google Sheet, con timestamp y
errores si los hubo.

## Estructura del repo

```
run_pipeline.py       # orquestador: descubre y corre cada módulo de ingestion
src/
  drive.py             # helpers de subida a Google Drive
  sheets.py             # registro de auditoría en Google Sheets
  ingestion/            # un script por variable/fuente de datos
gdelt_extraction/      # extractor de cobertura mediática GDELT (corre aparte, a mano)
CLAUDE.md              # contexto técnico completo del proyecto
```
