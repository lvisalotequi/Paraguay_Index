# Contexto de traspaso: Paraguay–Estados Unidos
Actualizado el 27 de agosto de 2026.

## Workflow simplificado y ledger — 30 agosto 2026

Ver WORKFLOW_EXTRACCION.md. `extraction_workflow.py plan` congela dry runs/SQL;
`execute --plan` verifica configuración, presupuesto, billing, recibos y caché.
`usage_ledger.py` deduplica *.complete.json por job_id. Estado: 8 jobs,
13.012.828.160 bytes (~12,119 GiB). Config: query 10/run 100/mes ledger 100 GiB.
No es cuota oficial. No borrar recibos. Año no planificado. 54 tests OK.

## Estimación 2015 — 31 agosto 2026

Solo dry runs: feb parcial–dic = 136,806 GiB (146.894.565.382 bytes). Plan se
detuvo: meses hasta 16,135 GiB exceden query cap10; total excede run100 y con
ledger actual excedería mes100. No ejecución ni cambios de límites. Ver
output/workflow/ESTIMACION_2015.md. Propuesta pendiente de autorización: query17,
run/mes100; feb–ago ahora y sep–dic siguiente mes calendario.

## Eficiencia proxy B agregado — 30 agosto 2026

Ver output/cost_efficiency_v1/RESULTADOS.md. Nuevo proxy_b_metrics.
Piloto abril: 0,678 GiB registrados vs 0,690 GiB previo (~1,84 % reducción);
CSV 734 vs 95.016 bytes (~99,23 % reducción). 20 proxy coinciden exactamente.
Facturación deshabilitada/sin cuenta antes/después. Abril mensual estimado
8,343 GiB, NO ejecutado por cap 1 GiB. Agregar reduce salida, casi no lectura.

ACTUALIZACIÓN: abril completo fue autorizado y ejecutado después con caps 10 GiB.
182 proxy (PY 179, US 3), 5 dominios, tono medio -0,6713625835; 8,343 GiB
registrados, CSV 753 bytes. Billing deshabilitado/sin cuenta antes/después.
Job/hash en output/cost_efficiency_v1/RESULTADOS.md. No repetir. Defaults 1 GiB.

## DECISIÓN VIGENTE: B aceptada e implementada

Leer primero CONTEXTO_PORTABLE_PROXY_B.md: sustituye las recomendaciones
anteriores de dejar B solo como candidata. Usuario autorizó B como proxy.
Default CLI candidates_themes + procesamiento B automático, dry run, caps 1 GiB.
Verificación billing antes y después. proxy_b_config.json congela listas aceptadas.
Ejecutado localmente: output/proxy_b_accepted_v1/january.json (14/67) y april.json
(20/88). Sin nuevas consultas BigQuery. 45 tests OK. No equivale a noticias válidas.
No iniciar nuevos períodos ni elevar límites sin autorización. Contexto portable
incluye metodología, límites, comandos, dependencias y advertencia de credenciales.

## Alternativas locales comparadas (último estado)

Ver output/rule_alternatives_v1/RESULTADOS.md y comparison.json.
Usuario prioriza bajo esfuerzo y acepta omisiones. Se recomienda alternativa B
exploratoria, NO desplegada: base AND [D OR (I AND (R OR E))], E en
institutional_proxy_alternatives.json. Enero: 14 seleccionadas (8 pertinentes,
5 excluidas, 1 dudosa). Abril: 20 (2 pertinentes, 2 excluidas, 1 dudosa,
15 sin revisar). No son porcentajes históricos ni prueba independiente: B usa
ambos pilotos para desarrollo. No recuperar extremos, no imputar porcentajes,
no confundir ausencia de revisión con exclusión. Sin consultas nuevas; 41 tests OK.

## Contraste local de abril completado (último estado)

Ver output/rule_contrast_april_v1/RESULTADOS.md y contrast.json.
Regla v1 sin cambios: principal 10 (9 sin revisar, 1 dudoso); ampliado adicional
17 (2 pertinentes, 4 excluidos, 11 sin revisar). Principal pierde las 2 pertinentes
conocidas; ambas son aranceles sin etiquetas R/D previstas. No afirmar precisión
del principal: no hay casos seleccionados con revisión concluyente. Solo 20/88
revisados. No escalar v1 como filtro validado. Ninguna consulta de red/BigQuery.
39 pruebas correctas. Siguiente posible trabajo: alternativas locales, sin descargas.

## Descarga autorizada de abril con Themes (último estado)

Completado piloto 4–6 abril 2025: 88 registros, 741.343.232 bytes (~0,690 GiB),
CSV 95.016 bytes. Ver output/theme_estimates_v1/april_pilot/DESCARGA.md.
Facturación deshabilitada y sin cuenta vinculada comprobadas antes y después.
Recibo y hash verificados. No repetir. Julio y mes completo NO ejecutados.
Pendiente comparar localmente la regla con las revisiones; candidatos no validados.

## Estimación con Themes (sin extracción)

Nuevo perfil candidates_themes: candidates más Themes, sin Persons/Organizations.
Dry runs: abril 4–6 = 0,690 GiB; julio 4–6 = 0,652 GiB;
abril completo = 8,490 GiB. Ver output/theme_estimates_v1/RESULTADOS.md.
No se ejecutó descarga: mes supera límite conservador 1 GiB. No ampliar
límites ni dividir ejecuciones para eludir el total sin decisión del usuario.
Perfil aún usa catálogo estimado; no equivale a selección institucional validada.

## Revisión de textos v2 (más reciente)

Ver output/recovery_pilots_v2/RESULTADOS.md y sample_review.json.
Sin nuevas consultas BigQuery. Dos textos completos adicionales recuperados:
ABC enero id 17 sigue dudoso por alcance de excancilleres; elsalvador.com enero
id 64 se excluye por relaciones separadas con Venezuela, no vínculo PY–US.
Acumulado: 5 textos recuperados de 17 problemas de acceso seleccionados;
3 excluidos y 2 dudosos. Quedan 12 textos pendientes, sin porcentaje imputado.
Muestra completa: 3 incluidos, 26 excluidos, 17 dudosos. V1 y crudos intactos.
No sortear verificaciones ni bloqueo de política del navegador. Para los textos
bloqueados, solicitar copias legítimamente accesibles al usuario.

## Pilotos adicionales y recuperación acotada

Se ejecutaron candidates 4–6 abril y 4–6 julio 2025: 88 y 91 candidatas,
628.097.024 bytes de cuota en total (0,585 GiB), con verificación de proyecto
sin facturación antes de cada trabajo y límite conjunto máximo de 1 GiB.
No repetir: ambos tienen recibos y CSV con hash verificado.
Ver output/recovery_pilots_v1/RESULTADOS.md y summary.json.
Muestreo congelado: 20 candidatas por nuevo piloto (10 por etiqueta PY/US),
más 6 de las 26 dudas de acceso de enero. Se revisaron 46 registros.
Abril muestra: 2 incluir / 13 excluir / 5 dudosas. Julio: 1 / 11 / 8.
Las 139 candidatas nuevas no muestreadas siguen sin revisar, no dudosas.
Entre 17 problemas de acceso seleccionados se localizaron 3 textos: 2 excluidos
y 1 aún dudoso; 0 inclusiones recuperadas. No implica 0% real de pertinencia.
Wayback falló desde la herramienta; no se probó ausencia de capturas.
No se fija porcentaje general ni imputación. Datos previos intactos;
adjudicaciones nuevas en sample_review.json, sin sobrescribir enero.
Tres nuevas inclusiones directas están en summary.json/new_confirmed_articles.
recovery_sampling.py y summarize_recovery.py reproducen offline muestra/resumen.

## Segundo piloto revisado (4–6 enero 2025)

Se revisaron las 86 candidatas del perfil ligero: 1 inclusión confirmada,
51 exclusiones y 34 dudosas/no verificables. Las 34 quedan fuera de métricas.
La inclusión es la noticia de Última Hora sobre política exterior y Senad–DEA.
No confundir clasificación completa con recuperación completa de los textos:
24 dudosas son inaccesibles, 2 tienen contenido/fecha cambiados y 8 mantienen
incertidumbre de alcance o país editorial. No se midió sensibilidad.

Archivos nuevos en output/pilot_2025_01_04_06/:
REVISION_COMPLETA.md, review_complete_v1.json, media_catalogue_v2.json y
valid_only_v1.json. Esta selección se conserva separada de las 9 válidas del
primer piloto. No se realizaron nuevas consultas BigQuery durante la revisión.
Las fechas corresponden a observación GDELT. SQL candidates descarga controles
amplios; review_candidate_gate.py exige inclusión revisada y país verificado.
La clasificación detectó 11 registros de fuentes editoriales fuera de PY/US
aunque el catálogo antiguo de GDELT los etiquetó US. Los demás países no
verificados permanecen explícitamente no verificados; no inferirlos del dominio.
Para reproducir y probar, usar Python con -X utf8 en Windows al imprimir JSON.

## Selección de trabajo autorizada

Por nueva decisión del usuario, la selección vigente es SOLO válidas:
output/gdelt/review/working_selection_v2.json: 9 incluidas (4 centrales y
5 contextuales). Los 17 dudosos quedan fuera sin cambiar su clasificación.
working_selection_v1.json (26 registros) se conserva como antecedente, no usar
como selección vigente. prepare_pilot_selection.py ahora reproduce v2.
Las 41 exclusiones permanecen en los originales/revisión completa, como controles
negativos. prepare_pilot_selection.py reproduce la selección con biblioteca
estándar, sin red ni escrituras (JSON por stdout). Campos y límites explicados
en WORKING_FIELDS.md. No se cambió SQL ni se consultó BigQuery. Dudosos no entran
en métricas confirmadas. Se conservaron los cuatro valores de tono, identidad,
fecha observada, país/idioma y evidencia/pendientes; metadatos extensos permanecen
en el CSV original. Esta selección no es una lista blanca para el histórico.

## Estado posterior al piloto autorizado
Se ejecutaron DOS consultas limitadas al 1–3 de enero de 2025: indicadores y
auditoría por URL. Cada una computó 827.326.464 bytes de cuota (0,771 GiB);
total 1,541 GiB. Se comprobó ausencia de facturación antes de cada ejecución.
El CSV de auditoría contiene 67 coapariciones: 38 de fuentes catalogadas PY y
29 US. El filtro antiguo acepta 63; NO equivalen a 63 noticias relevantes.
Hay falsos positivos temáticos y errores en el catálogo de países fuente.
La revisión ampliada cubre los 67 registros: 9 incluir (4 centrales y 5 de
contexto), 41 excluir y 17 dudosos. No se afirma lectura íntegra de todos los
textos: hay enlaces caídos, acceso parcial, una redirección a otro artículo y
sedes editoriales pendientes. Ver CLASSIFICATION_PILOT.md y los archivos
classification_v1.json / media_catalogue_v1.json en output/gdelt/review.
El catálogo contiene 31 dominios: 16 con país verificado, 5 con evidencia
histórica por revalidar y 10 sin confirmar. Listín Diario y teleSUR estaban
asignados a US; las sedes verificadas son DO y VE. No es un censo longitudinal.
Esta fase NO realizó nuevas consultas a BigQuery ni modificó SQL/facturación.
Las 9 inclusiones son de fuentes PY; los 12 dudosos del grupo GDELT US impiden
interpretar que no exista cobertura pertinente estadounidense.
No se recalculó tono con esta selección ni se ajustaron denominadores.

Se detectó que la fila BOTH del CSV original de indicadores estaba mal:
GROUP BY resolvía el alias antes del subtotal. El SQL está corregido mediante
GROUPING(corpus.source_country) y validado por dry run. No se repitió la descarga.
Los totales correctos se recalcularon localmente desde la auditoría en
output/gdelt/review/pilot_review.json. NO usar la fila BOTH del CSV original.
Datos originales conservados por huella; revisión separada. pilot_review.json
es la primera fase, no la clasificación ampliada. Ver CLASSIFICATION_PILOT.md.
inspect_pilot.mjs reconstruye únicamente esa primera fase; no reproduce las
decisiones curadas de classification_v1.json. validate_pilot_review.py valida
localmente integridad/consistencia sin acceso a red; 18 pruebas offline pasan
al combinar test_pilot_review.py y test_bilateral_media_extractor.py.

Nuevo perfil candidates: enero 2025 estimado en 3,761 GiB, SIN ejecutar el mes.
Trae URL/fecha/fuente/idioma/tono y coaparición geográfica, pero NO personas,
organizaciones, temas ni denominadores. No es equivalente a la métrica completa:
requiere clasificación local o lectura de textos. Perfil audit conserva esos
metadatos para refinar filtros sin nuevas consultas. Doce pruebas locales pasan.

## Objetivo y alcance
Dimensión: **Visibilidad mediática y relevancia pública**.
Noticias en español/inglés de fuentes asignadas a Paraguay o Estados Unidos.
Series mensuales desde marzo de 2015; febrero desde el día 19 es parcial.
Google Trends se mantiene separado por país. Su código no fue optimizado en
esta revisión; sigue siendo experimental/no oficial.

## Archivos necesarios
- bilateral_media_extractor.py: CLI y controles de seguridad.
- gdelt_queries.py: SQL de los perfiles.
- requirements.txt: dependencias.
- test_bilateral_media_extractor.py: pruebas locales sin consultas reales.
Copiar ambos archivos Python de producción al trasladar el extractor.

## Resultados de validación real (dry runs, sin extracción)
Proyecto: leandro-gdelt-2026-abc.
- Borrador anterior, enero 2025, tres tablas: 19,268 GiB.
- Perfil articles optimizado, enero completo: 9,341 GiB.
- Perfil articles, 1–3 enero 2025: 0,770 GiB.
- Perfil events separado, enero completo: 10,788 GiB.
El ahorro del perfil articles no es ahorro manteniendo todos los productos:
excluye la consulta de eventos. Ejecutar ambos perfiles procesa sus respectivos
datos; no se deben sumar sus conteos ni sus tonos. No se extrapolaron estos
tamaños a todos los años. BigQuery aceptó ambos SQL; eso no valida el contenido
ni la precisión metodológica de los resultados.

En la fase previa se verificó mediante gcloud que billingEnabled=false y
billingAccountName está vacío. No se activaron servicios ni facturación.
El piloto fue autorizado y ejecutado después; ver el estado actualizado arriba.

## Cambios
1. Perfil articles predeterminado: solo GKG más catálogo de fuentes. Usa campos
   compactos Locations, Themes, Organizations, Persons sin posiciones textuales.
   Mantiene volumen, fuentes, días, tono, dispersión y proporciones.
2. Perfil events opcional: CAMEO usa PRY/USA, no los FIPS PA/US que sí se usan
   en Locations. Se deduplican enlaces evento-artículo y después eventos.
   Las cuatro categorías de eventos no cuentan cada mención como otro evento.
3. El tono de eventos procede únicamente de documentos del corpus seleccionado;
   no se usan AvgTone/NumMentions globales que incluyen otros países fuente.
4. Denominadores y numeradores de artículos usan la misma deduplicación:
   URL exacta sin fragmento. Se conservan parámetros funcionales (?id=...);
   ya no se colapsan todas las noticias de una misma ruta.
5. Artículos no se repiten bajo tres direcciones. Las direcciones pertenecen
   exclusivamente al CSV de eventos. BOTH es un total, no una fila para sumar
   nuevamente con PY y US.
6. --pilot-days 3 consulta solo los primeros tres días de un único mes. Exporta
   period_start, period_end y partial_month=true; NO es un mes representativo
   ni un sustituto del mes completo. Nunca extrapolar sus conteos al mes.

## Seguridad
- Sin --execute: únicamente dry runs. No se aumenta ningún límite.
- Valores predeterminados: 5 GiB por consulta y 5 GiB para toda la ejecución.
- Se estima el plan completo antes de iniciar cualquier consulta real.
- maximum_bytes_billed acota cada trabajo en BigQuery.
- Antes de cada ejecución real se exige proyecto sin facturación y sin cuenta
  vinculada: API de lectura, o gcloud billing projects describe como alternativa.
  Si no puede verificarse, se detiene; no habilita APIs automáticamente.
- Resultados por mes/perfil/huella SQL, con recibo y hash de integridad.
  Una repetición reutiliza archivos completos sin volver a consultar.
- Se registra el job_id ANTES del envío. Ante un trabajo incierto/interrumpido,
  no se reenvía automáticamente: revisar el job_id en BigQuery. No borrar
  reservas para forzar un reintento sin investigar el trabajo anterior.
- El límite acumulado es por ejecución de este programa, no una medición de
  la cuota restante de toda la cuenta. Otros programas pueden consumir cuota.
  No activar facturación mientras se utiliza este flujo.
- La fecha final predeterminada es el último mes completo y el inicio también:
  ya no se inicia accidentalmente un histórico de once años.

## Comandos seguros (PowerShell, desde la carpeta del proyecto)
Validar el piloto, sin descargar:

```powershell
.\.venv\Scripts\python.exe bilateral_media_extractor.py gdelt --project leandro-gdelt-2026-abc --start 2025-01 --end 2025-01 --pilot-days 3
```

Validar un mes completo, sin descargar:

```powershell
.\.venv\Scripts\python.exe bilateral_media_extractor.py gdelt --project leandro-gdelt-2026-abc --start 2025-01 --end 2025-01
```

Pruebas locales:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_bilateral_media_extractor.py
```

La descarga del piloto requiere añadir deliberadamente --execute y pasar todas
las barreras. Ya se efectuó para articles/audit; no repetirla. El mes completo
con todos los metadatos sigue superando el límite;
no elevarlo automáticamente. SQL y estimaciones están en output/gdelt/articles
y output/gdelt/events.

## Límites metodológicos todavía abiertos
- Catálogo de países fuente: estimación de abril 2015, no un censo actualizado
  ni verificación de sede editorial. Excluye medios no catalogados y dominios
  ambiguos; requiere auditoría del catálogo antes de análisis sustantivo.
- Locations registra geografía, no toda posible relación bilateral implícita.
- Una organización cualquiera no prueba institucionalidad pública. El filtro
  actual es un proxy de coaparición institucional y puede incluir empresas.
- GKG no identifica uniformemente el centro narrativo. El borrador anterior
  exageraba al afirmar que excluía todas las noticias centradas en personas.
  La salida nueva lo llama institutional_cooccurrence_proxy y conserva
  named_person_share y articles_without_named_person como controles. No afirmar
  que resuelve la exclusión de personas centrales: se necesita validar una
  muestra o definir una regla editorial adicional antes del análisis final.
- Tono describe el artículo completo, no sentimiento dirigido específicamente
  a la relación bilateral. Umbrales provisionales: -1 y +1.
- No hay deduplicación semántica de textos sindicados ni entre meses; URLs
  con parámetros de seguimiento distintos todavía pueden contar por separado.
- Eventos es una COHORTE: eventos registrados por primera vez en ese mes y
  mencionados en noticias del corpus ese mismo mes. No incluye todos los eventos
  históricos mencionados nuevamente. Resolverlos requeriría otra extracción.
- Las medianas/cuartiles SQL son aproximados. No hay intervalos de confianza.
- Cero artículos no implica cero cobertura real; puede ser ausencia en GDELT
  o limitaciones de los filtros. Meses con tono ausente no deben imputarse a cero.

## Referencias
- https://docs.cloud.google.com/bigquery/docs/best-practices-costs
- https://docs.cloud.google.com/billing/docs/reference/rest/v1/projects/getBillingInfo
- https://blog.gdeltproject.org/multilingual-source-country-crossreferencing-dataset/
- https://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf
- https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
