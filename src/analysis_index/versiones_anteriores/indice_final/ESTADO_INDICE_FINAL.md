# Estado de `04_indice_final.qmd`

Archivo de traspaso entre sesiones del índice final. Última actualización: 2026-10-06, al cierre de las Etapas 1 a 4.

Este archivo no reemplaza al documento. `04_indice_final.qmd` es la fuente de verdad de cada decisión con su evidencia, y `docs/hoja_de_ruta_indice_final.qmd` define qué se hace en cada etapa (con la numeración vieja, ver sección 2).

---

## 1. Carpeta de trabajo

Todo lo que corresponde al análisis vive en `src/analysis_index/indice_final/`.

| Ruta | Contenido |
|:--|:--|
| `04_indice_final.qmd` | Documento de análisis. Es el único archivo que se edita |
| `04_indice_final.html` | Render del documento (solo HTML, no se genera Word ni PDF) |
| `estilo_documento.css` | Hoja de estilo del documento, incluida la vista del panel |
| `ESTADO_INDICE_FINAL.md` | Este archivo |
| `salidas/tablas/` | Una tabla CSV por tabla del documento, con prefijo `etapa_subetapa` |
| `salidas/figuras/` | Una imagen PNG por figura, con el mismo prefijo |
| `salidas/registro/` | `registro_decisiones.csv` y `opciones_evaluadas.csv` |
| `salidas/cache/` | Copia local del panel, solo si `USAR_CACHE = True` |
| `borradores/` | `04_resumen_analisis.qmd`, el borrador del usuario del que sale la Etapa 1, y su panel intermedio |
| `referencia/indice_final_anterior/` | La versión anterior del documento (26.375 líneas, con su render y sus salidas). Solo lectura: es la fuente de las Etapas 5 a 12 hasta que se actualicen. **No está en git** |

`src/analysis_index/indice_version_1/` es la versión de prueba y no se toca. `.gitignore` excluye `salidas/`, las carpetas `*_files/` y los `.pkl`.

## 2. Numeración nueva y correspondencia con la versión anterior

El documento ya no tiene presentación conceptual, ni Etapa 0 de configuración, ni marco teórico. El bloque de configuración (paquetes, funciones, parámetros) está al inicio, sin numerar.

| Nueva | Contenido | Viene de (versión anterior) | Estado |
|:--|:--|:--|:--|
| 1 | Importación, valores faltantes y ventana | Etapa 0, Etapa 3, subpregunta 4.6 y borrador `04_resumen_analisis` | **Hecha** |
| 2 | Selección de datos (2.1 a 2.5) | Etapa 2, más la subpregunta 2.5 nueva | **Hecha** |
| 3 | Exploración descriptiva | 4.1 a 4.5 | **Hecha** |
| 4 | Transformación de variables | Etapa 5 | **Hecha** |
| 5 | Consistencia interna y análisis multivariado | Etapa 6 | Pendiente |
| 6 | Normalización | Etapa 7 | Pendiente |
| 7 | Ponderación | Etapa 8 | Pendiente |
| 8 | Agregación | Etapa 9 | Pendiente |
| 9 a 12 | Sensibilidad, retorno a los datos, vínculos externos y resultados | Etapas 10 a 13 | En blanco por pedido del usuario |

Las subpreguntas conservan su número dentro de la etapa (la 6.8 vieja es la 5.8 nueva). Los códigos de decisión también se renumeran (D5.3 viejo es D4.3 nuevo).

## 3. Decisiones tomadas (todas de categoría Regla, estado Tomada)

Registro completo en `salidas/registro/`.

| Código | Decisión |
|:--|:--|
| D1.1 | Candidatas: las 29 variables con Sí o Tal vez en `En índice` |
| D1.2 | Los NA de las 11 variables con «ceros verdaderos» según `Razón de NAs` se escriben como 0 hasta 2025-Q4. El resto se conserva como NA |
| D1.3 | Ventana 2015-Q1 a 2025-Q4 (44 trimestres), umbral de cobertura 70%. Entran las 29 |
| D2.1 | Cada serie en un solo indicador: 15 nombradas en la `Matriz`, 14 por contenido |
| D2.2 | Par redundante si el valor absoluto de Spearman sobre cambios es ≥ 0,90. Esa subpregunta no excluye |
| D2.3a y D2.3b | Los indicadores sin serie se declaran limitación (hoy ninguno). El 2.2 queda cubierto de forma parcial |
| D2.4 | Se excluyen `usaspending_operativo` y `exim_desembolsado` (subconjuntos por definición de series con las que su par es redundante). Quedan 27 series, provisionales hasta 5.8. Los 5 derivados candidatos entran al panel de trabajo (32 columnas) y se transforman igual; la 5.3 decide cuáles se incorporan al índice |
| D3.3 | La admisibilidad de cada transformación se calcula desde los datos |
| D3.4 | Método de referencia para extremos: desviación absoluta mediana |
| D3.5 | Cada quiebre se clasifica con la evidencia documental y se trata según su clase |
| D4.1a y D4.1b | Series en dólares a precios constantes de 2015 con el IPC de EE. UU.; el stock de BEA con el deflactor anual. Precios corrientes entra a la Etapa 9 como factor |
| D4.2a, D4.2b y D4.2c | Series monetarias por habitante; población del INE; interpolación lineal al punto medio del trimestre |
| D4.3 | Logaritmo natural a 8 series (6 por el criterio y 2 por alineación dentro de su indicador). Los derivados candidatos reciben las mismas transformaciones que las series |
| D4.4 | Los valores extremos no se tratan; la winsorización entra a la Etapa 9 como factor |
| D4.5 | Conteo por trimestre para las 3 series dispersas (`bancomundial_proyectos_atribuible_eeuu`, `congreso_proyectos_relevantes_paraguay`, `ustr_hitos_consejo_comercio_inversion`) |
| D4.6a y D4.6b | Trimestres provisionales: 2015-Q1 (GDELT, fuente parcial) y 2025-Q4 (IPC con un mes sin publicar). **Solo se marcan: no se excluyen de la ventana, de la escala ni de ningún período de referencia** (decisión del usuario, 2026-10-06: «los datos son lo que son») |

## 4. Cambio de política que hay que recordar

La versión anterior escribía ceros solo donde una regla calculada decía que la fuente se había consultado por completo. Ahora la columna `Razón de NAs` declara cuáles NA son ceros, y se clasifica con `REGLAS_RAZON_NA` (bloque de parámetros). Consecuencias:

- La «familia de serie» y `COBERTURA_FUENTE` ya no existen. Se usan `grano_temporal`, `agregacion` y `unidad` del catálogo, `VARIABLES_CON_CERO` y `SERIES_DE_HECHOS` (series que suman hechos con fecha y tienen ceros verdaderos).
- Con la ventana fija no hay composición variable del índice, salvo 16 casillas sin dato de `bea_inversion_directa` (8), `inversion_directa_bcp` (4) y `turismo_receptivo_eeuu` (4).
- Cada cero escrito deja a su serie sin logaritmo (17 series sin logaritmo en total).
- El análisis factorial de la Etapa 5 deja de ser viable con dimensiones de más de 8 series (43 cambios trimestrales). Hay que concluirlo con el criterio y no forzarlo.
- Los textos de la versión anterior que nombran una serie o un trimestre concreto se reescriben para leerlos desde los resultados.

## 5. Hallazgos a tener presentes en las etapas siguientes

- **Condición de detención de 3.3 cumplida:** `inversion_directa_bcp` es monetaria y tiene 12 valores negativos (desinversión). No admite logaritmo. El documento lo informa. En 5.3 y 4.3 quedó sin transformar.
- **Series con ceros dominantes:** 3 dispersas más `dfc_comprometido` (64%, anual repetida) y `google_trends_paraguay_tariffs` (93%, promedio simple), que el criterio de 4.5 no alcanza por no sumar hechos. La Etapa 6 mide qué les hace la normalización.
- **Quiebres:** 25 detectados en 17 series con Bai y Perron; 16 coinciden con las fechas candidatas, 20 sin explicación documentada, ninguno de medición. 6 pares de la 2.2 tienen una serie con ceros dominantes y se reevalúan con Kendall en 5.1.
- **`fa_gov_*` 2026** está fuera de la ventana y es provisional (13% y 23% del mínimo de los años anteriores). Importa si se extiende la ventana.
- **IPC 2025-Q4** se calcula con dos meses (octubre de 2025 no se publicó): efecto posible de 0,18%.

## 6. Puntos que el usuario debe confirmar

1. **Ceros de cabecera de la DFC (2015-2017):** `dfc_comprometido` y `dfc_proyectos_vigentes` reciben 12 ceros cada una antes de su primer dato. La fuente es una lista de proyectos activos a la fecha de descarga. El documento lo declara como limitación y sigue el diccionario.
2. **Asignación por contenido (14 series):** la más débil es `exim_desembolsado` (hoy excluida por D2.4).
3. **`bea_inversion_directa` e `inversion_directa_bcp`:** siguen como candidatas. Su destino se decide con evidencia en 5.8. La segunda tiene valores negativos y queda sin transformar.
4. **Fuentes y enlaces:** la tabla de fuentes con enlace va en la Etapa 12.

## 7. Objetos disponibles para la Etapa 5

| Objeto | Contenido |
|:--|:--|
| `panel_transformado` | 44 trimestres × 32 columnas (27 series y 5 derivados), a precios constantes, por habitante y con logaritmo donde corresponde. Insumo de la Etapa 5 |
| `panel_trabajo` (= `panel_seleccion` + derivados), `panel_seleccion`, `panel_ventana`, `panel_tratado` | Estados anteriores del panel (32, 27, 29 y 29 columnas) |
| `SERIES_DE_TRABAJO`, `SERIES_DERIVADAS`, `METADATOS_DERIVADOS` | Series seleccionadas más derivados, y atributos de los derivados (unidad, grano, agregación, indicador) |
| `SERIES_SELECCIONADAS`, `SERIES_ETAPA_4`, `SERIES_EN_DOLARES`, `SERIES_CON_LOG`, `SERIES_DISPERSAS`, `SERIES_DE_HECHOS`, `VARIABLES_CON_CERO` | Listas de series |
| `TRIMESTRES_PROVISIONALES`, `TRIMESTRES_PROVISIONALES_EN_VENTANA`, `provisionales_en_panel` | Trimestres provisionales, solo marcas informativas. **La Etapa 6 no los excluye del cálculo de la escala** |
| `operacionalizacion` | Tabla de operacionalización con la columna `como_se_completa` |
| `catalogo_indexado`, `matriz_indicadores`, `INDICADOR_DE_SERIE`, `series_por_indicador` | Catálogo y marco |
| `redundancia_por_indicador`, `derivados_candidatos`, `derivados_correlaciones` | Resultados de 2.2 y 2.4 para 5.3 y 5.8 |
| `registro_decisiones`, `opciones_evaluadas` | Registro acumulado |

Funciones comunes del bloque de configuración: `num`, `numero_largo`, `porcentaje`, `letras`, `contar`, `cardinal`, `concordar`, `en_prosa`, `tabla`, `vista_panel`, `mostrar_figura`, `grilla_de_series`, `guardar_tabla`, `rangos_de_trimestres`, `anio_decimal`, `valor_p_legible`, `numero_legible`, `detener`. Funciones de etapa reutilizables: `serie_en_grano_propio`, `evaluar_extremos`, `a_anual`, `spearman_con_intervalo`.

## 8. Convenciones del documento

- Orden de cada subpregunta: enlace con la anterior, `En qué consiste`, `Qué muestran los datos` (código, tablas, figuras y cifras en línea), `La decisión` (registro, recuadro y tabla de opciones).
- **Ecuaciones:** cada subpregunta que aplica un cálculo muestra sus fórmulas en LaTeX (`$$ ... $$`), escritas con Write o cadenas raw. Las Etapas 3 y 4 ya las tienen; las etapas siguientes también deben tenerlas. Se renderizan con MathJax por CDN (necesita internet).
- **Al cierre de cada etapa** hay una sección de nivel 2 «Estado del panel al cierre de la Etapa N» con la vista **completa** del data.frame (todos los trimestres y todas las series), con los ceros escritos u otras marcas en ocre y las casillas sin dato en rojo. No se muestra el estado anterior.
- No hay bloques de validación. Las comprobaciones que detienen la ejecución usan `detener(...)`.
- Solo HTML y `.qmd`. No se generan Word ni PDF.
- Cada figura se guarda con `mostrar_figura(figura, "etapa_subetapa_nombre")`.
- Las etapas nuevas se agregan en el lugar de su encabezado vacío, antes de `# Archivos que produce el documento`, que debe quedar último.

## 9. Cómo renderizar

Entorno: `.venv/` en la raíz. Usar `quarto.exe` de Positron y no `quarto.cmd`.

```powershell
$env:QUARTO_PYTHON = "<raiz>\.venv\Scripts\python.exe"
& "<Positron>\resources\app\quarto\bin\quarto.exe" render "src\analysis_index\indice_final\04_indice_final.qmd" --to html
```

La generación tarda varios minutos (lee de Drive y simula los valores críticos de Bai y Perron). El documento limita los hilos de OpenBLAS a 4. Si el equipo tiene muy poca memoria virtual libre, el render puede fallar con `MemoryError`.
