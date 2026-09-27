"""Reviewed chains retain source identity, explicit order and missing places."""
import copy
import pytest
from test_site_export import site_inputs
from atlas.site_export import export_site, validate_bundle
from atlas.util import read_json, write_json


def chain_inputs(tmp_path):
    paths, ann = site_inputs(tmp_path)
    records = read_json(paths['snapshot'])['records']
    def ref(i):
        return dict(record_id=records[i]['id'], claim_index=0, quote_index=0, section='Synthetic chain evidence')
    def node(key, i, place):
        return dict(key=key, label=key, entity_kind='contact_group', place_id=place,
                    location_note='Synthetic reference point; individual locations are not supplied.',
                    event_date={'value':None,'status':'not_reported'}, date_basis='unknown',
                    date_note='The source does not report an exposure date.', membership_basis='Named synthetic episode membership.',
                    uncertainty='Synthetic group, without individual identities.', evidence=[ref(i)])
    def edge(key, start, end):
        return dict(key=key, label='Reported contact', kind='contact_exposure', directed=False,
                    direction_basis='not_reported', certainty='reported', basis='Explicit source contact reference.',
                    uncertainty='Contact does not establish infection.', from_node=start, to_node=end, evidence=[ref(0)])
    ann.update(contract_version='1.1.0', reviewed_chains=[dict(key='episode', kind='contact_exposure', label='Synthetic contact episode',
        scope='Named synthetic episode for dependency testing.', membership_review='Each member belongs to the same explicitly reviewed episode.',
        uncertainty='No transmission is asserted.', reviewed_at=ann['reviewed_at'], reviewed_by='Fixture',
        nodes=[node('origin',0,'p'),node('unknown',1,None),node('branch',0,'p')],
        edges=[edge('first','origin','unknown'),edge('second','origin','branch')])])
    write_json(paths['annotations'],ann)
    return paths,ann


def test_chain_evidence_branching_and_stable_ids(tmp_path):
    paths,ann=chain_inputs(tmp_path)
    bundle=export_site(**paths,out=tmp_path/'out')
    chain=bundle['reviewed_chains'][0]
    assert len(chain['nodes'])==3 and len(chain['edges'])==2
    assert chain['nodes'][1]['place_id'] is None and chain['nodes'][1]['coordinate_precision'] is None
    assert chain['nodes'][0]['event_date']['value'] is None
    assert len(chain['edges'][0]['eligibility']['record_ids'])==2
    assert len(chain['edges'][1]['eligibility']['record_ids'])==1
    ev={e['id']:e for e in bundle['evidence']}
    assert all(ev[e]['quote'] for item in chain['nodes']+chain['edges'] for e in item['evidence_ids'])
    ann['reviewed_chains'][0]['label']='Edited display label';write_json(paths['annotations'],ann)
    again=export_site(**paths,out=tmp_path/'again')['reviewed_chains'][0]
    assert chain['id']==again['id']
    assert [n['id'] for n in chain['nodes']]==[n['id'] for n in again['nodes']]


@pytest.mark.parametrize('change',[
    lambda c:c['edges'][0]['eligibility']['record_ids'].pop(),
    lambda c:c['edges'][0].update(from_node_id='missing'),
    lambda c:c['nodes'][0].update(place_id='missing'),
    lambda c:c['nodes'][0].update(coordinate_precision='Exact residence'),
    lambda c:c['nodes'][0].update(assertion_ids=[]),
    lambda c:c['nodes'][0].update(topic_ids=['unrelated']),
    lambda c:c['nodes'][0].update(evidence_ids=['missing']),
    lambda c:c['nodes'][0].update(document_ids=[]),
    lambda c:c['edges'][0].update(kind='established_transmission'),
    lambda c:c['edges'][0].update(directed=True),
    lambda c:c['nodes'].append(copy.deepcopy(c['nodes'][0])),
    lambda c:c['edges'].pop(),
])
def test_invalid_chain_graph_rejected(tmp_path,change):
    paths,_=chain_inputs(tmp_path);bundle=export_site(**paths,out=tmp_path/'out')
    change(bundle['reviewed_chains'][0])
    with pytest.raises(ValueError):validate_bundle(bundle)


def test_reporting_order_and_type_are_reviewed(tmp_path):
    paths,ann=chain_inputs(tmp_path);chain=ann['reviewed_chains'][0]
    chain['kind']='reporting_sequence';chain['nodes']=chain['nodes'][:2];chain['edges']=chain['edges'][:1]
    for node in chain['nodes']:node['entity_kind']='report'
    chain['edges'][0].update(kind='reporting_sequence',directed=True,direction_basis='reviewed_publication_order')
    write_json(paths['annotations'],ann)
    export_site(**paths,out=tmp_path/'valid')
    chain['edges'][0].update(from_node='unknown',to_node='origin');write_json(paths['annotations'],ann)
    with pytest.raises(ValueError,match='publication dates'):export_site(**paths,out=tmp_path/'bad')
    chain['edges'][0].update(from_node='origin',to_node='unknown');chain['kind']='established_transmission'
    chain['edges'][0].update(kind='established_transmission',certainty='uncertain',direction_basis='source_reported')
    write_json(paths['annotations'],ann)
    with pytest.raises(ValueError,match='source-established'):export_site(**paths,out=tmp_path/'uncertain')


def test_chain_quotes_must_exist_in_captured_source(tmp_path):
    paths,ann=chain_inputs(tmp_path)
    evidence=ann['reviewed_chains'][0]['nodes'][0]['evidence'][0]
    evidence.pop('quote_index');evidence['quote']='Invented household transmission statement.'
    write_json(paths['annotations'],ann)
    with pytest.raises(ValueError,match='not found'):export_site(**paths,out=tmp_path/'bad')


def test_source_established_branch_and_cycle_rejection(tmp_path):
    paths,ann=chain_inputs(tmp_path);chain=ann['reviewed_chains'][0]
    chain['kind']='established_transmission'
    for node in chain['nodes']:node['entity_kind']='case_group'
    for edge in chain['edges']:
        edge.update(kind='established_transmission',certainty='established_by_source',directed=True,direction_basis='source_reported')
    write_json(paths['annotations'],ann)
    bundle=export_site(**paths,out=tmp_path/'valid')
    assert len(bundle['reviewed_chains'][0]['edges'])==2
    reverse=copy.deepcopy(chain['edges'][0]);reverse.update(key='reverse',from_node='unknown',to_node='origin')
    chain['edges'].append(reverse);write_json(paths['annotations'],ann)
    with pytest.raises(ValueError,match='cycle'):export_site(**paths,out=tmp_path/'cycle')
