"""Standard SQL generators. No network calls or data writes at import time.

Compact GKG fields omit character offsets, which this analysis does not use.
Article and event outputs deliberately have different units of observation.
"""

from datetime import date, timedelta
import calendar


def build_proxy_b_metrics_query(window, config, catalogue):
    """Aggregate accepted proxy B in BigQuery; no article-level output."""
    start = max(window.start, date(2015, 2, 19)).isoformat()
    stop = (window.end + timedelta(days=1)).isoformat()
    partial = (window.start.day != 1 or window.start < date(2015, 2, 19) or
               window.end.day != calendar.monthrange(window.end.year, window.end.month)[1])
    verified = [(s['domain'].lower(), s['country_verified']) for s in catalogue['sources']
                if s.get('verification_status') == 'verified' and s.get('country_verified') in ('PY', 'US')]
    if not verified or len({d for d, _ in verified}) != len(verified):
        raise ValueError('Verified source panel is empty or contains duplicate domains')
    def sql(value):
        return value.replace('\\', '\\\\').replace("'", "''")
    source_rows = ',\n    '.join(f"STRUCT('{sql(d)}' AS domain, '{c}' AS source_country)" for d, c in verified)
    def pattern(key):
        values = config.get(key)
        if not values or any(not isinstance(v, str) or not v for v in values):
            raise ValueError(f'Invalid proxy theme list {key}')
        return '(^|;)(' + '|'.join(sql(v) for v in values) + ')(;|$)'
    return f"""
WITH sources AS (
  SELECT * FROM UNNEST([
    {source_rows}
  ])
), raw AS (
  SELECT g.DATE observed_at,
    REGEXP_REPLACE(g.DocumentIdentifier, r'#.*$', '') url_key,
    s.source_country, s.domain,
    SAFE_CAST(SPLIT(g.V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64) tone,
    SAFE_CAST(SPLIT(g.V2Tone, ',')[SAFE_OFFSET(1)] AS FLOAT64) positive_score,
    SAFE_CAST(SPLIT(g.V2Tone, ',')[SAFE_OFFSET(2)] AS FLOAT64) negative_score,
    REGEXP_CONTAINS(COALESCE(g.Themes, ''), r'{pattern('D')}') hit_d,
    REGEXP_CONTAINS(COALESCE(g.Themes, ''), r'{pattern('I')}') hit_i,
    REGEXP_CONTAINS(COALESCE(g.Themes, ''), r'{pattern('R')}') hit_r,
    REGEXP_CONTAINS(COALESCE(g.Themes, ''), r'{pattern('E')}') hit_e
  FROM `gdelt-bq.gdeltv2.gkg_partitioned` g
  JOIN sources s ON REGEXP_REPLACE(LOWER(NET.HOST(g.DocumentIdentifier)), r'^www\\.', '') = s.domain
  WHERE g._PARTITIONTIME >= TIMESTAMP('{start}')
    AND g._PARTITIONTIME < TIMESTAMP('{stop}')
    AND g.DATE >= {start.replace('-', '')}000000
    AND g.DATE < {stop.replace('-', '')}000000
    AND g.SourceCollectionIdentifier = 1
    AND STARTS_WITH(g.DocumentIdentifier, 'http')
    AND COALESCE(REGEXP_EXTRACT(g.TranslationInfo, r'srclc:([^;]+)'), 'eng') IN ('eng', 'spa')
    AND COALESCE(REGEXP_CONTAINS(g.Locations, r'(^|;)[1-5]#[^#;]*#PA#'), FALSE)
    AND COALESCE(REGEXP_CONTAINS(g.Locations, r'(^|;)[1-5]#[^#;]*#US#'), FALSE)
), dedup AS (
  SELECT * FROM raw
  QUALIFY ROW_NUMBER() OVER (PARTITION BY url_key ORDER BY observed_at, tone) = 1
), selected AS (
  SELECT * FROM dedup WHERE hit_d OR (hit_i AND (hit_r OR hit_e))
), expanded AS (
  SELECT s.*, country source_country_group
  FROM selected s CROSS JOIN UNNEST([s.source_country, 'BOTH']) country
), metrics AS (
  SELECT source_country_group, COUNT(*) proxy_articles,
    COUNT(DISTINCT domain) unique_domains,
    COUNT(tone) tone_n, AVG(tone) tone_mean,
    COUNT(positive_score) positive_score_n, AVG(positive_score) positive_score_mean,
    COUNT(negative_score) negative_score_n, AVG(negative_score) negative_score_mean
  FROM expanded GROUP BY source_country_group
)
SELECT DATE('{window.start.replace(day=1)}') month, country source_country,
  {str(partial).upper()} partial_month, DATE('{start}') period_start,
  DATE('{window.end}') period_end, 'proxy_b_v1_aggregate_unvalidated' selection_status,
  COALESCE(m.proxy_articles, 0) proxy_articles,
  COALESCE(m.unique_domains, 0) unique_domains,
  COALESCE(m.tone_n, 0) tone_n, m.tone_mean,
  COALESCE(m.positive_score_n, 0) positive_score_n, m.positive_score_mean,
  COALESCE(m.negative_score_n, 0) negative_score_n, m.negative_score_mean
FROM UNNEST(['PY', 'US', 'BOTH']) country
LEFT JOIN metrics m ON m.source_country_group = country
ORDER BY source_country
"""


def build_query(window, profile, theme_pattern):
    if profile not in ("articles", "events", "audit", "candidates", "candidates_themes"):
        raise ValueError("Unknown profile")
    start = max(window.start, date(2015, 2, 19)).isoformat()
    stop = (window.end + timedelta(days=1)).isoformat()
    partial = (window.start.day != 1 or window.start < date(2015, 2, 19) or
               window.end.day != calendar.monthrange(window.end.year, window.end.month)[1])
    theme_pattern = theme_pattern.replace("'", "''")
    base = f"""
WITH sources AS (
  SELECT LOWER(Domain) domain,
    MIN(IF(CountryHumanName = 'Paraguay', 'PY', 'US')) source_country
  FROM `gdelt-bq.gdeltv2.domainsbycountry_alllangs_april2015`
  GROUP BY domain
  HAVING COUNT(DISTINCT CountryHumanName) = 1
    AND MIN(CountryHumanName) IN ('Paraguay', 'United States', 'United States of America')
),
raw AS (
  SELECT g.DATE observed_at, g.DocumentIdentifier url,
    -- Preserve meaningful query parameters, e.g. ?id=123. Only drop fragments.
    REGEXP_REPLACE(g.DocumentIdentifier, r'#.*$', '') url_key,
    s.source_country, LOWER(g.SourceCommonName) domain,
    SAFE_CAST(SPLIT(g.V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64) tone,
    SAFE_CAST(SPLIT(g.V2Tone, ',')[SAFE_OFFSET(1)] AS FLOAT64) positive_score,
    SAFE_CAST(SPLIT(g.V2Tone, ',')[SAFE_OFFSET(2)] AS FLOAT64) negative_score,
    SAFE_CAST(SPLIT(g.V2Tone, ',')[SAFE_OFFSET(3)] AS FLOAT64) polarity,
    COALESCE(REGEXP_CONTAINS(g.Locations, r'(^|;)[1-5]#[^#;]*#PA#'), FALSE) mentions_py,
    COALESCE(REGEXP_CONTAINS(g.Locations, r'(^|;)[1-5]#[^#;]*#US#'), FALSE) mentions_us,
    (NULLIF(g.Organizations, '') IS NOT NULL OR
      REGEXP_CONTAINS(COALESCE(g.Themes, ''), r'{theme_pattern}')) institutional_signal,
    NULLIF(g.Persons, '') IS NOT NULL has_named_person,
    g.Persons persons, g.Organizations organizations, g.Themes themes,
    COALESCE(REGEXP_EXTRACT(g.TranslationInfo, r'srclc:([^;]+)'), 'eng') language
  FROM `gdelt-bq.gdeltv2.gkg_partitioned` g
  JOIN sources s ON LOWER(g.SourceCommonName) = s.domain
  WHERE g._PARTITIONTIME >= TIMESTAMP('{start}')
    AND g._PARTITIONTIME < TIMESTAMP('{stop}')
    AND g.DATE >= {start.replace('-', '')}000000
    AND g.DATE < {stop.replace('-', '')}000000
    AND g.SourceCollectionIdentifier = 1
    AND STARTS_WITH(g.DocumentIdentifier, 'http')
    AND COALESCE(REGEXP_EXTRACT(g.TranslationInfo, r'srclc:([^;]+)'), 'eng') IN ('eng', 'spa')
),
dedup AS (
  SELECT * FROM raw
  QUALIFY ROW_NUMBER() OVER (PARTITION BY url_key ORDER BY observed_at, url, tone) = 1
),
corpus AS (
  SELECT *, mentions_py AND mentions_us AND institutional_signal eligible
  FROM dedup
)
"""
    if profile in ('candidates', 'candidates_themes'):
        # Remove unused metadata explicitly; retain broad controls for review.
        first = base.index('    (NULLIF(g.Organizations')
        last = base.index('    COALESCE(REGEXP_EXTRACT(g.TranslationInfo', first)
        base = base[:first] + base[last:]
        if profile == 'candidates_themes':
            base = base[:first] + '    g.Themes themes,\n' + base[first:]
        base = base.replace('SELECT *, mentions_py AND mentions_us AND institutional_signal eligible',
                            'SELECT *')
        # Cheaper screening only: optimizer need not read Persons, Organizations
        # or Themes. These are NOT institutionally validated observations.
        return base + f"""
SELECT DATE('{window.start.replace(day=1)}') month, source_country,
  {str(partial).upper()} partial_month,
  DATE('{start}') period_start, DATE('{window.end}') period_end,
  'geographic_cooccurrence_unvalidated' selection_status,
  observed_at, url, url_key, domain, language, tone,
  positive_score, negative_score, polarity{', themes' if profile == 'candidates_themes' else ''}
FROM corpus
WHERE mentions_py AND mentions_us
ORDER BY source_country, observed_at, url_key
"""
    if profile == 'audit':
        return base + f"""
SELECT DATE('{window.start.replace(day=1)}') month, source_country,
  {str(partial).upper()} partial_month,
  DATE('{start}') period_start, DATE('{window.end}') period_end,
  observed_at, url, url_key, domain, language, tone,
  positive_score, negative_score, polarity, institutional_signal,
  has_named_person, persons, organizations, themes, eligible
FROM corpus
WHERE mentions_py AND mentions_us
ORDER BY source_country, observed_at, url_key
"""
    if profile == "articles":
        return base + f"""
, metrics AS (
  SELECT IF(GROUPING(corpus.source_country) = 1, 'BOTH', corpus.source_country) source_country,
    COUNT(*) monitored_articles,
    COUNTIF(mentions_py) articles_mentioning_py,
    COUNTIF(mentions_us) articles_mentioning_us,
    COUNTIF(mentions_py OR mentions_us) articles_mentioning_either,
    COUNTIF(mentions_py AND mentions_us) cooccurrence_articles,
    COUNTIF(eligible) unique_articles,
    COUNTIF(eligible AND NOT has_named_person) articles_without_named_person,
    COUNTIF(eligible AND language = 'spa') spanish_articles,
    COUNT(DISTINCT IF(eligible, domain, NULL)) unique_domains,
    COUNT(DISTINCT IF(eligible, DIV(observed_at, 1000000), NULL)) covered_days,
    COUNTIF(eligible AND tone IS NOT NULL) tone_observations,
    AVG(IF(eligible, tone, NULL)) tone_mean,
    STDDEV_SAMP(IF(eligible, tone, NULL)) tone_sd,
    APPROX_QUANTILES(IF(eligible, tone, NULL), 100)[SAFE_OFFSET(25)] tone_p25,
    APPROX_QUANTILES(IF(eligible, tone, NULL), 100)[SAFE_OFFSET(50)] tone_median,
    APPROX_QUANTILES(IF(eligible, tone, NULL), 100)[SAFE_OFFSET(75)] tone_p75,
    AVG(IF(eligible, positive_score, NULL)) positive_score_mean,
    AVG(IF(eligible, negative_score, NULL)) negative_score_mean,
    AVG(IF(eligible, polarity, NULL)) polarity_mean,
    AVG(IF(eligible, CAST(tone > 1 AS INT64), NULL)) positive_share,
    AVG(IF(eligible, CAST(tone BETWEEN -1 AND 1 AS INT64), NULL)) neutral_share,
    AVG(IF(eligible, CAST(tone < -1 AS INT64), NULL)) negative_share,
    AVG(IF(eligible, CAST(has_named_person AS INT64), NULL)) named_person_share
  FROM corpus GROUP BY GROUPING SETS ((corpus.source_country), ())
)
SELECT DATE('{window.start.replace(day=1)}') month, s.source_country,
  {str(partial).upper()} partial_month,
  DATE('{start}') period_start, DATE('{window.end}') period_end,
  'institutional_cooccurrence_proxy' corpus_definition,
  'gdelt_april2015_estimated_catalogue' source_country_method,
  COALESCE(m.monitored_articles, 0) monitored_articles,
  COALESCE(m.unique_articles, 0) unique_articles,
  m.* EXCEPT(source_country, monitored_articles, unique_articles),
  SAFE_DIVIDE(m.unique_articles, m.articles_mentioning_py) bilateral_share_of_py,
  SAFE_DIVIDE(m.unique_articles, m.articles_mentioning_us) bilateral_share_of_us,
  SAFE_DIVIDE(m.unique_articles, m.articles_mentioning_either) bilateral_share_of_either,
  SAFE_DIVIDE(m.unique_articles, m.monitored_articles) bilateral_share_of_monitored
FROM UNNEST(['PY', 'US', 'BOTH']) s_country
CROSS JOIN UNNEST([STRUCT(s_country AS source_country)]) s
LEFT JOIN metrics m USING(source_country)
ORDER BY source_country
"""

    # Event cohort: only events first recorded within this month. Resolving ALL
    # historical events mentioned this month would need an all-history join.
    # Use local document tone; e.AvgTone / e.NumMentions include worldwide media.
    return base + f"""
, links AS (
  SELECT DISTINCT c.source_country, e.GLOBALEVENTID event_id,
    IF(e.Actor1CountryCode = 'PRY', 'PY_TO_US', 'US_TO_PY') direction,
    c.url_key, c.tone, e.GoldsteinScale goldstein, e.QuadClass quad_class
  FROM corpus c
  JOIN `gdelt-bq.gdeltv2.eventmentions_partitioned` m
    ON REGEXP_REPLACE(m.MentionIdentifier, r'#.*$', '') = c.url_key
  JOIN `gdelt-bq.gdeltv2.events_partitioned` e USING(GLOBALEVENTID)
  WHERE c.eligible
    AND m._PARTITIONTIME >= TIMESTAMP('{start}') AND m._PARTITIONTIME < TIMESTAMP('{stop}')
    AND e._PARTITIONTIME >= TIMESTAMP('{start}') AND e._PARTITIONTIME < TIMESTAMP('{stop}')
    AND ((e.Actor1CountryCode = 'PRY' AND e.Actor2CountryCode = 'USA') OR
         (e.Actor1CountryCode = 'USA' AND e.Actor2CountryCode = 'PRY'))
), expanded AS (
  SELECT l.* EXCEPT(source_country), sc source_country, d direction_group
  FROM links l
  CROSS JOIN UNNEST([l.source_country, 'BOTH']) sc
  CROSS JOIN UNNEST([l.direction, 'TOTAL']) d
), per_event AS (
  SELECT source_country, direction_group, event_id,
    COUNT(DISTINCT url_key) local_article_mentions,
    AVG(tone) local_event_tone, COUNT(tone) valid_tone_links,
    SUM(tone) local_tone_sum, MIN(goldstein) goldstein, MIN(quad_class) quad_class
  FROM expanded GROUP BY source_country, direction_group, event_id
), metrics AS (
  SELECT source_country, direction_group, COUNT(*) unique_events,
    SUM(local_article_mentions) event_article_links,
    AVG(local_event_tone) event_tone_mean,
    SAFE_DIVIDE(SUM(local_tone_sum), SUM(valid_tone_links)) event_tone_weighted,
    AVG(goldstein) goldstein_mean,
    COUNTIF(quad_class = 1) verbal_cooperation,
    COUNTIF(quad_class = 2) material_cooperation,
    COUNTIF(quad_class = 3) verbal_conflict,
    COUNTIF(quad_class = 4) material_conflict
  FROM per_event GROUP BY source_country, direction_group
)
SELECT DATE('{window.start.replace(day=1)}') month, sc source_country, d direction,
  {str(partial).upper()} partial_month,
  DATE('{start}') period_start, DATE('{window.end}') period_end,
  'first_recorded_same_month' event_cohort,
  COALESCE(m.unique_events, 0) unique_events,
  m.* EXCEPT(source_country, direction_group, unique_events)
FROM UNNEST(['PY', 'US', 'BOTH']) sc
CROSS JOIN UNNEST(['PY_TO_US', 'US_TO_PY', 'TOTAL']) d
LEFT JOIN metrics m ON m.source_country = sc AND m.direction_group = d
ORDER BY source_country, direction
"""
