/* ATLAS reporting-window rules. Validate the bundle at build time with atlas site-verify. */
export const COMPACT_GROUPING_VERSION = '1.0.0';
const metricOrder = ['cases', 'deaths', 'hospitalizations', 'affected_holdings', 'affected_animals', 'samples_tested', 'positive_samples', 'test_positivity', 'other'];
const figureFields = ['label', 'metric', 'value', 'value_status', 'unit', 'count_kind', 'case_class', 'date_basis',
  'period_start', 'period_end', 'case_definition', 'population', 'stratum', 'denominator', 'denominator_status',
  'qualifier', 'origin_authority', 'disease', 'pathogen', 'host', 'geography', 'acquisition', 'transmission_role',
  'as_of', 'period_label', 'denominator_population', 'ratio_basis', 'cumulative_baseline', 'track_id',
  'review_status', 'observation_date', 'observation_date_status', 'source_date_warning'];
const ordered = value => Array.isArray(value) ? value.map(ordered) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, ordered(value[key])])) : value;

export function selectView(data, from, until, basis = 'publication', knowledgeCutoff = null, recordSelection = null, oneHealthOptions = null) {
  if (!['1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0'].includes(data.contract_version)) throw new Error('Unsupported ATLAS site contract');
  const day = value => /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
  if (!day(from) || !day(until) || from > until || !['publication', 'capture'].includes(basis)) throw new Error('Invalid reporting window');
  const cutoff = knowledgeCutoff === null ? null : Date.parse(knowledgeCutoff);
  if (cutoff !== null && (Number.isNaN(cutoff) || !/(Z|[+-]\d{2}:\d{2})$/.test(knowledgeCutoff))) throw new Error('Cutoff needs an explicit timezone');
  const cutoffDay = cutoff === null ? null : new Date(cutoff).toISOString().slice(0, 10);
  const selection = recordSelection === null ? null : new Set(recordSelection);
  const knownRecords = new Set(data.records.map(r => r.id));
  if (selection && [...selection].some(id => !knownRecords.has(id))) throw new Error('Unknown selected record');
  const records = data.records.filter(r => from <= r[basis].slice(0, 10) && r[basis].slice(0, 10) <= until &&
    (selection === null || selection.has(r.id)) &&
    (cutoff === null || (Date.parse(r.capture) <= cutoff && r.publication.slice(0, 10) <= cutoffDay)));
  const recordIds = new Set(records.map(r => r.id));
  const recordOrder = new Map(records.map((r, i) => [r.id, i]));
  const supported = rule => rule.record_ids.every(id => recordIds.has(id));
  const assertions = data.assertions.filter(a => supported(a.eligibility));
  const comparisons = data.comparisons.filter(c => supported(c.eligibility));
  const superseded = new Set(comparisons.flatMap(c => c.lineage.map(e => e.from_assertion_id)));
  const measureIds = new Set(assertions.filter(a => a.measure_id && !superseded.has(a.id)).map(a => a.measure_id));
  const measures = new Map(data.metrics.measures.map(m => [m.measure_id, m]));
  const separateAssertions = new Set(comparisons.filter(c => ['contradiction', 'different_scope', 'unresolved_association'].includes(c.kind)).flatMap(c => c.participant_ids));
  const separateMeasures = new Set(assertions.filter(a => separateAssertions.has(a.id)).map(a => a.measure_id));
  const figureKeys = new Map(data.metrics.measures.map(m => {
    const groupable = m.value_status === 'reported' && Number.isFinite(m.value) && m.observation_date !== null &&
      m.observation_date_status === 'reported' && !m.conflict_set && !separateMeasures.has(m.measure_id) &&
      figureFields.every(field => Object.hasOwn(m, field));
    return [m.measure_id, groupable ? JSON.stringify(figureFields.map(field => ordered(m[field]))) : `measure:${m.measure_id}`];
  }));
  const panels = data.metrics.panels.map(p => {
    const ids = p.measure_ids.filter(id => measureIds.has(id));
    const groups = new Map();
    for (const id of ids) {
      const m = measures.get(id), group = groups.get(m.context_id) ?? [];
      group.push(m); groups.set(m.context_id, group);
    }
    const cards = [...groups].map(([context_id, rows]) => {
      const dates = rows.map(m => m.observation_date).filter(Boolean).sort();
      const latest = dates.at(-1) ?? null;
      const selected = latest === null ? rows : rows.filter(m => m.observation_date === latest);
      return { context_id, observation_date: latest, measure_ids: selected.map(m => m.measure_id), priority: Math.min(...selected.map(m => m.priority)) };
    }).sort((a, b) => a.priority - b.priority || (b.observation_date ?? '').localeCompare(a.observation_date ?? '') || a.context_id.localeCompare(b.context_id));
    // Display repetition is grouped after evidence filtering and before the card limit.
    const figures = new Map();
    for (const card of cards) for (const id of card.measure_ids) {
      const m = measures.get(id), key = figureKeys.get(id);
      if (!figures.has(key)) figures.set(key, {label: m.label, metric: m.metric, value: m.value, value_status: m.value_status,
        unit: m.unit, observation_date: m.observation_date, priority: card.priority, measure_ids: [], context_ids: [], source_ids: [],
        basis: 'matching_recorded_scope_and_value', comparability_status: 'not_established'});
      const figure = figures.get(key);
      figure.measure_ids.push(id); figure.context_ids.push(m.context_id); figure.source_ids.push(m.source_id);
    }
    const compact = [...figures.values()].map(g => ({...g, id: `compact:${[...g.measure_ids].sort().join('|')}`,
      context_ids: [...new Set(g.context_ids)].sort(), source_ids: [...new Set(g.source_ids)].sort()}))
      .sort((a, b) => a.priority - b.priority || (b.observation_date ?? '').localeCompare(a.observation_date ?? '') ||
        metricOrder.indexOf(a.metric) - metricOrder.indexOf(b.metric) || a.id.localeCompare(b.id));
    return { kind: p.kind, id: p.id, measure_ids: ids, card_groups: cards.slice(0, 3),
      compact_groups: compact.slice(0, 3), compact_group_count: compact.length };
  });
  const assertionMeasures = new Map(assertions.filter(a => a.measure_id).map(a => [a.id, a.measure_id]));
  const disputedMeasures = new Set(comparisons.filter(c => c.kind === 'contradiction').flatMap(c => c.participant_ids.map(id => assertionMeasures.get(id))));
  const incompatible = new Map();
  for (const c of comparisons.filter(c => ['different_scope', 'unresolved_association'].includes(c.kind))) {
    for (const id of c.participant_ids.map(id => assertionMeasures.get(id)).filter(Boolean)) {
      if (!incompatible.has(id)) incompatible.set(id, new Set());
      incompatible.get(id).add(c.id);
    }
  }
  const reviewedSeries = (data.metrics.reviewed_series ?? []).map(series => {
    const members = series.members.filter(m => measureIds.has(m.measure_id) && supported(m.eligibility));
    const ids = new Set(members.map(m => m.measure_id));
    const connections = series.connections.filter(e => ids.has(e.from_measure_id) && ids.has(e.to_measure_id) &&
      supported(e.eligibility) && !disputedMeasures.has(e.from_measure_id) && !disputedMeasures.has(e.to_measure_id) &&
      ![...(incompatible.get(e.from_measure_id) ?? [])].some(id => incompatible.get(e.to_measure_id)?.has(id)));
    const evidenceIds = new Set([...members, ...connections].flatMap(m => m.evidence_ids));
    return {...series, members, connections, evidence: series.evidence.filter(e => evidenceIds.has(e.id))};
  }).filter(s => s.members.length);
  const measuredRecords = new Set(data.metrics.measures.filter(m => measureIds.has(m.measure_id)).map(m => m.source_reference?.record_id));
  const relationships = data.relationships.filter(r => supported(r.eligibility));
  const relationIds = new Set(relationships.map(r => r.id));
  const locationIds = new Set(data.location_memberships.filter(m => recordIds.has(m.record_id) && supported(m.eligibility)).map(m => m.id));
  const placeIds = data.places.filter(p => p.location_membership_ids.some(id => locationIds.has(id)) || p.relationship_ids.some(id => relationIds.has(id))).map(p => p.id);
  const reviewedChains = (data.reviewed_chains ?? []).map(chain => {
    const nodes = chain.nodes.filter(n => supported(n.eligibility));
    const byId = new Map(nodes.map(n => [n.id, n]));
    const edges = chain.edges.filter(e => byId.has(e.from_node_id) && byId.has(e.to_node_id) && supported(e.eligibility));
    return {...chain, nodes, edges,
      selection_complete: nodes.length === chain.nodes.length && edges.length === chain.edges.length,
      drawable_edge_ids: edges.filter(e => byId.get(e.from_node_id).place_id !== null &&
        byId.get(e.to_node_id).place_id !== null).map(e => e.id)};
  }).filter(chain => chain.nodes.length);
  const diseases = new Map((data.diseases ?? []).map(d => [d.id, d.label]));
  const diseaseReviews = new Map((data.disease_reviews ?? []).map(r => [r.record_id, r]));
  const slices = new Map(), overlapping = new Map();
  const unknownReasons = {not_reviewed: [], unresolved: [], support_outside_selection: []};
  let reviewedCount = 0;
  for (const record of records) {
    const review = diseaseReviews.get(record.id);
    const active = review && supported(review.eligibility);
    let id = 'unclassified', label = 'Unclassified', kind = 'unclassified';
    if (active) {
      reviewedCount++;
      kind = review.kind;
      if (kind === 'single_disease') {
        id = review.disease_ids[0]; label = diseases.get(id);
      } else if (kind === 'multiple_diseases') {
        id = kind; label = 'Multiple diseases';
      } else if (kind === 'not_disease_specific') {
        id = kind; label = 'No disease-specific subject';
      } else { kind = 'unclassified'; unknownReasons.unresolved.push(record.id); }
      for (const diseaseId of review.disease_ids) {
        if (!overlapping.has(diseaseId)) overlapping.set(diseaseId, {id: diseaseId, label: diseases.get(diseaseId), record_ids: []});
        overlapping.get(diseaseId).record_ids.push(record.id);
      }
    } else unknownReasons[review ? 'support_outside_selection' : 'not_reviewed'].push(record.id);
    if (!slices.has(id)) slices.set(id, {id, label, kind, record_ids: []});
    slices.get(id).record_ids.push(record.id);
  }
  const partition = [...slices.values()].map(s => ({...s, count: s.record_ids.length,
    proportion: records.length ? s.record_ids.length / records.length : null}))
    .sort((a, b) => b.count - a.count || a.id.localeCompare(b.id));
  const diseaseComposition = {
    version: '1.0.0', meaning: 'reporting_attention', counting_unit: 'report_entry',
    denominator: records.length, denominator_basis: 'all_selected_report_entries',
    partition: true, partition_rule: 'single_disease_or_multiple_or_not_specific_or_unclassified',
    chart: records.length ? 'ring' : 'empty', reviewed_record_count: reviewedCount,
    unclassified_record_count: slices.get('unclassified')?.record_ids.length ?? 0,
    categories: partition, unknown_reasons: unknownReasons,
    overlapping_diseases: {partition: false, chart: 'bar',
      categories: [...overlapping.values()].map(s => ({...s, count: s.record_ids.length}))
        .sort((a, b) => b.count - a.count || a.id.localeCompare(b.id))},
  };
  const ohOptions = oneHealthOptions ?? {};
  if (Object.keys(ohOptions).some(k => !['domains','observation_from','observation_until'].includes(k))) throw new Error('Unknown One Health selection option');
  const domains = ohOptions.domains == null ? null : new Set(ohOptions.domains);
  if (domains && [...domains].some(d => !['human','animal','environment','food','unknown'].includes(d))) throw new Error('Unknown One Health domain');
  const obsFrom = ohOptions.observation_from ?? null, obsUntil = ohOptions.observation_until ?? null;
  if ((obsFrom === null) !== (obsUntil === null) || (obsFrom !== null && (!day(obsFrom) || !day(obsUntil) || obsFrom > obsUntil))) throw new Error('Invalid observation window');
  const eligibleNodes = (data.one_health_nodes ?? []).filter(n => supported(n.eligibility) && (!domains || domains.has(n.domain)));
  const interval = n => n.observation_date.value ? [n.observation_date.value,n.observation_date.value] :
    n.period_start.value && n.period_end.value ? [n.period_start.value,n.period_end.value] : null;
  const ohNodes = eligibleNodes.filter(n => obsFrom === null || (interval(n) && interval(n)[0] <= obsUntil && interval(n)[1] >= obsFrom));
  const ohNodeIds = new Set(ohNodes.map(n => n.id));
  const contested = new Map();
  for (const c of comparisons.filter(c => c.kind === 'contradiction')) for (const aid of c.participant_ids) {
    if (!contested.has(aid)) contested.set(aid, []); contested.get(aid).push(c.id);
  }
  const ohRelations = (data.one_health_relations ?? []).filter(r => ohNodeIds.has(r.from_node_id) && ohNodeIds.has(r.to_node_id) &&
    supported(r.eligibility) && !superseded.has(r.source_assertion_id)).map(r => ({...r,
      contested: contested.has(r.source_assertion_id), comparison_ids: contested.get(r.source_assertion_id) ?? []}));
  const ohReviews = new Map((data.one_health_reviews ?? []).map(r => [r.record_id,r]));
  const ohCoverage = {selected_records: records.length, reviewed: 0, partial: 0, unresolved: 0, no_relevant_observation: 0,
    not_reviewed: 0, support_outside_selection: 0, pending_record_ids: [], observations_by_domain: {}, records_by_domain: {}, relationships_by_kind: {}, relationships_by_basis: {}};
  for (const r of records) {
    const review = ohReviews.get(r.id), state = !review ? 'not_reviewed' : !supported(review.eligibility) ? 'support_outside_selection' : review.outcome;
    ohCoverage[state]++;
    if (!['reviewed','no_relevant_observation'].includes(state)) ohCoverage.pending_record_ids.push(r.id);
  }
  const domainRecords = new Map();
  for (const n of ohNodes) {
    ohCoverage.observations_by_domain[n.domain] = (ohCoverage.observations_by_domain[n.domain] ?? 0) + 1;
    if (!domainRecords.has(n.domain)) domainRecords.set(n.domain,new Set());domainRecords.get(n.domain).add(n.record_id);
  }
  for (const [domain, ids] of domainRecords) ohCoverage.records_by_domain[domain] = ids.size;
  for (const r of ohRelations) {
    ohCoverage.relationships_by_kind[r.kind] = (ohCoverage.relationships_by_kind[r.kind] ?? 0) + 1;
    ohCoverage.relationships_by_basis[r.basis] = (ohCoverage.relationships_by_basis[r.basis] ?? 0) + 1;
  }
  const oneHealth = {nodes: ohNodes, relations: ohRelations, coverage: ohCoverage,
    undated_nodes: obsFrom === null ? [] : eligibleNodes.filter(n => interval(n) === null),
    reviews: [...ohReviews.values()].filter(r => recordIds.has(r.record_id) && supported(r.eligibility)),
    observation_window: obsFrom === null ? null : {from: obsFrom, until: obsUntil},
    geographic_projection: 'reviewed_places_only_no_inferred_arcs',
    counting_unit: 'source_observation', comparability: 'no_cross_domain_aggregation'};
  return {
    one_health: oneHealth,
    disease_composition: diseaseComposition,
    compact_grouping_version: COMPACT_GROUPING_VERSION,
    record_ids: records.map(r => r.id), document_ids: [...new Set(records.map(r => r.document_id))],
    assertion_ids: assertions.map(a => a.id), comparison_ids: comparisons.map(c => c.id),
    superseded_assertion_ids: [...superseded], relationship_ids: [...relationIds], place_ids: placeIds,
    location_membership_ids: [...locationIds],
    panels, reviewed_series: reviewedSeries, reviewed_chains: reviewedChains,
    numeric_coverage: {record_count: records.length, records_with_measures: records.filter(r => measuredRecords.has(r.id)).length,
      records_without_reviewed_measures: records.filter(r => !measuredRecords.has(r.id)).length,
      reviewed_series_count: reviewedSeries.length, reviewed_connection_count: reviewedSeries.reduce((n, s) => n + s.connections.length, 0)},
    source_coverage: data.source_coverage.map(e => {
      const ids = e.record_ids.filter(id => recordIds.has(id));
      const positions = ids.map(id => recordOrder.get(id)).sort((a, b) => a - b);
      return {id: e.id, record_ids: ids, document_ids: [...new Set(positions.map(i => records[i].document_id))]};
    }).filter(e => e.record_ids.length),
  };
}
