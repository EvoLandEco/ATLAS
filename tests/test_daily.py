import copy
import json
import subprocess
from importlib.resources import files

import pytest

from atlas.daily import prepare_daily, selected_documents
from atlas.util import digest, write_json


def daily_inputs():
    text = 'The authority reported 0 cases in Namibia. An unusual exposure is under active investigation.\n'
    doc = dict(id='doc_one',source_id='national',url='https://health.example/report',
        content_url='https://health.example/report',title='Investigation',published_at='2026-10-01',
        publication_precision='day',capture='2026-10-02T00:00:00Z',text_sha256=digest(text.encode()),
        raw_sha256=digest(text.encode()),parse_status='text_ready')
    finding = dict(key='cases',kind='reported_count',text='The authority reports 0 cases in Namibia and is investigating an unusual exposure.',
        status='reported',statement_kind='source_statement',attribution=dict(value='Health authority',status='reported'),
        observation_period=dict(value=None,status='not_reported'),
        places=[dict(name='Namibia',country_code='NA',role='reporting_scope')],
        evidence=[dict(quote=q,start=None,language_tag='en',translation=None) for q in ['The authority reported 0 cases in Namibia.','An unusual exposure is under active investigation.']])
    review = dict(document_id=doc['id'],source_text_sha256=doc['text_sha256'],language_tag='en',title_translation=None,
        outcome='relevant',findings=[finding],reviewed_at='2026-10-03T00:00:00Z',reviewed_by='Source reviewer',
        review_state='source_checked_draft',limitations=['The source does not establish a cause.'])
    ann = dict(daily_version='0.2.1',reviews=[review],watch_assessments=[dict(key='investigation',label='Cause under investigation',
        finding_keys=['doc_one:cases'],reason_for_attention='The cause remains under investigation.',
        follow_up_question='Has the authority reported a cause?',reviewed_at=review['reviewed_at'],
        reviewed_by='Source reviewer',review_state='source_checked_draft', temporal_status='current',
        development_date='2026-10-01',date_basis='source_event_date',development_finding_keys=['doc_one:cases'],follow_up_finding_keys=['doc_one:cases'],counterevidence_finding_keys=[],
        criteria=[dict(kind='unusual_event',finding_keys=['doc_one:cases'],reason='Synthetic unusual-event review for the selector fixture.')],
        decision_reason='Source evidence requires follow-up review.',location_label='Namibia',diagnostic_label='Cause unknown',
        key_facts=[dict(label='Cases',text='0 cases reported',finding_keys=['doc_one:cases'])],
        review_due_at='2026-10-04T00:00:00Z')],reconciliations=[])
    config = dict(sources=[dict(id='national',name='Health authority',role='official_national_reporting',allowed_hosts=['health.example'])])
    acquisition = dict(completed_at='2026-10-02T02:00:00Z',publication_from='2026-09-30',publication_until='2026-10-06',sources=[])
    source = dict(source_export_id='a'*64,source_site_sha256='b'*64,source_manifest_sha256='c'*64,map_snapshot_sha256='d'*64)
    return [doc],{doc['id']:text},ann,config,acquisition,dict(documents=[],records=[]),source


def test_daily_exact_evidence_and_selector(tmp_path):
    args=daily_inputs(); data=prepare_daily(*args)
    assert data['documents'][0]['country_codes']==['NA']
    assert data['documents'][0]['processing_status']=='weekly_review_pending'
    assert data['findings'][0]['observation_period']['value'] is None
    assert any('0 cases' in e['quote'] for e in data['evidence'])
    assert data['watch_assessments'][0]['event_identity']=='not_assigned'
    assert data['knowledge_cutoff'].startswith('2026-10-03T00:00:00')
    selector=tmp_path/'view.mjs';selector.write_text(files('atlas').joinpath('assets/daily_view.js').read_text())
    write_json(tmp_path/'daily.json',data)
    subprocess.run(['node','--input-type=module','-e','''
import fs from 'node:fs';import assert from 'node:assert/strict';
const {selectDaily}=await import(process.argv[1]);const data=JSON.parse(fs.readFileSync(process.argv[2]));
assert.equal(selectDaily(data,'2026-10-01','2026-10-01').watch_items.length,1);
assert.equal(selectDaily(data,'2026-10-02','2026-10-06').documents.length,0);
assert.equal(selectDaily(data,'2026-09-30','2026-09-30').documents.length,0);
assert.equal(selectDaily(data,'2026-10-02','2026-10-02','capture').documents.length,1);
const early=selectDaily(data,'2026-10-01','2026-10-01','publication','2026-10-02T01:00:00Z');
assert.equal(early.documents.length,1);assert.equal(early.findings.length,0);
assert.deepEqual(early.documents[0].country_codes,[]);assert.equal(early.documents[0].review_id,null);
assert.equal(selectDaily(data,'2026-10-01','2026-10-01','publication','2026-10-02T01:00:00Z',null,['NA']).documents.length,0);
assert.equal(selectDaily(data,'2026-10-01','2026-10-01','publication',null,null,null,'2026-10-04T00:00:00Z').watch_items.length,1);
assert.equal(selectDaily(data,'2026-10-01','2026-10-01','publication',null,null,null,'2027-10-04T00:00:00Z').watch_items.length,1);
assert.equal(selectDaily({...data,watch_items:[]},'2026-10-01','2026-10-01').watch_items.length,0);
assert.equal(selectDaily(data,'2026-10-01','2026-10-01','publication','2026-10-03T01:00:00Z').watch_items.length,1);
assert.throws(()=>selectDaily(data,'2026-02-30','2026-10-01'));
assert.throws(()=>selectDaily(data,'2026-10-01','2026-10-01','publication','2026-10-03'));
''',selector.as_uri(),str(tmp_path/'daily.json')],check=True)
    for mutation in [lambda a:a['reviews'][0].update(source_text_sha256='f'*64),
                     lambda a:a['reviews'][0]['findings'][0]['evidence'][0].update(quote='A fabricated quote'),
                     lambda a:a['reviews'][0].update(reviewed_at='2026-10-01T00:00:00Z'),
                     lambda a:a['watch_assessments'][0].update(finding_keys=['absent']),
                     lambda a:a['reviews'].append(copy.deepcopy(a['reviews'][0]))]:
        broken=copy.deepcopy(args);mutation(broken[2])
        with pytest.raises(ValueError):prepare_daily(*broken)


def test_daily_exact_version_and_pending_reconciliation():
    args=daily_inputs(); old=args[0][0]
    revised=dict(old,id='doc_two',capture='2026-10-04T00:00:00Z',published_at='2026-10-07')
    assert selected_documents([old,revised],'2026-09-30','2026-10-06')==[]
    data=prepare_daily(*args)
    args[2]['reconciliations']=[dict(review_id=data['documents'][0]['review_id'],weekly_export_id='a'*64,
        record_ids=[],disposition='reviewed_not_exported',reason='All weekly review stages are complete.',
        reviewed_at='2026-10-07T15:00:00Z',reviewed_by='Reviewer',weekly_inbox_sha256='e'*64)]
    with pytest.raises(ValueError,match='completed weekly handoff'):prepare_daily(*args)


def test_daily_source_coverage_preserves_check_scope_and_time():
    from pathlib import Path
    from atlas.util import stamp
    cases=json.loads((Path(__file__).parent/'fixtures/daily-source-coverage.json').read_text())
    for case in cases:
        args=daily_inputs();args[3]['sources'][0]['enabled']=case['enabled']
        args[4]['sources']=[dict(source_id='national',notes=[],**case['check'])]
        coverage=prepare_daily(*args)['source_coverage'][0]
        assert coverage['status']==case['status'],case['name']
        assert coverage['checked_at']==(stamp(case['checked_at']) if case['checked_at'] else None),case['name']
    args[4]['sources'][0]['checked_at']='2026-10-04T00:00:00Z'
    with pytest.raises(ValueError,match='Source check follows acquisition'):prepare_daily(*args)


def test_daily_publication_bindings_use_source_url_and_date():
    args=daily_inputs();args[5]['channels']=[dict(id='public-channel',acquisition_source='national')]
    base=dict(id='base-one',channel_id='public-channel',url=args[0][0]['url'],publication='2026-10-01')
    args[5]['documents']=[base,dict(base,id='base-two'),dict(base,id='older-edition',publication='2026-09-01'),
        dict(base,id='other-source',channel_id='another-channel')]
    result=prepare_daily(*args)['documents'][0]
    assert result['channel_id']=='public-channel' and result['base_document_ids']==['base-one','base-two']
    assert result['processing_status']=='weekly_review_pending'


def test_undated_daily_reviews_remain_outside_report_and_watch_selection():
    from atlas.daily import dated_annotations
    args=daily_inputs();args[0][0].update(published_at=None,publication_precision='unknown')
    original=copy.deepcopy(args[2])
    data=prepare_daily(*args)
    assert data['documents']==data['findings']==data['watch_assessments']==[]
    assert args[2]==original
    _,receipt=dated_annotations(args[0],args[2],args[4])
    assert receipt['excluded_documents'][0]['reason']=='missing_publication_date'
    assert len(receipt['excluded_review_ids'])==1
    assert receipt['excluded_watch_keys']==['investigation']


def test_daily_legacy_reconstruction_matches_frozen_output():
    from pathlib import Path
    args=daily_inputs();args[0][0].update(published_at=None,publication_precision='unknown')
    expected=json.loads((Path(__file__).parent/'fixtures/daily-0.2.1-undated.json').read_text())
    data=prepare_daily(*args,_legacy=True)
    data.update(generated_at=expected['generated_at'],software_version=expected['software_version'])
    data['daily_id']=digest({k:v for k,v in data.items() if k not in {'daily_id','generated_at'}})
    assert data==expected


def test_daily_export_schema_requires_its_version_and_publication_date():
    import jsonschema
    from atlas.daily import DailyExport
    data=prepare_daily(*daily_inputs())
    schema=DailyExport.model_json_schema()
    jsonschema.validate(data,schema)
    for broken in [dict(data,daily_version='0.2.1'),
                   dict(data,documents=[dict(data['documents'][0],publication=None)])]:
        with pytest.raises(jsonschema.ValidationError):jsonschema.validate(broken,schema)
        with pytest.raises(ValueError):DailyExport.model_validate(broken)
    assert schema['properties']['daily_version']['const']=='0.2.2'
    document=schema['$defs'][schema['properties']['documents']['items']['$ref'].split('/')[-1]]
    assert document['properties']['publication']['type']=='string'


def test_daily_mixed_watch_support_requires_reassessment():
    args=daily_inputs();args[0][0].update(published_at=None,publication_precision='unknown')
    args[2]['watch_assessments'][0]['finding_keys'].append('dated_document:cases')
    with pytest.raises(ValueError,match='reassess its dated findings'):
        prepare_daily(*args)


def test_daily_capture_reuses_original_objects_and_is_idempotent(tmp_path,monkeypatch):
    from atlas.daily import capture_daily,read_documents
    from atlas.store import Store
    from atlas.sources import save_document
    from atlas import sources
    weekly=Store(tmp_path/'weekly');source=dict(id='national')
    ident=save_document(weekly,source,text='Captured source.',raw=b'<p>Captured source.</p>',
        title='Report',url='https://health.example/report',content_url='https://health.example/report',
        published_at='2026-10-01',at='2026-10-02T00:00:00Z')
    head=weekly.verify();weekly.close();calls=[]
    config=dict(sources=[dict(id='national',enabled=True),dict(id='another',enabled=True),dict(id='closed',enabled=False)])
    def collect(store,received,since,**bounds):
        from atlas.util import utcnow
        assert received==config
        calls.append(bounds);checks=[]
        for src in received['sources']:
            check=dict(source_id=src['id'],status='empty' if src['enabled'] else 'disabled')
            store.append('source_check',check,utcnow());checks.append(check)
        return dict(sources=checks,documents_seen=0,documents_new=0)
    monkeypatch.setattr(sources,'collect',collect)
    state=tmp_path/'daily'
    first=capture_daily(state,tmp_path/'weekly',config,'2026-10-01','2026-10-07')
    assert capture_daily(state,tmp_path/'weekly',config,'2026-10-01','2026-10-07')==first
    assert len(calls)==1 and calls[0]['until']=='2026-10-07'
    assert first['source_ids']==['another','national']
    assert all(first['started_at']<=c['checked_at']<=first['completed_at'] for c in first['sources'])
    docs=read_documents(state,first['completed_at'])
    assert len(docs)==1 and docs[0]['id']==ident and docs[0]['capture'].startswith('2026-10-02')
    weekly=Store(tmp_path/'weekly');assert weekly.verify()==head;weekly.close()
    with pytest.raises(ValueError,match='separate archive'):capture_daily(tmp_path/'weekly',tmp_path/'weekly',{},'2026-10-01','2026-10-07')


def test_daily_bundle_reconstructs_source_evidence(tmp_path):
    from test_source_text import inputs
    from atlas.daily import export_daily,verify_daily
    from atlas.store import Store
    paths,bundle,_,_,_=inputs(tmp_path)
    args=daily_inputs();doc=args[0][0];state=tmp_path/'daily-state';store=Store(state)
    raw=args[1][doc['id']].encode()
    payload={k:v for k,v in doc.items() if k not in {'id','capture'}}
    payload.update(text_object=store.object(raw,'txt'),raw_object=store.object(raw,'bin'))
    store.append('document',payload,doc['capture'],doc['id']);store.close()
    acquisition=tmp_path/'acquisition.json';annotations=tmp_path/'daily-annotations.json'
    write_json(acquisition,args[4]);write_json(annotations,args[2]);out=tmp_path/'daily'
    receipt=export_daily(state,args[3],acquisition,annotations,bundle,paths['snapshot'],out)
    assert verify_daily(out,state,args[3],acquisition,annotations,bundle,paths['snapshot'])==receipt
    (state/payload['raw_object']).write_bytes(b'Changed captured source')
    with pytest.raises(ValueError,match='raw source object'):verify_daily(out,state,args[3],acquisition,annotations,bundle,paths['snapshot'])


def test_reconciliation_requires_receipt_chain_and_exact_review(tmp_path):
    from atlas.handoff import file_reference
    args=daily_inputs();data=prepare_daily(*args);jobs={};refs={}
    export=dict(bundle_path=str(tmp_path),map_snapshot_path=str(tmp_path/'snapshot.json'),
        manifest_sha256='c'*64,map_snapshot_sha256='d'*64,export_id='a'*64)
    for job,hour in [('review',7),('production',9),('inbox',12)]:
        receipt=dict(schema_version='1.0.0',cycle='2026-10-07',job=job,status='completed',
            completed_at=f'2026-10-07T{hour:02}:00:00Z',ledger_head='f'*64,dependencies={k:v['sha256'] for k,v in refs.items()},
            export=export if job!='review' else None,reviewed_export_id='a'*64 if job=='inbox' else None,
            post_review_validation='passed' if job=='inbox' else None)
        path=tmp_path/(job+'.json');write_json(path,receipt);refs[job]=file_reference(path)
        jobs[job]=dict(status='completed',completed_at=receipt['completed_at'],receipt=refs[job])
    handoff=dict(weekly_ready=True,cycle='2026-10-07',current_export=export,jobs=jobs,ledger=dict(head_hash='f'*64))
    args[2]['reconciliations']=[dict(review_id=data['documents'][0]['review_id'],weekly_export_id='a'*64,
        record_ids=[],disposition='reviewed_not_exported',reason='The reviewed item does not require a scientific record.',
        reviewed_at='2026-10-07T15:00:00Z',reviewed_by='Reviewer',weekly_inbox_sha256=refs['inbox']['sha256'])]
    assert prepare_daily(*args,weekly_handoff=handoff)['documents'][0]['processing_status']=='weekly_reviewed'
    args[2]['reviews'][0]['limitations'].append('Additional source uncertainty.')
    with pytest.raises(ValueError,match='reviewed version'):prepare_daily(*args,weekly_handoff=handoff)


def test_watch_selection_is_independent_of_source_and_covers_all_findings():
    from atlas.daily import WatchInput, watch_decision
    cases=json.loads((__import__('pathlib').Path(__file__).parent/'fixtures/daily-watch-decisions.json').read_text())
    for case in cases:
        args=daily_inputs();w=args[2]['watch_assessments'][0]
        w.update(temporal_status=case['temporal_status'], development_date=case.get('development_date','2026-10-01'),
            criteria=[dict(kind=k,finding_keys=['doc_one:cases'],reason='Source-supported significance in the synthetic fixture.') for k in case['criteria']])
        assert watch_decision(WatchInput.model_validate(w))==case['expected'],case['name']
        extra={'severe_impact':'Severe animal illness is reported.', 'spread_change':'The event has reached a new district.', 'response_gap':'The response lacks essential supplies.', 'time_sensitive_action':'The health authority requests immediate protective action.'}
        f=args[2]['reviews'][0]['findings'][0]
        for kind in case['criteria']:
            if kind in extra:
                q=extra[kind];args[1]['doc_one']+=q+'\n';f['text']+=' '+q
                f['evidence'].append(dict(quote=q,start=None,language_tag='en',translation=None))
        args[0][0]['text_sha256']=digest(args[1]['doc_one'].encode())
        args[2]['reviews'][0]['source_text_sha256']=args[0][0]['text_sha256']
        if 'time_sensitive_action' in case['criteria']:f['kind']='response_measure'
        result=prepare_daily(*args)
        assert bool(result['watch_items'])==(case['expected']!='not_selected')
        args[3]['sources'][0]['name']='Another monitored publisher'
        assert [r['attention'] for r in prepare_daily(*args)['watch_items']]==[r['attention'] for r in result['watch_items']]
    args=daily_inputs();args[2]['watch_assessments']=[]
    with pytest.raises(ValueError,match='every reviewed daily finding'):prepare_daily(*args)
    for field,value in [('review_due_at','2026-10-05T00:00:00Z'),('development_finding_keys',['absent'])]:
        args=daily_inputs();args[2]['watch_assessments'][0][field]=value
        with pytest.raises(ValueError):prepare_daily(*args)

    args=daily_inputs();args[2]['watch_assessments'][0]['reason_for_attention']='word '*50
    with pytest.raises(ValueError,match='55-word'):prepare_daily(*args)


def publication_binding_inputs():
    from pathlib import Path
    args=daily_inputs()
    fixture=json.loads((Path(__file__).parent/'fixtures/daily-publication-binding.json').read_text())
    binding=fixture['binding'];versions=binding['document_versions']
    versions[1].update(source_text_sha256=args[0][0]['text_sha256'],raw_sha256=args[0][0]['raw_sha256'])
    args[0][0]['url']=fixture['document_urls'][1]
    site=args[5];site['channels']=[dict(id='channel',acquisition_source='national')]
    site['documents']=[dict(id=v['document_id'],channel_id='channel',url=url,publication='2026-10-01',
        capture='2026-10-02T00:00:00Z',text_sha256=v['source_text_sha256'],raw_sha256=v['raw_sha256'])
        for v,url in zip(versions,fixture['document_urls'])]
    site['assertions']=[dict(id=prefix+str(i),document_id=v['document_id'],kind=kind,evidence_ids=['e'+str(i)])
        for i,v in enumerate(versions,1) for prefix,kind in [('a','finding'),('m','measure')]]
    site['comparisons']=[dict(id=key,kind='republication',status='documented',participant_ids=ids,
        reviewed_at='2026-10-03T00:00:00Z') for key,ids in [('c12',['a1','a2']),('c23',['a2','a3'])]]
    site['evidence']=[dict(id='e'+str(i),document_id=v['document_id'],source_text_sha256=v['source_text_sha256']) for i,v in enumerate(versions,1)]
    args[2]['publication_bindings']=[binding]
    return args


def test_reviewed_publication_alias_preserves_source_versions():
    args=publication_binding_inputs();old=copy.deepcopy(args);old[2].pop('publication_bindings')
    before=prepare_daily(*old);after=prepare_daily(*args)
    assert before['documents'][0]['base_document_ids']==['doc_one']
    assert after['documents'][0]['base_document_ids']==['base-one','base-three','doc_one']
    assert after['knowledge_cutoff']==before['knowledge_cutoff']
    for key in ['evidence','findings','watch_items','watch_assessments','reconciliations','source_coverage']:
        assert after[key]==before[key]
    assert {k:v for k,v in after['documents'][0].items() if k!='base_document_ids'}=={
        k:v for k,v in before['documents'][0].items() if k!='base_document_ids'}
    # Assertion comparisons without a publication review retain separate reports.
    assert before['documents'][0]['base_document_ids']==['doc_one']
    with_empty=copy.deepcopy(old);with_empty[2]['publication_bindings']=[]
    assert prepare_daily(*with_empty)['annotations_sha256']==before['annotations_sha256']


@pytest.mark.parametrize('mutation',[
    lambda a:a[2]['publication_bindings'][0]['document_versions'][0].update(source_text_sha256='0'*64),
    lambda a:a[2]['publication_bindings'][0]['document_versions'][0].update(raw_sha256='0'*64),
    lambda a:a[5]['documents'][0].update(channel_id='other'),
    lambda a:a[5]['documents'][0].update(publication='2026-09-01'),
    lambda a:a[2]['publication_bindings'][0].update(reviewed_at='2026-10-01T00:00:00Z'),
    lambda a:a[2]['publication_bindings'][0]['assertion_ids'].remove('m1'),
    lambda a:a[2]['publication_bindings'][0]['comparison_ids'].remove('c12'),
    lambda a:a[5]['comparisons'][0].update(kind='corroboration'),
    lambda a:a[2]['publication_bindings'][0].update(comparison_ids=['absent']),
    lambda a:a[5]['comparisons'][0].update(participant_ids=['a1','foreign']),
    lambda a:a[2]['publication_bindings'][0]['evidence_ids'].remove('e1'),
    lambda a:a[5]['evidence'][0].update(document_id='foreign'),
    lambda a:a[5]['evidence'].pop(),
    lambda a:a[2]['publication_bindings'].append(copy.deepcopy(a[2]['publication_bindings'][0])),
    lambda a:a[0][0].update(id='unrelated'),
])
def test_publication_binding_rejects_stale_partial_or_unrelated_scope(mutation):
    args=publication_binding_inputs();mutation(args)
    with pytest.raises(ValueError):prepare_daily(*args)


def test_publication_binding_metadata_preserves_historical_evidence_selection(tmp_path):
    args=publication_binding_inputs();data=prepare_daily(*args)
    selector=tmp_path/'view.mjs';selector.write_text(files('atlas').joinpath('assets/daily_view.js').read_text())
    write_json(tmp_path/'daily.json',data)
    subprocess.run(['node','--input-type=module','-e','''
import fs from 'node:fs';import assert from 'node:assert/strict';
const {selectDaily}=await import(process.argv[1]);const data=JSON.parse(fs.readFileSync(process.argv[2]));
const view=t=>selectDaily(data,'2026-10-01','2026-10-01','publication',t);
assert.deepEqual(view('2026-10-03T23:59:59Z').documents[0].base_document_ids,['base-one','base-three','doc_one']);
assert.deepEqual(view('2026-10-04T00:00:00Z').documents[0].base_document_ids,['base-one','base-three','doc_one']);
assert.equal(selectDaily(data,'2026-10-02','2026-10-02').documents.length,0);
assert.equal(view('2026-10-03T23:59:59Z').findings.length,view('2026-10-04T00:00:00Z').findings.length);
''',selector.as_uri(),str(tmp_path/'daily.json')],check=True)


def test_sealed_daily_v022_reconstruction_preserves_identity():
    from pathlib import Path
    expected=json.loads((Path(__file__).parent/'fixtures/daily-v0.2.2.json').read_text())
    data=prepare_daily(*daily_inputs())
    data.update(generated_at=expected['generated_at'],software_version=expected['software_version'])
    data['daily_id']=digest({k:v for k,v in data.items() if k not in {'daily_id','generated_at'}})
    assert data==expected
    args=publication_binding_inputs()
    with pytest.raises(ValueError,match='contract 0.2.2'):prepare_daily(*args,_legacy=True)
