/* Map links are source assessments with explicit endpoints and quoted support. */
const mapLinkTypes = new Set(['movement', 'shared_event', 'hypothesis']);
function validateMapLinks(links, records) {
  const lookup = new Map(records.map(r => [r.id, r]));
  const ids = new Set();
  for (const link of links) {
    if (!link.id || ids.has(link.id)) throw new Error('Map link IDs must be unique');
    ids.add(link.id);
    if (!mapLinkTypes.has(link.type) || !link.label || !link.basis || !link.limit)
      throw new Error('Map link requires a type and source assessment');
    if (typeof link.directed !== 'boolean' || (link.directed && link.type !== 'movement'))
      throw new Error('Only reported movement has directed geographic endpoints');
    for (const endpoint of [link.from, link.to]) {
      if (!endpoint.label || !endpoint.precision || !Number.isFinite(endpoint.lon) ||
          !Number.isFinite(endpoint.lat) || Math.abs(endpoint.lon) > 180 || Math.abs(endpoint.lat) > 90)
        throw new Error('Map endpoint requires a location and its precision');
    }
    if (!link.support.length) throw new Error('Map link requires source evidence');
    for (const [id, index] of link.support) {
      const claim = lookup.get(id)?.claims.find(c => c.claim_index === index);
      if (!claim?.quotes?.length) throw new Error('Map link has missing quoted evidence');
    }
  }
}
function mapLinks(links, rows) {
  const ids = new Set(rows.map(r => r.id));
  return links.filter(l => l.support.every(([id]) => ids.has(id)));
}
function windowRecords(records, from, until, basis) {
  if (!['publication', 'capture'].includes(basis) || from > until) throw new Error('Invalid reporting window');
  return records.filter(r => from <= r[basis].slice(0, 10) && r[basis].slice(0, 10) <= until);
}
if (typeof module !== 'undefined') module.exports = { validateMapLinks, mapLinks, windowRecords };
