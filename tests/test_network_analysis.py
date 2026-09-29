"""Repeat reporting and filters cannot silently create episode identities."""
import pytest
from atlas.network_analysis import counts, summarize, units_from_site, validate_reviews


def unit(key, record, a='SN', b='IT', directed=True):
    return dict(id=key, record_ids=[record], kind='movement', directed=directed,
                from_country=a, to_country=b, assertion_ids=[], evidence_ids=[], identity_status='unreviewed', movement_category='living_travellers')


def test_reviewed_repeat_reporting_and_partial_selection():
    units = [unit('u1', 'r1'), unit('u2', 'r2'), unit('u3', 'r3')]
    review = dict(id='journey', relationship_ids=['u1', 'u2'], evidence_ids=['e1', 'e2'],
                  reviewed_at='2026-09-29T10:00:00Z', reviewed_by='Fixture', basis='Explicit same journey.',
                  source_lineage='Two follow-up accounts of the same named notification.', status='source_checked_draft')
    site = dict(evidence=[dict(id='e1', record_id='r1'), dict(id='e2', record_id='r2')])
    assert validate_reviews([review], units, site) == {'u1', 'u2'}
    full = summarize(units, [review], {'r1', 'r2', 'r3'})
    assert (full['raw']['units'], full['repeat_report_corrected']['units'], full['reviewed_group_subset']['units']) == (3, 2, 1)
    assert full['identity_coverage']['ungrouped_relationships'] == 1
    assert full['repeat_report_corrected']['ranking_status'] == 'unavailable_partial_identity_review'
    assert all(r['rank'] is None for r in full['repeat_report_corrected']['incident_strength'])
    partial = summarize(units, [review], {'r1', 'r3'})
    assert partial['repeat_report_corrected']['units'] == 2
    assert partial['reviewed_group_subset']['units'] == 0
    assert summarize(units, [review], set())['raw']['units'] == 0
    with pytest.raises(ValueError):
        validate_reviews([review, dict(review, id='overlap')], units, site)
    with pytest.raises(ValueError):
        validate_reviews([review], [units[0], unit('u2', 'r2', 'IT', 'SN')], site)


def test_direction_ties_and_country_exclusions():
    stats = counts([unit('a', 'r', 'NA', 'ZA'), unit('b', 's', 'ZA', 'NA', False)])
    assert [r['rank'] for r in stats['incident_strength']] == [1, 1]
    assert stats['incoming_travel'] == [dict(key='ZA', value=1, rank=1)]
    assert stats['pair_multiplicity'] == [dict(key='NA|ZA', value=2, rank=1)]
    site = dict(areas=[dict(code=c, code_system='ISO_3166_1_alpha_2') for c in ['NA', 'ZA']],
                places=[dict(id='a', area_codes=['NA']), dict(id='b', area_codes=['ZA']), dict(id='x', area_codes=['NA', 'ZA'])],
                assertions=[dict(id='assert', evidence_ids=['e'])], relationships=[])
    base = dict(category='geographic_link', kind='movement', directed=True, from_place_id='a', to_place_id='b', assertion_ids=['assert'], eligibility={'record_ids':['r']})
    site['relationships'] = [dict(base, id='valid'), dict(base, id='domestic', to_place_id='a'),
                             dict(base, id='unknown', to_place_id='x'), dict(base, id='hypothesis', kind='hypothesis')]
    units, exclusions = units_from_site(site)
    assert [u['id'] for u in units] == ['valid']
    assert units[0]['from_country'] == 'NA'
    assert {e['reason'] for e in exclusions} == {'domestic', 'hypothesis', 'ambiguous_or_non_country_endpoint'}


def test_export_replay_and_tamper_detection(tmp_path):
    from test_site_export import site_inputs
    from atlas.site_export import export_site
    from atlas.network_analysis import run
    from atlas.util import read_json, write_json
    paths, _ = site_inputs(tmp_path)
    bundle = tmp_path/'site'
    export_site(**paths, out=bundle)
    reviews = tmp_path/'reviews.json'
    write_json(reviews, {'repeat_report_reviews': [], 'granularity_reviews': [], 'identity_reviews': []})
    out = tmp_path/'network'
    transport_args = dict(map_path=paths['snapshot'], release_id='a'*64)
    first = run(bundle, reviews, [], out, **transport_args)
    assert run(bundle, reviews, [], out, True, **transport_args) == first
    assert run(bundle, reviews, [], out, **transport_args) == first
    data = read_json(out/'network-analysis.json')
    assert data['scopes'][0]['combined']['raw']['units'] == 0
    import copy
    import jsonschema
    from atlas.network_analysis import schema, validate_analysis
    from atlas.util import digest
    wrong = copy.deepcopy(data)
    corrected = wrong['scopes'][0]['combined']['repeat_report_corrected']
    corrected['ranking_status'] = 'unavailable_partial_identity_review'
    corrected['incident_strength'] = [dict(key='NA', value=1, rank=1)]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(wrong, schema())
    wrong = copy.deepcopy(data)
    wrong['inputs']['site_sha256'] = 'not-a-digest'
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(wrong, schema())
    wrong = copy.deepcopy(data)
    del wrong['coverage']['frame_completeness']
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(wrong, schema())
    wrong = copy.deepcopy(data)
    wrong['scopes'][0]['id'] = 'f'*64
    wrong['analysis_id'] = digest({k:v for k,v in wrong.items() if k!='analysis_id'})
    with pytest.raises(ValueError, match='scope identity'):
        validate_analysis(wrong)
    data['scopes'][0]['combined']['raw']['units'] = 99
    write_json(out/'network-analysis.json', data)
    with pytest.raises(ValueError, match='checksum'):
        run(bundle, reviews, [], out, True, **transport_args)


def test_human_travel_excludes_products_remains_and_unknown_granularity():
    rows = [dict(unit(str(i), 'r', 'CN', 'CH'), movement_category=g)
            for i, g in enumerate(['living_travellers', 'product_shipments', 'human_remains', 'vessel_only', 'unresolved'])]
    assert counts(rows)['incoming_travel'] == [dict(key='CH', value=1, rank=1)]
    assert counts(rows)['units'] == 5


def test_capture_history_keeps_failure_and_unselected_recovery(tmp_path):
    from atlas.network_analysis import coverage_ledger
    from atlas.util import write_json
    receipt = tmp_path/'receipts.json'
    batches = [{'source_id':'who', 'completed_at':'2026-09-29T00:00:00Z',
                'source_receipt_sha256':'a'*64, 'entries':[{'url':'https://www.who.int/a', 'status':'failed'}]},
               {'source_id':'who', 'completed_at':'2026-09-29T01:00:00Z',
                'source_receipt_sha256':'b'*64, 'entries':[{'url':'https://www.who.int/a', 'status':'captured', 'parse_status':'text_ready'}]}]
    write_json(receipt,batches)
    rows = coverage_ledger(dict(channels=[],records=[],documents=[],location_memberships=[]), [(receipt,batches)])
    assert rows[0]['stages']['fetch'] == 'receipt_capture_not_selected'
    assert rows[0]['stages']['eligibility'] == 'unknown'
    assert [h['status'] for h in rows[0]['history']] == ['failed','captured']
    assert rows[0]['history'][1]['receipt_sha256'] == 'b'*64


def test_assessment_coverage_is_separate_from_resolved_identity():
    rows = [dict(unit('u1', 'r1'), identity_status='source_checked_identity_unresolved'), unit('u2', 'r2')]
    summary = summarize(rows, [], {'r1', 'r2'})
    assert summary['identity_coverage']['assessed_relationships'] == 1
    assert summary['identity_coverage']['grouped_relationships'] == 0
    assert summary['repeat_report_corrected']['ranking_status'] == 'unavailable_partial_identity_review'
    assert summary['movement_coverage']['living_travellers'] == 2
    group = dict(id='singleton', relationship_ids=['u1'], evidence_ids=['e1'],
                 reviewed_at='2026-09-29T10:00:00Z', reviewed_by='Fixture', basis='No other reports.',
                 source_lineage='One source.', status='source_checked_draft')
    with pytest.raises(ValueError):
        validate_reviews([group], rows, {'evidence':[{'id':'e1','record_id':'r1'}]})


def test_identity_candidates_include_reverse_direction_without_assigning_identity():
    from atlas.network_analysis import identity_candidates
    rows = [unit('one','r1'), unit('reverse','r2','IT','SN'),
            dict(unit('shared','r3'),kind='shared_event'), unit('other','r4','CN','CH')]
    assert identity_candidates(rows) == {'one':['reverse'],'reverse':['one'],'shared':[],'other':[]}
    assert all(r['identity_status']=='unreviewed' for r in rows)
