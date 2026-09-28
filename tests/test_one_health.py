"""Synthetic evidence checks for One Health observations and exact relations."""
import copy
import json
import subprocess
import pytest
from test_site_export import site_inputs
from atlas.util import read_json, write_json
from atlas.site_export import export_site, validate_bundle


def one_health_inputs(tmp_path):
    paths, ann = site_inputs(tmp_path)
    rs = read_json(paths['snapshot'])['records']
    missing = dict(value=None, status='not_extracted')
    def ref(i):
        return dict(record_id=rs[i]['id'], claim_index=0, quote_index=0, section='Synthetic observation')
    nodes = []
    for i, domain in enumerate(['human','environment']):
        nodes.append(dict(key=domain, record_id=rs[i]['id'], label=domain, domain=domain,
            entity_kind='sample', roles=['sampled_matrix'], scope='episode', taxon=missing, material=missing,
            agent=dict(value='Synthetic organism',status='reported'), agent_kind='pathogen', finding='agent_detected',
            observation_date=missing, period_start=missing, period_end=missing, date_basis='unknown',
            period_label=missing, date_note='Sample day is not extracted.',
            sampling={k:missing for k in ['sample_unit','frame','collection_method','test_method']},
            measure_keys=[],place_ids=[],location_note='Location has not been reviewed.',
            evidence=[ref(i)],uncertainty='Synthetic observation without inferred transmission.'))
    date_fields={k:nodes[0][k] for k in ['observation_date','period_start','period_end','date_basis','period_label','date_note']}
    ann.update(contract_version='1.3.0',one_health_nodes=nodes,one_health_reviews=[dict(record_id=r['id'],outcome='partial',
        scope='Synthetic quoted passage',reviewed_sections=['Synthetic observation'],reason='Selected section inspected.',
        pending_items=['Review the remaining source sections.'],evidence=[ref(i)],reviewed_at=ann['reviewed_at'],
        reviewed_by='Fixture',review_state='source_checked_draft') for i,r in enumerate(rs)],one_health_relations=[dict(
        key='association',label='Genomic association',from_node={k:nodes[0][k] for k in ['record_id','key']},
        to_node={k:nodes[1][k] for k in ['record_id','key']},kind='genomic_association',basis='source_reported',
        source_assertion_key='claim:'+rs[1]['id']+':0',evidence_types=['genomic_analysis'],directed=False,
        direction_basis='not_reported',source_certainty=dict(value='Matching isolates',status='reported'),
        scope='Named synthetic comparison',reason='Source-defined isolate comparison.',uncertainty='Direction is unresolved.',
        evidence=[ref(1)],reviewed_at=ann['reviewed_at'],reviewed_by='Fixture',review_state='source_checked_draft',**date_fields)])
    write_json(paths['annotations'],ann)
    return paths,ann


def test_evidence_layer_and_stable_content(tmp_path):
    paths,ann=one_health_inputs(tmp_path);b=export_site(**paths,out=tmp_path/'out')
    assert len(b['one_health_nodes'])==2 and len(b['one_health_relations'])==1
    assert len(b['one_health_relations'][0]['eligibility']['record_ids'])==2
    ann['reviewed_at']='2026-09-27T12:00:00Z';write_json(paths['annotations'],ann)
    again=export_site(**paths,out=tmp_path/'again')
    assert b['one_health_nodes']==again['one_health_nodes']
    node=ann['one_health_nodes'][0];node['label']='Revised synthetic observation label';write_json(paths['annotations'],ann)
    changed=export_site(**paths,out=tmp_path/'changed')
    assert b['one_health_nodes'][0]['id']!=changed['one_health_nodes'][0]['id']


@pytest.mark.parametrize('change',[
    lambda b:b['one_health_relations'][0]['eligibility']['record_ids'].pop(),
    lambda b:b['one_health_relations'][0].update(from_node_id='missing'),
    lambda b:b['one_health_relations'][0].update(directed=True,direction_basis='source_reported'),
    lambda b:b['one_health_relations'][0].update(source_assertion_id='missing'),
    lambda b:b['one_health_nodes'][0].update(place_ids=['p']),
    lambda b:b['one_health_nodes'][0].update(measure_ids=['missing']),
    lambda b:b['one_health_nodes'][0].update(domain='food',roles=['reservoir']),
    lambda b:b['one_health_nodes'][0].update(observation_date={'value':'2026-01-01','status':'reported'}),
    lambda b:b['one_health_reviews'][0].update(pending_items=[]),
    lambda b:b['one_health_nodes'].append(copy.deepcopy(b['one_health_nodes'][0])),
])
def test_invalid_one_health_support(tmp_path,change):
    paths,_=one_health_inputs(tmp_path);b=export_site(**paths,out=tmp_path/'out');change(b)
    with pytest.raises(ValueError):validate_bundle(b)


def test_selector_drops_edges_without_bridging_and_scopes_corrections(tmp_path):
    paths,_=one_health_inputs(tmp_path);b=export_site(**paths,out=tmp_path/'out')
    script="""
import fs from 'node:fs';import assert from 'node:assert/strict';
const {selectView}=await import(process.argv[1]);const b=JSON.parse(fs.readFileSync(process.argv[2]));
const full=selectView(b,'2026-07-01','2026-08-02');
assert.equal(full.one_health.nodes.length,2);assert.equal(full.one_health.relations.length,1);
assert.equal(full.one_health.coverage.partial,2);
const short=selectView(b,'2026-07-01','2026-07-31');assert.equal(short.one_health.nodes.length,1);assert.equal(short.one_health.relations.length,0);
const filtered=selectView(b,'2026-07-01','2026-08-02','publication',null,[b.records[0].id]);assert.equal(filtered.one_health.relations.length,0);
const early=selectView(b,'2026-07-01','2026-08-02','publication','2026-09-25T23:59:59Z');assert.equal(early.one_health.relations.length,0);
const domain=selectView(b,'2026-07-01','2026-08-02','publication',null,null,{domains:['environment']});assert.equal(domain.one_health.nodes.length,1);assert.equal(domain.one_health.relations.length,0);
const dated=selectView(b,'2026-07-01','2026-08-02','publication',null,null,{observation_from:'2026-01-01',observation_until:'2026-12-31'});assert.equal(dated.one_health.nodes.length,0);assert.equal(dated.one_health.undated_nodes.length,2);
b.comparisons[0].kind='contradiction';b.comparisons[0].lineage=[];b.comparisons[0].participant_ids=[b.one_health_relations[0].source_assertion_id];
assert.equal(selectView(b,'2026-07-01','2026-08-02').one_health.relations[0].contested,true);
b.comparisons[0].kind='correction';
b.comparisons[0].lineage=[{from_assertion_id:b.one_health_relations[0].source_assertion_id,to_assertion_id:b.comparisons[0].participant_ids[0],evidence_ids:b.comparisons[0].evidence_ids}];
assert.equal(selectView(b,'2026-07-01','2026-08-02').one_health.relations.length,0);
"""
    subprocess.run(['node','--input-type=module','-e',script,(tmp_path/'out/view.mjs').as_uri(),str(tmp_path/'out/atlas-site.json')],check=True)


def test_cross_species_requires_identified_hosts(tmp_path):
    from atlas.one_health import identity
    paths,_=one_health_inputs(tmp_path);b=export_site(**paths,out=tmp_path/'out')
    edge=b['one_health_relations'][0]
    edge.update(kind='cross_species_transmission');edge['id']=identity('relation',edge,{e['id']:e for e in b['evidence']})
    with pytest.raises(ValueError,match='identified pathogen hosts'):validate_bundle(b)


def test_missing_source_span_is_rejected(tmp_path):
    paths,ann=one_health_inputs(tmp_path)
    ann['one_health_nodes'][0]['evidence']=[dict(record_id=ann['one_health_nodes'][0]['record_id'],quote='Uncaptured transmission claim',section='Uncaptured')]
    write_json(paths['annotations'],ann)
    with pytest.raises(ValueError,match='not found'):export_site(**paths,out=tmp_path/'out')


def test_negative_environmental_observation_has_no_transmission(tmp_path):
    paths, ann = one_health_inputs(tmp_path)
    ann['one_health_nodes'][1]['finding'] = 'agent_not_detected'
    write_json(paths['annotations'], ann)
    with pytest.raises(ValueError, match='detected isolate evidence'):
        export_site(**paths, out=tmp_path/'invalid')
    ann['one_health_relations'] = []
    write_json(paths['annotations'], ann)
    b = export_site(**paths, out=tmp_path/'valid')
    assert b['one_health_nodes'][1]['finding'] == 'agent_not_detected'
    assert b['one_health_relations'] == []
