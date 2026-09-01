# Workflow simplificado y registro acumulado

Actualizado: 30 agosto 2026.

## Objetivo

Reducir intervención conversacional sin relajar seguridad. Dos pasos: congelar un plan mediante dry run y ejecutar únicamente ese plan. Configuración en workflow_config.json; metodología proxy B agregada, proyecto y presupuestos no se vuelven a escribir en cada comando.

La carpeta canónica es `output/cost_efficiency_v1/april_month`; contiene abril 2025 completo y permite reutilizarlo al planificar 2015 sin repetir la consulta.

## Registro acumulado

`usage_ledger.py` reconstruye `output/query_usage_ledger.json` desde todos los recibos `*.complete.json`. Deduplica por job_id y falla ante recibos inválidos o contradictorios. Para recibos futuros conserva proyecto, perfil, ventana, fecha, SQL, bytes procesados y registrados. Para recibos antiguos infiere la fecha a partir de la modificación del recibo y el hash SQL desde el archivo hermano; esta fecha inferida es una limitación explícita.

Estado al 30 agosto 2026: 8 trabajos únicos y 13.012.828.160 bytes registrados, aproximadamente 12,119 GiB. Esto suma todas las consultas completadas presentes en `output`, no solamente abril mensual ni solamente proxy B. No es dinero cobrado.

El ledger controla un presupuesto interno mensual de 100 GiB, configurable. Se comprueba al planificar y nuevamente al ejecutar. El límite por consulta es 10 GiB y por invocación 100 GiB. Los defaults del extractor directo siguen en 1 GiB; el workflow usa sus valores explícitos.

## Uso

Planificar, sin extracción:

```powershell
.\.venv\Scripts\python.exe extraction_workflow.py plan --start 2015-03 --end 2015-03
```

El comando realiza dry runs, verifica presupuestos, actualiza ledger, congela configuración y hashes SQL, y devuelve la ruta del plan. Si detecta SQL equivalente ya ejecutado fuera de la carpeta operativa, se detiene para evitar duplicarlo.

Ejecutar después de revisar el plan y autorizar el consumo:

```powershell
.\.venv\Scripts\python.exe extraction_workflow.py execute --plan RUTA_DEL_PLAN.json
```

La ejecución rechaza cambios de configuración/SQL, planes ya registrados o presupuestos mensuales superados. El extractor vuelve a estimar, valida todos los meses antes de comenzar, comprueba facturación antes/después de cada consulta, usa máximos por trabajo, reservas, recibos, hashes y caché. Al finalizar actualiza el ledger y crea un registro de ejecución.

`plan` no autoriza `execute`. En Codex, la ejecución remota seguirá mostrando la solicitud de permiso de la aplicación; si Leandro ejecuta PowerShell directamente, no necesita intervención de Codex.

## Límites y condiciones

- El ledger cubre recibos disponibles localmente. Si se borran o no se copian al trasladar el proyecto, el total queda incompleto. No borrar recibos.
- No es el medidor oficial de cuota de Google; es control reproducible del proyecto.
- Una ejecución puede completar BigQuery y fallar en la comprobación posterior. El recibo impide reintento automático; inspeccionar antes de continuar.
- La caché depende del SQL y archivos guardados. Cambiar el panel o proxy genera una consulta distinta.
- `proxy_b_metrics` no conserva URLs ni Themes; no permite recalibrar B localmente.
- Un año todavía requiere estimación previa completa y autorización. No se ha planificado ni ejecutado.

## Explicación de los dos tamaños

`maximum_bytes_billed` limita bytes que una consulta puede procesar. Para abril BigQuery leyó 8.957.811.101 bytes y registró 8.957.984.768 bytes. Después de filtrar, deduplicar, aplicar B y agregar, descargamos únicamente 753 bytes.

Los 753 bytes no podían obtenerse leyendo solo 753 bytes: contienen resúmenes derivados del recorrido de columnas grandes de GDELT. Es análogo a revisar un archivo grande y escribir tres totales en una hoja pequeña. Reducir las filas finales disminuye transferencia y almacenamiento, pero no necesariamente el escaneo.
