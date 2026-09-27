import copy
import pytest
from atlas.util import digest,write_json
from test_metrics import inputs,run


def series_inputs(tmp_path):
    paths=inputs(tmp_path);snapshot,annotations,sources,batch,data=paths
    original=data['records'][0];doc=original['document_id']
    original['claims'][0]['quotes']=['Ten confirmed cases were reported for 1 to 7 July 2026.']
    quote='Confirmed cases meet the stated laboratory definition in the national surveillance programme.'
    original['claims'][0]['quotes'].append(quote)
    first=batch['measures'][0];first.update(count_kind='interval',period_start={'value':'2026-07-01','status':'reported'},period_end={'value':'2026-07-07','status':'reported'},as_of={'value':None,'status':'not_reported'},period_label='Week one')
    first['evidence']['quote']=original['claims'][0]['quotes'][0]
    second=copy.deepcopy(first);second.update(annotation_key='second',period_start={'value':'2026-07-08','status':'reported'},period_end={'value':'2026-07-14','status':'reported'},period_label='Week two')
    later=copy.deepcopy(original);later['id']=doc+':1';later['publication']='2026-07-15';later['claims'][0]['quotes'][0]='Ten confirmed cases were reported for 8 to 14 July 2026.'
    second['source_reference']['record_id']=later['id'];second['evidence']['quote']=later['claims'][0]['quotes'][0]
    data['records'].append(later);batch['measures'].append(second)
    # A single source method passage supports both reporting intervals.
    text='\n'.join(dict.fromkeys(q for r in data['records'] for c in r['claims'] for q in c['quotes']))
    (sources/(doc+'.txt')).write_text(text)
    batch['records_sha256']=digest(data['records']);batch['contract_version']='0.2.0'
    batch['series_reviews']=[dict(series_id='programme-confirmed-weekly',label='Reported confirmed cases',operation='reported_interval_counts',scope='National programme',reason='Same published definition and adjacent reporting weeks.',limitations=['Reporting completeness is not measured.'],reviewed_by='Fixture reviewer',reviewed_at='2026-09-27T00:00:00Z',members=[dict(annotation_key=k,evidence_keys=['definition']) for k in ['ten','second']],connections=[dict(from_key='ten',to_key='second',evidence_keys=[])],evidence=[dict(key='definition',record_id=original['id'],document_id=doc,quote=quote,section='Case definition')])]
    write_json(snapshot,data);write_json(annotations,batch)
    return paths


def test_reviewed_series_preserves_values_and_requires_complete_evidence(tmp_path):
    paths=series_inputs(tmp_path);x=run(paths,tmp_path/'export');s=x['reviewed_series'][0]
    assert len(s['connections'])==1 and len(s['members'])==2
    assert [m['value'] for m in x['measures']]==[10,10]
    assert s['connections'][0]['eligibility']['record_ids']==[r['id'] for r in paths[4]['records']]
    from atlas.metrics import export_metrics
    partial=export_metrics(*paths[:3],tmp_path/'partial','2026-07-15','2026-07-15')
    assert partial['reviewed_series']==[]


@pytest.mark.parametrize('change,match',[
    (lambda b:b['measures'][1]['period_start'].update(value='2026-07-09'),'gap or overlap'),
    (lambda b:b['measures'][1]['period_start'].update(value='2026-07-07'),'gap or overlap'),
    (lambda b:b['measures'][1].update(conflict_set='disputed'),'unresolved'),
    (lambda b:b['measures'][1]['geography'].update(value='Other geography'),'scope differs'),
    (lambda b:b['series_reviews'][0]['evidence'][0].update(quote='Unsupported method.'),'source occurrence'),
])
def test_rejects_unreviewable_connections(tmp_path,change,match):
    paths=series_inputs(tmp_path);change(paths[3]);write_json(paths[1],paths[3])
    with pytest.raises(ValueError,match=match):run(paths,tmp_path/'bad')


def test_rejects_year_reset_and_rate_permission(tmp_path):
    paths=series_inputs(tmp_path)
    for m in paths[3]['measures']:
        m['count_kind']='cumulative';m['cumulative_baseline']={'value':'2026 week 1','status':'reported'}
    paths[3]['series_reviews'][0]['operation']='cumulative_reporting_totals'
    paths[3]['measures'][1]['cumulative_baseline']['value']='2027 week 1'
    write_json(paths[1],paths[3])
    with pytest.raises(ValueError,match='scope differs'):run(paths,tmp_path/'bad')
    paths[3]['measures'][1]['cumulative_baseline']['value']='2026 week 1'
    paths[3]['measures'][1].update(unit='percent',ratio_basis='source_reported')
    write_json(paths[1],paths[3])
    with pytest.raises(ValueError,match='count review|count.*requires'):run(paths,tmp_path/'rate')
