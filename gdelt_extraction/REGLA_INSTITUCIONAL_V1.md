# Regla de selección institucional económica — propuesta v1

Dimensión: **visibilidad mediática, relevancia pública**.
Fecha: 27 de agosto de 2026. Estado: diseño y prototipo local; NO activado en el extractor.

## 1. Qué medirá

Un indicador aproximado de coocurrencia Paraguay–Estados Unidos con señales institucionales en noticias de un panel de medios. No prueba que cada documento describa una relación bilateral efectiva. No es un censo del ecosistema informativo de Internet.

La disponibilidad actual del texto no entra en la regla. No hay lectura automática de páginas, recuperación de enlaces, modelos de lenguaje, embeddings ni rescate porcentual.

## 2. Filtro base B

- Noticias web con referencias geográficas a Paraguay y Estados Unidos en Locations.
- Medio del panel editorial verificado PY/US. Usar el host de la URL; no atribuir país por extensión, idioma o catálogo estimado de GDELT.
- Idioma eng/spa según metadatos; conservar que eng puede ser una inferencia cuando TranslationInfo está vacío.
- Período de observación definido y URL deduplicada.
- País editorial desconocido, fecha de extracción incompleta o metadatos ausentes no significan noticia irrelevante. Registrar esos controles por separado.

El catálogo actual es una base, no un panel histórico certificado. Antes del histórico hay que fijar dominios, alias, tipo de fuente y cambios conocidos de país/editor. Separar medios periodísticos de portales institucionales; estos últimos, si se incluyen, deben tener serie propia. No exigir sobrevivir hasta 2026 para admitir un medio histórico. Una verificación actual no certifica automáticamente 2015.

## 3. Regla temática exacta

Usar Themes, dividido por punto y coma; comparar tokens completos con las listas versionadas en institutional_proxy_rule_v1.json.

- D: diplomacia, embajadores, sanciones, cooperación militar/económica o tratados.
- I: gobierno, organismos intergubernamentales, legislación, fuerzas armadas o cargos públicos seleccionados.
- R: política comercial, libre comercio, disputas comerciales, conectividad/logística comercial, fronteras o inmigración.

Principal = B Y [D O (I Y R)].
Ampliada = B Y (D O I O R).
Ampliada adicional = ampliada MENOS principal.
Resto = coocurrencia sin esas señales; no equivale a exclusión temática verificada.

Las listas exactas, no estas descripciones, son el contrato reproducible. No basta cualquier organización, cualquier tema económico o la palabra “presidente” en una URL. No se usan títulos ni slugs.

Es una decisión de diseño: dos señales no demuestran relación causal ni bilateral. Diplomacia puede referirse a un tercer país; un cargo puede ser anterior o figurado. Son errores esperables que deben medirse, no esconderse.

No eliminar por Persons: impediría captar actuaciones de presidentes, ministros y embajadores. Tampoco se garantiza excluir perfiles personales. Empresas y colectivos podrán entrar cuando activen la misma regla, sin clasificación especial costosa. Se acepta que pueden perderse cooperación cultural, educativa, sanitaria y otros temas no cubiertos; no ampliar etiquetas silenciosamente.

## 4. Prueba disponible, sin nueva extracción

Primer piloto: 67 registros, 1–3 enero de 2025. Catálogo actual utilizado solo como diagnóstico, sin certificar retrospectivamente el panel.

| Grupo automático | Pertinentes según revisión previa | No pertinentes | Dudosos | Total |
|---|---:|---:|---:|---:|
| Principal | 8 | 2 | 0 | 10 |
| Ampliado adicional | 1 | 9 | 4 | 14 |
| Solo coocurrencia | 0 | 18 | 6 | 24 |
| País/idioma no habilitado por el filtro base | 0 | 12 | 7 | 19 |

Principal: 8/10 coinciden con pertinencia previa y conserva 8/9 pertinentes identificados en ese piloto. NO son precisión/recobrado históricos: es diagnóstico dentro de una muestra pequeña usada para diseñar la regla; las revisiones previas tampoco son verdad perfecta y hay 17 dudas.

Ampliada total: 24 = 10 + 14, no 14. La comparación principal/ampliada es análisis de sensibilidad, no un intervalo estadístico ni límites garantizados del número real.

Los pilotos económicos de enero 4–6, abril y julio carecen de Themes: no es posible validar esta regla en ellos sin enriquecimiento adicional. No inventar resultados para esos pilotos.

## 5. Extracción propuesta

Conservar: fecha de observación, URL, host, idioma, país del panel, tono/puntuaciones y Themes. Locations se consulta para filtrar, sin necesidad de exportar su cadena completa.

Añadir Themes al perfil candidates y calcular las etiquetas localmente. No leer Persons ni Organizations; no unir Events/EventMentions. Conservar candidatos amplios y sus temas, no solo principal, para ajustar reglas localmente sin repetir GDELT.

Esto reduce trabajo manual, no garantiza menos bytes que el piloto candidates: añadir Themes puede aumentar la lectura de BigQuery. El ahorro esperado es frente a extracción más rica y revisión de textos. Antes de ejecutar, comparar dry runs; mantener proyecto sin facturación, máximo por consulta y máximo acumulado. No modificar esos controles.

Leer columnas necesarias y filtrar particiones; reducir filas de salida o usar LIMIT no garantiza reducir bytes leídos. [Documentación de BigQuery](https://docs.cloud.google.com/bigquery/docs/best-practices-performance-compute).

No repetir lo ya descargado. El prototipo local no modifica el extractor, los CSV, las revisiones ni las listas de válidas.

## 6. Métricas mensuales

Para principal y ampliada, por fuentes PY, fuentes US y total:
- URLs distintas, medios distintos y días con cobertura.
- Media de tone, positive_score y negative_score; número de tonos observados.
- Fracciones de documentos positivos/negativos/neutros, si se usan, con umbrales fijados y documentados; no confundirlas con las puntuaciones léxicas.
- Proporción principal/coocurrencias del mismo panel. No denominarla cuota de todo Internet.

Para cuota sobre toda la producción del panel hace falta otro denominador, no disponible en candidates. No añadir esa extracción sin estimarla.

Tono = tono del documento completo, no sentimiento dirigido a la relación bilateral. Fuente PY/US no indica dirección de la relación; no producir PY→US con estos datos.

Deduplicar por URL sin fragmento; preservar parámetros significativos. Dentro del mes usar la primera observación determinista. Una URL que reaparece en otros meses podrá contar como cobertura observada en esos meses: no llamarla nueva publicación. Registrar esta convención. No se eliminan automáticamente sindicaciones con distinta URL.

Mes sin consulta completa = faltante, nunca cero. Consulta completa sin seleccionadas = volumen 0 y tono nulo. Marcar primer y último mes parciales. El diseño actual usa GKG 2 desde 19 febrero 2015; enero y primeros días de febrero quedan no disponibles en esta serie, sin empalmar otro producto como si fuera equivalente. [Referencia GDELT](https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/).

## 7. Control acotado antes de escalar

Congelar v1 ahora. Proponer una validación independiente de hasta 60 registros, repartidos entre períodos temprano, medio y reciente y entre principal y resto del marco de coocurrencias; representar ambos países de fuente cuando existan casos. Registrar selección y probabilidades, sin reemplazar inaccesibles por accesibles.

No recuperar páginas caídas en cadena: un intento público por registro; si falla, queda no evaluable. Informar resultados con y sin pendientes, no reasignarles porcentajes. La muestra no mide noticias que GDELT nunca captó ni las que no pasaron la coocurrencia geográfica.

Este control necesitaría datos enriquecidos fuera del piloto usado para diseñar. No está ejecutado ni autorizado por este documento. Si el rendimiento no sostiene la interpretación institucional, publicar únicamente el indicador de coocurrencia o revisar el diseño: nunca llamarlo clasificación validada por conveniencia.

## 8. Archivos

- institutional_proxy_rule_v1.json: listas cerradas y fórmulas.
- institutional_proxy_rule.py: clasificador puro sin red, con condición base provista por el llamador.
- output/rule_design_v1/pilot_diagnostic.json: resultado por URL y etiquetas activadas.
- test_institutional_proxy_rule.py: reproducción del diagnóstico y controles de coincidencia exacta.

El protocolo de análisis de tablas se aplicó para conservar los datos crudos y separar resultados derivados. No se creó ni modificó ningún CSV o Excel.

