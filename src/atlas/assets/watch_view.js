/* Use the exact scientific selector's record IDs before limiting displayed items. */
export function selectWatch(data, selectedRecordIds, knowledgeCutoff = null) {
  if (data.watch_version !== '0.1.0') throw new Error('Unsupported watch contract');
  const ids = new Set(selectedRecordIds);
  const cutoff = knowledgeCutoff === null ? null : Date.parse(knowledgeCutoff);
  if (cutoff !== null && (Number.isNaN(cutoff) || !/(Z|[+-]\d{2}:\d{2})$/.test(knowledgeCutoff))) throw new Error('Cutoff needs an explicit timezone');
  return data.items.filter(item => item.eligibility.record_ids.every(id => ids.has(id)) &&
    (cutoff === null || Date.parse(item.reviewed_at) <= cutoff));
}
