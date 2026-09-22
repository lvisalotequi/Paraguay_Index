# mre_scraping — noticias del Ministerio de Relaciones Exteriores de Paraguay (2015–2025)

Actualizado: 2026-09-22. Adaptado al proyecto a partir de un scraper que el
usuario trajo ya armado y probado (`mre_eeuu_scraper_portable.zip`) — ver
`git log` de este archivo para el origen. Documenta solo los cambios hechos
para integrarlo; el diseño original está en `CONTEXTO_ORIGINAL.md`.

## Qué es

Descarga noticias públicas del archivo del MRE de Paraguay
(`mre.gov.py/archivo-de-noticias/`), combina el archivo actual con capturas
históricas de Wayback Machine (para cubrir noticias de antes de que existiera
el archivo actual), y cuenta/clasifica menciones a Estados Unidos con reglas
explícitas — **sin IA**: la misma copia de las páginas y la misma
configuración producen siempre el mismo resultado, igual que el resto del
proyecto.

Alimenta la dimensión `2_Actividad_gubernamental_y_diplomatica` — es la
contraparte, del lado paraguayo, de fuentes como `ustr_consejo_comercio_inversion.py`
y `congreso_menciones_paraguay.py` (que miden actividad diplomática/legislativa
desde el lado de EE.UU.): acá se mide cuánto y en qué noticias la propia
Cancillería paraguaya reporta actividad vinculada a EE.UU.

## Por qué corre acá y no en `src/ingestion/`

Igual que `gdelt_extraction/` (ver `CLAUDE.md` sección 4, excepción
documentada): **este proceso no es una llamada liviana a una API**, es un
scraping largo con caché local en disco y checkpoint reanudable — la
recolección completa 2015-2025 tarda **horas**, no minutos (índice CDX de
Wayback + descarga individual de cada noticia con demora entre pedidos para
no saturar el sitio). No tiene sentido correrlo en GitHub Actions. Por eso
corre a mano, localmente, y `src/ingestion/mre_menciones_eeuu.py` (fuera de
esta carpeta) solo sube a Drive lo que esta carpeta ya produjo — mismo patrón
que `gdelt_proxy_b.py` con `gdelt_extraction/`.

## Cambio hecho para integrarlo (2026-09-22): bypass de Cloudflare

El sitio actual (`mre.gov.py`) devuelve **403 Forbidden** con `requests`
normal (bloqueo por huella TLS, no por headers) — confirmado al correr el
scraper tal como venía. Es el mismo bloqueo que ya tienen `bcp.gov.py` y
`state.gov` en este proyecto. Se corrigió con el mismo workaround que ya usa
el resto del proyecto: `curl_cffi` con `impersonate="chrome"` en la clase
`Fetcher` de `scraper_mre.py` (antes usaba `requests` normal). Verificado:
`https://www.mre.gov.py/archivo-de-noticias/` pasó de 403 a 200 con el
cambio. Sin este cambio, el archivo *actual* del MRE quedaba inaccesible y
la cobertura dependía 100% de lo que Wayback llegó a archivar (las noticias
más recientes, todavía no archivadas, se hubieran perdido).

**Bug real encontrado al cambiar de librería (2026-09-22, corregido):** el
manejo de errores de `Fetcher.get()` capturaba `requests.RequestException` -
ese nombre existe en la librería `requests` normal, pero `curl_cffi.requests`
no lo expone al mismo nivel (queda en `requests.exceptions.RequestException`).
Con el cambio de import, un timeout real de red terminaba en un
`AttributeError` sin manejar en vez de reintentar como estaba pensado -
apareció en la práctica al correr el scraping completo (un timeout de 45s
contra el índice CDX de Wayback tumbó el proceso entero). Corregido
cambiando la excepción capturada a `requests.exceptions.RequestException`.
Verificado con un caso forzado (URL inválida) que ahora sí levanta
`RuntimeError` de forma controlada, como está diseñado.

## ⚠️ Correr desde una ruta corta, no desde esta carpeta del repo

La carpeta de este repo dentro de la Unidad compartida es muy larga (~190
caracteres, ver `CLAUDE.md` sección 5, "Windows: rutas largas") — sumada a
la caché de este scraper (un archivo `.html` + `.json` por noticia, con
nombre hash de 64 caracteres) se supera fácil el límite de 260 caracteres de
Windows. **Confirmado en la práctica (2026-09-22): ni siquiera arrancó
`python3` desde una ruta de prueba ya larga.** La corrida real (2015-2025) se
hizo copiando estos mismos archivos a una ruta corta (`C:\mre_scraping\` o
similar) y corriendo desde ahí — el código versionado en el repo es el
mismo, solo cambia dónde se ejecuta. Ver la sección "Windows: rutas largas"
de `CLAUDE.md` para las dos soluciones (ruta corta, o habilitar
`LongPathsEnabled`).

## ⏳ Corrida en curso (2026-09-22) — estado para retomar si se corta la sesión

Hay una corrida completa 2015-2025 corriendo **en background, fuera del
repo**, en `C:\mre_test\` (ruta corta, ver la sección de arriba sobre por
qué no corre desde esta carpeta). Arrancó 2026-09-22 ~08:57. Datos para
retomar el seguimiento:

- **Log**: `C:\mre_test\corrida_completa.log`
- **Salida**: `C:\mre_test\salida_2015_2025\` (checkpoint.ndjson se puede
  inspeccionar en cualquier momento, aunque el proceso siga corriendo)
- **Progreso a las 10:20**: 2.700 de 9.304 URLs procesadas (~29%), ritmo
  estable de ~100 cada 2-3 min → estimado **~3-4 horas más** desde ese
  momento. Errores puntuales (algunos 404 de Wayback, algún corte de DNS
  momentáneo) son esperados y no frenan la corrida - ver "Limitaciones
  conocidas" más abajo.
- **Cómo confirmar si ya terminó**: `tail` del log busca la línea
  `INFO Listo: C:\mre_test\salida_2015_2025` (o revisar si el proceso
  python3 con ese PID ya no existe).

**Pasos que faltan una vez termine** (nada de esto se hizo todavía):
1. Correr `clasificar_bilateral.py --entrada C:\mre_test\salida_2015_2025\noticias_todas.csv --salida <carpeta>` desde `C:\mre_test\` (con el código YA parcheado ahí, mismo bypass y fix que en este repo).
2. Copiar `noticias_clasificadas.csv` y `C:\mre_test\salida_2015_2025\manifiesto.json` a `mre_scraping/output/` (dentro del repo).
3. Correr `src/ingestion/mre_menciones_eeuu.py` (sube a Drive).
4. Correr `src/processing/actividad_gubernamental_y_diplomatica.py` (genera `mre_noticias_bilaterales`/`mre_menciones_totales_eeuu`).
5. Verificar con recálculo independiente (mismo patrón que toda otra variable de esta sesión) y recién ahí marcar como Validado en `README.md`/`DICCIONARIO_VARIABLES.md`.

## Cómo correrlo

```powershell
cd C:\alguna-ruta-corta\mre_scraping   # copiar esta carpeta ahi antes, ver arriba
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest -v
```

Piloto rápido:

```powershell
.\.venv\Scripts\python.exe scraper_mre.py --desde 2024 --hasta 2025 --limite 10 --max-paginas-actual 1 --salida salida_piloto --cache cache
```

Corrida completa (tarda horas; `checkpoint.ndjson` permite reanudar si se corta):

```powershell
.\.venv\Scripts\python.exe scraper_mre.py --desde 2015 --hasta 2025 --salida salida_2015_2025 --cache cache --demora 1.5
```

Clasificación bilateral (después de que termine la recolección):

```powershell
.\.venv\Scripts\python.exe clasificar_bilateral.py --entrada salida_2015_2025\noticias_todas.csv --salida salida_bilateral_2015_2025
```

Esto genera `noticias_clasificadas.csv` y `resumen_bilateral_mensual.csv` —
esos dos archivos (más `manifiesto.json`) son los que sube
`src/ingestion/mre_menciones_eeuu.py`. Copiarlos a esta carpeta
(`mre_scraping/output/`, ver `.gitignore`) antes de correr esa fuente.

## Qué entrega (sin cambios respecto al diseño original)

- `noticias_todas.csv`: fecha, mes, título, descripción, texto completo,
  URLs, fuente, estado de extracción y conteo de menciones — una fila por
  noticia recolectada.
- `noticias_clasificadas.csv` (de `clasificar_bilateral.py`): lo anterior
  más `es_bilateral`, `puntaje_bilateral`, `nivel_relevancia` ("sin mención"
  / "mención simple" / "bilateral" / "bilateral de peso"), `tipo_relacion`,
  y la evidencia textual de cada clasificación.
- `resumen_bilateral_mensual.csv`: por mes, cuántas noticias válidas,
  menciones simples, bilaterales y bilaterales de peso.
- `manifiesto.json`: parámetros de la corrida, controles de calidad, conteos
  totales — para poder auditar que una corrida no se dio por completa con
  bloqueos o meses vacíos sin avisar.

## Reglas de clasificación (sin IA, ver `reglas_bilaterales.json`)

Puntaje por señales explícitas (mención de EE.UU., de Paraguay, acción
bilateral, instrumento/acuerdo, actor de alto nivel, área sustantiva),
penalización si la única señal es multilateral (Mercosur/OEA/ONU) sin
evidencia bilateral adicional, y un chequeo de "núcleo próximo" (EE.UU. y
Paraguay mencionados dentro de una ventana de ~350 caracteres junto con una
acción bilateral) antes de confirmar `es_bilateral`. Umbral de bilateralidad
y de "peso alto" configurables en el propio JSON. 10 tests de regresión
(`test_scraper_mre.py`, `test_clasificar_bilateral.py`) cubren los casos
límite (mención incidental, mención lejana, multilateral sin interacción,
Emiratos Árabes Unidos vs. Estados Unidos).

## Limitaciones conocidas (heredadas del diseño original + lo encontrado en la corrida real)

- Wayback no garantiza haber archivado todas las páginas — el conteo mide
  noticias recuperables, no necesariamente la producción histórica completa
  del MRE.
- Una de las cuatro consultas al índice CDX de Wayback
  (`www2.mre.gov.py/index.php/noticias`) falló con un error de JSON mal
  formado en la corrida de prueba (2026-09-22) — no frena la corrida (las
  otras tres consultas sí funcionan), pero es cobertura parcial a tener en
  cuenta si los conteos de algún período parecen bajos.
- El conteo es textual y reproducible; no mide si el tono de la mención es
  favorable o crítico (mismo principio que ya aplica el proyecto en
  `congreso_menciones_paraguay.py` — ver `DICCIONARIO_VARIABLES.md`).
