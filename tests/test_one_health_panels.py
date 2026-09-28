"""Panel evidence retains sampling units, date precision and source eligibility."""
import copy
import subprocess
import pytest
from atlas.site_export import export_site,validate_bundle
from atlas.util import read_json,write_json,digest
from test_one_health import one_health_inputs


def panel_inputs(tmp_path):
    paths,ann=one_health_inputs(tmp_path)
    original=ann['one_health_nodes'][0]['evidence'][0]
    quote='Samples were collected in July 2026. The response team began a water protection action that month.'
    source=paths['source_dir']/(original['record_id'].split(':')[0]+'.txt')
    source.write_text(source.read_text()+'\n'+quote)
    acquired=read_json(paths['results']);acquired[0]['document']['text_sha256']=digest(source.read_bytes());write_json(paths['results'],acquired)
    ref=dict(record_id=original['record_id'],quote=quote,section='Synthetic sampling and action methods')
    ann['assertions'].append(dict(key='fixture:panel-source',record_id=original['record_id'],claim_index=0,kind='statement',text=quote,evidence=[ref]))
    node={k:ann['one_health_nodes'][0][k] for k in ['record_id','key']}
    missing=dict(value=None,status='not_reported')
    time=dict(kind='sample_collection',extent='point',start=dict(value='2026-07',status='reported'),end=missing,precision='month',certainty='exact',label='Collection in July 2026',reason='The source gives a month, without a day.')
    review=dict(source_assertion_key='fixture:panel-source',record_id=node['record_id'],reviewed_at=ann['reviewed_at'],reviewed_by='Fixture',reason='Synthetic panel evidence review.',evidence=[ref])
    ann.update(contract_version='1.4.0',one_health_timings=[dict(key='collection',node=node,time=time,**review)],one_health_sampling_assessments=[dict(key='sampling',node=node,positive_measure_key=None,tested_measure_key=None,pair_status='unresolved',unit=missing,frame=missing,population=missing,target=missing,method=missing,pooling=missing,clustering=missing,repeated_sampling=missing,time=time,**review)],one_health_contexts=[dict(key='action',label='Source-described action',kind='reported_intervention',variable=missing,method=missing,time=time,node_refs=[node],measure_keys=[],place_ids=[],linkage_note='This passage describes the action for this source observation.',**review)])
    write_json(paths['annotations'],ann);return paths,ann


def test_panel_roundtrip_and_selection(tmp_path):
    paths,ann=panel_inputs(tmp_path);b=export_site(**paths,out=tmp_path/'out');again=export_site(**paths,out=tmp_path/'again')
    assert b['contract_version']=='1.5.0'
    for field in ['one_health_timings','one_health_sampling_assessments','one_health_contexts']:assert b[field]==again[field]
    assert b['one_health_timings'][0]['time']['start']['value']=='2026-07'
    assert b['one_health_sampling_assessments'][0]['display']=='counts_only'
    assert b['one_health_sampling_assessments'][0]['proportion'] is None
    script="""
import fs from 'node:fs';import assert from 'node:assert/strict';
const {selectView}=await import(process.argv[1]);const b=JSON.parse(fs.readFileSync(process.argv[2]));
const full=selectView(b,'2026-07-01','2026-08-02');assert.equal(full.one_health.timings.length,1);assert.equal(full.one_health.contexts.length,1);
const july=selectView(b,'2026-07-01','2026-08-02','publication',null,null,{observation_from:'2026-07-15',observation_until:'2026-07-15'});assert.equal(july.one_health.timings.length,1);
const aug=selectView(b,'2026-07-01','2026-08-02','publication',null,null,{observation_from:'2026-08-01',observation_until:'2026-08-31'});assert.equal(aug.one_health.timings.length,0);
const excluded=selectView(b,'2026-07-01','2026-08-02','publication',null,[b.records[1].id]);assert.equal(excluded.one_health.contexts.length,0);
"""
    subprocess.run(['node','--input-type=module','-e',script,(tmp_path/'out/view.mjs').as_uri(),str(tmp_path/'out/atlas-site.json')],check=True)


@pytest.mark.parametrize('mutation',[
    lambda a:a['one_health_timings'][0]['time'].update(precision='day'),
    lambda a:a['one_health_timings'][0]['time'].update(precision='unknown'),
    lambda a:a['one_health_sampling_assessments'][0].update(pair_status='matched'),
    lambda a:a['one_health_contexts'][0].update(kind='evaluated_effect'),
    lambda a:a['one_health_contexts'][0].update(place_ids=['p']),
])
def test_invalid_panel_evidence(tmp_path,mutation):
    paths,ann=panel_inputs(tmp_path);mutation(ann);write_json(paths['annotations'],ann)
    with pytest.raises(ValueError):export_site(**paths,out=tmp_path/'out')


def test_sampling_ratio_needs_explicit_matching_scope():
    from atlas.one_health import sampling_display
    reported=lambda v:dict(value=v,status='reported')
    row=dict(positive_measure_id='positive',tested_measure_id='tested',pair_status='matched',**{k:reported(k) for k in ['unit','frame','population','target']})
    measures={'positive':dict(metric='positive_samples',unit='samples',value=96,denominator=209),'tested':dict(metric='samples_tested',unit='samples',value=209,denominator=None)}
    display,value,reason=sampling_display(row,measures)
    assert display=='proportion' and value==96/209 and 'prevalence' in reason
    assert sampling_display(dict(row,pair_status='unresolved'),measures)[0]=='counts_only'
    negative=copy.deepcopy(measures);negative['positive']['metric']='other'
    with pytest.raises(ValueError,match='outcome'):sampling_display(row,negative)
    mismatch=copy.deepcopy(measures);mismatch['tested']['value']=210
    with pytest.raises(ValueError,match='denominator'):sampling_display(row,mismatch)
    zero=copy.deepcopy(measures);zero['positive'].update(value=0,denominator=0);zero['tested']['value']=0
    assert sampling_display(row,zero)[:2]==('counts_only',None)
    impossible=copy.deepcopy(measures);impossible['positive']['value']=-1
    with pytest.raises(ValueError,match='negative'):sampling_display(row,impossible)


def test_panel_tampering_is_rejected(tmp_path):
    paths,_=panel_inputs(tmp_path);b=export_site(**paths,out=tmp_path/'out')
    b['one_health_sampling_assessments'][0]['display']='proportion'
    with pytest.raises(ValueError):validate_bundle(b)


def test_panel_dates_cutoffs_and_exact_proposition_review(tmp_path):
    paths,ann=panel_inputs(tmp_path)
    cutoff=copy.deepcopy(ann['one_health_timings'][0]);cutoff.update(key='cutoff');cutoff['time'].update(kind='reporting_cutoff',label='Reporting month')
    unknown=copy.deepcopy(ann['one_health_timings'][0]);unknown.update(key='unknown');unknown['time'].update(start=dict(value=None,status='not_reported'),end=dict(value=None,status='not_reported'),precision='unknown',extent='unknown')
    ann['one_health_timings'].extend([cutoff,unknown]);write_json(paths['annotations'],ann);export_site(**paths,out=tmp_path/'out')
    script="""
import fs from 'node:fs';import assert from 'node:assert/strict';
const {selectView}=await import(process.argv[1]);const b=JSON.parse(fs.readFileSync(process.argv[2]));
const get=(options={})=>selectView(b,'2026-07-01','2026-08-02','publication',null,null,options);
assert.equal(get().one_health.timings.length,1);assert.equal(get().one_health.reporting_cutoffs.length,1);assert.equal(get().one_health.undated_timings.length,1);
assert.equal(get({observation_from:'2026-08-01',observation_until:'2026-08-31'}).one_health.timings.length,0);assert.equal(get({observation_from:'2026-08-01',observation_until:'2026-08-31'}).one_health.reporting_cutoffs.length,1);
const primary=b.one_health_timings[0].source_assertion_id;
b.comparisons[0].kind='contradiction';b.comparisons[0].lineage=[];b.comparisons[0].participant_ids=[primary];
assert.equal(get().one_health.timings[0].contested,true);assert.equal(get().one_health.contexts[0].contested,true);
b.comparisons[0].kind='correction';b.comparisons[0].lineage=[{from_assertion_id:primary,to_assertion_id:b.comparisons[0].participant_ids[0],evidence_ids:b.comparisons[0].evidence_ids}];
assert.equal(get().one_health.timings.length,0);assert.equal(get().one_health.reporting_cutoffs.length,0);assert.equal(get().one_health.undated_timings.length,0);assert.equal(get().one_health.contexts.length,0);
"""
    subprocess.run(['node','--input-type=module','-e',script,(tmp_path/'out/view.mjs').as_uri(),str(tmp_path/'out/atlas-site.json')],check=True)


def test_panel_bound_measure_review(tmp_path):
    paths,_=panel_inputs(tmp_path);export_site(**paths,out=tmp_path/'out')
    script="""
import fs from 'node:fs';import assert from 'node:assert/strict';
const {selectView}=await import(process.argv[1]);const b=JSON.parse(fs.readFileSync(process.argv[2]));
const metric=b.assertions.find(a=>a.measure_id);b.one_health_contexts[0].measure_ids=[metric.measure_id];
const get=()=>selectView(b,'2026-07-01','2026-08-02');
b.comparisons[0].kind='contradiction';b.comparisons[0].lineage=[];b.comparisons[0].participant_ids=[metric.id];
assert.equal(get().one_health.contexts[0].contested,true);assert.equal(get().one_health.timings[0].contested,false);
b.comparisons[0].kind='correction';b.comparisons[0].lineage=[{from_assertion_id:metric.id,to_assertion_id:b.one_health_contexts[0].source_assertion_id,evidence_ids:b.comparisons[0].evidence_ids}];
assert.equal(get().one_health.contexts.length,0);assert.equal(get().one_health.timings.length,1);
"""
    subprocess.run(['node','--input-type=module','-e',script,(tmp_path/'out/view.mjs').as_uri(),str(tmp_path/'out/atlas-site.json')],check=True)


def test_open_detection_period_keeps_unknown_boundary(tmp_path):
    paths,ann=panel_inputs(tmp_path)
    time=ann['one_health_timings'][0]['time'];time.update(kind='detection',extent='open_interval',label='Detections since July 2026')
    write_json(paths['annotations'],ann);export_site(**paths,out=tmp_path/'out')
    script="""
import fs from 'node:fs';import assert from 'node:assert/strict';
const {selectView}=await import(process.argv[1]);const b=JSON.parse(fs.readFileSync(process.argv[2]));
const view=selectView(b,'2026-07-01','2026-08-02');assert.equal(view.one_health.timings.length,0);assert.equal(view.one_health.undated_timings.length,1);
assert.equal(view.one_health.undated_timings[0].time.start.value,'2026-07');assert.equal(view.one_health.undated_timings[0].time.end.value,null);
"""
    subprocess.run(['node','--input-type=module','-e',script,(tmp_path/'out/view.mjs').as_uri(),str(tmp_path/'out/atlas-site.json')],check=True)


def test_known_month_with_unclassified_date_kind_stays_off_timeline(tmp_path):
    paths,ann=panel_inputs(tmp_path)
    row=ann['one_health_timings'][0]
    row['time'].update(kind='unknown',label='July 2026',reason='The month is known; its epidemiological meaning remains unresolved.')
    write_json(paths['annotations'],ann);export_site(**paths,out=tmp_path/'out')
    script="""
import fs from 'node:fs';import assert from 'node:assert/strict';
const {selectView}=await import(process.argv[1]);const b=JSON.parse(fs.readFileSync(process.argv[2]));
const view=selectView(b,'2026-07-01','2026-08-02','publication',null,null,{observation_from:'2026-08-01',observation_until:'2026-08-31'});
assert.equal(view.one_health.timings.length,0);assert.equal(view.one_health.undated_timings.length,1);
assert.equal(view.one_health.undated_timings[0].time.start.value,'2026-07');assert.equal(view.one_health.undated_timings[0].time.kind,'unknown');
"""
    subprocess.run(['node','--input-type=module','-e',script,(tmp_path/'out/view.mjs').as_uri(),str(tmp_path/'out/atlas-site.json')],check=True)
