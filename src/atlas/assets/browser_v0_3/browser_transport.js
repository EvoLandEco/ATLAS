/* Decode only a checksum-verified browser core from a validated transport manifest. */
import {TABLES} from './browser_tables.js';
import {prepareSummaryView} from './site_view.js';
export const BROWSER_TRANSPORT_VERSION = '0.3.0';
export {TABLES};
const rule = 'all_supporting_records_in_window', partial = 'hide_relationship_keep_visible_assertions';
const exactKeys = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) &&
  Object.keys(value).length === keys.length && keys.every(k => Object.hasOwn(value, k));
const fail = message => { throw new Error(message); };
const ref = (array, id) => Number.isSafeInteger(id) && id >= 0 && id < array.length ? array[id] : fail('Invalid browser table reference');
export function decodeBrowserCore(core, exportId) {
  if (!exactKeys(core, ['transport_version','source_export_id','metadata','strings','eligibility_record_sets','tables']) ||
      core.transport_version !== BROWSER_TRANSPORT_VERSION || core.source_export_id !== exportId) fail('Browser core version or source mismatch');
  if (!Array.isArray(core.strings) || core.strings.some(s => typeof s !== 'string') || new Set(core.strings).size !== core.strings.length) fail('Invalid string dictionary');
  if (!Array.isArray(core.eligibility_record_sets)) fail('Invalid eligibility dictionary');
  const eligibility = core.eligibility_record_sets.map(ids => {
    if (!Array.isArray(ids)) fail('Invalid eligibility row');
    return {rule, partial, record_ids: ids.map(id => ref(core.strings, id))};
  });
  if (!exactKeys(core.tables, Object.keys(TABLES))) fail('Unexpected browser tables');
  if (!exactKeys(core.metadata, ['contract_version','snapshot','reviewed_chains','metrics']) ||
      !['1.5.0','1.6.0','1.7.0','1.8.0'].includes(core.metadata.contract_version) ||
      !exactKeys(core.metadata.metrics, ['contract_version','coverage'])) fail('Invalid browser metadata');
  const data = {...core.metadata, metrics: {...core.metadata.metrics}};
  for (const [name, spec] of Object.entries(TABLES)) {
    const table = core.tables[name];
    if (!exactKeys(table, ['columns','encoding','rows']) || JSON.stringify(table.columns) !== JSON.stringify(spec.columns) ||
        JSON.stringify(table.encoding) !== JSON.stringify(spec.encoding) || !Array.isArray(table.rows)) fail(`Invalid browser table ${name}`);
    const rows = table.rows.map(row => {
      if (!Array.isArray(row) || row.length !== spec.columns.length) fail(`Invalid tuple in ${name}`);
      return Object.fromEntries(spec.columns.map((column, i) => {
        const value = row[i], mode = spec.encoding[i];
        if (value === null) {
          if (mode === 'eligibility') fail('Missing eligibility');
          return [column, null];
        }
        return [column, mode === 'string' ? ref(core.strings, value) : mode === 'strings'
          ? (Array.isArray(value) ? value.map(id => ref(core.strings,id)) : fail('Invalid string list'))
          : mode === 'eligibility' ? ref(eligibility, value) : value];
      }));
    });
    if (name.startsWith('metrics.')) data.metrics[name.slice(8)] = rows;
    else data[name] = rows;
  }
  for (const m of data.metrics.measures) if (m.compact_figure_id !== null && (!Number.isSafeInteger(m.compact_figure_id) || m.compact_figure_id < 0)) fail('Invalid compact figure identity');
  return data;
}
export function prepareBrowserView(core, exportId) {
  const data = decodeBrowserCore(core, exportId);
  return {data, select: prepareSummaryView(data)};
}
// Full series metadata is already resident; selected method evidence comes from a verified detail store.
export function hydrateBrowserView(view, seriesById) {
  return {...view, reviewed_series: view.reviewed_series.map(summary => {
    const full = seriesById.get(summary.series_id);
    if (!full) fail(`Missing series detail ${summary.series_id}`);
    const ids = new Set(summary.evidence_ids);
    const evidence = full.evidence.filter(row => ids.has(row.id));
    if (evidence.length !== ids.size) fail('Missing series evidence');
    const {evidence_ids, ...rest} = summary;
    return {...rest, evidence};
  })};
}
