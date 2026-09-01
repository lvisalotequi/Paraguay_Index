# Selección de trabajo y campos afinados

Selección vigente, revisión 2: solo los 9 registros incluidos (4 centrales y
5 contextuales). Los 17 dudosos quedan fuera, sin reclasificarlos como excluidos.
Las 41 exclusiones también quedan fuera, pero todos siguen en los originales y
en classification_v1.json para conservar trazabilidad y estudiar falsos positivos.
No se ejecutó ninguna consulta, estimación ni cambio de configuración en Google Cloud.

## Campos conservados

| Grupo | Campos | Uso |
| --- | --- | --- |
| Identidad | review_id, url, url_key, domain, domain_gdelt | Vincular auditoría y controlar duplicados sin confundir medio con propietario |
| Tiempo | observed_at_gdelt, month, periodo y partial_month | Fecha de observación; no se inventa fecha de publicación |
| País e idioma | language_gdelt, source_country_gdelt, source_country_verified, country_status | Separar estimación heredada de verificación editorial |
| Tono | tone, positive_score, negative_score, polarity | Conservar medidas disponibles; valores ausentes no se convierten en cero |
| Relevancia | decision, eligible_for_confirmed_metrics, focus, reason_code, historical_focus | Distinguir incluidos, contexto y pendientes |
| Evidencia | content_access, evidence_urls, reviewed_on, unresolved | Saber qué se verificó y qué falta resolver |
| Republicación | related_article_ids | Señalar relación entre notas sin eliminar automáticamente publicaciones distintas |

publication_date_verified queda nulo: esta fase no verificó sistemáticamente
la fecha original de cada texto. La nota 67 queda únicamente en la auditoría,
fuera de la selección vigente.

## Campos que no se repiten en la selección compacta

Persons, Organizations, Themes, institutional_signal, has_named_person y eligible
permanecen en el CSV de auditoría, pero no se usan como prueba de pertinencia.
La decisión revisada reemplaza al indicador automático para este piloto.
Los contadores de bytes pertenecen al trabajo de extracción, no a cada noticia:
no se suman las copias repetidas de esos contadores en las filas del CSV.

Los motivos completos permanecen en classification_v1.json; se enlazan por
review_id/url. El catálogo de países permanece en media_catalogue_v1.json.

## Reglas de uso

- Solo eligible_for_confirmed_metrics=true integra una futura métrica confirmada.
  Los 17 dudosos no cuentan como válidos, excluidos ni tono cero.
- Conservar las cinco inclusiones contextuales separables de las cuatro centrales.
- unresolved está vacío en los nueve incluidos; la auditoría conserva las dudas.
  No se asignan contrapartes institucionales a partir de nombres detectados por GDELT.
- No usar los 9 registros como denominador de todo el ecosistema informativo:
  son únicamente las inclusiones de este piloto.
- Mantener las 41 exclusiones como controles negativos al probar reglas nuevas.
  Afinar solo con positivos no permite comprobar falsos positivos.
- No se recalculó tono: primero resolver o separar explícitamente la incertidumbre.

## Implicaciones para futuras extracciones

El perfil candidates existente ya devuelve fecha, URL, dominio, idioma y los
cuatro componentes numéricos de tono usados aquí. Puede servir de base ligera,
pero exige clasificación posterior y no incluye denominadores. No se cambió
SQL ni se aseguró un ahorro nuevo: reducir campos en un archivo local no
reduce retroactivamente los bytes procesados por BigQuery.

No convertir estos 9 enlaces ni sus medios en una lista blanca del histórico.
Son un conjunto de trabajo de tres días, no una definición exhaustiva del estudio.

## Reproducción local

prepare_pilot_selection.py utiliza solo la biblioteca estándar y archivos locales.
Valida correspondencia de URLs antes de seleccionar, conserva las cuatro medidas
de tono y emite JSON por salida estándar; no escribe ni sobrescribe archivos.
working_selection_v2.json es la instantánea vigente, con hash del CSV de entrada.
working_selection_v1.json se conserva solo como antecedente de 26 registros;
el script ahora reproduce v2. No se necesitan credenciales ni facturación.

```powershell
.\.venv\Scripts\python.exe prepare_pilot_selection.py
.\.venv\Scripts\python.exe -m unittest -v test_pilot_selection.py test_pilot_review.py test_bilateral_media_extractor.py
```
