# Estado de `04_construccion_indice.qmd`

Contexto para retomar el trabajo desde cualquier máquina. Última actualización:
2026-09-13.

Este archivo describe el documento de construcción del índice: qué es, cómo se
corre, qué convenciones sigue, qué está decidido y qué falta. **No reemplaza al
`.qmd`**, que es la fuente de verdad de cada decisión con su evidencia.

---

## 1. Qué es y por qué existe

`src/04_analysis_index/04_construccion_indice.qmd` construye el US-PY Engagement
Index siguiendo los diez pasos del *Handbook on Constructing Composite Indicators*
de la OCDE/JRC, desarrollados en trece etapas.

Es un documento **nuevo y separado** de `04_analysis_index.qmd`, que sigue en el
repo pero cuyo contenido el usuario invalidó como decisión: aquel había elegido
métodos sin evaluar sistemáticamente las alternativas, que es justamente lo que
este corrige. No se lo debe usar como referencia ni citar en el documento nuevo.

Archivos que lo componen:

| Archivo | Rol |
|:--|:--|
| `04_construccion_indice.qmd` | El documento. Fuente de verdad. |
| `estilo_documento.css` | Hoja de estilos: ancho de página, jerarquía del TOC, tablas. |
| `_cache_*.csv` | Caches locales de los insumos externos. **Ignorados por git**, se regeneran solos. |

---

## 2. Cómo se renderiza

Quarto no se instala con pip: viene con Positron. **Usar `quarto.exe`, nunca
`quarto.cmd`** — el `.cmd` devuelve exit 0 sin generar nada.

```bash
cd "<raiz del repo>"
export QUARTO_PYTHON="$(py -c 'import sys; print(sys.executable)')"
"C:/Users/piero/AppData/Local/Programs/Positron/resources/app/quarto/bin/quarto.exe" \
  render "src/04_analysis_index/04_construccion_indice.qmd" --to html
```

En otra máquina la ruta de Positron cambia; el resto es igual. El puente jupyter
de Quarto necesita `pyyaml`, `ipykernel`, `nbclient` y `nbformat` en el intérprete.

### Insumos externos y caches

El documento descarga tres cosas y las guarda en cache local. En una máquina nueva
los caches no existen y se regeneran en el primer render, que por eso tarda más y
**exige credenciales de Drive e internet**.

| Cache | Origen | Qué trae |
|:--|:--|:--|
| `_cache_panel_integracion.csv` | Drive, `03_integracion/panel_trimestral_largo.csv` | El panel de 12 series × 48 trimestres |
| `_cache_ipc_eeuu.csv` | API pública de BLS, serie `CUUR0000SA0` | IPC mensual de EE.UU. para deflactar |
| `_cache_paraguay_escala.csv` | API del Banco Mundial, `SP.POP.TOTL` y `NY.GDP.MKTP.CD` | Población y PBI de Paraguay |

**Cuidado con los caches**: si un script auxiliar los escribe con otra forma de
columnas, el documento falla. Ya ocurrió dos veces. Ante un `KeyError` extraño en
el setup, borrar el cache y dejar que se regenere.

Los dos insumos externos (IPC, población/PBI) son una solución provisoria
declarada en el propio documento: lo que corresponde es incorporarlos como fuentes
de `src/ingestion/` con su archivo versionado en Drive.

---

## 3. Convenciones obligatorias

Estas convenciones surgieron de correcciones explícitas del usuario. Respetarlas.

### Estructura de cada etapa

1. **Tabla "Qué resuelve esta etapa"**: una fila por pregunta, con la decisión que
   produce. Funciona como mapa.
2. **Un apartado numerado por pregunta** (`## N.1 · Título`), y dentro de él, en
   este orden:
   - `### En qué consiste` — las técnicas disponibles **para esa pregunta y nada
     más**. Ninguna se descarta antes de explicarse.
   - `### Qué muestran los datos` — la evidencia aplicada.
   - El callout de decisión.
3. **`## Resumen de las decisiones de la etapa`** con el bloque `registrar_decision`.
4. Callout de cierre.

Lo que **no** se debe hacer: agrupar todas las explicaciones al inicio, toda la
evidencia después y todas las decisiones al final. Esa era la estructura original
en tres fases y el usuario la rechazó porque obliga a recordar seis técnicas a lo
largo de muchas páginas.

### Redacción

- **Tercera persona impersonal.** Nada de segunda persona ni de dirigirse al lector.
- **Oraciones completas**, no frases telegráficas ni fragmentos sin verbo.
- **Cada decisión lleva su justificación en la misma oración**: `**Se decide** X,
  **porque** Y`. Los párrafos de `**Se descarta**` explican las alternativas, no
  la elección.
- **Cero conocimiento previo asumido**: cada prueba y cada término se explican en
  lenguaje llano antes de aparecer en el código.
- **No mencionar el análisis anterior** ni compararse con él.
- Comentarios de código sin tildes; la prosa del documento sí lleva tildes.

### Código

Sigue el estilo del usuario: pasos numerados que reescriben el objeto, un
comentario sobre cada asignación, un argumento por línea, sufijos consistentes y
bloque de validación al final de cada tramo. Todos los parámetros declarados en el
bloque de configuración, nunca dispersos.

### Verificación

**Toda cifra citada en la prosa debe coincidir con lo que imprime el código.** Ya
hubo varios desfases detectados y corregidos. Después de cada render conviene
extraer las salidas del HTML y contrastarlas contra el texto.

---

## 4. Alcance y datos

El análisis parte del panel de `03_integracion`: **12 series × 48 trimestres**,
que operacionalizan **8 indicadores** de los 16 del marco conceptual.

| Indicador | Series |
|:--|:--|
| Asistencia oficial de EE.UU. | `fa_gov_obligaciones`, `fa_gov_desembolsos` |
| Gasto federal ejecutado | `usaspending_obligaciones` |
| Atención legislativa del Congreso | `congreso_proyectos_relevantes_paraguay` |
| Tratados bilaterales vigentes | `state_gov_tias_vigentes` |
| Comercio bilateral de bienes | `exportaciones`, `importaciones` |
| Remesas familiares | `remesas` |
| Volumen de cobertura | `gdelt_proxy_articles_py`, `gdelt_proxy_articles_us` |
| Tono de la cobertura | `gdelt_tone_promedio_py`, `gdelt_tone_promedio_us` |

**Ventana de análisis: 2015-Q1 a 2026-Q1, 45 trimestres, sin ninguna casilla
faltante.** El extremo lo fija la extracción por lote de GDELT, no el rezago de
publicación.

### El constructo

El índice mide la **fortaleza del vínculo** con **dirección interpretable**: un
valor más alto significa un relacionamiento más denso y en mejores términos.

Esta definición fue **corregida por el usuario** el 2026-09-11. La versión previa
decía que el índice medía "intensidad y no calidad", y eso resultó erróneo.
Cualquier texto que reintroduzca esa formulación está mal.

---

## 5. Estado por etapa

| Etapa | Estado |
|:--|:--|
| 0 · Configuración | Completa |
| 1 · Marco teórico y registro | Completa |
| 2 · Selección de datos | Completa |
| 3 · Datos faltantes | Completa |
| 4 · Exploración descriptiva | Completa |
| 5 · Transformación | Completa |
| 6 · Consistencia interna | Completa |
| 7 · Normalización | Completa, con **una decisión pendiente del usuario** (ver §7) |
| 8 · Ponderación | **Pendiente** |
| 9 · Agregación | Pendiente |
| 10 · Sensibilidad y robustez | Pendiente |
| 11 · Retorno a los datos | Pendiente |
| 12 · Vínculos externos | Pendiente |
| 13 · Resultados y comunicación | Pendiente |

Al cierre de la Etapa 7 el panel está normalizado: media 100 y desvío 10 sobre el
período de referencia, con un recorrido de 68,5 a 143,8.

---

## 6. Las 31 decisiones tomadas

| # | Decisión |
|:--|:--|
| 0.1 | El análisis parte del panel de `03_integracion`, no de `02_limpias` |
| 1.1 | El índice se trata como modelo formativo |
| 1.2 | Las cuatro dimensiones integran el análisis; la ponderación se resuelve en la Etapa 8 |
| 1.3 | El registro de decisiones es una tabla estructurada dentro del documento |
| 2.1 | Las doce series avanzan; ninguna se excluye por redundancia ni por cobertura |
| 2.2 | El alcance queda declarado como parcial: 8 de 16 indicadores del marco |
| 2.3 | El inventario de derivados queda abierto hasta la Etapa 6 |
| 3.1 | No se aplica ninguna imputación estadística ni interpolación |
| 3.2 | Las series de hechos con fecha reciben ceros hasta el límite de cobertura de su fuente |
| 3.3 | Las series de nivel publicado conservan sus vacíos; excepción: cabecera del stock de tratados |
| 4.1 | La desviación absoluta mediana es el método de referencia para atípicos |
| 4.2 | Los trimestres del año fiscal en curso se marcan como incompletos |
| 4.3 | Ventana 2015-Q1 a 2026-Q1, conservando las doce series |
| 4.4 | El último trimestre de la ventana se publica marcado como provisional |
| 5.1 | Las 6 series monetarias se deflactan por IPC de EE.UU., base 2015-Q1 |
| 5.2 | Las 6 series monetarias se expresan por habitante |
| 5.3 | Logaritmo en 5 series; se descartan Box-Cox y Yeo-Johnson |
| 5.4 | Los valores extremos no reciben tratamiento adicional |
| 5.5 | Las 2 series de la dimensión 2 se conservan sin transformar |
| 5.6 | El trimestre provisional se conserva sin corregir y se excluye del período de referencia |
| 6.1 | Correlación de Spearman como medida de referencia |
| 6.2 | La redundancia se evalúa sobre cambios trimestrales, no sobre niveles |
| 6.3 | Ninguna serie se excluye por redundancia; umbral declarado en 0,90 |
| 6.4 | Los cuatro indicadores derivados candidatos se descartan |
| 6.5 | El alfa de Cronbach se reporta como descripción, no como validez |
| 6.6 | La estructura multivariada no admite reducción a factores comunes |
| 7.1 | El tono entra con polaridad positiva, sin invertir |
| 7.2 | La atención legislativa se conserva como aproximación, con su limitación declarada |
| 7.3 | Puntaje z reescalado a media 100 y desvío 10 |
| 7.4 | La referencia se congela y no se recalcula en cada edición |
| 7.5 | Período de referencia: la ventana completa sin el trimestre provisional (44 trimestres) |

---

## 7. Lo que está abierto

### Decisión pendiente del usuario: la dirección de la atención legislativa

De los 7 proyectos de ley que la serie contabiliza, **uno solo es inequívocamente
favorable** (la resolución que da la bienvenida al presidente Peña), tres son
restrictivos (dos sobre importación de carne vacuna, uno de seguridad regional),
uno más es de seguridad y dos no admiten clasificación. **Ninguno fue promulgado**;
de los 49 proyectos que mencionan Paraguay en once años, solo uno llegó a ser ley.

Cuatro opciones planteadas, sin respuesta todavía:

- **A (recomendada)** — Tabla de clasificación versionada en el módulo de
  ingestión, con la dirección de cada proyecto. El proyecto **ya usa este patrón**
  en el histórico fijo de hitos de USTR y en el de TIAS. Son 7 clasificaciones en
  11 años. Es la única que arregla el problema de raíz. Implica tocar
  `src/ingestion/congreso_menciones_paraguay.py`.
- **B** — Contar solo proyectos promulgados. Reproducible, pero dejaría la serie en
  casi cero.
- **C** — Excluir la serie; la dimensión 2 quedaría solo con tratados.
- **D** — Dejarla como está, con la limitación declarada (estado actual).

### Restricción que la Etapa 8 hereda

**El tono debe conservar peso suficiente para compensar al volumen dentro de su
dimensión.** En los 12 trimestres donde el volumen estadounidense es alto y su tono
desfavorable, la dimensión 4 promedia 102,2 contra 99,2 en el resto: el tono
compensa. Si la ponderación le diera un peso marginal, ese mecanismo dejaría de
funcionar y los trimestres de cobertura intensa y desfavorable elevarían el índice.

La Etapa 8 hereda además de la Etapa 6 que **los pesos no pueden derivarse de la
estructura de los datos** (KMO 0,499; cuatro componentes para el 68,6% de la
variación), y de la Etapa 5 que **dos series discriminan mucho menos que las
demás** (la del Congreso toma 2 valores y la de tratados 4, frente a 45 de las
otras).

### Factores comprometidos para el análisis de sensibilidad (Etapa 10)

- El criterio de corte de los ceros estructurales (Decisión 3.2).
- El umbral de 3 menciones que define los proyectos relevantes del Congreso.
- Winsorizar al percentil 1-99, como alternativa a no tratar los atípicos.
- Excluir la serie de atención legislativa.

### Pendientes de otras etapas del pipeline

- **Stock de tratados previos a 2015.** La serie cuenta solo los TIAS que entraron
  en vigor desde 2015, pero existen anteriores todavía vigentes: el código de
  ingestión nombra dos, el TIAS 12995 de 1998 y el 94-817 de 1994. El usuario pidió
  revisarlo **al final**. Conseguir el inventario completo exige la publicación
  *Treaties in Force*, que devuelve 403 y cuyas ediciones viejas son PDF escaneado.
- **Bug latente** en `_anio_desde_tias()`: interpreta "94-817" como año 2094. Hoy no
  causa daño porque igual queda fuera del rango.
- Mover IPC, población y PBI a `src/ingestion/`.

---

## 8. Hallazgos que conviene no perder

- **Correlación en niveles vs en cambios.** Tratados vigentes y exportaciones
  correlacionan 0,763 en niveles y **−0,004 en cambios**: la asociación era
  tendencia común. De las 7 parejas que superan 0,5 en niveles, ninguna lo conserva
  en cambios.
- **Deflactar cambia conclusiones.** Con 39,4% de inflación acumulada, las remesas
  pasan de +30% nominal a −4,8% real (robusto bajo cinco criterios) y las
  importaciones de +33% a aproximadamente cero (no robusto: el signo depende del
  criterio).
- **Box-Cox y Yeo-Johnson ganaban y se descartaron igual**, porque estiman su
  exponente con los datos disponibles y la transformación cambiaría en cada
  actualización.
- **La referencia móvil desplaza valores publicados hasta 18 puntos**; la fija,
  exactamente cero.
- **El período base 2015-2019 es inviable**: el stock de tratados vale cero durante
  esos seis años y una serie constante no se puede normalizar contra él.
- **Los medios paraguayos aportan el 91,6% de los artículos**, y por eso los
  derivados agregados de GDELT reproducían la serie paraguaya.
- **Obligaciones y desembolsos no se suman**: son el mismo dinero en dos momentos.
  Correlacionan 0,872 con **dos años de rezago**. Sumarlos daría 446 M contra un
  programa real de unos 223 M.
- **El tono ocupa el 2,1% de su escala teórica** (−3,80 a +0,32) y es negativo en 86
  de 90 observaciones. Un tono negativo no significa cobertura hostil: el
  periodismo escribe en negativo por defecto. Lo informativo es el movimiento, no
  el signo.

---

## 9. Para continuar en otra máquina

1. `git pull` en el repo.
2. Confirmar que existe `.env` con `GOOGLE_APPLICATION_CREDENTIALS` apuntando al
   JSON de la cuenta de servicio (no está en git).
3. Renderizar. El primer render descarga los tres insumos externos y crea los
   caches; tarda más y necesita internet.
4. Leer este archivo y el `.qmd`. Retomar por la **Etapa 8 · Ponderación**,
   respetando las restricciones de §7.
