import copy,json,sqlite3
from pathlib import Path
import pytest
from pydantic import ValidationError
from epiweekly.models import TextValue,DateValue,Mention,Observation,Extraction,Review,reported
from epiweekly.demo import sample_mention,add_example
from epiweekly.semantics import normalize_mention,evidence_errors,series_key,cumulative_change
from epiweekly.config import vocabulary
from epiweekly.registry import apply_reviews,match_candidates,review_queue,add_relation
from epiweekly.snapshot import build_snapshot
from epiweekly.export import validate_snapshot,export_snapshot,verify_bundle,csv_bytes
from epiweekly.util import read_json,uid,canonical,digest
from epiweekly.workflow import approve,approved_bundle,run

AT='2026-09-09T06:00:00Z';CUT='2026-09-09T06:37:00Z'

@pytest.mark.parametrize('status',['not_reported','unknown','not_applicable','pending_verification','conflicting','not_extracted','not_comparable','access_restricted'])
def test_missing_reasons(status):
    assert TextValue(value=None,status=status).value is None
    with pytest.raises(ValidationError):TextValue(value='available',status=status)

@pytest.mark.parametrize('value',[-1,float('nan'),float('inf'),0.5])
def test_invalid_counts(value):
    m=sample_mention();o=m['observations'][0];o['value']=value
    with pytest.raises(ValidationError):Observation.model_validate(o)

@pytest.mark.parametrize('value',['20260909','2026-09-09T00:00:00Z','2026-02-30'])
def test_exact_dates(value):
    with pytest.raises(ValidationError):DateValue(value=value,status='reported')

def test_reported_zero():
    o=sample_mention(0)['observations'][0]
    assert Observation.model_validate(o).value==0

def test_value_status_contract():
    o=sample_mention()['observations'][0];o['value_status']='unknown'
    with pytest.raises(ValidationError):Observation.model_validate(o)

def test_namibia_preserved():
    m=Mention.model_validate(sample_mention(country='NA'))
    assert m.country_code.value=='NA'

def test_country_validation():
    with pytest.raises(ValidationError):Mention.model_validate(sample_mention(country='ZZ'))

def test_normalization():
    m=Mention.model_validate(sample_mention(disease='bird flu',host='humans'))
    canonical=normalize_mention(m,vocabulary())
    assert canonical.disease.value=='avian influenza'

def test_evidence_rejection(store,config):
    m=sample_mention();m['observations'][0]['value']=999
    cid=add_example(store,config,m,at=AT)
    assert store.get(cid)['payload']['validation_errors']
    with pytest.raises(ValueError):apply_reviews(store,[Review(candidate_id=cid,action='accept',event_key='x',reviewer='AA',rationale='test')],AT)

def test_quote_anchor():
    m=Mention.model_validate(sample_mention())
    assert evidence_errors(m,'An unrelated source')

def test_ledger_immutability(store):
    ident=store.append('test',{'a':1},AT)
    assert store.append('test',{'a':1},AT,ident)==ident
    with pytest.raises(ValueError):store.append('test',{'a':2},AT,ident)
    with pytest.raises(sqlite3.IntegrityError):store.db.execute('DELETE FROM records')
    assert store.verify()['records']==1

def test_deduplicated_document_capture(store,config):
    a=add_example(store,config,sample_mention(),at=AT,event_key='test',label='same')
    b=add_example(store,config,sample_mention(),at=AT,event_key='test',label='same')
    assert a==b and len(store.records('document'))==1

def test_explicit_id_suggestion_requires_review(store,config):
    add_example(store,config,sample_mention(),at=AT,event_key='test')
    cid=add_example(store,config,sample_mention(135,'2026-09-15'),at='2026-09-16T06:00:00Z')
    match=match_candidates(store,store.get(cid))[0]
    assert match['reason']=='same_explicit_authority_event_id' and match['decision']=='review_required'
    assert len(review_queue(store))==1

def test_different_hosts_require_separate_events(store,config):
    add_example(store,config,sample_mention(),at=AT,event_key='test')
    cid=add_example(store,config,sample_mention(host='pig'),at=AT)
    with pytest.raises(ValueError):apply_reviews(store,[Review(candidate_id=cid,action='accept',event_key='test',reviewer='AA',rationale='test')],AT)

def test_case_can_develop_into_outbreak(store,config):
    add_example(store,config,sample_mention(1,kind='single_case'),at=AT,event_key='test')
    add_example(store,config,sample_mention(3,kind='outbreak'),at=AT,event_key='test')
    assert len(build_snapshot(store,config,CUT)['tables']['events'])==1

def test_surveillance_aggregate_is_separate(store,config):
    add_example(store,config,sample_mention(),at=AT,event_key='test')
    cid=add_example(store,config,sample_mention(kind='surveillance_aggregate'),at=AT)
    with pytest.raises(ValueError):apply_reviews(store,[Review(candidate_id=cid,action='accept',event_key='test',reviewer='AA',rationale='test')],AT)

def test_future_review_not_in_earlier_snapshot(store,config):
    cid=add_example(store,config,sample_mention(),at=AT)
    apply_reviews(store,[Review(candidate_id=cid,action='accept',event_key='test',reviewer='AA',rationale='test')],'2026-09-10T06:00:00Z')
    assert build_snapshot(store,config,CUT)['tables']['events']==[]

def test_future_observation_excluded(store,config):
    add_example(store,config,sample_mention(3,'2026-09-30'),at=AT,event_key='test')
    report=build_snapshot(store,config,CUT)
    assert not report['tables']['events']
    assert len(report['metadata']['quality']['future_dated_candidates_excluded'])==1

def test_conflict_preserves_claims(store,config):
    add_example(store,config,sample_mention(120),at=AT,event_key='test')
    add_example(store,config,sample_mention(125),at=AT,event_key='test',source_id='example_digest')
    snap=build_snapshot(store,config,CUT)
    m=snap['tables']['event_metrics'][0]
    assert m['value'] is None and m['value_status']=='conflicting'
    assert len(m['supporting_observation_ids'])==2
    assert all(not o['selected_current'] for o in snap['tables']['observations'])

def test_equal_claims_not_added(store,config):
    add_example(store,config,sample_mention(120),at=AT,event_key='test')
    add_example(store,config,sample_mention(120),at=AT,event_key='test',source_id='example_digest')
    snap=build_snapshot(store,config,CUT)
    assert snap['tables']['event_metrics'][0]['value']==120
    assert sum(o['selected_current'] for o in snap['tables']['observations'])==1

def test_case_definition_separates_series(store,config):
    add_example(store,config,sample_mention(120),at=AT,event_key='test')
    add_example(store,config,sample_mention(125,case_definition='Example definition v2'),at=AT,event_key='test')
    assert len(build_snapshot(store,config,CUT)['tables']['event_metrics'])==2

def test_interval_vs_cumulative_separate(store,config):
    add_example(store,config,sample_mention(120),at=AT,event_key='test')
    m=sample_mention(5);m['observations'][0]['count_kind']='interval'
    add_example(store,config,m,at=AT,event_key='test')
    assert len(build_snapshot(store,config,CUT)['tables']['event_metrics'])==2

def test_demo_evolution(demo_run):
    root,result,weekly=demo_run
    assert [len(s['tables']['events']) for s in weekly]==[2,3,3]
    def cases(s):return next(m for m in s['tables']['event_metrics'] if m['event_id']==uid('evt','example-febrile-2026') and m['metric']=='cases')
    assert [cases(s)['value'] for s in weekly]==[120,135,132]
    assert cases(weekly[1])['change_in_reported_cumulative']==15
    assert cases(weekly[2])['change_in_reported_cumulative']==-3
    assert cases(weekly[2])['change_label']=='downward_revision'
    assert weekly[2]['metadata']['quality']['pending_review_mentions']==1
    pig=next(e for e in weekly[2]['tables']['events'] if e['host']=='pig')
    assert pig['lifecycle_status']=='active' and pig['update_class']=='carried_forward'

def test_correction_preserves_old_values(demo_run):
    last=demo_run[2][-1]
    old=[o for o in last['tables']['observations'] if o['value']==135]
    assert len(old)==2 and all(o['superseded'] for o in old)

def test_persistent_opportunity_ids(demo_run):
    a,b,c=demo_run[2]
    earlier={o['opportunity_id'] for o in a['tables']['opportunities']}
    later={o['opportunity_id'] for o in c['tables']['opportunities']}
    assert earlier<=later

def test_history_and_relationship_basis(demo_run):
    last=demo_run[2][-1]
    assert len(last['tables']['event_history'])==8
    assert last['tables']['relationships'][0]['basis']=='analyst_hypothesis'

def test_byte_identical_replay(demo_run,tmp_path):
    snap=demo_run[2][-1];out=tmp_path/'replay';export_snapshot(snap,out)
    original=Path(demo_run[1]['latest'])/'dataset.zip'
    assert original.read_bytes()==(out/'dataset.zip').read_bytes()

def test_bundle_tamper_detected(demo_run,tmp_path):
    out=tmp_path/'bundle';export_snapshot(demo_run[2][-1],out)
    (out/'events.csv').write_text('tampered')
    with pytest.raises(ValueError):verify_bundle(out)

def test_export_has_no_private_source_text(demo_run):
    snap=demo_run[2][-1]
    public=canonical(snap)
    for key in ['text_object','raw_object','raw_mention','chunk_start','api_key']:
        assert f'"{key}"' not in public

def test_csv_injection_and_na(demo_run):
    rows=copy.deepcopy(demo_run[2][-1]['tables']['events']);rows[0]['title']='=HYPERLINK("evil")'
    rows[0]['country_code']='NA'
    content=csv_bytes('events',rows).decode()
    assert "'=HYPERLINK" in content and ',NA,reported,' in content

def test_null_reason_required(demo_run):
    s=copy.deepcopy(demo_run[2][-1]);del s['tables']['events'][0]['pathogen_status']
    with pytest.raises(Exception):validate_snapshot(s)

def test_bad_iso_dates_rejected(demo_run):
    s=copy.deepcopy(demo_run[2][-1]);s['metadata']['report_date']='next Wednesday'
    with pytest.raises(Exception):validate_snapshot(s)

def test_approval_content_bound(demo_run,tmp_path):
    source=Path(demo_run[1]['latest']);approval=tmp_path/'approval.json'
    approve(source,'Example editor','Reviewed synthetic demonstration.',approval)
    assert approved_bundle(source,approval)['approved']
    earlier=Path(demo_run[1]['reports'][0])
    with pytest.raises(ValueError):approved_bundle(earlier,approval)

def test_reassignment_keeps_history(store,config):
    cid=add_example(store,config,sample_mention(),at=AT,event_key='original')
    before=build_snapshot(store,config,CUT)
    apply_reviews(store,[Review(candidate_id=cid,action='accept',event_key='corrected',reviewer='AA',rationale='Correct event identity.')],'2026-09-16T06:00:00Z')
    after=build_snapshot(store,config,'2026-09-16T06:37:00Z',previous=before)
    assert len(after['tables']['event_identities'])==2
    assert before['tables']['events'][0]['event_key']=='original'
    validate_snapshot(after)

def test_repeated_automatic_run_is_idempotent(store,config):
    store.append('run_receipt',{'report_date':'2026-09-09','report_id':'recorded','bundle':'saved'},AT)
    assert run(store,config,report_date='2026-09-09')['status']=='already_completed'

def test_interval_duration_separates_measurements(store,config):
    a=sample_mention(120);a['observations'][0]['count_kind']='interval'
    b=sample_mention(10);b['observations'][0].update(count_kind='interval',period_start=reported('2026-09-08'))
    add_example(store,config,a,at=AT,event_key='test')
    add_example(store,config,b,at=AT,event_key='test')
    assert len(build_snapshot(store,config,CUT)['tables']['event_metrics'])==2

def test_bound_differences_are_not_comparable(demo_run):
    a=copy.deepcopy(demo_run[2][1]['tables']['event_metrics'][0]);b=copy.deepcopy(a)
    a['qualifier']=b['qualifier']='at_least'
    assert cumulative_change(a,b)==(None,'not_comparable')
