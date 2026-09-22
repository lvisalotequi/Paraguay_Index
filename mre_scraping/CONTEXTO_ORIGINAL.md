# Contexto para replicar y continuar el proyecto

## Objetivo

Recuperar noticias publicadas por el Ministerio de Relaciones Exteriores de
Paraguay entre 2015 y 2025, conservar fecha, título, descripción, texto y URL,
y producir conteos mensuales relacionados con Estados Unidos.

El proyecto separa dos etapas:

1. `scraper_mre.py` recolecta y limpia las noticias.
2. `clasificar_bilateral.py` distingue menciones simples, noticias bilaterales y
   noticias bilaterales de peso mediante reglas explícitas.

No se utiliza IA. Las mismas páginas, reglas y configuraciones producen la misma
clasificación.

## Fuentes

- Sitio actual: `https://www.mre.gov.py/archivo-de-noticias/`
- Índice CDX y capturas de Wayback Machine para noticias históricas.
- El sitio actual puede responder con HTTP 403 según la red. El programa registra
  el bloqueo y continúa con Wayback cuando se ejecutan ambas fuentes.

## Archivos esenciales

- `scraper_mre.py`: descubrimiento, descarga, caché, extracción y conteo inicial.
- `clasificar_bilateral.py`: segunda etapa de clasificación.
- `terminos_eeuu.json`: variantes textuales de Estados Unidos.
- `reglas_bilaterales.json`: señales, puntajes y umbrales de bilateralidad.
- `requirements.txt`: dependencias con versiones fijadas.
- `README.md`: instalación y comandos.
- `test_scraper_mre.py` y `test_clasificar_bilateral.py`: pruebas de regresión.

## Decisiones metodológicas ya incorporadas

- Se cuentan por separado noticias con alguna mención y número de apariciones.
- “Emiratos Árabes Unidos” no cuenta como Estados Unidos.
- La descripción no se suma al conteo porque suele repetir el primer párrafo.
- En el portal histórico se elimina el carrusel “Últimas Noticias Publicadas”.
- Se eliminan duplicados por URL canónica.
- Se prefieren capturas sin parámetros de paginación.
- Cada registro se guarda en `checkpoint.ndjson`, permitiendo reanudar.
- La clasificación bilateral exige proximidad entre Estados Unidos, Paraguay y
  una acción diplomática. Las menciones multilaterales o incidentales se excluyen.

## Aspectos que todavía conviene mejorar

- Cuando una captura de Wayback devuelve 404, consultar capturas alternativas de
  la misma URL antes de marcar `error_descarga`.
- Medir la cobertura por mes y documentar meses con pocas o ninguna noticia.
- Revisar manualmente una muestra estratificada de bilaterales, menciones simples
  y casos fronterizos para calibrar los umbrales.
- Mantener todas las reglas nuevas en JSON y añadir pruebas antes de cambiarlas.

## Criterio de éxito

Una corrida completa debe entregar el manifiesto de estados, noticias válidas,
errores visibles, cobertura mensual y evidencia de clasificación por noticia. No
debe presentar como completa una serie con bloqueos o meses vacíos sin advertirlo.

