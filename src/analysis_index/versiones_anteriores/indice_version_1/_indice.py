"""Fuente unica del US-PY Engagement Index para las etapas de analisis.

Este modulo reconstruye el indice EXACTAMENTE como lo construye el documento
metodologico `04_construccion_indice.qmd` y el informe `05_informe_construccion_indice.qmd`,
a partir de los tres caches locales que ese documento produce
(`_cache_panel_integracion.csv`, `_cache_ipc_eeuu.csv`, `_cache_paraguay_escala.csv`).

Existe para que el documento de analisis e interpretacion no vuelva a calcular el
indice por su cuenta: importa `construir_indice()` y trabaja sobre los objetos que
devuelve, de modo que las cifras de la interpretacion nunca puedan desincronizarse
de las de la construccion. La funcion `verificar_anclajes()` comprueba, contra los
valores que la construccion declara, que la reconstruccion sigue siendo fiel.

Correrlo directo (`py _indice.py`) imprime la validacion de anclajes.
"""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd


# PARAMETROS DEL INDICE --------------------------------------------------------
# Todos identicos a los del documento de construccion. Cambiar el indice es
# cambiar estas constantes, nunca el codigo de mas abajo.

# 1. Caches locales que produce el documento metodologico
ARCHIVO_PANEL = "_cache_panel_integracion.csv"
ARCHIVO_IPC = "_cache_ipc_eeuu.csv"
ARCHIVO_ESCALA = "_cache_paraguay_escala.csv"


# 2. Ventana de analisis y trimestre que la fuente publica de manera incompleta
VENTANA_DESDE = "2015-Q1"
VENTANA_HASTA = "2026-Q1"

TRIMESTRES_PROVISIONALES = ["2026-Q1"]


# 3. Periodo base: ultima decada completa anterior al periodo sobre el que se informa
ANIO_FIN_DECADA_BASE = "2024"


# 4. Escala publicada: promedio y desvio de la referencia
MEDIA_OBJETIVO = 100
DESVIO_OBJETIVO = 10


# 5. Trimestre cuyos precios sirven de referencia para el ajuste por inflacion
TRIMESTRE_BASE_PRECIOS = "2015-Q1"


# 6. Indicador que operacionaliza cada serie. Cuatro indicadores llevan dos series
INDICADOR_DE_SERIE = {
    "fa_gov_obligaciones": "Asistencia oficial de EE.UU.",
    "fa_gov_desembolsos": "Asistencia oficial de EE.UU.",
    "usaspending_obligaciones": "Gasto federal ejecutado",
    "congreso_proyectos_relevantes_paraguay": "Atencion legislativa del Congreso",
    "state_gov_tias_vigentes": "Tratados bilaterales vigentes",
    "exportaciones": "Comercio bilateral de bienes",
    "importaciones": "Comercio bilateral de bienes",
    "remesas": "Remesas familiares",
    "gdelt_proxy_articles_py": "Volumen de cobertura",
    "gdelt_proxy_articles_us": "Volumen de cobertura",
    "gdelt_tone_promedio_py": "Tono de la cobertura",
    "gdelt_tone_promedio_us": "Tono de la cobertura",
}


# 7. Familia de cada serie: determina que significa una casilla vacia
FAMILIA_SERIE = {
    "fa_gov_obligaciones": "nivel publicado",
    "fa_gov_desembolsos": "nivel publicado",
    "usaspending_obligaciones": "hechos con fecha",
    "congreso_proyectos_relevantes_paraguay": "hechos con fecha",
    "state_gov_tias_vigentes": "nivel publicado",
    "exportaciones": "nivel publicado",
    "importaciones": "nivel publicado",
    "remesas": "nivel publicado",
    "gdelt_proxy_articles_py": "hechos con fecha",
    "gdelt_proxy_articles_us": "hechos con fecha",
    "gdelt_tone_promedio_py": "nivel publicado",
    "gdelt_tone_promedio_us": "nivel publicado",
}


# 8. Tipo de cobertura de las series de hechos: fija el limite hasta donde se
#    escribe el cero estructural
TIPO_COBERTURA = {
    "usaspending_obligaciones": "consulta en vivo",
    "congreso_proyectos_relevantes_paraguay": "consulta en vivo",
    "gdelt_proxy_articles_py": "extraccion por lote",
    "gdelt_proxy_articles_us": "extraccion por lote",
}


# 9. Etiqueta corta y color de cada dimension, fijos en todo el analisis
ETIQUETA_DIMENSION = {
    "1_Compromiso_financiero_oficial_limpias": "D1 · Compromiso financiero oficial",
    "2_Actividad_gubernamental_y_diplomatica_limpias": "D2 · Vínculo político-institucional",
    "3_Compromiso_economico_privado_limpias": "D3 · Compromiso económico privado",
    "4_Visibilidad_mediatica_y_relevancia_publica_limpias": "D4 · Visibilidad mediática",
}

COLOR_DIMENSION = {
    "1_Compromiso_financiero_oficial_limpias": "#1f4e79",
    "2_Actividad_gubernamental_y_diplomatica_limpias": "#b35c00",
    "3_Compromiso_economico_privado_limpias": "#2e7d5b",
    "4_Visibilidad_mediatica_y_relevancia_publica_limpias": "#7a4e9e",
}


# 10. Anclajes que declara la construccion, para verificar que la reconstruccion
#     sigue siendo fiel (recorrido del panel normalizado y promedio del indice
#     en el periodo de referencia)
ANCLAJE_NORMALIZADO_MIN = 64.5
ANCLAJE_NORMALIZADO_MAX = 154.2
ANCLAJE_REFERENCIA_TRIMESTRES = 36


def _ultimo_trimestre_completo(fecha):
    """Ultimo trimestre ya terminado en esa fecha: uno en curso no esta cubierto
    entero por la fuente."""

    anio, mes = int(fecha[:4]), int(fecha[5:7])

    en_curso = (mes - 1) // 3 + 1

    return f"{anio}-Q{en_curso - 1}" if en_curso > 1 else f"{anio - 1}-Q4"


def _asimetria(valores):
    """Cuanto se extiende la distribucion hacia un lado."""

    centrado = valores - valores.mean()

    return (centrado ** 3).mean() / (centrado.std(ddof=0) ** 3)


def construir_indice(carpeta=None):
    """Reconstruye el indice desde los caches y devuelve todos los objetos que la
    interpretacion necesita, en un unico espacio de nombres.

    carpeta: donde estan los tres caches. Por defecto, la carpeta de este modulo.
    """

    # 0. Carpeta de los caches
    carpeta = Path(carpeta) if carpeta is not None else Path(__file__).resolve().parent


    # 1. Panel trimestral que publica la etapa de integracion, con su indicador
    panel_crudo = pd.read_csv(carpeta / ARCHIVO_PANEL).assign(
        indicador=lambda d: d["variable"].map(INDICADOR_DE_SERIE),
    )


    # 2. Orden declarado de las series y de los trimestres del panel
    orden_series = panel_crudo["variable"].drop_duplicates().tolist()

    trimestres_panel = panel_crudo["trimestre"].drop_duplicates().sort_values().tolist()


    # 3. Catalogo con los atributos que no dependen del trimestre
    catalogo_series = (
        panel_crudo
        .groupby(["dimension", "indicador", "variable"], as_index=False)
        .agg(
            unidad=("unidad", "first"),
            grano_temporal=("grano_temporal", "first"),
        )
        .set_index("variable")
        .loc[orden_series]
        .reset_index()
    )

    dimension_de_serie = catalogo_series.set_index("variable")["dimension"]


    # 4. Trimestres que quedan dentro de la ventana declarada
    trimestres_ventana = [t for t in trimestres_panel if VENTANA_DESDE <= t <= VENTANA_HASTA]


    # 5. Series de hechos: una casilla vacia significa que no hubo hechos
    series_hechos = [v for v, f in FAMILIA_SERIE.items() if f == "hechos con fecha"]


    # 6. Ultimo trimestre observado y fecha de extraccion de cada serie de hechos
    ultimo_observado = (
        panel_crudo[panel_crudo["en_fuente"]].groupby("variable")["trimestre"].max()
    )

    fecha_extraccion = (
        panel_crudo.groupby("variable")["archivo_origen"].first()
        .str.extract(r"(\d{4}-\d{2}-\d{2})")[0]
    )


    # 7. Limite de cobertura: hasta donde se puede escribir el cero estructural
    limite_cobertura = {
        variable: (
            ultimo_observado[variable] if TIPO_COBERTURA[variable] == "extraccion por lote"
            else _ultimo_trimestre_completo(fecha_extraccion[variable])
        )
        for variable in series_hechos
    }


    # 8. Cero estructural en las series de hechos hasta su limite de cobertura
    panel_tratado = panel_crudo.assign(valor_tratado=lambda d: d["valor"])

    for variable in series_hechos:

        es_cero = (
            (panel_tratado["variable"] == variable)
            & (~panel_tratado["en_fuente"])
            & (panel_tratado["trimestre"] <= limite_cobertura[variable])
        )

        panel_tratado.loc[es_cero, "valor_tratado"] = 0.0


    # 9. El stock de tratados vale cero antes de su primer instrumento
    primer_tratado = panel_tratado[
        (panel_tratado["variable"] == "state_gov_tias_vigentes") & panel_tratado["en_fuente"]
    ]["trimestre"].min()

    es_cabecera = (
        (panel_tratado["variable"] == "state_gov_tias_vigentes")
        & (~panel_tratado["en_fuente"])
        & (panel_tratado["trimestre"] < primer_tratado)
    )

    panel_tratado.loc[es_cabecera, "valor_tratado"] = 0.0


    # 10. Version ancha y recortada a la ventana, insumo de las transformaciones
    panel_ventana = (
        panel_tratado[panel_tratado["trimestre"].isin(trimestres_ventana)]
        .pivot(index="trimestre", columns="variable", values="valor_tratado")
        .loc[trimestres_ventana, orden_series]
    )


    # 11. Indice de precios de EE.UU. llevado a trimestre promediando los meses
    ipc_mensual = pd.read_csv(carpeta / ARCHIVO_IPC)

    ipc_trimestral = (
        ipc_mensual
        .assign(trimestre=lambda d: d["anio"].astype(str) + "-Q" + (((d["mes"] - 1) // 3) + 1).astype(str))
        .groupby("trimestre", as_index=False)
        .agg(ipc=("ipc", "mean"))
    )


    # 12. Deflactor trimestral: precios de cada trimestre respecto del base
    ipc_base = ipc_trimestral.loc[ipc_trimestral["trimestre"] == TRIMESTRE_BASE_PRECIOS, "ipc"].iloc[0]

    deflactor_trimestral = (
        ipc_trimestral
        .assign(deflactor=lambda d: d["ipc"] / ipc_base)
        .set_index("trimestre")["deflactor"]
        .reindex(trimestres_ventana)
    )


    # 13. Deflactor anual, para las series que la fuente publica una vez por anio
    #     y el modulo de limpieza repite en los cuatro trimestres
    anio_de_trimestre = pd.Series([t[:4] for t in trimestres_ventana], index=trimestres_ventana)

    deflactor_anual = deflactor_trimestral.groupby(anio_de_trimestre).transform("mean")

    series_grano_anual = (
        catalogo_series.loc[catalogo_series["grano_temporal"] == "anio repetido", "variable"].tolist()
    )


    def deflactor_de(variable):
        """Deflactor que corresponde al grano de cada serie."""

        return deflactor_anual if variable in series_grano_anual else deflactor_trimestral


    # 14. Series monetarias y de tono, para saber a cuales se aplica cada ajuste
    series_monetarias = catalogo_series.loc[catalogo_series["unidad"] == "USD", "variable"].tolist()

    series_tono = [v for v in orden_series if "tone" in v]


    # 15. Deflacta las series monetarias a dolares del trimestre base
    panel_deflactado = panel_ventana.copy()

    for variable in series_monetarias:

        panel_deflactado[variable] = panel_ventana[variable] / deflactor_de(variable)


    # 16. Poblacion de Paraguay por trimestre, arrastrando el ultimo anio publicado
    escala_paraguay = pd.read_csv(carpeta / ARCHIVO_ESCALA).set_index("anio")

    ultimo_anio_publicado = int(escala_paraguay.index.max())

    poblacion_trimestral = pd.Series(
        [escala_paraguay.loc[min(int(t[:4]), ultimo_anio_publicado), "poblacion"] for t in trimestres_ventana],
        index=trimestres_ventana,
    )


    # 17. Series monetarias por habitante
    panel_por_habitante = panel_deflactado.copy()

    for variable in series_monetarias:

        panel_por_habitante[variable] = panel_deflactado[variable] / poblacion_trimestral


    # 18. Series discretas: toman pocos valores distintos y quedan fuera del log
    umbral_proporcion_discreta = 1 / 3

    anios_de_la_ventana = pd.Series(trimestres_ventana).str[:4].nunique()

    observaciones_propias = pd.Series({
        variable: (
            anios_de_la_ventana if variable in series_grano_anual else len(panel_por_habitante)
        )
        for variable in orden_series
    })

    diversidad = pd.DataFrame({
        "valores_distintos": panel_por_habitante[orden_series].nunique(),
        "observaciones_propias": observaciones_propias,
    }).assign(proporcion=lambda d: d["valores_distintos"] / d["observaciones_propias"])

    series_discretas = diversidad[diversidad["proporcion"] < umbral_proporcion_discreta].index.tolist()


    # 19. El logaritmo se aplica donde reduce la asimetria, y se extiende a la otra
    #     serie del mismo indicador cuando el criterio las separa
    criterio_log = pd.DataFrame([
        {
            "variable": variable,
            "indicador": INDICADOR_DE_SERIE[variable],
            "asimetria_sin_log": _asimetria(panel_por_habitante[variable]),
            "asimetria_con_log": (
                _asimetria(np.log(panel_por_habitante[variable]))
                if (panel_por_habitante[variable] > 0).all() else np.nan
            ),
            "discreta": variable in series_discretas,
        }
        for variable in orden_series
    ]).assign(
        mejora=lambda d: d["asimetria_sin_log"].abs() - d["asimetria_con_log"].abs(),
    ).assign(
        log_por_asimetria=lambda d: (d["mejora"] > 0) & ~d["discreta"],
    )


    # 20. Indicadores cuyas dos series discrepan en si llevan log: se armonizan
    indicadores_partidos = (
        criterio_log.groupby("indicador")["log_por_asimetria"]
        .agg(["sum", "size"])
        .query("0 < sum < size")
        .index.tolist()
    )

    series_con_log = sorted(
        criterio_log.loc[
            criterio_log["log_por_asimetria"]
            | (criterio_log["indicador"].isin(indicadores_partidos) & ~criterio_log["discreta"]),
            "variable",
        ].tolist()
    )


    # 21. Panel transformado, insumo de la normalizacion
    panel_transformado = panel_por_habitante.copy()

    for variable in series_con_log:

        panel_transformado[variable] = np.log(panel_transformado[variable])


    # 22. Trimestres efectivamente medidos: la ventana sin el provisional
    ventana_medida = [t for t in trimestres_ventana if t not in TRIMESTRES_PROVISIONALES]


    # 23. Primera regla del periodo base: la ultima decada completa anterior al
    #     periodo sobre el que se informa
    decada_base = [t for t in ventana_medida if t[:4] <= ANIO_FIN_DECADA_BASE]


    # 24. Segunda regla: se retiran los anios en que las DOCE series quedan por
    #     debajo de su propio promedio de lo medido
    posicion_relativa = (
        (panel_transformado.loc[ventana_medida] - panel_transformado.loc[ventana_medida].mean())
        / panel_transformado.loc[ventana_medida].std()
    )

    anio_de_la_ventana = pd.Series([t[:4] for t in ventana_medida], index=ventana_medida)

    anios_deprimidos = [
        anio for anio, posiciones in posicion_relativa.groupby(anio_de_la_ventana)
        if (posiciones.mean() < 0).all()
    ]

    periodo_referencia = [t for t in decada_base if t[:4] not in anios_deprimidos]


    # 25. Media y desvio de cada serie sobre el periodo de referencia: quedan
    #     CONGELADOS, las ediciones futuras normalizan contra ellos
    referencia_congelada = pd.DataFrame({
        "media": panel_transformado.loc[periodo_referencia].mean(),
        "desvio": panel_transformado.loc[periodo_referencia].std(),
    })


    # 26. Normaliza cada serie contra su propia referencia congelada
    panel_normalizado = pd.DataFrame({
        variable: (
            (panel_transformado[variable] - referencia_congelada.loc[variable, "media"])
            / referencia_congelada.loc[variable, "desvio"] * DESVIO_OBJETIVO + MEDIA_OBJETIVO
        )
        for variable in orden_series
    })


    # 27. Estructura del indice y peso de cada serie por reparto en tres niveles
    estructura = pd.DataFrame({
        "variable": orden_series,
        "dimension": [dimension_de_serie[v] for v in orden_series],
        "indicador": [INDICADOR_DE_SERIE[v] for v in orden_series],
    })

    peso_por_dimension = 1 / estructura["dimension"].nunique()

    estructura["peso"] = [
        peso_por_dimension
        / estructura.loc[estructura["dimension"] == dim, "indicador"].nunique()
        / len(estructura[(estructura["dimension"] == dim) & (estructura["indicador"] == ind)])
        for dim, ind in zip(estructura["dimension"], estructura["indicador"])
    ]

    pesos = estructura.set_index("variable")["peso"].reindex(orden_series)


    # 28. Indice de cada indicador: promedio de las series que lo miden
    indices_por_indicador = pd.DataFrame({
        indicador: panel_normalizado[bloque["variable"].tolist()].mean(axis=1)
        for indicador, bloque in estructura.groupby("indicador")
    })


    # 29. Indice de cada dimension: promedio de sus indicadores
    indicadores_de_cada_dimension = (
        estructura[["dimension", "indicador"]].drop_duplicates()
        .groupby("dimension")["indicador"].apply(list)
    )

    indices_por_dimension = pd.DataFrame({
        ETIQUETA_DIMENSION[dimension]: indices_por_indicador[indicadores].mean(axis=1)
        for dimension, indicadores in indicadores_de_cada_dimension.items()
    })


    # 30. Indice general: promedio de las cuatro dimensiones
    indice = indices_por_dimension.mean(axis=1)


    # 31. Desbalance: distancia entre la dimension mas alta y la mas baja
    desbalance = indices_por_dimension.max(axis=1) - indices_por_dimension.min(axis=1)


    # 32. Anio y marca de provisional de cada trimestre de la ventana
    anio_serie = pd.Series([t[:4] for t in trimestres_ventana], index=trimestres_ventana)

    es_provisional = pd.Series(
        [t in TRIMESTRES_PROVISIONALES for t in trimestres_ventana],
        index=trimestres_ventana,
    )


    # 33. Series continuas: ni discretas ni de grano anual. Son la referencia
    #     contra la cual se lee el tamano de los saltos de las series discretas
    series_continuas = [
        v for v in orden_series
        if v not in series_discretas and v not in series_grano_anual
    ]


    return SimpleNamespace(
        # panel en cada estado
        panel_crudo=panel_crudo,
        panel_ventana=panel_ventana,
        panel_deflactado=panel_deflactado,
        panel_por_habitante=panel_por_habitante,
        panel_transformado=panel_transformado,
        panel_normalizado=panel_normalizado,
        # indice y componentes
        indices_por_indicador=indices_por_indicador,
        indices_por_dimension=indices_por_dimension,
        indice=indice,
        desbalance=desbalance,
        # estructura y pesos
        estructura=estructura,
        pesos=pesos,
        referencia_congelada=referencia_congelada,
        catalogo_series=catalogo_series,
        # indices y agrupamientos utiles
        orden_series=orden_series,
        trimestres_panel=trimestres_panel,
        trimestres_ventana=trimestres_ventana,
        ventana_medida=ventana_medida,
        periodo_referencia=periodo_referencia,
        anios_deprimidos=anios_deprimidos,
        anio_serie=anio_serie,
        es_provisional=es_provisional,
        dimension_de_serie=dimension_de_serie,
        # conjuntos de series
        series_monetarias=series_monetarias,
        series_tono=series_tono,
        series_con_log=series_con_log,
        series_discretas=series_discretas,
        series_grano_anual=series_grano_anual,
        series_continuas=series_continuas,
        series_hechos=series_hechos,
        # constantes y etiquetas
        INDICADOR_DE_SERIE=INDICADOR_DE_SERIE,
        ETIQUETA_DIMENSION=ETIQUETA_DIMENSION,
        COLOR_DIMENSION=COLOR_DIMENSION,
        MEDIA_OBJETIVO=MEDIA_OBJETIVO,
        DESVIO_OBJETIVO=DESVIO_OBJETIVO,
        VENTANA_DESDE=VENTANA_DESDE,
        VENTANA_HASTA=VENTANA_HASTA,
        TRIMESTRES_PROVISIONALES=TRIMESTRES_PROVISIONALES,
        ANIO_FIN_DECADA_BASE=ANIO_FIN_DECADA_BASE,
        TRIMESTRE_BASE_PRECIOS=TRIMESTRE_BASE_PRECIOS,
    )


def salto_por_unidad(idx, variable):
    """Cuantos puntos de la escala desplaza un cambio de una unidad en una serie
    discreta, con el MISMO metodo que el documento de construccion: el valor
    normalizado de cada nivel se redondea a un decimal y el salto es la pendiente
    sobre el recorrido nativo de la serie.
    """

    # 1. Nivel nativo de la serie (sin log en las series discretas) y su valor
    #    normalizado, redondeado a un decimal
    nativa = idx.panel_transformado[variable]

    niveles = sorted(nativa.unique())

    normalizados = [round(idx.panel_normalizado.loc[nativa == nivel, variable].iloc[0], 1) for nivel in niveles]


    # 2. Pendiente: puntos que cuesta una unidad nativa
    return (max(normalizados) - min(normalizados)) / (max(niveles) - min(niveles))


def movimiento_continuo(idx):
    """Movimiento trimestral tipico de una serie continua, con el MISMO metodo que
    el documento de construccion: la mediana de las medianas del cambio trimestral
    absoluto de cada serie continua. Es la referencia contra la cual se leen los
    saltos de las series discretas.
    """

    # 1. Mediana del cambio trimestral absoluto de cada serie continua
    medianas = pd.Series({
        variable: idx.panel_normalizado[variable].diff().abs().median()
        for variable in idx.series_continuas
    })


    # 2. Mediana de esas medianas
    return medianas.median()


def verificar_anclajes(idx=None, carpeta=None):
    """Comprueba que la reconstruccion coincide con lo que declara la construccion.

    Devuelve un DataFrame de una fila por anclaje, con lo esperado, lo obtenido y
    si coincide. Sirve como validacion dentro del documento de analisis.
    """

    # 1. Reconstruye el indice si no se recibe uno ya construido
    idx = idx if idx is not None else construir_indice(carpeta)


    # 2. Recorrido del panel normalizado y promedio del indice en la referencia
    normalizado_min = idx.panel_normalizado.min().min()

    normalizado_max = idx.panel_normalizado.max().max()

    promedio_referencia = idx.indice.loc[idx.periodo_referencia].mean()


    # 3. Tabla de anclajes: esperado contra obtenido
    anclajes = pd.DataFrame([
        {
            "anclaje": "recorrido minimo del panel normalizado",
            "esperado": ANCLAJE_NORMALIZADO_MIN,
            "obtenido": round(normalizado_min, 1),
        },
        {
            "anclaje": "recorrido maximo del panel normalizado",
            "esperado": ANCLAJE_NORMALIZADO_MAX,
            "obtenido": round(normalizado_max, 1),
        },
        {
            "anclaje": "promedio del indice en el periodo de referencia",
            "esperado": float(MEDIA_OBJETIVO),
            "obtenido": round(promedio_referencia, 4),
        },
        {
            "anclaje": "trimestres del periodo de referencia",
            "esperado": float(ANCLAJE_REFERENCIA_TRIMESTRES),
            "obtenido": float(len(idx.periodo_referencia)),
        },
    ])

    anclajes["coincide"] = np.isclose(anclajes["esperado"], anclajes["obtenido"], atol=0.05)

    return anclajes


if __name__ == "__main__":

    resultado = construir_indice()

    control = verificar_anclajes(resultado)

    print(control.to_string(index=False))

    print(f"\nrecorrido del indice general: {resultado.indice.min():.2f} "
          f"({resultado.indice.idxmin()}) a {resultado.indice.max():.2f} "
          f"({resultado.indice.idxmax()})")

    print(f"todos los anclajes coinciden: {'si' if control['coincide'].all() else 'NO'}")
