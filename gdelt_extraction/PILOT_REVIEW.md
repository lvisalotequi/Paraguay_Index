# Piloto GDELT: 1–3 de enero de 2025

## Actualización: revisión ampliada

La primera pasada sobre los 67 registros está documentada en
CLASSIFICATION_PILOT.md: 9 incluir, 41 excluir, 17 dudosos. Los dudosos no se
cuentan como excluidos ni como pertinentes. Hay 31 dominios revisados, con
16 países verificados, 5 evidencias históricas por revalidar y 10 sin confirmar.
Los datos curados están en output/gdelt/review/classification_v1.json y
media_catalogue_v1.json; no se cambió la extracción original ni se consultó
BigQuery nuevamente. El resto de este documento conserva los hallazgos de
la primera fase y debe leerse como antecedente.

## Resultado operativo
Dos consultas acotadas: indicadores y URLs/metadatos de auditoría.
Lectura imputable a cuota: 827.326.464 bytes cada una; 1,541 GiB total.
Proyecto sin facturación y sin cuenta vinculada comprobado antes de cada una.
No se descargó ningún mes completo ni se activaron servicios.

## Por qué se procesan tantos bytes
BigQuery lee columnas de millones de registros del periodo para localizar
coincidencias. Los 9,341 GiB estimados no son el tamaño del CSV resultante.
Filtrar más temas reduce filas devueltas, pero no necesariamente columnas/bloques
leídos. LIMIT tampoco garantiza ahorro. La partición temporal sí permite evitar
otros días. Reducir columnas y evitar tablas adicionales produce ahorro real.
Fuente: https://docs.cloud.google.com/bigquery/docs/best-practices-costs

## Alternativas estimadas para enero 2025
| Perfil | GiB | Contenido y límites |
| --- | ---: | --- |
| Borrador original | 19,268 | Artículos y eventos juntos; tenía errores metodológicos |
| articles optimizado | 9,341 | Volumen/tono y denominadores; clasificación aproximada |
| candidates ligero | 3,761 | URLs, fechas, fuente, idioma y tono; sin clasificación institucional ni denominadores |

Estas alternativas NO son productos equivalentes. No presentar el ahorro de
candidates como si conservara todas las variables. El mes solo se estimó.

## Qué encontró la revisión
Coapariciones de países: PY=38 y US=29 (67). Filtro preliminar: PY=34 y US=29
(63). Es una muestra exploratoria festiva, no representativa del mes o del año.

1. Señales institucionales demasiado amplias: organizaciones deportivas y
   empresas privadas pasan el filtro de "alguna organización".
2. Persons incompleto: el perfil de Ana Brizueña no tiene personas detectadas,
   pese a estar centrado en una persona. No basta con filtrar Persons vacío.
3. País de fuente incorrecto: Listín Diario aparece como US, pero su aviso legal
   ubica su sede en República Dominicana. Afecta dos filas del piloto.
4. Hay notas antiguas/redifundidas: la fecha GKG es la de observación, no prueba
   de fecha original de publicación.
5. Fila BOTH original inválida por agregación SQL. Se corrigió el generador y
   se reconstruyeron los totales localmente. No se repitió la consulta.

## Textos revisados y decisiones documentadas
- Incluir por tema institucional: declaraciones del embajador sobre la relación
  bilateral. Los nombres corresponden a cargos públicos, no a vida privada.
  https://www.ultimahora.com/tras-acusaciones-de-pena-ostfield-brinda-en-las-fiestas-por-fortalecer-lazos-entre-eeuu-y-paraguay
- Incluir por tema institucional: respuesta del embajador a críticas oficiales.
  https://www.abc.com.py/politica/2025/01/01/el-mensaje-del-embajador-de-eeuu-tras-la-dura-critica-de-santiago-pena/
- Incluir por tema institucional: negociación intergubernamental Senad–DEA.
  https://www.ultimahora.com/dea-segun-rachid-negociaciones-son-entre-santi-y-donald-trump
- Excluir: perfil personal de maquilladora/influencer.
  https://www.lanacion.com.py/lnpop/2025/01/01/maquillaje-con-proposito-la-inspiradora-trayectoria-de-ana-brizuena/
- Excluir fuente dominicana: https://listindiario.com/aviso-legal.html

En esa primera fase quedaban 61 artículos pendientes. Las 29 banderas locales
por URL/sección/país no equivalen a 29 exclusiones definitivas: son prioridades
de revisión. No calcular una tasa de precisión de toda la muestra con solo
cuatro textos revisados. Reglas exploratorias, no validadas fuera del piloto.

## Recomendación
Antes del histórico, depurar el catálogo de medios y clasificar estos candidatos
localmente. Exigir una relación institucional identificable, no mera coaparición.
Excluir deporte/entretenimiento/perfiles privados; conservar autoridades cuando
actúan en su cargo y existe relación bilateral sustantiva. Mantener ambiguos
separados y no descartar automáticamente cualquier mención de una empresa.

Para ahorrar consultas repetidas, guardar una extracción de candidatos/metadatos
y probar reglas localmente. El perfil ligero es viable si se acepta obtener la
evidencia institucional mediante lectura posterior de noticias; para 2015 muchos
enlaces pueden no estar disponibles. Los denominadores normalizados requieren
otra extracción planificada: no se derivan de las noticias bilaterales solas.

## Archivos
- output/gdelt/audit/2025-01-pilot3d_1866e9bca2eaae69a1f2.csv: 67 registros originales.
- output/gdelt/articles/2025-01-pilot3d_c1a2845287c9a69d00e2.csv: indicadores originales;
  NO usar fila BOTH.
- output/gdelt/review/pilot_review.json: decisiones, banderas, verificaciones y
  totales combinados corregidos. Nunca interpretar tono provisional como tono
  validado de la relación bilateral.
