// Read-only CSV inspection plus JSON annotations; original data never modified.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { Workbook } from '@oai/artifact-tool';

const root = path.resolve('output/gdelt');
async function readRows(file) {
  const wb = await Workbook.fromCSV((await fs.readFile(file, 'utf8')).replace(/^\uFEFF/, ''), { sheetName: 'Data' });
  const values = wb.worksheets.getItemAt(0).getUsedRange().values;
  const [head, ...body] = values;
  return body.filter(r => r[0] !== null && r[0] !== '').map(r => Object.fromEntries(head.map((h, i) => [h, r[i]])));
}
const metricsPath = path.join(root, 'articles/2025-01-pilot3d_c1a2845287c9a69d00e2.csv');
const auditPath = path.join(root, 'audit/2025-01-pilot3d_1866e9bca2eaae69a1f2.csv');
const metrics = await readRows(metricsPath);
const audit = await readRows(auditPath);
const yes = x => String(x).toLowerCase() === 'true';
const numeric = x => x === null || x === '' ? null : Number(x);
const candidates = audit.filter(r => yes(r.eligible));
const reviewed = new Map([
  ['https://www.ultimahora.com/tras-acusaciones-de-pena-ostfield-brinda-en-las-fiestas-por-fortalecer-lazos-entre-eeuu-y-paraguay', ['include_institutional', 'Relación diplomática y cooperación; texto revisado.']],
  ['https://www.abc.com.py/politica/2025/01/01/el-mensaje-del-embajador-de-eeuu-tras-la-dura-critica-de-santiago-pena/', ['include_institutional', 'Declaraciones oficiales sobre la relación bilateral; texto revisado.']],
  ['https://www.ultimahora.com/dea-segun-rachid-negociaciones-son-entre-santi-y-donald-trump', ['include_institutional', 'Negociación intergubernamental Senad–DEA; texto revisado.']],
  ['https://www.lanacion.com.py/lnpop/2025/01/01/maquillaje-con-proposito-la-inspiradora-trayectoria-de-ana-brizuena/', ['exclude_personal', 'Perfil de maquilladora/influencer; texto revisado. GDELT Persons vacío.']],
]);
const sports = /\/(deportes|athletic|futboledicion-impresa)\/|premier-league|nba\/|mundial-de-rally/;
const entertainment = /\/(lnpop|espectaculos)\/|cinco-discos-del-2024|festival-internacional-del-nuevo-cine/;
const commercial = /penny-stocks|shares-up-8-1|bitcoin-mining-powerhouse|announcement-fee-updates/;
const annotations = audit.map(row => {
  const u = new URL(row.url);
  const flags = [];
  if (sports.test(u.pathname) || ['d10.ultimahora.com', 'mlsmultiplex.com'].includes(u.hostname)) flags.push('sports_section_candidate');
  if (entertainment.test(u.pathname)) flags.push('entertainment_candidate');
  if (commercial.test(u.pathname)) flags.push('commercial_candidate');
  if (u.hostname.endsWith('usgs.gov')) flags.push('government_bulletin_not_news_outlet');
  let decision = reviewed.get(row.url) ?? ['pending', 'Sin lectura completa; no clasificar definitivamente por URL.'];
  if (u.hostname === 'listindiario.com') {
    flags.push('source_country_error_verified');
    decision = ['exclude_source_country', 'Sede dominicana verificada: https://listindiario.com/aviso-legal.html'];
  }
  return { url: row.url, source_country_gdelt: row.source_country,
    original_eligible: yes(row.eligible), original_has_named_person: yes(row.has_named_person),
    decision: decision[0], basis: decision[1], flags };
});
const checks = [];
for (const country of ['PY', 'US']) {
  const records = candidates.filter(r => r.source_country === country);
  const tones = records.map(r => numeric(r.tone)).filter(x => x !== null);
  const metric = metrics.find(r => r.source_country === country);
  assert.equal(records.length, Number(metric.unique_articles));
  assert.equal(audit.filter(r => r.source_country === country).length, Number(metric.cooccurrence_articles));
  const mean = tones.reduce((a, b) => a + b, 0) / tones.length;
  assert.ok(Math.abs(mean - Number(metric.tone_mean)) < 1e-10);
  assert.ok(Math.abs(['positive_share', 'neutral_share', 'negative_share'].reduce((a, k) => a + Number(metric[k]), 0) - 1) < 1e-10);
  checks.push({ country, cooccurrences: audit.filter(r => r.source_country === country).length,
    provisional_candidates: records.length, tone_mean_provisional: mean });
}
const allTones = candidates.map(r => numeric(r.tone)).filter(x => x !== null);
const correctedCombined = {
  note: 'Recalculado localmente, sin repetir consulta. No es una métrica validada de relación bilateral.',
  monitored_articles: metrics.filter(r => r.source_country !== 'BOTH').reduce((a, r) => a + Number(r.monitored_articles), 0),
  cooccurrence_articles: audit.length,
  unique_articles_provisional: candidates.length,
  unique_domains: new Set(candidates.map(r => r.domain)).size,
  tone_mean_provisional: allTones.reduce((a, b) => a + b, 0) / allTones.length,
};
assert.equal(correctedCombined.unique_articles_provisional, checks.reduce((a, r) => a + r.provisional_candidates, 0));
const rawBoth = metrics.find(r => r.source_country === 'BOTH');
const report = {
  period_start: '2025-01-01', period_end: '2025-01-03', partial_month: true,
  inputs: { metricsPath, auditPath },
  raw_combined_row_invalid: Number(rawBoth.unique_articles) !== candidates.length,
  explanation: 'GROUP BY resolvía el alias y el subtotal quedaba NULL. SQL corregido con GROUPING(corpus.source_country). Conservar original como evidencia, no usar su fila BOTH.',
  checks, correctedCombined,
  decisions: Object.fromEntries([...new Set(annotations.map(r => r.decision))].map(k => [k, annotations.filter(r => r.decision === k).length])),
  heuristic_flagged: annotations.filter(r => r.flags.length).length,
  heuristic_flags_are_not_final_exclusions: true,
  annotations,
};
await fs.mkdir(path.join(root, 'review'), { recursive: true });
await fs.writeFile(path.join(root, 'review/pilot_review.json'), JSON.stringify(report, null, 2), 'utf8');
console.log(JSON.stringify({ checks, correctedCombined, decisions: report.decisions,
  heuristic_flagged: report.heuristic_flagged, combined_row_invalid: report.raw_combined_row_invalid }, null, 2));
