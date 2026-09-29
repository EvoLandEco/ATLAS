"""Reproducible reporting-network summaries from a validated site bundle."""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

from atlas import __version__
from atlas.site_export import eligible, verify_site
from atlas.util import atomic_write, canonical, canonical_url, digest, read_json, stamp, write_json

VERSION = '0.2.0'
METHOD = 'reporting-network-3'
GRANULARITIES = ('individual_journey', 'aggregate_travellers', 'shared_episode', 'product_consignment', 'human_remains_transfer', 'vessel_voyage', 'unresolved')
MOVEMENT_CATEGORIES = ('living_travellers', 'product_shipments', 'human_remains', 'vessel_only', 'unresolved', 'not_applicable')

CITATIONS = [
    {'id': 'barrat2004', 'citation': 'Barrat A, Barthélemy M, Pastor-Satorras R, Vespignani A. The architecture of complex weighted networks. PNAS. 2004;101:3747–3752.', 'doi': '10.1073/pnas.0400087101'},
    {'id': 'jones2008', 'citation': 'Jones KE et al. Global trends in emerging infectious diseases. Nature. 2008;451:990–993.', 'doi': '10.1038/nature06536'},
    {'id': 'allen2017', 'citation': 'Allen T et al. Global hotspots and correlates of emerging zoonotic diseases. Nature Communications. 2017;8:1124.', 'doi': '10.1038/s41467-017-00923-8'},
]


def index(rows):
    result = {r['id']: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate entity ID')
    return result


def units_from_site(site):
    places = index(site['places'])
    assertions = index(site['assertions'])
    countries = {a['code'] for a in site['areas'] if a['code_system'] == 'ISO_3166_1_alpha_2'}
    units, excluded = [], []
    for r in sorted(index(site['relationships']).values(), key=lambda x: x['id']):
        if r['category'] != 'geographic_link':
            continue
        endpoints = [sorted(set(places[r[k]]['area_codes'])) for k in ('from_place_id', 'to_place_id')]
        reason = None
        if r['kind'] not in ('movement', 'shared_event'):
            reason = 'hypothesis'
        elif any(len(e) != 1 or e[0] not in countries for e in endpoints):
            reason = 'ambiguous_or_non_country_endpoint'
        elif endpoints[0] == endpoints[1]:
            reason = 'domestic'
        if reason:
            excluded.append({'relationship_id': r['id'], 'reason': reason, 'record_ids': r['eligibility']['record_ids']})
            continue
        units.append({'id': r['id'], 'kind': r['kind'], 'directed': r['directed'],
                      'from_country': endpoints[0][0], 'to_country': endpoints[1][0],
                      'record_ids': sorted(r['eligibility']['record_ids']),
                      'assertion_ids': sorted(r['assertion_ids']),
                      'evidence_ids': sorted({e for a in r['assertion_ids'] for e in assertions[a]['evidence_ids']}),
                      'identity_status': 'unreviewed'})
    return units, excluded


def identity_candidates(units):
    """Candidate lookup preserves direction differences for source review."""
    blocks = defaultdict(list)
    for u in units:
        blocks[(u['kind'], tuple(sorted((u['from_country'], u['to_country']))))].append(u['id'])
    return {key: [other for other in ids if other != key]
            for ids in map(sorted, blocks.values()) for key in ids}


def validate_reviews(reviews, units, site):
    """A review groups repeated statements, never accepts a registry event."""
    known, evidence, assigned = index(units), index(site['evidence']), set()
    group_ids = set()
    for g in reviews:
        required = {'id', 'relationship_ids', 'evidence_ids', 'reviewed_at', 'reviewed_by', 'basis', 'source_lineage', 'status'}
        if set(g) != required or g['status'] != 'source_checked_draft':
            raise ValueError('Invalid repeat-report review fields or status')
        stamp(g['reviewed_at'])
        if g['id'] in group_ids or not g['basis'] or not g['reviewed_by'] or not g['source_lineage']:
            raise ValueError('Missing or duplicate review identity')
        group_ids.add(g['id'])
        ids = g['relationship_ids']
        if len(ids) < 2 or len(set(ids)) != len(ids) or assigned.intersection(ids):
            raise ValueError('Overlapping or empty relationship membership')
        members = [known[i] for i in ids]
        signatures = {(u['kind'], u['directed'], (u['from_country'], u['to_country']) if u['directed'] else tuple(sorted((u['from_country'], u['to_country'])))) for u in members}
        if len(signatures) != 1:
            raise ValueError('A repeat-report unit must preserve type, endpoints and direction')
        supported = {evidence[e]['record_id'] for e in g['evidence_ids']}
        if not {r for u in members for r in u['record_ids']} <= supported:
            raise ValueError('Review evidence must cover every supporting record')
        assigned.update(ids)
    return assigned


def ranking(counter):
    rows = []
    prior, rank = None, 0
    for position, (key, value) in enumerate(sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])), 1):
        if value != prior:
            rank = position
        rows.append({'key': key, 'value': value, 'rank': rank})
        prior = value
    return rows


def counts(units):
    nodes, pairs, incoming = Counter(), Counter(), Counter()
    for u in units:
        a, b = u['from_country'], u['to_country']
        nodes.update((a, b))
        pairs['|'.join(sorted((a, b)))] += 1
        if u['kind'] == 'movement' and u['directed'] and u.get('movement_category') == 'living_travellers':
            incoming[b] += 1
    return {'units': len(units), 'incident_strength': ranking(nodes), 'pair_multiplicity': ranking(pairs), 'incoming_travel': ranking(incoming)}


def summarize(units, reviews, selected_records):
    selected = [u for u in units if set(u['record_ids']) <= selected_records]
    selected_ids = {u['id'] for u in selected}
    active = [g for g in reviews if set(g['relationship_ids']) <= selected_ids]
    grouped = {i for g in active for i in g['relationship_ids']}
    by_id = index(selected)
    representatives = [by_id[g['relationship_ids'][0]] for g in active]
    corrected = [u for u in selected if u['id'] not in grouped] + representatives
    correction_counts = counts(corrected)
    partial = len(grouped) < len(selected)
    correction_counts['ranking_status'] = 'unavailable_partial_identity_review' if partial else 'reviewed_scope'
    if partial:
        for metric in ('incident_strength', 'pair_multiplicity', 'incoming_travel'):
            for row in correction_counts[metric]:
                row['rank'] = None
    return {'relationship_ids': sorted(selected_ids), 'raw': counts(selected),
            'repeat_report_corrected': correction_counts, 'reviewed_group_subset': counts(representatives),
            'identity_coverage': {'grouped_relationships': len(grouped), 'ungrouped_relationships': len(selected)-len(grouped),
                                  'active_group_ids': [g['id'] for g in active],
                                  'assessed_relationships': sum(u['identity_status'] != 'unreviewed' for u in selected),
                                  'unassessed_relationships': sum(u['identity_status'] == 'unreviewed' for u in selected)},
            'movement_coverage': {k: sum(u.get('movement_category') == k for u in selected) for k in MOVEMENT_CATEGORIES},
            'correction_status': 'partial' if len(grouped) < len(selected) else ('reviewed_scope' if selected else 'empty_selection')}


def coverage_ledger(site, collections):
    """Keep discovery histories; selected captures resolve only capture/parse state."""
    rows = {}
    channels = {c['id']: c['acquisition_source'] for c in site['channels']}
    for path, batches in collections:
        receipt_hash = digest(path.read_bytes())
        if not isinstance(batches, list):
            raise ValueError('Collection input must be a list of source receipts')
        for batch in batches:
            for entry in batch.get('entries', []):
                if not entry.get('url'):
                    continue
                key = (batch['source_id'], canonical_url(entry['url']))
                row = rows.setdefault(key, {'source': key[0], 'url': key[1], 'history': [], 'document_ids': []})
                original_hash = batch.get('source_receipt_sha256', receipt_hash)
                if not re.fullmatch('[0-9a-f]{64}', original_hash):
                    raise ValueError('Invalid acquisition receipt digest')
                row['history'].append({'receipt_sha256': original_hash, 'input_sha256': receipt_hash,
                                       'receipt_index': entry.get('receipt_index'), 'status': entry.get('status', 'unknown'),
                                       'parse_status': entry.get('parse_status', 'unknown'), 'document_id': entry.get('document_id'),
                                       'content_url': entry.get('content_url'),
                                       'completed_at': batch.get('completed_at'), 'publication': entry.get('published_at')})
    records = index(site['records'])
    geography = defaultdict(set)
    for loc in site['location_memberships']:
        geography[loc['document_id']].add(loc['area_code'])
    for doc in site['documents']:
        key = (channels[doc['channel_id']], canonical_url(doc['url']))
        row = rows.setdefault(key, {'source': key[0], 'url': key[1], 'history': [], 'document_ids': []})
        row['document_ids'].append(doc['id'])
        row.setdefault('record_ids', []).extend(doc['record_ids'])
    for key, row in sorted(rows.items()):
        rids = sorted(set(row.get('record_ids', [])))
        row['id'] = 'coverage_' + digest(key)[:24]
        row['record_ids'] = rids
        row['geography_scope'] = sorted({code for d in row['document_ids'] for code in geography[d]})
        row['geography_scope_status'] = 'exported_mentions_not_sampling_frame' if row['document_ids'] else 'unknown'
        row['topic_ids'] = sorted({records[r]['topic_id'] for r in rids})
        row['publication_dates'] = sorted({records[r]['publication'][:10] for r in rids})
        recovered = any(h['status'] in {'captured', 'reused', 'captured_pending_section_review'} for h in row['history'])
        parsed = any(h['parse_status'] == 'text_ready' for h in row['history'])
        row['stages'] = {'discovery': 'receipt_present' if row['history'] else 'history_not_supplied',
                         'fetch': 'captured' if rids else ('receipt_capture_not_selected' if recovered else 'not_established_by_selected_export'),
                         'parse': 'captured_text' if rids else ('receipt_text_not_selected' if parsed else 'unknown'),
                         'extraction': 'findings_selected_full_document_coverage_unknown' if rids else 'unknown',
                         'eligibility': 'selected' if rids else 'unknown',
                         'review': dict(Counter(records[r]['geographic_review'] for r in rids))}
    return sorted(rows.values(), key=lambda r: r['id'])


def build(site, reviews, inputs, collections=(), granularity_reviews=(), identity_reviews=()):
    records = index(site['records'])
    units, excluded = units_from_site(site)
    unit_index = index(units)
    assigned = validate_reviews(reviews, units, site)
    evidence_index = index(site['evidence'])
    granularities = {}
    for g in granularity_reviews:
        required = {'relationship_id', 'granularity', 'movement_category', 'evidence_ids', 'basis', 'reviewed_at', 'reviewed_by'}
        if set(g) != required or g['granularity'] not in GRANULARITIES or g['movement_category'] not in MOVEMENT_CATEGORIES:
            raise ValueError('Invalid granularity review')
        stamp(g['reviewed_at'])
        key = g['relationship_id']
        if key in granularities or not g['basis'] or not g['reviewed_by']:
            raise ValueError('Duplicate or incomplete granularity review')
        if not set(unit_index[key]['record_ids']) <= {evidence_index[e]['record_id'] for e in g['evidence_ids']}:
            raise ValueError('Granularity evidence must cover supporting records')
        expected_category = {'product_consignment': 'product_shipments', 'human_remains_transfer': 'human_remains',
                             'vessel_voyage': 'vessel_only', 'shared_episode': 'not_applicable',
                             'individual_journey': 'living_travellers', 'aggregate_travellers': 'living_travellers'}
        if g['granularity'] in expected_category and g['movement_category'] != expected_category[g['granularity']]:
            raise ValueError('Granularity and movement category disagree')
        granularities[key] = g
    assessed = {}
    candidates_by_id = identity_candidates(units)
    for g in identity_reviews:
        required = {'relationship_id', 'evidence_ids', 'basis', 'candidate_relationship_ids', 'reviewed_at', 'reviewed_by'}
        if set(g) != required or g['relationship_id'] in assessed or not g['basis'] or not g['reviewed_by']:
            raise ValueError('Invalid or duplicate identity assessment')
        stamp(g['reviewed_at'])
        key = g['relationship_id']
        if not set(unit_index[key]['record_ids']) <= {evidence_index[e]['record_id'] for e in g['evidence_ids']}:
            raise ValueError('Identity evidence must cover supporting records')
        if g['candidate_relationship_ids'] != candidates_by_id[key]:
            raise ValueError('Identity assessment candidate set is stale')
        assessed[key] = g
    for u in units:
        assessment = granularities.get(u['id'], {})
        u['granularity'] = assessment.get('granularity', 'unresolved')
        u['movement_category'] = assessment.get('movement_category', 'unresolved')
        if u['kind'] == 'movement' and u['movement_category'] == 'not_applicable':
            raise ValueError('Movement requires an assessed or unresolved subject')
        if u['kind'] == 'shared_event' and u['movement_category'] not in {'unresolved', 'not_applicable'}:
            raise ValueError('Shared event cannot carry a movement category')
        if u['id'] in assessed:
            u['identity_status'] = 'source_checked_identity_unresolved'
        if u['id'] in assigned:
            u['identity_status'] = 'source_checked_repeat_report_group'
    for g in reviews:
        if len({(unit_index[i]['granularity'], unit_index[i]['movement_category']) for i in g['relationship_ids']}) != 1:
            raise ValueError('Repeat-report group mixes observation units')
        if not set(g['relationship_ids']) <= assessed.keys():
            raise ValueError('Repeat-report membership requires current identity assessments')
    ledger = coverage_ledger(site, collections)
    since, until = site['snapshot']['publication_from'], site['snapshot']['publication_until']
    all_records = {r for r, v in records.items() if eligible({'record_ids': [r]}, records, since, until)}
    scopes = [('full', 'full', None, all_records)]
    for g in reviews:
        support = {r for i in g['relationship_ids'] for r in unit_index[i]['record_ids']}
        scopes.append(('reviewed-group:'+g['id'], 'reviewed_group_support', g['id'], support & all_records))
    for channel in sorted({r['channel_id'] for r in records.values()}):
        scopes.append(('without-source:'+channel, 'source_omission', channel, {i for i in all_records if records[i]['channel_id'] != channel}))
    organizations = {c['id']: c['organization_id'] for c in site['channels']}
    for organization in sorted(set(organizations.values())):
        scopes.append(('without-organization:'+organization, 'organization_omission', organization,
                       {i for i in all_records if organizations[records[i]['channel_id']] != organization}))
    for month in sorted({r['publication'][:7] for r in records.values()}):
        scopes.append(('month:'+month, 'publication_month', month, {i for i in all_records if records[i]['publication'].startswith(month)}))
    for topic in sorted({records[r]['topic_id'] for u in units for r in u['record_ids']}):
        scopes.append(('topic:'+topic, 'reporting_topic', topic, {i for i in all_records if records[i]['topic_id'] == topic}))
    results = []
    for key, kind, value, selected in scopes:
        by_type = {t: summarize([u for u in units if u['kind'] == t], [g for g in reviews if all(unit_index[i]['kind'] == t for i in g['relationship_ids'])], selected) for t in ('movement', 'shared_event')}
        selection = {'kind': kind, 'value': value, 'since': since, 'until': until, 'basis': 'publication'}
        results.append({'id': digest(selection), 'selection_sha256': digest(sorted(selected)), 'key': key, 'selection': selection,
                        'combined': summarize(units, reviews, selected), 'by_type': by_type})
    result = {'contract_version': VERSION, 'method': {'id': METHOD, 'code_sha256': digest(Path(__file__).read_bytes()), 'software_version': __version__},
              'inputs': inputs, 'release_status': 'research_preview', 'publication_authorized': False,
              'target': 'Eligible cross-country geographic statements in the captured reporting corpus',
              'definitions': {'incident_strength': 'Number of eligible units incident on a country; count, not degree or risk.',
                              'pair_multiplicity': 'Number of eligible units for an unordered country pair.',
                              'incoming_travel': 'Number of directed, source-reviewed living-traveller statements ending in a country; excludes products, remains, vessel-only movements and unresolved categories. Not traveller, journey, case or risk counts.',
                              'repeat_report_corrected': 'One unit per fully eligible reviewed repeat-report group, plus one per unreviewed statement. Partial correction, not a complete episode count.',
                              'reviewed_group_subset': 'Counts within explicit source-checked groups only; excluded unreviewed statements remain unknown.'},
              'selection_rules': {'relationships': 'All supporting records must be selected using the site selector.',
                                  'groups': 'Apply a group only if all member relationships are eligible. Otherwise retain raw statements.',
                                  'unsupported_filters': 'Precomputed scopes require an exact key. Recompute descriptive counts for other selections; never reuse fitted estimates.',
                                  'date_meaning': 'Publication periods, not occurrence or infection periods.'},
              'unavailable': {'complete_episode_ranking': 'Identity review does not cover every relationship or establish distinctness among unresolved episodes.',
                              'collection_adjusted': 'No complete discovery frame or known positive document inclusion probabilities; selection may depend on unobserved content.',
                              'surveillance_adjusted': 'No validated independent detection/reporting effort measure or ascertainment model for this target.',
                              'confidence_intervals': 'This is a descriptive census of selected statements. Dependence between repeated episodes and sources is incompletely reviewed; source omission ranges are sensitivity checks, not confidence intervals.'},
              'records': [dict({k: r[k] for k in ('id', 'document_id', 'channel_id', 'topic_id', 'publication', 'capture')}, organization_id=organizations[r['channel_id']]) for r in sorted(records.values(), key=lambda x:x['id'])],
              'units': units, 'excluded': excluded, 'repeat_report_reviews': reviews, 'granularity_reviews': list(granularity_reviews), 'identity_reviews': list(identity_reviews),
              'movement_category_definitions': {'living_travellers': 'Movement attributed to living people, individually or in an aggregate; case confirmation is not required.',
                  'product_shipments': 'Movement of products or commodities.', 'human_remains': 'Transfer of a deceased person.',
                  'vessel_only': 'Vessel itinerary without an individually resolved traveller unit.',
                  'unresolved': 'The reviewed source does not determine the movement subject, or review is absent.',
                  'not_applicable': 'Shared event relationship, not a movement statement.'},
              'scopes': results, 'citations': CITATIONS,
              'coverage': {'ledger_content_sha256': digest(ledger), 'discovered_or_selected_urls': len(ledger), 'selected_documents': len(site['documents']),
                           'frame_completeness': 'unknown', 'source_independence': 'not_established',
                           'interpretation': 'Pipeline completion within supplied receipts; not the probability of detecting a real-world event.'}}
    evidence = index(site['evidence'])
    span_members = defaultdict(set)
    for u in units:
        for eid in u['evidence_ids']:
            e = evidence[eid]
            span_members[(e['source_text_sha256'], e['start'], e['end'])].add(u['id'])
    result['source_span_reuse'] = [{'source_text_sha256': key[0], 'start': key[1], 'end': key[2], 'relationship_ids': sorted(ids)}
                                   for key, ids in sorted(span_members.items()) if len(ids) > 1]
    result['sensitivity_interpretation'] = 'Source and organization omission removes whole reporting blocks. Publication month and topic views describe composition. Shared source spans indicate reused evidence, not episode identity. No resampling interval or surveillance adjustment is fitted.'
    result['uncertainty'] = {'status': 'not_estimated', 'lower': None, 'upper': None, 'reason': 'Counts condition on the selected reporting corpus; episode dependence and inclusion probabilities do not support a sampling interval.'}
    result['analysis_id'] = digest(result)
    return result, ledger


def schema():
    """Closed nested contract; semantic validation also checks identities and counts."""
    def obj(fields):
        return {'type': 'object', 'additionalProperties': False, 'properties': fields, 'required': list(fields)}
    def arr(item, unique=False):
        return {'type': 'array', 'items': item, 'uniqueItems': unique}
    text = {'type': 'string', 'minLength': 1}
    integer = {'type': 'integer', 'minimum': 0}
    sha = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
    strings = arr(text, True)
    day = {'type': 'string', 'format': 'date'}
    instant = {'type': 'string', 'format': 'date-time'}
    country = {'type': 'string', 'pattern': '^[A-Z]{2}$'}
    rank = obj({'key': text, 'value': integer, 'rank': {'type': 'integer', 'minimum': 1}})
    nullable_rank = obj({'key': text, 'value': integer, 'rank': {'type': ['integer', 'null'], 'minimum': 1}})
    measures = ('incident_strength', 'pair_multiplicity', 'incoming_travel')
    counts_schema = obj({'units': integer, **{m: arr(rank) for m in measures}})
    corrected = obj({'units': integer, 'ranking_status': {'enum': ['unavailable_partial_identity_review', 'reviewed_scope']}, **{m: arr(nullable_rank) for m in measures}})
    corrected['allOf'] = [{'if': {'properties': {'ranking_status': {'const': status}}}, 'then': {'properties': {m: {'items': {'properties': {'rank': constraint}}} for m in measures}}} for status, constraint in [('unavailable_partial_identity_review', {'type': 'null'}), ('reviewed_scope', {'type': 'integer', 'minimum': 1})]]
    summary = obj({'relationship_ids': strings, 'raw': counts_schema, 'repeat_report_corrected': corrected,
                   'reviewed_group_subset': counts_schema,
                   'identity_coverage': obj({'grouped_relationships': integer, 'ungrouped_relationships': integer, 'active_group_ids': strings, 'assessed_relationships': integer, 'unassessed_relationships': integer}),
                   'movement_coverage': obj({k: integer for k in MOVEMENT_CATEGORIES}),
                   'correction_status': {'enum': ['partial', 'reviewed_scope', 'empty_selection']}})
    summary['allOf'] = [{'if': {'properties': {'correction_status': {'const': 'partial'}}}, 'then': {'properties': {'repeat_report_corrected': {'properties': {'ranking_status': {'const': 'unavailable_partial_identity_review'}}}}}}]
    selection = obj({'kind': {'enum': ['full', 'reviewed_group_support', 'source_omission', 'organization_omission', 'publication_month', 'reporting_topic']},
                     'value': {'type': ['string', 'null']}, 'since': day, 'until': day, 'basis': {'const': 'publication'}})
    selection['allOf'] = [{'if': {'properties': {'kind': {'const': 'full'}}}, 'then': {'properties': {'value': {'type': 'null'}}}, 'else': {'properties': {'value': text}}}]
    unit = obj({'id': text, 'kind': {'enum': ['movement', 'shared_event']}, 'directed': {'type': 'boolean'},
                'from_country': country, 'to_country': country, 'record_ids': strings, 'assertion_ids': strings, 'evidence_ids': strings,
                'identity_status': {'enum': ['unreviewed', 'source_checked_repeat_report_group', 'source_checked_identity_unresolved']},
                'movement_category': {'enum': list(MOVEMENT_CATEGORIES)}, 'granularity': {'enum': list(GRANULARITIES)}})
    review = obj({'id': text, 'relationship_ids': strings, 'evidence_ids': strings, 'reviewed_at': instant, 'reviewed_by': text,
                  'basis': text, 'source_lineage': text, 'status': {'const': 'source_checked_draft'}})
    granularity = obj({'relationship_id': text, 'granularity': unit['properties']['granularity'], 'movement_category': unit['properties']['movement_category'], 'evidence_ids': strings,
                       'basis': text, 'reviewed_at': instant, 'reviewed_by': text})
    uncertainty = obj({'status': {'const': 'not_estimated'}, 'lower': {'type': 'null'}, 'upper': {'type': 'null'}, 'reason': text})
    fields = {'contract_version': {'const': VERSION}, 'analysis_id': sha,
              'method': obj({'id': {'const': METHOD}, 'code_sha256': sha, 'software_version': text}),
              'inputs': obj({'site_sha256': sha, 'reviews_sha256': sha, 'collection_sha256': arr(sha)}),
              'release_status': {'const': 'research_preview'}, 'publication_authorized': {'const': False}, 'target': text,
              'definitions': obj({k: text for k in (*measures, 'repeat_report_corrected', 'reviewed_group_subset')}),
              'selection_rules': obj({k: text for k in ('relationships', 'groups', 'unsupported_filters', 'date_meaning')}),
              'unavailable': obj({k: text for k in ('complete_episode_ranking', 'collection_adjusted', 'surveillance_adjusted', 'confidence_intervals')}),
              'uncertainty': uncertainty,
              'records': arr(obj({'id': text, 'document_id': text, 'channel_id': text, 'organization_id': text, 'topic_id': text, 'publication': text, 'capture': instant})),
              'units': arr(unit), 'excluded': arr(obj({'relationship_id': text, 'reason': {'enum': ['hypothesis', 'domestic', 'ambiguous_or_non_country_endpoint']}, 'record_ids': strings})),
              'repeat_report_reviews': arr(review), 'granularity_reviews': arr(granularity),
              'identity_reviews': arr(obj({'relationship_id': text, 'evidence_ids': strings, 'candidate_relationship_ids': strings, 'basis': text, 'reviewed_at': instant, 'reviewed_by': text})),
              'movement_category_definitions': obj({k: text for k in MOVEMENT_CATEGORIES}),
              'scopes': arr(obj({'id': sha, 'key': text, 'selection_sha256': sha, 'selection': selection, 'combined': summary,
                                 'by_type': obj({'movement': summary, 'shared_event': summary})})),
              'citations': arr(obj({'id': text, 'citation': text, 'doi': text})),
              'coverage': obj({'ledger_content_sha256': sha, 'discovered_or_selected_urls': integer, 'selected_documents': integer,
                               'frame_completeness': {'const': 'unknown'}, 'source_independence': {'const': 'not_established'}, 'interpretation': text}),
              'source_span_reuse': arr(obj({'source_text_sha256': sha, 'start': integer, 'end': integer, 'relationship_ids': strings})),
              'sensitivity_interpretation': text}
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'ATLAS network analysis '+VERSION, **obj(fields)}


def validate_analysis(data):
    import jsonschema
    jsonschema.Draft202012Validator(schema(), format_checker=jsonschema.FormatChecker()).validate(data)
    body = {k: v for k, v in data.items() if k != 'analysis_id'}
    if digest(body) != data['analysis_id']:
        raise ValueError('Analysis content identity mismatch')
    records, units = index(data['records']), index(data['units'])
    candidate_ids = identity_candidates(list(units.values()))
    assessed = {g['relationship_id']: g for g in data['identity_reviews']}
    granularities = {g['relationship_id']: g for g in data['granularity_reviews']}
    if len(assessed) != len(data['identity_reviews']) or len(granularities) != len(data['granularity_reviews']):
        raise ValueError('Duplicate source assessment')
    if not set(assessed) <= units.keys() or not set(granularities) <= units.keys():
        raise ValueError('Assessment refers to unknown relationship')
    grouped = {i for g in data['repeat_report_reviews'] for i in g['relationship_ids']}
    if sum(len(g['relationship_ids']) for g in data['repeat_report_reviews']) != len(grouped):
        raise ValueError('Overlapping repeat-report groups')
    if not grouped <= assessed.keys():
        raise ValueError('Repeat-report membership lacks identity assessment')
    for key, review in assessed.items():
        if review['candidate_relationship_ids'] != candidate_ids[key]:
            raise ValueError('Identity assessment candidate set is stale')
    for key, u in units.items():
        assessment = granularities.get(key, {})
        if any(u[k] != assessment.get(k, 'unresolved') for k in ('granularity', 'movement_category')):
            raise ValueError('Unit differs from its source assessment')
        expected = 'source_checked_repeat_report_group' if key in grouped else ('source_checked_identity_unresolved' if key in assessed else 'unreviewed')
        if u['identity_status'] != expected:
            raise ValueError('Unit identity status differs from its source assessment')
    prefixes = {'full': 'full', 'source_omission': 'without-source:', 'organization_omission': 'without-organization:',
                'publication_month': 'month:', 'reporting_topic': 'topic:', 'reviewed_group_support': 'reviewed-group:'}
    seen = set()
    for scope in data['scopes']:
        selection = scope['selection'];kind = selection['kind'];value = selection['value']
        expected_key = 'full' if kind == 'full' and value is None else prefixes[kind] + str(value)
        if scope['key'] != expected_key or scope['id'] != digest(selection) or scope['id'] in seen:
            raise ValueError('Invalid or duplicate scope identity')
        seen.add(scope['id'])
        if selection['since'] > selection['until']:
            raise ValueError('Reversed scope dates')
        selected_records = {rid for rid in records if eligible({'record_ids': [rid]}, records, selection['since'], selection['until'])}
        if kind in ('source_omission', 'organization_omission'):
            field = 'channel_id' if kind == 'source_omission' else 'organization_id'
            selected_records = {rid for rid in selected_records if records[rid][field] != value}
        elif kind == 'publication_month':
            if not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])', value):
                raise ValueError('Invalid publication month')
            selected_records = {rid for rid in selected_records if records[rid]['publication'].startswith(value)}
        elif kind == 'reporting_topic':
            selected_records = {rid for rid in selected_records if records[rid]['topic_id'] == value}
        elif kind == 'reviewed_group_support':
            group = next(g for g in data['repeat_report_reviews'] if g['id'] == value)
            selected_records &= {rid for key in group['relationship_ids'] for rid in units[key]['record_ids']}
        if scope['selection_sha256'] != digest(sorted(selected_records)):
            raise ValueError('Scope record selection identity mismatch')
        if scope['combined'] != summarize(list(units.values()), data['repeat_report_reviews'], selected_records):
            raise ValueError('Scope counts or review coverage disagree with selection')
        for relationship_type in ('movement', 'shared_event'):
            type_units = [u for u in units.values() if u['kind'] == relationship_type]
            type_reviews = [g for g in data['repeat_report_reviews'] if all(units[i]['kind'] == relationship_type for i in g['relationship_ids'])]
            if scope['by_type'][relationship_type] != summarize(type_units, type_reviews, selected_records):
                raise ValueError('Relationship type selection mismatch')
        for summary in [scope['combined'], *scope['by_type'].values()]:
            selected = [units[i] for i in summary['relationship_ids']]
            if summary['raw'] != counts(selected):
                raise ValueError('Raw counts disagree with selected relationships')
            pending = summary['identity_coverage']['ungrouped_relationships']
            if pending and summary['repeat_report_corrected']['ranking_status'] != 'unavailable_partial_identity_review':
                raise ValueError('Incomplete identity review cannot produce corrected ranks')
    for u in units.values():
        if not set(u['record_ids']) <= set(records):
            raise ValueError('Unknown supporting record')


def transport_schema():
    def obj(fields):
        return {'type': 'object', 'additionalProperties': False, 'properties': fields, 'required': list(fields)}
    sha = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
    asset = obj({'relative_path': {'type': 'string', 'pattern': r'^(releases|network-analysis)/[0-9a-f]{64}/[a-z-]+([.]schema)?[.](json|mjs)$'},
                 'bytes': {'type': 'integer', 'minimum': 1}, 'sha256': sha})
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'ATLAS network transport 0.1.0',
            **obj({'transport_version': {'const': '0.1.0'}, 'publication_authorized': {'const': False},
                   'analysis_id': sha, 'site_release_id': sha, 'hash_basis': {'const': 'sha256_file_bytes'},
                   'resolution': {'type': 'string', 'minLength': 1},
                   **{k: asset for k in ('site', 'map', 'selector', 'analysis', 'schema', 'coverage')}})}


def transport(result, bundle, map_path, release_id, out):
    import jsonschema
    if not re.fullmatch('[0-9a-f]{64}', release_id):
        raise ValueError('Invalid site release ID')
    site = read_json(bundle/'atlas-site.json')
    if digest(map_path.read_bytes()) != site['snapshot']['source_snapshot_sha256']:
        raise ValueError('Map is not the exact site input snapshot')
    def asset(path, relative_path):
        return {'relative_path': relative_path, 'bytes': path.stat().st_size, 'sha256': digest(path.read_bytes())}
    release_prefix = 'releases/'+release_id+'/'
    analysis_prefix = 'network-analysis/'+result['analysis_id']+'/'
    descriptor = {'transport_version': '0.1.0', 'publication_authorized': False, 'analysis_id': result['analysis_id'],
            'site_release_id': release_id, 'hash_basis': 'sha256_file_bytes',
            'resolution': 'Relative to a consumer-configured trusted dataset service root; no automatic activation.',
            'site': asset(bundle/'atlas-site.json', release_prefix+'atlas-site.json'),
            'map': asset(map_path, release_prefix+'map.json'),
            'selector': asset(bundle/'view.mjs', release_prefix+'view.mjs'),
            'analysis': asset(out/'network-analysis.json', analysis_prefix+'network-analysis.json'),
            'schema': asset(out/'network-analysis.schema.json', analysis_prefix+'network-analysis.schema.json'),
            'coverage': asset(out/'coverage-ledger.json', analysis_prefix+'coverage-ledger.json')}
    jsonschema.validate(descriptor, transport_schema())
    return descriptor


def run(bundle, review_path, collection_paths, out, verify=False, map_path=None, release_id=None):
    verify_site(bundle)
    site_path = bundle/'atlas-site.json'
    site = read_json(site_path)
    review_input = read_json(review_path)
    if set(review_input) != {'repeat_report_reviews', 'granularity_reviews', 'identity_reviews'}:
        raise ValueError('Review input requires repeat_report_reviews, granularity_reviews and identity_reviews arrays')
    reviews = review_input['repeat_report_reviews']
    collections = [(p, read_json(p)) for p in collection_paths]
    inputs = {'site_sha256': digest(site_path.read_bytes()), 'reviews_sha256': digest(review_path.read_bytes()),
              'collection_sha256': sorted(digest(p.read_bytes()) for p in collection_paths)}
    result, ledger = build(site, reviews, inputs, collections, review_input['granularity_reviews'], review_input['identity_reviews'])
    validate_analysis(result)
    if (map_path is None) != (release_id is None):
        raise ValueError('Map and site release ID must be supplied together')
    if verify or out.exists():
        manifest = read_json(out/'manifest.json')
        expected_files = {'network-analysis.json', 'coverage-ledger.json', 'network-analysis.schema.json'}
        if map_path is not None:
            expected_files.update({'network-transport.json', 'network-transport.schema.json'})
        if set(manifest['files']) != expected_files:
            raise ValueError('Unexpected candidate files')
        for name, sha in manifest['files'].items():
            if digest((out/name).read_bytes()) != sha:
                raise ValueError('Candidate checksum mismatch')
        if read_json(out/'network-analysis.schema.json') != schema():
            raise ValueError('Schema differs from analysis method')
        if read_json(out/'network-analysis.json') != result or read_json(out/'coverage-ledger.json') != ledger:
            raise ValueError('Analysis replay differs from saved candidate')
        if map_path is not None and read_json(out/'network-transport.json') != transport(result, bundle, map_path, release_id, out):
            raise ValueError('Transport binding differs from exact local assets')
        if map_path is not None and read_json(out/'network-transport.schema.json') != transport_schema():
            raise ValueError('Transport schema mismatch')
    else:
        out.mkdir(parents=True, exist_ok=False)
        atomic_write(out/'network-analysis.json', canonical(result)+'\n')
        write_json(out/'coverage-ledger.json', ledger)
        write_json(out/'network-analysis.schema.json', schema())
        if map_path is not None:
            write_json(out/'network-transport.json', transport(result, bundle, map_path, release_id, out))
            write_json(out/'network-transport.schema.json', transport_schema())
        write_json(out/'manifest.json', {'files': {p.name: digest(p.read_bytes()) for p in sorted(out.iterdir())}})
    return {'analysis_id': result['analysis_id'], 'units': len(result['units']), 'reviewed_groups': len(reviews), 'scopes': len(result['scopes']), 'status': 'valid'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--reviews', type=Path, required=True)
    parser.add_argument('--collection', type=Path, action='append', default=[])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--map', dest='map_path', type=Path)
    parser.add_argument('--release-id')
    args = parser.parse_args()
    print(run(args.bundle, args.reviews, args.collection, args.out, args.verify, args.map_path, args.release_id))


if __name__ == '__main__':
    main()
