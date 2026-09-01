# Ejecución histórica portable

Desde 2026-09-01 este código vive dentro del repo `Paraguay_Index`, en
`gdelt_extraction/` (ver CLAUDE.md sección 6). Este documento sigue siendo la
referencia para instalar y correr el extractor en una computadora nueva.

## Alcance congelado

- Periodo cubierto hasta ahora: febrero de 2015 a diciembre de 2025 (completo).
  Enero de 2026 en adelante todavía no tiene estimado generado.
- Fuente: GDELT 2.1 GKG en BigQuery.
- Perfil: `proxy_b_metrics` con la regla B aceptada.
- Proyecto actual: `us-py-engagement-idx` (el mismo proyecto GCP del resto del
  pipeline de Paraguay_Index — no `leandro-gdelt-2026-abc`, que era el proyecto
  personal usado antes de integrarlo al repo).
- Techo preventivo acumulado por mes calendario: 850 GiB.
- Límite por consulta: 20 GiB.
- Límite por bloque: 100 GiB.
- Facturación: debe permanecer inhabilitada; el programa falla de forma cerrada si no puede comprobarlo.

## Archivos imprescindibles

- `historical_campaign.py`: coordinador reanudable.
- `historical_workflow_config.json`: proyecto y límites.
- `bilateral_media_extractor.py`, `extraction_workflow.py`, `gdelt_queries.py`, `proxy_b.py` y `proxy_b_config.json`: consulta y controles.
- `usage_ledger.py` y la carpeta `output`: recibos y deduplicación.
- `output/historical_estimates/estimate_2015-02_2025-12_reconciled.json`: estimación y bloques congelados.
- `requirements.txt`: dependencias.

## Preparación en otra computadora

0. **Instalar Google Cloud SDK** (`gcloud`) si no está — no viene con Python ni
   con el repo. Descargar de https://cloud.google.com/sdk/docs/install y
   confirmar que el usuario que corra esto tenga acceso al proyecto
   `us-py-engagement-idx` (o a un proyecto GCP propio sin facturación, si se
   arranca de cero en otro proyecto).
1. **Windows: si el repo va a vivir en una ruta larga** (nombres de carpeta con
   emoji, muchos niveles — como la Unidad compartida de este proyecto), hay que
   habilitar rutas largas *antes* de crear el venv o correr nada, si no
   `ensurepip` falla al crear el venv y luego `open()` falla con
   `FileNotFoundError` en archivos que sí existen dentro de `output/`. En
   PowerShell como administrador, una sola vez:
   ```powershell
   New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
   ```
   Verificar con `(Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled").LongPathsEnabled` (debe dar `1`).
   Google Drive para escritorio no soporta symlinks/junctions como atajo para
   acortar la ruta — no sirve como alternativa a este paso. Si el checkout va
   a vivir en una ruta corta (fuera de Drive, por ejemplo), este paso no hace falta.
2. Crear el entorno virtual — preferible en una ruta corta fuera del repo si el
   repo mismo está en una ruta larga (ej. `C:\Users\<usuario>\.venvs\gdelt_extraction`),
   así los scripts (que resuelven sus rutas relativas a su propio archivo, no al
   venv) funcionan igual sin depender de rutas largas para el venv en sí:
   ```powershell
   py -3.11 -m venv C:\Users\<usuario>\.venvs\gdelt_extraction
   C:\Users\<usuario>\.venvs\gdelt_extraction\Scripts\python.exe -m pip install -r requirements.txt
   gcloud init
   gcloud auth application-default login
   C:\Users\<usuario>\.venvs\gdelt_extraction\Scripts\python.exe historical_campaign.py --prepare
   ```

La preparación solo verifica y hace `dry run`. Para ejecutar después de revisar el plan:

```powershell
python historical_campaign.py --execute
```

El coordinador procesa bloques cronológicos, vuelve a estimarlos, comprueba la facturación antes de las consultas, registra recibos y escribe `output/historical_campaign/CONTINUIDAD.md`. Se detiene antes de que la suma registrada y el siguiente bloque superen 850 GiB.

Copiar siempre la carpeta `output` junto con el código. Sin los recibos, otra instalación no puede reconocer de forma fiable qué consultas ya se ejecutaron. Un cambio de equipo o proyecto debe hacerse para continuidad legítima, no para eludir cuotas del servicio.
