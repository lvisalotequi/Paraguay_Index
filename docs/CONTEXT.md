# Paraguay_Index — contexto del repositorio

Este documento existe para que cualquier sesion (humana o de Claude Code) que
retome este repositorio tenga el contexto minimo sin depender del historial
de una conversacion previa.

## Objetivo del proyecto

Construir un indice de las relaciones bilaterales entre Paraguay y Estados
Unidos ("US-PY Engagement Index"), a partir de cuatro dimensiones. Cada
dimension se mide con varias variables, y cada variable se extrae mediante
un script de ingestion independiente.

## Estructura del repo

```
run_pipeline.py        # script maestro: descubre y corre los modulos de src/ingestion
src/
  ingestion/            # un archivo .py por variable/fuente de datos
  sheets.py             # helpers para leer/escribir en el Google Sheet de salida
config/
  credential_cloud.json # credencial de la cuenta de servicio de Google (NO se sube a git)
.github/workflows/
  run_pipeline.yml       # workflow de GitHub Actions, disparo manual (workflow_dispatch)
.env.example             # variables de entorno necesarias para correr en local
```

## Como funciona el pipeline

1. `run_pipeline.py` escanea `src/ingestion/` en busca de modulos que
   definan una funcion `run()`.
2. Cada `run()` debe devolver un `pandas.DataFrame` con los datos de esa
   variable/fuente.
3. El pipeline escribe cada DataFrame en su propia pestana del Google Sheet
   de salida (una pestana por modulo, incluida como el nombre del archivo).
4. Al final, siempre agrega una fila en la pestana `pipeline_log` con
   timestamp, modulos corridos y errores (si los hubo) — esto sirve como
   prueba de que la corrida efectivamente ocurrio.

### Como agregar un nuevo script de ingestion

Crear `src/ingestion/<nombre_variable>.py` con esta forma minima:

```python
import pandas as pd

def run() -> pd.DataFrame:
    # ... extraer datos de la fuente ...
    return pd.DataFrame({"columna": [...]})
```

No hace falta tocar `run_pipeline.py`: el modulo se descubre solo. Archivos
que empiezan con `_` se ignoran (utiles para helpers compartidos).

## Correr el pipeline en local

1. `pip install -r requirements.txt`
2. Copiar `.env.example` a `.env` y completar `SHEET_ID` con el ID del
   Google Sheet de destino (`GOOGLE_APPLICATION_CREDENTIALS` ya apunta a
   `config/credential_cloud.json`).
3. `python run_pipeline.py`

## Correr el pipeline en GitHub Actions

El workflow `.github/workflows/run_pipeline.yml` es manual por ahora
(pestana **Actions > Run Pipeline > Run workflow** en GitHub). Necesita dos
secrets configurados en **Settings > Secrets and variables > Actions**:

- `GOOGLE_SHEETS_CREDENTIALS`: el contenido completo (JSON) de
  `config/credential_cloud.json`.
- `SHEET_ID`: el ID del Google Sheet de destino.

## Google Sheets — puntos clave

- El Sheet de destino debe estar compartido como **Editor** con el email de
  la cuenta de servicio (campo `client_email` dentro de
  `config/credential_cloud.json`).
- Ojo con Sheets guardados dentro de una **Unidad compartida** de Google
  Workspace: suelen bloquear compartir con cuentas externas al dominio
  (una cuenta de servicio de GCP cuenta como externa salvo delegacion de
  dominio). Si el Sheet definitivo debe vivir en una Unidad compartida, hay
  que habilitar "permitir compartir fuera de la organizacion" en esa unidad,
  o agregar la cuenta de servicio como miembro directo de la unidad.

## Estado actual

- Estructura del pipeline y conexion a Google Sheets: probada y funcionando
  en local.
- `src/ingestion/` esta vacio: todavia no se cargo ningun script de
  extraccion real.
- El workflow de GitHub Actions esta configurado para disparo manual
  (`workflow_dispatch`); no hay cron programado.
- El repo tenia previamente un pipeline en R (`Paraguay_index_master_script.R`)
  y un workflow que corria un script `NIUBIZ_master_script.R` de otro
  proyecto — eran archivos vacios / de otra plantilla y se eliminaron.
