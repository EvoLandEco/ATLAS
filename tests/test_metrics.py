import copy
from pathlib import Path
import jsonschema
import pytest
from atlas.metrics import export_metrics, MetricAnnotations, MetricsExport
from atlas.util import digest, write_json, read_json


def inputs(tmp_path):
    doc='doc_'+'a'*24
    quotes=['As of 1 July 2026, 10 confirmed cases were reported in Country A.',
            'A journey between Country A and Country B was reported.',
            'As of 1 July 2026, another section gives 11 confirmed cases.']
    records=[{'id':doc+':0','document_id':doc,'track':'a','source':'Authority','publication':'2026-07-02',
              'date_basis':'publication date','capture':'2026-09-25T12:00:00Z','url':'https://example.org/report',
              'claims':[{'claim_index':i,'text':q,'quotes':[q]} for i,q in enumerate(quotes)]}]
    def tv(value=None):return {'value':value,'status':'reported' if value else 'not_reported'}
    annotation={'annotation_key':'ten','label':'Confirmed cases','metric':'cases','value':10,'value_status':'reported',
        'unit':'people','count_kind':'cumulative','case_class':'confirmed','date_basis':'report',
        'disease':tv('Example disease'),'pathogen':tv(),'host':tv('Humans'),'geography':tv('Country A'),
        'population':tv('Reported national outbreak'),'as_of':tv('2026-07-01'),'period_label':'As of 1 July 2026',
        'source_reference':{'record_id':doc+':0','document_id':doc,'claim_index':0,'quote_indexes':[0]},
        'evidence':{'field':'value','quote':quotes[0]},'semantic_note':'Synthetic fixture with a source-stated count, class and date.'}
    data={'records':records,'tracks':[{'id':'a'}],'input_sha256':'fixture',
          'map_links':[{'id':'journey','support':[[doc+':0',1]]}],'relationships':[]}
    batch={'contract_version':'0.1.0','records_sha256':digest(records),'review_status':'source_checked_draft',
           'reviewed_by':'Fixture','reviewed_at':'2026-09-26T12:00:00Z','scope':'Synthetic test','measures':[annotation],
           'pending_candidate_count':0}
    sources=tmp_path/'sources';sources.mkdir();(sources/(doc+'.txt')).write_text('\n'.join(quotes))
    snapshot=tmp_path/'snapshot.json';annotations=tmp_path/'annotations.json'
    write_json(snapshot,data);write_json(annotations,batch)
    return snapshot,annotations,sources,batch,data


def run(paths,out,**kwargs):
    return export_metrics(*paths[:3],out,'2026-07-01','2026-07-31',**kwargs)


def test_exact_claim_panels_and_schema(tmp_path):
    paths=inputs(tmp_path);x=run(paths,tmp_path/'out')
    assert x['coverage']['measure_count']==1
    link=next(p for p in x['panels'] if p['kind']=='geographic_link')
    assert link['measure_ids']==[] and len(link['finding_ids'])==1
    assert x['series'][0]['connect_points'] is False
    jsonschema.Draft202012Validator(read_json(tmp_path/'out/metrics.schema.json')).validate(x)
    assert (tmp_path/'out/index.html').exists()
    with pytest.raises(ValueError,match='empty'):run(paths,tmp_path/'out')


def test_future_capture_and_inclusive_bounds(tmp_path):
    paths=inputs(tmp_path)
    assert run(paths,tmp_path/'early',knowledge_cutoff='2026-09-24T23:59:59Z')['records']==[]
    x=run(paths,tmp_path/'known',knowledge_cutoff='2026-09-25T12:00:00Z')
    assert len(x['records'])==1
    assert export_metrics(*paths[:3],tmp_path/'one','2026-07-02','2026-07-02')['coverage']['measure_count']==1
    assert run(paths,tmp_path/'capture',basis='capture')['records']==[]


@pytest.mark.parametrize('change',[lambda m:m.update(value=999),lambda m:m['source_reference'].update(claim_index=99),
    lambda m:m['source_reference'].update(document_id='doc_'+'b'*24),lambda m:m.update(denominator=10,denominator_status='reported'),
    lambda m:m.update(unit='percent',value=10)])
def test_invalid_evidence_and_denominators(tmp_path,change):
    paths=inputs(tmp_path);change(paths[3]['measures'][0]);write_json(paths[1],paths[3])
    with pytest.raises(ValueError):run(paths,tmp_path/'bad')


def test_conflicts_and_revisions_remain_explicit(tmp_path):
    paths=inputs(tmp_path);batch=paths[3];a=batch['measures'][0];a['conflict_set']='same-date'
    b=copy.deepcopy(a);b.update(annotation_key='eleven',value=11)
    b['source_reference']['claim_index']=2;b['evidence']['quote']=paths[4]['records'][0]['claims'][2]['quotes'][0]
    batch['measures'].append(b);write_json(paths[1],batch)
    x=run(paths,tmp_path/'conflict');assert len(x['conflicts'][0]['measure_ids'])==2
    assert len(next(p for p in x['panels'] if p['kind']=='topic')['card_groups'][0]['measure_ids'])==2
    assert [m['value'] for m in x['measures']]==[10,11]
    b['supersedes']=['ten'];b['revision_reason']='Synthetic explicit correction.';write_json(paths[1],batch)
    x=run(paths,tmp_path/'revision');assert x['measures'][0]['superseded'] and not x['measures'][1]['superseded']


def test_observation_dates_drive_cards_and_missing_is_not_zero(tmp_path):
    paths=inputs(tmp_path);batch=paths[3];a=batch['measures'][0]
    b=copy.deepcopy(a);b['annotation_key']='retrospective';b['as_of']['value']='2026-06-01'
    c=copy.deepcopy(a);c.update(annotation_key='unknown',value=None,value_status='unknown');c['as_of']={'value':None,'status':'not_reported'}
    batch['measures']=[b,c,a];write_json(paths[1],batch)
    x=run(paths,tmp_path/'out');topic=next(p for p in x['panels'] if p['kind']=='topic')
    assert topic['card_groups'][0]['observation_date']=='2026-07-01'
    assert len(topic['card_groups'][0]['measure_ids'])==1
    assert next(m for m in x['measures'] if m['annotation_key']=='unknown')['value'] is None


def test_population_and_scope_are_separate_contexts(tmp_path):
    paths=inputs(tmp_path);batch=paths[3];a=batch['measures'][0]
    for field in ['population','geography','case_definition']:
        b=copy.deepcopy(a);b['annotation_key']=field;b[field]={'value':'Different scope','status':'reported'};batch['measures'].append(b)
    b=copy.deepcopy(a);b.update(annotation_key='incident',count_kind='interval');batch['measures'].append(b)
    write_json(paths[1],batch);x=run(paths,tmp_path/'out');assert len(x['series'])==5


def test_snapshot_binding_and_source_quote_validation(tmp_path):
    paths=inputs(tmp_path);paths[3]['records_sha256']='wrong';write_json(paths[1],paths[3])
    with pytest.raises(ValueError,match='different record'):run(paths,tmp_path/'bad')
    paths[3]['records_sha256']=digest(paths[4]['records']);write_json(paths[1],paths[3])
    next(paths[2].iterdir()).write_text('Unrelated source content')
    with pytest.raises(ValueError,match='captured source'):run(paths,tmp_path/'bad')


def test_panel_membership_order_and_single_source_normalization(tmp_path,monkeypatch):
    from atlas import metrics
    paths=inputs(tmp_path);batch,data=paths[3:];first=data['records'][0]
    second=copy.deepcopy(first);second.update(id=first['id']+'-other',track='b')
    data['records'].append(second);data['tracks'].append({'id':'b'})
    extra=copy.deepcopy(batch['measures'][0]);extra['annotation_key']='second-count'
    batch['measures'][0]['context_references']=[dict(record_id=second['id'],document_id=second['document_id'],claim_index=0,quote_indexes=[0])]
    batch['measures'].append(extra)
    data['map_links'].append({'id':'both','support':[[second['id'],0],[first['id'],2],[first['id'],0],[second['id'],0]]})
    batch['records_sha256']=digest(data['records']);write_json(paths[0],data);write_json(paths[1],batch)
    source=(paths[2]/(first['document_id']+'.txt')).read_text();calls=[];normalize=metrics.norm
    def counted(text):
        if text==source:calls.append(text)
        return normalize(text)
    monkeypatch.setattr(metrics,'norm',counted)
    result=run(paths,tmp_path/'out')
    for panel in result['panels']:
        support={tuple(pair) for pair in panel['support']}
        assert panel['measure_ids']==[m['measure_id'] for m in result['measures'] if all((e['record_id'],e['claim_index']) in support for e in m['evidence_references'])]
        assert panel['finding_ids']==[f['finding_id'] for f in result['findings'] if (f['evidence']['record_id'],f['evidence']['claim_index']) in support]
    assert len(next(p for p in result['panels'] if p['id']=='both')['measure_ids'])==2
    assert len(next(p for p in result['panels'] if p['kind']=='record' and p['id']==first['id'])['measure_ids'])==1
    assert len(calls)==1
