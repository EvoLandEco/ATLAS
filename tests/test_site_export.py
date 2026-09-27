"""Comparison fixtures keep interpretation and window eligibility in ATLAS."""
import copy
from pathlib import Path
import pytest
from atlas.site_export import Comparison, Eligibility, eligible, validate_bundle, SiteBundle


def test_temporal_comparison_requires_all_evidence():
    records={'old':{'publication':'2026-07-01','capture':'2026-09-25T12:00:00Z'},
             'new':{'publication':'2026-08-01','capture':'2026-09-26T12:00:00Z'}}
    rule=Eligibility(record_ids=['old','new'])
    assert not eligible(rule,records,'2026-07-01','2026-07-31','publication')
    assert eligible(rule,records,'2026-07-01','2026-08-01','publication')
    assert not eligible(rule,records,'2026-07-01','2026-08-01','publication','2026-09-25T23:59:59Z')
    assert not eligible(rule,records,'2026-09-26','2026-09-26','capture')
    assert eligible(Eligibility(record_ids=['new']),records,'2026-09-26','2026-09-26','capture')


def test_comparison_kinds_do_not_imply_revision_or_independence():
    c=dict(id='c',kind='contradiction',status='unresolved',participant_ids=['a','b'],participant_labels={'a':'Original section','b':'Second section'},
           reason='Two sections describe the same quantity and period.',scope_review='Same scope reviewed.',
           evidence_ids=['e'],eligibility={'record_ids':['old','new']},reviewed_at='2026-09-26T12:00:00Z',
           reviewed_by='Fixture',review_state='source_checked_draft',lineage=[],independence=None)
    Comparison.model_validate(c)
    with pytest.raises(ValueError): Comparison.model_validate(dict(c,kind='correction'))
    with pytest.raises(ValueError): Comparison.model_validate(dict(c,kind='corroboration',status='documented'))
    for kind in ['republication','different_scope','unresolved_association']:
        Comparison.model_validate(dict(c,kind=kind,status='documented' if kind!='unresolved_association' else 'unresolved'))
    Comparison.model_validate(dict(c,kind='correction',status='documented',lineage=[{'from_assertion_id':'a','to_assertion_id':'b','evidence_ids':['e']}]))
    with pytest.raises(ValueError): Comparison.model_validate(dict(c,kind='republication',status='documented',lineage=[{'from_assertion_id':'a','to_assertion_id':'b','evidence_ids':['e']}]))


def site_inputs(tmp_path):
    from test_metrics import inputs,run
    from atlas.util import read_json,write_json,digest
    paths=inputs(tmp_path);snapshot,annotations,sources,batch,data=paths
    first=data['records'][0]
    first.update(title='Source selection',conflict=True)
    first['claims'][0]['quotes'][0]='As of 1 July 2026, 10 confirmed cases were reported in Country A.'
    second=copy.deepcopy(first);second.update(id='doc_'+'b'*24+':0',document_id='doc_'+'b'*24,publication='2026-08-02',capture='2026-09-26T12:00:00Z',conflict=False)
    second['claims']=[{'claim_index':0,'text':'Correction: the total on 1 July was 11 confirmed cases, replacing 10.', 'quotes':['Correction: the total on 1 July was 11 confirmed cases, replacing 10.']}]
    (sources/(second['document_id']+'.txt')).write_text(second['claims'][0]['quotes'][0])
    data['records'].append(second)
    data['tracks'][0].update(label='Example reporting topic',kind='Country summary',disease_group='Example disease')
    data['map_links']=[]
    batch['records_sha256']=digest(data['records']);write_json(snapshot,data);write_json(annotations,batch)
    from atlas.metrics import export_metrics
    export_metrics(snapshot,annotations,sources,tmp_path/'metrics','2026-07-01','2026-09-30')
    acquired=[]
    for r in data['records']:
        acquired.append(dict(document_id=r['document_id'],document=dict(title='Canonical source title',url=r['url'],content_url=r['url'],published_at=r['publication'],publication_precision='day',source_id='authority',text_sha256=digest((sources/(r['document_id']+'.txt')).read_bytes()),raw_sha256='0'*64)))
    results=tmp_path/'results.json';write_json(results,acquired)
    old='claim:'+first['id']+':0';new='claim:'+second['id']+':0'
    comparison=dict(key='correction',kind='correction',status='documented',participants=[old,new],participant_labels=['Original report','Correction notice'],reason='The later source explicitly replaces the original total.',scope_review='Same confirmed-case quantity, reporting population and 1 July cutoff.',evidence=[dict(record_id=second['id'],claim_index=0,quote_index=0,section='Correction notice')],lineage=[[old,new]])
    ann=dict(contract_version='1.0.0',records_sha256=digest(data['records']),reviewed_at='2026-09-26T12:00:00Z',reviewed_by='Synthetic fixture',organizations=[dict(id='authority',name='Example Authority')],channels=[dict(id='channel',name='Example bulletin',organization_id='authority',snapshot_source='Authority',acquisition_source='authority')],areas=[dict(code='NA',label='Namibia')],places=[dict(id='p',label='Example reference point',longitude=17,latitude=-22,precision='National reference point',area_codes=['NA'],topic_ids=['a'])],endpoints=[],locations=[],assertions=[],comparisons=[comparison],limitations=['Synthetic fixture; no real outbreak.'])
    site_annotations=tmp_path/'site-annotations.json';write_json(site_annotations,ann)
    schedule=tmp_path/'weekly.yml';schedule.write_text("on:\n  schedule:\n    - cron: '37 8 * * 3'\n      timezone: Europe/Amsterdam\n")
    return dict(snapshot=snapshot,results=results,metrics_path=tmp_path/'metrics/metrics.json',annotations=site_annotations,source_dir=sources,schedule=schedule),ann


def test_export_references_revision_windows_and_manifest(tmp_path):
    from atlas.site_export import export_site,verify_site
    from atlas.util import read_json
    import jsonschema
    paths,_=site_inputs(tmp_path);out=tmp_path/'site'
    bundle=export_site(**paths,out=out)
    assert verify_site(out)['status']=='valid'
    jsonschema.Draft202012Validator(read_json(out/'atlas-site.schema.json')).validate(bundle)
    records={r['id']:r for r in bundle['records']};c=bundle['comparisons'][0]
    assert not eligible(c['eligibility'],records,'2026-07-01','2026-07-31')
    assert eligible(c['eligibility'],records,'2026-07-01','2026-08-02')
    assert bundle['snapshot']['next_update_date']=='2026-09-30'
    assert bundle['areas'][0]['code']=='NA'
    assert bundle['snapshot']['schedule_activation']=='not_verified'
    assert len(c['lineage'])==1
    assert all(d['title']=='Canonical source title' for d in bundle['documents'])
    again=export_site(**paths,out=tmp_path/'again')
    assert bundle['assertions']==again['assertions'] and bundle['comparisons']==again['comparisons']
    with pytest.raises(ValueError,match='empty'):export_site(**paths,out=out)
    (out/'atlas-site.json').write_text('{}')
    with pytest.raises(ValueError,match='checksum'):verify_site(out)


@pytest.mark.parametrize('change',[
    lambda b:b['comparisons'][0]['eligibility'].update(record_ids=[b['records'][0]['id']]),
    lambda b:b['comparisons'][0]['participant_ids'].append('missing'),
    lambda b:b['evidence'][0].update(claim_index=99),
    lambda b:b['evidence'][0].update(document_id=b['documents'][1]['id']),
    lambda b:b['documents'][0].update(url='javascript:alert(1)'),
    lambda b:b['records'][0]['assertion_ids'].clear(),
    lambda b:b['source_coverage'][0]['document_ids'].clear(),
    lambda b:b['places'][0].update(area_codes=['XX']),
    lambda b:b['snapshot'].update(captured_at='2026-01-01T00:00:00Z'),
    lambda b:b.update(contract_version='2.0.0'),
])
def test_build_boundary_rejects_invalid_graph(tmp_path,change):
    from atlas.site_export import export_site
    paths,_=site_inputs(tmp_path);bundle=export_site(**paths,out=tmp_path/'site');change(bundle)
    with pytest.raises((ValueError,KeyError)):validate_bundle(bundle)


def test_source_hash_binding_and_revision_cycle(tmp_path):
    from atlas.site_export import export_site
    from atlas.util import write_json
    paths,ann=site_inputs(tmp_path)
    c=ann['comparisons'][0];c['lineage'].append(list(reversed(c['lineage'][0])))
    write_json(paths['annotations'],ann)
    with pytest.raises(ValueError,match='Revision publication|Cyclic'):export_site(**paths,out=tmp_path/'bad')
    c['lineage'].pop();write_json(paths['annotations'],ann)
    next(paths['source_dir'].iterdir()).write_text('Changed source')
    with pytest.raises(ValueError,match='hash differs'):export_site(**paths,out=tmp_path/'bad')


def test_planned_schedule_uses_capture_and_timezone(tmp_path):
    from atlas.site_export import planned_update
    schedule=tmp_path/'weekly.yml';schedule.write_text("on:\n  schedule:\n    - cron: '37 8 * * 3'\n      timezone: Europe/Amsterdam\n")
    assert planned_update('2026-09-30T06:36:00Z',schedule)['next_update_date']=='2026-09-30'
    assert planned_update('2026-09-30T06:37:00Z',schedule)['next_update_date']=='2026-10-07'
    assert planned_update('2026-10-24T12:00:00Z',schedule)['next_update_date']=='2026-10-28'


def test_repeated_spans_keep_occurrences_pages_and_memberships(tmp_path,monkeypatch):
    import re
    from atlas import site_export
    from atlas.util import read_json,write_json,digest
    paths,ann=site_inputs(tmp_path);data=read_json(paths['snapshot']);record=data['records'][0]
    did=record['document_id'];quote=record['claims'][0]['quotes'][0]
    source=paths['source_dir']/(did+'.txt')
    text='Résumé '+source.read_text()+'\n[[PAGE 2]]'+quote.replace(' ','\n')+'\n[[PAGE 3]]'+quote
    source.write_text(text)
    acquired=read_json(paths['results'])
    next(r for r in acquired if r['document_id']==did)['document']['text_sha256']=digest(source.read_bytes())
    write_json(paths['results'],acquired)
    for occurrence,role in [(1,'occurrence'),(2,'context')]:
        ann['locations'].append(dict(record_id=record['id'],claim_index=0,area_code='NA',role=role,
            evidence=[dict(record_id=record['id'],claim_index=0,quote_index=0,occurrence=occurrence,section='Repeated table')],reason='Synthetic source location reference.'))
    ann['comparisons'][0]['participants'].append('claim:'+record['id']+':1')
    ann['comparisons'][0]['participant_labels'].append('Context in original report')
    write_json(paths['annotations'],ann)
    finditer=re.finditer;pattern=r'\s+'.join(re.escape(w) for w in quote.split());searches=[]
    def counted(pattern_arg,text_arg,*args,**kwargs):
        if pattern_arg==pattern and text_arg==text:searches.append(1)
        return finditer(pattern_arg,text_arg,*args,**kwargs)
    monkeypatch.setattr(site_export.re,'finditer',counted)
    bundle=site_export.export_site(**paths,out=tmp_path/'site')
    assert len(searches)==1
    monkeypatch.undo()
    ev={e['id']:e for e in bundle['evidence']}
    assert [ev[m['evidence_ids'][0]]['page'] for m in bundle['location_memberships']]==[2,3]
    for e in bundle['evidence']:
        captured=(paths['source_dir']/(e['document_id']+'.txt')).read_text()
        pages=re.findall(r'\[\[PAGE (\d+)\]\]',captured[:e['start']])
        assert e['page']==(int(pages[-1]) if pages else None)
        assert captured[e['start']:e['end']]==e['quote']
    first=next(r for r in bundle['records'] if r['id']==record['id'])
    assert first['comparison_ids']==[bundle['comparisons'][0]['id']]
    assert len(first['location_membership_ids'])==2
    for field in ['comparison_ids','location_membership_ids']:
        broken=copy.deepcopy(bundle)
        next(r for r in broken['records'] if r['id']==record['id'])[field].clear()
        with pytest.raises(ValueError):validate_bundle(broken)


def test_place_memberships_preserve_reference_order(tmp_path):
    from atlas.site_export import export_site
    from atlas.util import read_json,write_json
    paths,ann=site_inputs(tmp_path);snapshot=read_json(paths['snapshot'])
    for r in reversed(snapshot['records']):
        ann['locations'].append(dict(record_id=r['id'],claim_index=0,area_code='NA',role='reporting_scope',
            evidence=[dict(record_id=r['id'],claim_index=0,quote_index=0,section='Source scope')],reason='Fixture reporting scope.'))
    write_json(paths['annotations'],ann);bundle=export_site(**paths,out=tmp_path/'site')
    for p in bundle['places']:
        rids=[r['id'] for r in bundle['records'] if r['topic_id'] in p['topic_ids']]
        rels=[r for r in bundle['relationships'] if p['id'] in {r['from_place_id'],r['to_place_id']}]
        locs=[m['id'] for m in bundle['location_memberships'] if m['area_code'] in p['area_codes'] and
              (m['record_id'] in rids or any(m['record_id'] in r['eligibility']['record_ids'] for r in rels))]
        assert p['record_ids']==rids and p['relationship_ids']==[r['id'] for r in rels] and p['location_membership_ids']==locs
