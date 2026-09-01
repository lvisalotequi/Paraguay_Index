# Contexto de traspaso — proxy B aceptado

Actualizado: 27 agosto 2026. Usuario: Leandro.

## Workflow autónomo — actualización 30 agosto 2026

Leer WORKFLOW_EXTRACCION.md. Nuevos usage_ledger.py, extraction_workflow.py y
workflow_config.json. Flujo plan/execute congelado; presupuesto interno mensual
100 GiB, consulta 10 GiB, ejecución 100 GiB; verificación antes de ambos pasos.
Ledger inicial: 8 jobs únicos, 13.012.828.160 bytes (~12,119 GiB) según recibos.
Fechas legacy pueden ser mtime. No borrar recibos. No es cuota oficial ni cobro.
54 tests OK. No se ejecutó el año. `execute` siempre requiere autorización.

### Estimación 2015 — 31 agosto 2026

Ver output/workflow/ESTIMACION_2015.md. Dry runs febrero parcial–diciembre:
146.894.565.382 bytes = 136,806 GiB. Ninguna descarga. Plan rechazado por caps
query 10/run 100/ledger mensual 100 GiB; julio máximo 16,135 GiB. No se elevaron.
Recomendación pendiente: query cap 17 GiB, mantener run/mes 100, ejecutar dos
lotes: feb–ago (~79,23 GiB) y sep–dic (~57,58 GiB) en meses calendario separados.

## Actualización 30 agosto 2026 — eficiencia agregada

Leer output/cost_efficiency_v1/RESULTADOS.md. Se añadió perfil experimental
proxy_b_metrics. Piloto 4–6 abril ejecutado: 727.711.744 bytes registrados,
3 filas/734 bytes, 20 proxy (PY 19, US 1), coincide exactamente con B local.
Frente a candidates_themes: solo ~1,84 % menos lectura, pero ~99,23 % menos CSV.
Billing deshabilitado/sin cuenta comprobado antes y después. No repetir.
Abril completo agregado: dry run 8.957.811.101 bytes (8,343 GiB), NO ejecutado;
supera cap operativo 1 GiB. La agregación no soluciona el costo de lectura porque
Themes/Locations/URL/idioma/tono siguen escaneándose. Antes de un año, elegir
auditoría (candidates_themes) o solo serie congelada (proxy_b_metrics), estimar
un mes y mantener presupuesto acumulado.

### Abril completo ejecutado posteriormente

Autorizado con caps explícitos 10 GiB: 182 proxy B (PY 179, US 3), 5 dominios,
tono n=182 y medio -0,6713625835. Procesado 8.957.811.101 bytes; registrado
8.957.984.768 bytes (8,343 GiB); CSV 753 bytes. Billing deshabilitado/sin cuenta
comprobado antes/después. Job gdelt_safe_45c78ddcf72a4403bf1362deb4422c31,
SHA256 999aac9d63a5707e5a65f38551a63d8be1b8e39d1c9e4d6d14f43717f9cbe51e.
No repetir. Defaults siguen 1 GiB. Siguiente paso acordado: añadir optimizaciones
de workflow/registro acumulado antes de estimar o ejecutar un año.

## Decisión vigente

El usuario aceptó explícitamente ejecutar B como proxy y usar B en las próximas extracciones. Prioriza bajo costo y reproducibilidad frente a revisión exhaustiva. No continuar recuperando páginas caídas, no inventar porcentajes de rescate y no perseguir excepciones individuales. No ejecutar nuevas descargas solo por abrir este contexto.

Dimensión oficial: **visibilidad mediática, relevancia pública** de relaciones interinstitucionales Paraguay–Estados Unidos. Fuentes editoriales PY/US; idiomas español/inglés. Gobierno, instituciones y colectivos; personas pueden aparecer en función oficial. La exclusión perfecta de perfiles privados o empresas no se garantiza con metadatos.

## Metodología congelada

Configuración aceptada: proxy_b_config.json, versión proxy_b_v1_accepted_2026_08_27. Sus listas exactas D/I/R/E son la referencia operativa; no modificar las antiguas configuraciones experimentales para reproducir B.

Selección = base Y [D O (I Y (R O E))].

- Base: coocurrencia geográfica PY–US en GDELT, fuente verificada del catálogo, idioma eng/spa, ventana definida y URL deduplicada.
- D: señales diplomáticas, embajadores, sanciones, tratados y cooperación.
- I: gobierno, instituciones y cargos públicos seleccionados.
- R: señales internacionales de comercio, fronteras e inmigración.
- E: EPU_ECONOMY, ECON_TAXATION, WB_1121_TAXATION, EPU_CATS_TAXES.

Temas comparados por token completo. Economía sin I no basta. No depende del título, nombres propios, lectura de URL ni evaluación manual. Metadatos sin señales o país no verificado quedan fuera del proxy con motivo registrado; no borrar crudos. Dudoso/sin revisar no significa irrelevante y no puede detectarse automáticamente: puede entrar un caso semánticamente dudoso si activa B.

Es una aproximación de coocurrencia con señales institucionales/económicas, NO noticias individualmente validadas. Tono = documento completo, no sentimiento dirigido a la relación bilateral. PY/US es país de fuente, no dirección de interacción. No publicar estos resultados como calidad de relaciones diplomáticas.

## Implementación actual

- bilateral_media_extractor.py: perfil por defecto candidates_themes; dry run por defecto; ambos límites por defecto 1 GiB. Tras --execute descarga candidatos y aplica proxy_b.py localmente, también cuando reutiliza caché verificada.
- gdelt_queries.py: candidates_themes añade Themes; no lee Persons/Organizations ni une Events. Los perfiles articles/events/audit/candidates siguen disponibles como diagnósticos antiguos, NO son la metodología B predeterminada.
- proxy_b.py: procesa CSV local, filtra por catálogo y B, produce JSON con seleccionadas, auditoría, métricas por mes/fuente y hashes de configuración, catálogo e input. No usa red. No sobrescribe archivos existentes en su CLI.
- El extractor verifica facturación deshabilitada y cuenta no vinculada inmediatamente antes y después de cada consulta de datos. Fallo de comprobación = detener. Nunca habilitar facturación ni vincular tarjeta.
- Guarda SQL, reserva de job antes de ejecutar, recibo y SHA256. No repetir trabajos ambiguos. Si falla la comprobación posterior, inspeccionar recibo y datos antes de cualquier reintento: la descarga pudo completarse.

Las métricas actuales incluyen URLs seleccionadas, dominios y medias de tone, positive_score y negative_score con sus denominadores. Las ventanas de piloto siguen marcadas como parciales: no son un mes completo. Sin filas no se inventa un mes cero. Ceros con filas disponibles se refieren solo al marco descargado y catálogo, no ausencia real de cobertura nacional.

Deduplicación por mes y url_key (URL sin fragmento), primera observación; parámetros relevantes preservados. No deduplica automáticamente textos sindicados con URLs diferentes. En distintos meses una URL puede volver a contar como cobertura observada, no como publicación nueva.

## Ejecutado en esta sesión

Solo ejecución local de B sobre archivos existentes, ninguna nueva consulta BigQuery:

- output/proxy_b_accepted_v1/january.json: 14 seleccionadas / 67 candidatas, 1–3 enero 2025.
- output/proxy_b_accepted_v1/april.json: 20 seleccionadas / 88 candidatas, 4–6 abril 2025.

Los números son proxies, no válidas confirmadas. Enero: 8 pertinentes conocidas, 5 exclusiones, 1 dudosa entre seleccionadas. Abril: 2 pertinentes, 2 exclusiones, 1 dudosa y 15 sin revisar. B se diseñó utilizando estos pilotos: NO validación independiente ni precisión histórica. 45 pruebas locales correctas, incluyendo futura ejecución simulada y las dos comprobaciones de facturación.

## Seguridad y consumo

Proyecto privado: leandro-gdelt-2026-abc. Última descarga real: abril 4–6 con Themes, 88 registros; 741.343.232 bytes (~0,690 GiB), CSV 95.016 bytes. Estado de facturación comprobado antes y después de esa descarga: deshabilitada y sin cuenta vinculada. No es garantía continua: volver a verificar antes de cada descarga.

Archivo: output/theme_estimates_v1/april_pilot/candidates_themes/2025-04-pilot3d-from04_efc7321c426cb3c7babe.csv. SHA256: 605cfa6edcbf7c2ead4f0f5a8b3eab602e1e689f578a9e8066b9839173b9bace. Conservar recibo/reserva adjuntos.

Abril completo se estimó en 8,49 GiB y NO se descargó. Julio 4–6 con Themes: 0,652 GiB estimados, NO descargados. No subir límites ni dividir ejecuciones para eludir el presupuesto total. Los límites son por ejecución; no existe un presupuesto acumulado automático entre invocaciones distintas. Menos filas seleccionadas no garantiza menos bytes de lectura.

## Comandos para retomar

Desde la carpeta del proyecto, PowerShell. Estimación únicamente (julio sigue pendiente):

```powershell
.\.venv\Scripts\python.exe bilateral_media_extractor.py gdelt --project leandro-gdelt-2026-abc --start 2025-07 --end 2025-07 --pilot-days 3 --pilot-start-day 4 --profile candidates_themes --output output/theme_estimates_v1/july_pilot --max-gib 1 --max-total-gib 1
```

No añadir --execute hasta que el usuario autorice la descarga tras revisar el consumo. Con --execute, B se aplica automáticamente después; salida proxy_b_*.json junto al CSV.

Reprocesamiento puramente local, sin Google, usando un nombre de salida nuevo:

```powershell
.\.venv\Scripts\python.exe proxy_b.py RUTA_AL_CSV_CON_THEMES --output RUTA_NUEVA_AL_RESULTADO.json
.\.venv\Scripts\python.exe -m unittest discover -q
```

Los CSV económicos sin Themes no sirven para B; el procesador los rechaza. No volver a descargar enero/abril existentes para recalcular.

## Qué llevar a otro sitio

Este documento es autónomo como contexto. Para ejecutar código, copiar conservando estructura:

- bilateral_media_extractor.py, gdelt_queries.py, proxy_b.py, proxy_b_config.json y requirements.txt.
- output/pilot_2025_01_04_06/media_catalogue_v2.json (dependencia obligatoria del filtro editorial).
- Los CSV que se quieran procesar con sus .sql, .complete.json y .reserved.json; resultados proxy_b_accepted_v1 y reportes, si se desea conservar historial.
- Para reproducir todas las pruebas, copiar el proyecto de código y datos de prueba completo, excluyendo credenciales y entornos.

No copiar ni publicar application_default_credentials.json, archivos de cuenta de servicio, carpetas gcloud o .venv. Crear entorno nuevo e instalar requirements.txt; el análisis local B usa solo biblioteca estándar. La autenticación Google solo se necesita para consultas remotas, mediante cuenta personal: no requiere crear cuenta de servicio ni activar facturación. El entorno actual usa Python 3.10 y muestra advertencia de soporte futuro de Google; para un entorno nuevo preferir Python 3.11 o superior.

## Límites históricos pendientes

Serie actual GKG2 desde 19 febrero 2015; enero y primeras semanas de febrero 2015 faltantes, no ceros. No empalmar otro producto sin metodología propia. La fecha es observación GDELT, no necesariamente publicación. El catálogo es incompleto y no está certificado históricamente: no representa todo Internet. La consulta conserva el catálogo estimado GDELT como prefiltro y el código local aplica el verificado; puede omitir fuentes y no acredita cobertura completa estadounidense. Revisar el panel antes de afirmar representatividad longitudinal.

No iniciar extracción 2015–actualidad ni ampliar alcance por el hecho de que B esté aceptada. El próximo paso requiere autorización de período y presupuesto, manteniendo estos controles.
