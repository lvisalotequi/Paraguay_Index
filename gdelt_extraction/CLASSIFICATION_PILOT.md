# Revisión del piloto: clasificación v1

Fecha de revisión: 27 de agosto de 2026. Periodo GDELT: 1–3 de enero de 2025.
Dimensión: **Visibilidad mediática y relevancia pública**.

## Resultado

Los 67 registros tienen una decisión documentada: **9 incluir, 41 excluir y 17 dudosos**.
No significa que se hayan leído 67 textos completos. Se revisaron los textos disponibles,
se conservaron cuatro decisiones de lectura de la fase anterior y se separaron los
enlaces inaccesibles, textos parciales y fuentes no verificadas.

**No se ejecutaron nuevas consultas a BigQuery**, ni se modificaron facturación, límites
o archivos originales. Esta fase utilizó archivos locales y páginas públicas.

| País asignado por GDELT (NO país corregido) | Incluir | Excluir | Dudoso | Total |
| --- | ---: | ---: | ---: | ---: |
| PY | 9 | 24 | 5 | 38 |
| US | 0 | 17 | 12 | 29 |
| Total | 9 | 41 | 17 | 67 |

No interpretar la fila US como ausencia real de cobertura estadounidense: hay
12 pendientes en ese grupo y la selección inicial de GDELT es incompleta.

Dentro de las 9 inclusiones hay **4 de foco central** (2, 3, 8 y 28) y
**5 de contexto** (7, 10, 14, 19 y 29). La 28 es opinión histórica publicada
en 2025: cuenta como visibilidad mediática, no como acontecimiento nuevo.
La 29 tiene un vínculo contextual particularmente débil y debe revisarse en
un análisis de sensibilidad. La 19 es un resumen multitemático que repite parte
de la 14: son dos URLs/publicaciones, no dos hechos ni dos narrativas independientes.

No se recalculó tono ni se presenta una precisión definitiva del extractor.
Esta revisión es de un solo codificador asistido, sobre tres días festivos; no
mide exhaustividad, acuerdo entre codificadores ni validez fuera de la muestra.

## Criterio de codificación propuesto

1. Incluir una interacción institucional identificable entre contrapartes de
   Paraguay y Estados Unidos, o su discusión sustantiva como contexto.
2. Conservar autoridades nombradas cuando el texto trata su función pública,
   no vida privada. Esta es la interpretación operativa usada aquí, no un
   filtro de “ausencia de nombres propios”.
3. Incluir empresas cuando participan en promoción oficial de inversiones,
   sanciones u otra actuación pública vinculada a ambas partes. No basta
   operar en ambos países, cotizar en bolsa o cobrar un flete entre ellos.
4. No atribuir BID, Gafilat u organismos multilaterales a US por su sede.
   Tampoco “dólar”, “inglés”, “Miami” o el nombre del río Paraguay prueban el vínculo.
5. No usar sección o URL como única causa de exclusión. Los casos deportivos
   leídos se excluyen por contenido; los inaccesibles quedan dudosos.
6. Mantener foco central/contextual, género histórico/opinión, resumen
   multitemático y posible republicación como variables de sensibilidad.
7. País del medio es país editorial, no país del servidor, del autor,
   de la agencia citada, de la audiencia ni de la noticia.
8. Dudoso no es cero, negativo ni excluido: mantenerlo separado.

## Límites de lectura

- current_text: cuerpo disponible en el acceso actual; no una captura de enero 2025.
- prior_text_review: lectura documentada en la primera fase.
- search_full_text: cuerpo recuperado en el resultado del buscador del mismo URL.
- publisher_mirror: copia bajo el CDN del mismo editor.
- country_only: exclusión por sede del medio, sin afirmar lectura del artículo.
- unavailable: no se recuperó texto suficiente.
- partial_text: parte visible seguida de restricción de acceso.
- syndicated_alternative: texto homónimo de agencia; identidad de la copia no verificada.
- changed_redirect: URL devuelve otra noticia.

Las páginas actuales pueden cambiar respecto a las observadas por GDELT.
La nota 44 está fechada en 2011, aunque fue observada en el piloto de 2025.
La 67 ahora redirige a un partido de noviembre de 2025. No reemplazar el
documento original con el destino actual como si fueran idénticos.

## Decisiones por registro

Los enlaces son evidencia del contenido cuando se indica lectura; en los
inaccesibles documentan el objeto intentado. Para exclusiones geográficas,
la evidencia está en el catálogo.

| ID | Documento | Decisión | Motivo | Acceso |
| --- | --- | --- | --- | --- |
| 1 | [Abrir noticia](https://www.lanacion.com.py/lnpop/2025/01/01/maquillaje-con-proposito-la-inspiradora-trayectoria-de-ana-brizuena/) | Excluir | Perfil de maquillaje e influencer; sin relación institucional bilateral. | prior_text_review |
| 2 | [Abrir noticia](https://www.ultimahora.com/tras-acusaciones-de-pena-ostfield-brinda-en-las-fiestas-por-fortalecer-lazos-entre-eeuu-y-paraguay) | Incluir | Declaraciones del embajador sobre cooperación y vínculos entre los dos gobiernos. | prior_text_review |
| 3 | [Abrir noticia](https://www.abc.com.py/politica/2025/01/01/el-mensaje-del-embajador-de-eeuu-tras-la-dura-critica-de-santiago-pena/) | Incluir | Respuesta del embajador estadounidense a críticas del presidente paraguayo en su función oficial. | prior_text_review |
| 4 | [Abrir noticia](https://www.abc.com.py/deportes/motor/2025/01/01/automovilismo-paraguay-arranca-su-ano-sonado/) | Excluir | Calendario y participantes del automovilismo; sin vínculo institucional PY–US. | current_text |
| 5 | [Abrir noticia](https://www.abc.com.py/espectaculos/musica/2025/01/01/leo-dan-el-cantante-y-compositor-argentino-muere-a-los-82-anos/) | Excluir | Obituario de cantante y giras; menciones geográficas no constituyen relación institucional. | current_text |
| 6 | [Abrir noticia](https://www.abc.com.py/politica/2025/01/02/fuerte-division-cartista-en-caaguazu-de-cara-a-las-municipales-del-2026/) | Excluir | Disputas electorales en Caaguazú; el texto no establece vínculo con Estados Unidos. | current_text |
| 7 | [Abrir noticia](https://www.abc.com.py/politica/2025/01/02/seprelad-persiste-con-el-ocultamiento-de-los-financistas-del-pleno-de-gafilat/) | Incluir | Financiación de Gafilat/Seprelad con discusión de Tabesa y sanciones de OFAC; vínculo institucional secundario. | current_text |
| 8 | [Abrir noticia](https://www.ultimahora.com/dea-segun-rachid-negociaciones-son-entre-santi-y-donald-trump) | Incluir | Negociación entre Gobierno paraguayo y Estados Unidos sobre Senad–DEA. | prior_text_review |
| 9 | [Abrir noticia](https://www.abc.com.py/economia/2025/01/02/cotizacion-del-dolar-cuanto-se-aprecio-y-en-que-valor-cerro-en-el-2024/) | Excluir | Cotización dólar/guaraní y operaciones del BCP; no identifica relación bilateral institucional. | current_text |
| 10 | [Abrir noticia](https://www.abc.com.py/politica/2025/01/02/carro-culpa-a-villate-de-su-salida-del-ejecutivo/) | Incluir | Cambio de vocería presidencial motivado por comunicación de la cooperación Senad–DEA; funcionarios en sus cargos. | current_text |
| 11 | [Abrir noticia](https://www.lanacion.com.py/futboledicion-impresa/2025/01/02/llegada-de-benedetto-genera-gran-expectativa/) | Excluir | Contratación de futbolista y situación de Olimpia; sin vínculo público bilateral. | current_text |
| 12 | [Abrir noticia](https://www.abc.com.py/opinion/2025/01/02/crisis-en-la-gobernanza-climatica-20-parte-ii/) | Dudoso | No se recuperó el texto de la columna climática; el título no permite resolver su pertinencia. | unavailable |
| 13 | [Abrir noticia](https://d10.ultimahora.com/pretemporada-en-el-este) | Excluir | Pretemporada de Cerro Porteño y movimientos de jugadores. | current_text |
| 14 | [Abrir noticia](https://www.lanacion.com.py/politica/2025/01/02/medio-espanol-destaca-a-pena-como-un-elocuente-vendedor-del-potencial-de-paraguay/) | Incluir | Promoción oficial de inversiones: reuniones de Peña en San Francisco con Nvidia, Google, Meta y Amazon. | current_text |
| 15 | [Abrir noticia](https://www.lanacion.com.py/pais/2025/01/02/el-ultimo-viaje-del-tranvia-en-asuncion-una-nostalgia-que-cumplio-28-anos/) | Dudoso | Historia del tranvía menciona franquicias de varios países, incluido US; no identifica suficientemente la contraparte estadounidense. | current_text |
| 16 | [Abrir noticia](https://foco.lanacion.com.py/2025/01/02/primera-industria-de-resina-de-almidon-de-mandioca-posicionara-al-paraguay/) | Excluir | Apoyo del Viceministerio de Mipymes a empaques sostenibles; sin contraparte de Estados Unidos en el texto. | current_text |
| 17 | [Abrir noticia](https://www.lanacion.com.py/futboledicion-impresa/2025/01/02/en-donde-seguira-richard-sanchez/) | Excluir | Posibles destinos y carrera de Richard Sánchez. | current_text |
| 18 | [Abrir noticia](https://www.lanacion.com.py/negocios/2025/01/02/dolar-arranco-el-ano-con-aumento-de-70-puntos/) | Excluir | Movimiento del dólar y mercado cambiario local, sin relación institucional PY–US. | current_text |
| 19 | [Abrir noticia](https://www.lanacion.com.py/tapa-lnpm/2025/01/02/ln-pm-edicion-del-2-de-enero/) | Incluir | Resumen multitemático con promoción presidencial ante empresarios estadounidenses; repite parcialmente el contenido de la nota 14. | current_text |
| 20 | [Abrir noticia](https://www.abc.com.py/deportes/futbol/internacional/2025/01/02/diego-gomez-necesita-un-poco-de-tiempo-antes-de-de-debutar-con-brighton-dice-su-tecnico/) | Excluir | Adaptación de Diego Gómez a Brighton tras jugar en Miami; carrera deportiva individual. | current_text |
| 21 | [Abrir noticia](https://www.abc.com.py/deportes/futbol/2025/01/02/2-de-mayo-largo-viaje-de-norte-a-este/) | Excluir | Pretemporada y plantel del club 2 de Mayo. | current_text |
| 22 | [Abrir noticia](https://www.abc.com.py/nacionales/2025/01/02/indi-seguira-sobre-artigas-pero-tendra-oficinas-en-otras-tres-ciudades/) | Excluir | Oficinas del Indi y comunidades indígenas paraguayas; Filadelfia se refiere a Boquerón, no prueba vínculo con US. | current_text |
| 23 | [Abrir noticia](https://www.lanacion.com.py/negocios/2025/01/02/the-banker-destaca-a-fernandez-valdovinos-como-el-ministro-de-finanzas-del-ano-en-america/) | Dudoso | Texto del mismo editor en CDN: premio The Banker y calificación de Moody’s; definir si calificación soberana privada integra el alcance institucional. | publisher_mirror |
| 24 | [Abrir noticia](https://www.lanacion.com.py/politica/2025/01/02/prieto-es-un-idolo-con-pie-de-barro-dice-sindicalista-ante-la-falta-de-pago-de-salarios/) | Excluir | Salarios municipales de Ciudad del Este y reclamo sindical; no vínculo con US. | current_text |
| 25 | [Abrir noticia](https://www.abc.com.py/deportes/futbol/2025/01/02/tembetary-garcia-guerreno-es-nuevo-nomada/) | Dudoso | Página inaccesible; URL deportiva, pero no se considera prueba suficiente de exclusión definitiva. | unavailable |
| 26 | [Abrir noticia](https://www.lanacion.com.py/negocios/2025/01/02/don-angel-el-toro-de-agroganadera-pukavy-elegido-como-mejor-macho-entre-todas-las-razas/) | Excluir | Premio internacional a toro de ganadería privada; sin relación institucional PY–US identificada. | current_text |
| 27 | [Abrir noticia](https://www.abc.com.py/deportes/motor/2025/01/03/dakar-2025-arabia-saudi-sainz-y-brabec-por-la-defensa-del-titulo/) | Excluir | Competidores del Dakar y ausencia de representación paraguaya; no cooperación bilateral. | current_text |
| 28 | [Abrir noticia](https://www.abc.com.py/opinion/2025/01/03/la-politica-de-carter-y-el-paraguay-de-stroessner/) | Incluir | Opinión sobre política de derechos humanos de Carter, Congreso de US, dictadura paraguaya y observación electoral. | current_text |
| 29 | [Abrir noticia](https://www.abc.com.py/politica/2025/01/03/gafilat-se-lava-las-manos-sobre-la-financiacion-de-reunion-en-su-nombre/) | Incluir | Financiación de Gafilat con referencia al abogado de Cartes ante Seprelad y sanción estadounidense; vínculo de contexto muy débil. | current_text |
| 30 | [Abrir noticia](https://www.ultimahora.com/cinco-discos-del-2024) | Excluir | Reseña de discos y artistas de diversos países; sin cooperación institucional. | current_text |
| 31 | [Abrir noticia](https://www.ultimahora.com/dolar-sube-70-puntos-a-la-venta-en-arranque-del-ano) | Excluir | Cotización del dólar e intervenciones del BCP; no relación bilateral institucional. | current_text |
| 32 | [Abrir noticia](https://www.lanacion.com.py/tapa-lnpm/2025/01/03/ln-pm-edicion-del-3-de-enero/) | Excluir | Resumen sobre Colombia/Pecci, becas, clima, 911 y salarios locales; sin vínculo estadounidense en el cuerpo. | current_text |
| 33 | [Abrir noticia](https://d10.ultimahora.com/el-pipa-benedetto-se-entrena-en-olimpia) | Excluir | Entrenamiento de Benedetto y plantel de Olimpia. | current_text |
| 34 | [Abrir noticia](https://d10.ultimahora.com/ofrecen-2-5-millones-por-oscar-romero-se-pondra-la-azulgrana) | Excluir | Ofertas por Óscar Romero entre clubes; no vínculo público bilateral. | current_text |
| 35 | [Abrir noticia](https://www.ultimahora.com/filtrado-ecologico-el-innovador-sistema-para-el-acceso-al-agua-segura-en-el-chaco) | Excluir | Agua en el Chaco: cooperación BID y agencia española; BID no se imputa a Estados Unidos por su sede. | current_text |
| 36 | [Abrir noticia](https://www.abc.com.py/deportes/futbol/2025/01/03/intensa-primera-jornada-en-olimpia/) | Dudoso | URL inaccesible; solo localización de un resumen secundario deportivo, insuficiente para cerrar lectura. | unavailable |
| 37 | [Abrir noticia](https://www.lanacion.com.py/negocios/2025/01/03/migraciones-registro-record-en-movimiento-fronterizo-en-diciembre-del-2024/) | Excluir | Migraciones describe flujos con Argentina y Brasil; no relación con Estados Unidos. | current_text |
| 38 | [Abrir noticia](https://www.lanacion.com.py/negocios/2025/01/03/mundial-de-rally-en-paraguay-aguarda-recibir-a-mas-de-250000-visitantes/) | Excluir | Organización turística del rally con autoridades paraguayas; sin contraparte estadounidense identificable. | current_text |
| 39 | [Abrir noticia](https://listindiario.com/las-mundiales/20250101/republica-dominicana-paises-dominio-ingles-latinoamerica_839706.html) | Excluir | Listín Diario: sede editorial en República Dominicana; fuera de países fuente. | country_only |
| 40 | [Abrir noticia](https://www.nytimes.com/athletic/6014938/2025/01/01/premier-league-transfer-players-needing-move/) | Dudoso | No se recuperó el artículo de The Athletic; no excluir definitivamente solo por URL. | unavailable |
| 41 | [Abrir noticia](https://www.syracuse.com/tv/2025/01/how-to-watch-brentford-vs-arsenal-time-tv-schedule-free-live-stream-for-premier-league-matchday-19.html) | Excluir | Guía para ver un partido inglés y crónica futbolística; menciones de jugadores y televisión. | current_text |
| 42 | [Abrir noticia](https://www.alabamawx.com/?p=274129) | Dudoso | No se recuperó el documento por identificador; el sitio raíz ha cambiado de dominio. | unavailable |
| 43 | [Abrir noticia](https://www.univision.com/noticias/salud/cambio-climatico-contribuye-casos-record-dengue-americas-caribe-2024) | Excluir | Panorama regional del dengue; Paraguay y Estados Unidos aparecen en estadísticas separadas, sin relación bilateral. | current_text |
| 44 | [Abrir noticia](https://eturbonews.com/brazil-swears-first-female-president/) | Excluir | Asunción presidencial brasileña: US y Paraguay se relacionan separadamente con Brasil. Texto fechado en 2011. | search_full_text |
| 45 | [Abrir noticia](https://wtop.com/world/2024/12/ap-photos-a-river-route-for-food-and-crime-the-dual-nature-of-a-major-south-american-waterway/) | Dudoso | WTOP devuelve 404. Versión AP homónima no muestra vínculo bilateral, pero no se verificó identidad íntegra de la copia WTOP. | syndicated_alternative |
| 46 | [Abrir noticia](https://www.nytimes.com/athletic/6029646/2025/01/02/diego-gomez-brighton-the-athletic-500-rating/) | Dudoso | No se recuperó el texto de The Athletic sobre Diego Gómez. | unavailable |
| 47 | [Abrir noticia](https://www.foodonline.com/doc/hb-a-path-to-mitigating-drought-0001) | Excluir | Aprobaciones regulatorias de trigo HB4 enumeradas por país; no se describe interacción institucional PY–US. | current_text |
| 48 | [Abrir noticia](https://www.thegardenisland.com/2025/01/02/hawaii-news/hawaiian-electric-delivers-answers-to-puc-probe/) | Dudoso | Texto visible sobre incendio de Maui, seguido de acceso restringido; Asuncion es apellido. No se verificó el artículo íntegro. | partial_text |
| 49 | [Abrir noticia](https://www.diariolasamericas.com/mundo/los-paises-mas-dominio-del-ingles-la-region-n5368984) | Excluir | Ranking de dominio del inglés; idioma inglés no equivale a relación con instituciones estadounidenses. | current_text |
| 50 | [Abrir noticia](https://www.themarketsdaily.com/2025/01/02/bitfarms-nasdaqbitf-shares-up-8-1-time-to-buy.html) | Dudoso | Página de Bitfarms inaccesible; no se infiere su contenido institucional desde el título. | unavailable |
| 51 | [Abrir noticia](https://www.travelmarketreport.com/destinations/articles/costa-rica-changes-yellow-fever-vaccination-requirements) | Excluir | Requisitos de ingreso de Costa Rica para viajeros procedentes de varios países; no relación institucional PY–US. | current_text |
| 52 | [Abrir noticia](https://mlsmultiplex.com/club-america-could-lose-richard-sanchez-to-fc-cincinnati-01jgm2kse8zv) | Excluir | Posible transferencia de Richard Sánchez a Cincinnati; carrera de futbolista. | current_text |
| 53 | [Abrir noticia](https://mlsmultiplex.com/miguel-almiron-in-mls-charlotte-fc-goes-big-chasing-the-impossible-01jgm21gxznq) | Excluir | Posible fichaje de Miguel Almirón por Charlotte; relación entre clubes y jugador. | current_text |
| 54 | [Abrir noticia](https://www.santacruzsentinel.com/2025/01/02/tom-karwin-on-gardening-winter-plants-that-prep-for-spring-blossoms/) | Dudoso | No se pudo leer la columna de jardinería; pendiente, sin descartar solo por URL. | unavailable |
| 55 | [Abrir noticia](https://listindiario.com/la-republica/educacion/20250102/como-sido-desempeno-pais-dominio-ingles-ultimos-4-anos_839851.html) | Excluir | Listín Diario: fuente dominicana, no estadounidense. | country_only |
| 56 | [Abrir noticia](https://www.surysur.net/una-inversion-china-modifica-la-geopolitica-de-sudamerica/) | Excluir | Análisis China–Perú y US–Argentina; Paraguay aparece en el nombre de una hidrovía, sin contraparte institucional paraguaya. | current_text |
| 57 | [Abrir noticia](https://dominicanrepublicpost.com/como-ha-sido-el-desempeno-de-republica-dominicana-en-dominio-del-ingles-durante-los-ultimos-4-anos/) | Dudoso | Texto no recuperado y sede editorial no verificada; nombre del dominio no prueba país. | unavailable |
| 58 | [Abrir noticia](https://volcanoes.usgs.gov/hans-public/notice/DOI-USGS-NMI-2025-01-02T21:51:17+00:00) | Dudoso | Aviso del USGS no recuperado; fuente gubernamental, no medio periodístico. Mantener pendiente de regla sobre fuentes oficiales. | unavailable |
| 59 | [Abrir noticia](https://listverse.com/2025/01/02/10-nazi-war-criminals-who-fled-to-latin-america-after-wwii/) | Excluir | Perfiles de criminales nazis; detención por estadounidenses y paso por Paraguay no describen relación institucional bilateral. | current_text |
| 60 | [Abrir noticia](https://www.flcourier.com/news/busy-and-full-highlights-of-carter-s-life/article_f87a7faa-c9a7-11ef-822b-3b189807ea5f.html) | Dudoso | Cronología de Carter inaccesible; podría contener actividad institucional, no excluir por nombre propio. | unavailable |
| 61 | [Abrir noticia](https://www.insidermonkey.com/blog/is-bitfarms-ltd-bitf-among-the-best-long-term-penny-stocks-to-buy-according-to-hedge-funds-1417852/) | Excluir | Análisis bursátil de Bitfarms con instalaciones en varios países; sin relación institucional entre Paraguay y US. | current_text |
| 62 | [Abrir noticia](https://www.telesurtv.net/opinion/45-festival-internacional-del-nuevo-cine-latinoamericano/) | Excluir | teleSUR: sede central verificada en Caracas, Venezuela; no se recuperó el artículo, exclusión por fuente. | country_only |
| 63 | [Abrir noticia](https://www.yahoo.com/news/earth-tilt-creates-short-cold-150303724.html) | Excluir | Divulgación astronómica, sin relación institucional bilateral. | search_full_text |
| 64 | [Abrir noticia](https://www.coindesk.com/markets/2025/01/03/how-chinese-lending-firm-cango-became-a-bitcoin-mining-powerhouse) | Excluir | Operaciones mineras de Cango/Bitmain en distintos países; sin relación institucional PY–US. | current_text |
| 65 | [Abrir noticia](https://www.ajot.com/news/msc-announcement-fee-updates) | Excluir | Aviso de tarifas privadas de MSC para rutas que incluyen Paraguay–US; no arancel estatal ni cooperación pública. | current_text |
| 66 | [Abrir noticia](https://latinamericanpost.com/analysis-en/jimmy-carters-latin-american-legacy-is-his-brightest-achievement/) | Dudoso | Contenido institucional pertinente sobre Carter y elecciones paraguayas; sede editorial de LatinAmerican Post no verificada. | current_text |
| 67 | [Abrir noticia](https://www.vavel.com/en-us/nba/2025/01/04/1208934-atlanta-hawks-vs-los-angeles-lakerslivescore-updates-stream-info-and-how-to-watch-nba-match.html) | Dudoso | URL de enero redirige a crónica NBA de noviembre de 2025; no se validó el documento observado en el piloto. | changed_redirect |

## Catálogo inicial de fuentes

31 dominios observados: **16 con país verificado, 5 con evidencia histórica
que requiere revalidación y 10 sin confirmar**. Incluye subdominios:
no equivale a 31 propietarios editoriales independientes.

Los 16 verificados tienen evidencia primaria suficiente para esta primera
revisión; no se acredita con ello continuidad de sede durante 2015–2026.
Ninguna entrada tiene un intervalo longitudinal de vigencia establecido.
Los enlaces fallidos figuran como intentos, no como pruebas.

Listín Diario y teleSUR estaban asignados a US y quedan fuera por sus sedes
en República Dominicana y Venezuela. No extender automáticamente la corrección
a medios distintos ni eliminar registros originales.

| Dominio | GDELT | País verificado | Estado | Evidencia / limitación |
| --- | --- | --- | --- | --- |
| lanacion.com.py | PY | PY | verified | [Evidencia o intento](https://www.lanacion.com.py/negocios_edicion_impresa/2022/05/25/desde-hace-27-anos-fortaleciendo-la-democracia-de-nuestra-nacion/) — Historia del editor: diario paraguayo en Fernando de la Mora; identifica al grupo Nación Media. |
| ultimahora.com | PY | PY | verified | [Evidencia o intento](https://www.ultimahora.com/filtrado-ecologico-el-innovador-sistema-para-el-acceso-al-agua-segura-en-el-chaco) — Pie editorial: Benjamín Constant 658, Asunción. |
| abc.com.py | PY | PY | verified | [Evidencia o intento](https://www.abc.com.py/nacionales/2025/01/02/indi-seguira-sobre-artigas-pero-tendra-oficinas-en-otras-tres-ciudades/) — Pie editorial: Editorial AZETA, Yegros 745, Asunción, Paraguay. |
| d10.ultimahora.com | PY | PY | verified | [Evidencia o intento](https://d10.ultimahora.com/pretemporada-en-el-este) — Pie editorial identifica D10.ULTIMAHORA.COM, Asunción, Paraguay. |
| foco.lanacion.com.py | PY | PY | verified | [Evidencia o intento](https://www.lanacion.com.py/negocios_edicion_impresa/2022/05/25/desde-hace-27-anos-fortaleciendo-la-democracia-de-nuestra-nacion/) — Historia del editor identifica a Foco dentro de Nación Media; contacto de Foco confirma mismo editor. |
| listindiario.com | US | DO | verified | [Evidencia o intento](https://listindiario.com/aviso-legal.html) — Aviso legal ubica al editor en Santo Domingo, República Dominicana; contradice GDELT US. |
| nytimes.com | US | US | verified | [Evidencia o intento](https://www.sec.gov/Archives/edgar/data/71691/000007169126000003/0000071691-26-000003-index.htm) — Declaración corporativa ante SEC: dirección del editor en Nueva York. No prueba sede de cada corresponsal. |
| syracuse.com | US | US | verified | [Evidencia o intento](https://www.advancemediany.com/wp-content/uploads/2019/10/Birth-form_2019.pdf) — Documento del editor para Syracuse.com/The Post-Standard: dirección Syracuse, Nueva York. |
| alabamawx.com | US | Sin confirmar | unverified | [Evidencia o intento](https://alabamaweathernetwork.com/) — Raíz redirige a Alabama Weather Network, con dirección en Birmingham US. Falta validar continuidad del editor de enero 2025. |
| univision.com | US | Sin confirmar | historical_evidence | [Evidencia o intento](https://corporate.televisaunivision.com/press/2017/11/06/univision-news-appoints-john-b-perez-svp-production-technical-operations/amp/) — Comunicado propio ubica operaciones de Univision News en Doral, Florida (2017); comprobar continuidad en 2025. |
| eturbonews.com | US | Sin confirmar | historical_evidence | [Evidencia o intento](https://eturbonews.com/why-etn-corporation-joined-the-caribbean-tourism-organization-this-week/) — Editor declara sede central en Hawaii (2018), con oficinas internacionales; comprobar continuidad en 2025. |
| wtop.com | US | US | verified | [Evidencia o intento](https://wtop.com/privacy-policy/) — Pie propio: Chevy Chase, Maryland. No confundir sede de AP con editor WTOP. |
| foodonline.com | US | Sin confirmar | unverified | [Evidencia o intento](https://www.foodonline.com/doc/hb-a-path-to-mitigating-drought-0001) — Identifica editor/controlador Life Science Connect, pero no se verificó sede; contacto no recuperado. |
| thegardenisland.com | US | US | verified | [Evidencia o intento](https://www.thegardenisland.com/2025/01/02/hawaii-news/hawaiian-electric-delivers-answers-to-puc-probe/) — Pie del medio: Lihue, Hawaii. |
| diariolasamericas.com | US | US | verified | [Evidencia o intento](https://www.diariolasamericas.com/contacto) — Contacto editorial en Miami, Florida, Estados Unidos. |
| themarketsdaily.com | US | Sin confirmar | unverified | [Evidencia o intento](https://www.themarketsdaily.com/contact) — Página de contacto no recuperada; no inferir país desde temática bursátil. |
| travelmarketreport.com | US | US | verified | [Evidencia o intento](https://www.travelmarketreport.com/destinations/articles/costa-rica-changes-yellow-fever-vaccination-requirements) — Pie propio: Oyster Bay, Nueva York; American Marketing Group. |
| mlsmultiplex.com | US | Sin confirmar | historical_evidence | [Evidencia o intento](https://fansided.com/2017/03/13/hiring-jr-editor-launch-team/) — Sitio identifica pertenencia a FanSided; publicación de 2017 ubica sede editorial en Chicago. Revalidar en 2025. |
| santacruzsentinel.com | US | Sin confirmar | unverified | [Evidencia o intento](https://www.santacruzsentinel.com/) — Acceso y búsqueda no aportaron evidencia editorial verificable en esta revisión; no negar por ello su posible origen US. |
| surysur.net | US | Sin confirmar | unverified | [Evidencia o intento](https://www.surysur.net/una-inversion-china-modifica-la-geopolitica-de-sudamerica/) — Artículo accesible, pero sin sede editorial verificable; no asignar US por catálogo heredado. |
| dominicanrepublicpost.com | US | Sin confirmar | unverified | [Evidencia o intento](https://dominicanrepublicpost.com/about-us/) — Acceso fallido; dominio alusivo a República Dominicana no basta para asignar país. |
| volcanoes.usgs.gov | US | US | verified | [Evidencia o intento](https://www.usgs.gov/) — US Geological Survey, organismo del Departamento del Interior estadounidense. Tipo fuente gubernamental, no prensa. |
| listverse.com | US | Sin confirmar | unverified | [Evidencia o intento](https://listverse.com/about-listverse/) — Página propia describe equipo internacional sin sede clara; propiedad/autor no equivalen a país editorial. |
| flcourier.com | US | Sin confirmar | unverified | [Evidencia o intento](https://www.flcourier.com/site/contact.html) — Contacto no recuperado; pendiente verificación documental del editor. |
| insidermonkey.com | US | US | verified | [Evidencia o intento](https://www.insidermonkey.com/contact-us/) — Contacto propio en Nueva York. |
| telesurtv.net | US | VE | verified | [Evidencia o intento](https://www.telesurtv.net/sobre-nosotros/) — Historia propia y noticia de aniversario de julio 2025 identifican sede central Caracas; medio multinacional, no US. |
| yahoo.com | US | Sin confirmar | historical_evidence | [Evidencia o intento](https://downloads.regulations.gov/COLC-2015-0013-86026/attachment_1.pdf) — Escrito del propio Yahoo ante autoridad US identifica sede en Sunnyvale; evidencia histórica, no edición territorial específica. |
| coindesk.com | US | Sin confirmar | historical_evidence | [Evidencia o intento](https://downloads.coindesk.com/research/state-of-blockchain/2018/q2/sob2018q2-2018.pdf) — Informe propio de 2018 identifica sede Nueva York; comprobar continuidad y distinguir filiales internacionales. |
| ajot.com | US | US | verified | [Evidencia o intento](https://www.ajot.com/news/msc-announcement-fee-updates) — Pie del American Journal of Transportation en Plymouth, Massachusetts. |
| latinamericanpost.com | US | Sin confirmar | unverified | [Evidencia o intento](https://latinamericanpost.com/contact-us/) — Contacto y About Us identifican Globsa.org, sin sede editorial. No asignar US ni Colombia por temas. |
| vavel.com | US | Sin confirmar | unverified | [Evidencia o intento](https://www.vavel.com/en-us/staff.html) — Edición USA con equipo internacional; /en-us no acredita una sede estadounidense. |

## Próximo uso del código

- Guardar candidatos una sola vez y aplicar revisiones localmente.
- Usar esta clasificación como conjunto de desarrollo, no de prueba independiente.
- Validar reglas en otra muestra antes de escalar; no descargarla sin estimación
  y autorización del periodo y límite.
- No reemplazar el filtro de coaparición por un diccionario extraído de nueve
  positivos: excluiría relaciones que este piloto no contiene.
- Para deduplicación distinguir URL repetida, republicación y mismo hecho.
  Las noticias distintas sobre un mismo hecho sí aportan cobertura mediática.
- No recalcular relevancia normalizada con denominadores del catálogo antiguo
  mientras el numerador usa países corregidos.
- El tono GDELT del artículo completo no equivale a sentimiento hacia el vínculo
  bilateral; particularmente problemático en resúmenes como la nota 19.
- No se cambió SQL ni se incorporó este catálogo parcial como lista blanca:
  hacerlo ahora podría perder medios pertinentes.

Archivos de trabajo: classification_v1.json y media_catalogue_v1.json en
output/gdelt/review. pilot_review.json conserva la primera fase y sus
totales provisionales; no debe confundirse con esta revisión.

Verificación local, sin red ni Google Cloud:

```powershell
.\.venv\Scripts\python.exe validate_pilot_review.py
```

