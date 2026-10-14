import copy
import json
import subprocess

import pytest

from atlas.util import write_json
from atlas.watch import export_watch, prepare_watch, validate_watch, verify_watch
from test_source_text import inputs


def watch_inputs(tmp_path):
    paths, bundle, site, source, _ = inputs(tmp_path)
    assessment = site['report_assessments'][0]
    assertions = {a['id']:a for a in site['assertions']}
    support = set(assessment['evidence_ids'])
    for aid in assessment['assertion_ids']:
        support.update(assertions[aid]['evidence_ids'])
    support.add(next(e['id'] for e in site['evidence'] if e['record_id'] != assessment['record_id']))
    ann = dict(watch_version='0.1.0',review_scope='Synthetic two-source evidence review.',
        limitations=['Synthetic report selection, not a clinical risk assessment.'],
        reviews=[dict(key='illness',record_id=assessment['record_id'],label='Cause of illness unconfirmed',
            reason_for_attention='The source leaves the cause of illness unestablished.',
            follow_up_question='Has the source established the cause of illness?',
            assertion_ids=assessment['assertion_ids'],evidence_ids=sorted(support),
            diagnostic_assessment_id=assessment['id'],
            source_text_hashes={d['id']:d['text_sha256'] for d in site['documents']},
            reviewed_at='2026-10-07T12:00:00Z',reviewed_by='Synthetic captured-source review')])
    return paths, bundle, site, source, ann


def test_watch_preserves_diagnosis_and_all_source_selection(tmp_path):
    paths, bundle, site, source, ann = watch_inputs(tmp_path)
    data = prepare_watch(site, ann, source)
    assert validate_watch(data, site, source)['items'] == 1
    row = data['items'][0]
    assert row['diagnostic_status'] == dict(value='unconfirmed',status='reported')
    assert row['event_identity'] == 'not_assigned'
    assert len(row['eligibility']['record_ids']) == 2
    assert row['latest_publication'] == '2026-08-02'
    write_json(tmp_path/'watch-annotations.json',ann)
    out = tmp_path/'watch'
    export_watch(bundle,paths['snapshot'],tmp_path/'watch-annotations.json',out)
    assert verify_watch(out,bundle,paths['snapshot'])['status'] == 'valid'
    subprocess.run(['node','--input-type=module','-e','''
import fs from 'node:fs';import assert from 'node:assert/strict';
const {selectWatch}=await import(process.argv[1]);
const {selectView}=await import(process.argv[2]);
const watch=JSON.parse(fs.readFileSync(process.argv[3]));
const site=JSON.parse(fs.readFileSync(process.argv[4]));
const full=selectView(site,'2026-07-01','2026-08-02');
assert.equal(selectWatch(watch,full.record_ids).length,1);
assert.equal(selectWatch(watch,selectView(site,'2026-07-01','2026-07-31').record_ids).length,0);
assert.equal(selectWatch(watch,selectView(site,'2026-08-02','2026-08-02').record_ids).length,0);
assert.equal(selectWatch(watch,full.record_ids,'2026-10-07T11:59:59Z').length,0);
assert.equal(selectWatch(watch,full.record_ids,'2026-10-07T12:00:00Z').length,1);
assert.throws(()=>selectWatch(watch,full.record_ids,'2026-10-07'));
''',(out/'watch-view.mjs').as_uri(),(bundle/'view.mjs').as_uri(),str(out/'watch.json'),str(bundle/'atlas-site.json')],check=True)
    for mutate in [lambda d:d['items'][0]['eligibility']['record_ids'].pop(),
                   lambda d:d['items'][0]['diagnostic_status'].update(value='source_confirmed'),
                   lambda d:d['items'][0].update(latest_publication='2026-10-07'),
                   lambda d:d.update(source_export_id='b'*64)]:
        broken=copy.deepcopy(data);mutate(broken)
        with pytest.raises(ValueError):validate_watch(broken,site,source)
    for mutate in [lambda a:a['reviews'][0].update(source_text_hashes={}),
                   lambda a:a['reviews'][0].update(evidence_ids=[]),
                   lambda a:a['reviews'][0].update(diagnostic_assessment_id='absent'),
                   lambda a:a['reviews'][0].update(reviewed_at='2026-01-01T00:00:00Z')]:
        broken=copy.deepcopy(ann);mutate(broken)
        with pytest.raises(ValueError):prepare_watch(site,broken,source)
    without_diagnosis=copy.deepcopy(ann);without_diagnosis['reviews'][0]['diagnostic_assessment_id']=None
    assert prepare_watch(site,without_diagnosis,source)['items'][0]['diagnostic_status']==dict(value=None,status='not_extracted')
