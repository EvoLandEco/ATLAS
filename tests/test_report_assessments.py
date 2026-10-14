import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from atlas.site_export import export_site, validate_bundle
from atlas.util import digest, read_json, write_json
from test_site_export import site_inputs


def assessment_inputs(tmp_path):
    from atlas.metrics import export_metrics
    paths, ann = site_inputs(tmp_path)
    fixture = read_json(Path(__file__).parent/'fixtures/report-assessments.json')
    snapshot = read_json(paths['snapshot'])
    record = snapshot['records'][0]
    record.update(title='Fatal pneumonia under investigation', conflict=False)
    record['claims'] = [dict(claim_index=i, text=q, quotes=[q]) for i, q in enumerate(fixture['claims'])]
    snapshot['records'] = [record]
    source = paths['source_dir']/(record['document_id']+'.txt')
    source.write_text('\n'.join(fixture['claims']))
    write_json(paths['snapshot'], snapshot)
    acquired = read_json(paths['results'])[:1]
    acquired[0]['document']['text_sha256'] = digest(source.read_bytes())
    write_json(paths['results'], acquired)
    metric_ann = read_json(tmp_path/'annotations.json')
    metric_ann.update(records_sha256=digest(snapshot['records']), measures=[])
    write_json(tmp_path/'annotations.json', metric_ann)
    export_metrics(paths['snapshot'], tmp_path/'annotations.json', paths['source_dir'], tmp_path/'signal-metrics', '2026-07-01', '2026-09-30')
    paths['metrics_path'] = tmp_path/'signal-metrics/metrics.json'
    ann.update(contract_version='1.5.0', records_sha256=digest(snapshot['records']), comparisons=[], report_assessments=[])
    for assessment in fixture['assessments']:
        row = dict(assessment)
        ci = row.pop('claim_index')
        row.update(record_id=record['id'], assertions=['claim:'+record['id']+':'+str(ci)],
                   source_text_sha256=digest(source.read_bytes()), reviewed_at='2026-09-26T12:00:00Z',
                   reviewed_by='Synthetic source review', supersedes=[],
                   evidence=[dict(record_id=record['id'], claim_index=ci, quote_index=0, section='Synthetic source')])
        ann['report_assessments'].append(row)
    write_json(paths['annotations'], ann)
    return paths, ann


def test_unconfirmed_report_preserves_scoped_assessments(tmp_path):
    paths, _ = assessment_inputs(tmp_path)
    bundle = export_site(**paths, out=tmp_path/'site')
    assert bundle['contract_version'] == '1.9.0'
    assert {a['kind'] for a in bundle['report_assessments']} == {'source_authenticity', 'diagnostic_status', 'authority_response', 'expert_appraisal'}
    assert bundle['metrics']['measures'] == []
    assert bundle['relationships'] == []
    assert bundle['one_health_relations'] == []
    assert bundle['metrics']['reviewed_series'] == []
    broken = copy.deepcopy(bundle)
    broken['report_assessments'][1]['source_text_sha256'] = '0'*64
    with pytest.raises(ValueError, match='Assessment source'):
        validate_bundle(broken)
    node = shutil.which('node')
    assert node, 'Node is required for selector checks'
    result = subprocess.run([node, '--input-type=module', '-e', '''
import fs from 'node:fs';
import assert from 'node:assert/strict';
const data=JSON.parse(fs.readFileSync(process.argv[1]));
const {selectView}=await import(process.argv[2]);
const {makeCore}=await import(process.argv[3]);
const {prepareBrowserView}=await import(process.argv[4]);
const id='0'.repeat(64),browser=prepareBrowserView(makeCore(data,id),id);
const view=(from,until,cutoff=null)=>selectView(data,from,until,'publication',cutoff);
assert.equal(view('2026-07-02','2026-07-02').report_assessments.length,4);
assert.equal(view('2026-07-03','2026-08-01').report_assessments.length,0);
assert.equal(view('2026-07-01','2026-07-01').report_assessments.length,0);
assert.equal(view('2026-07-02','2026-07-02','2026-09-25T23:59:59Z').report_assessments.length,0);
for(const args of [['2026-07-02','2026-07-02'],['2026-07-03','2026-08-01'],
 ['2026-07-01','2026-07-01'],['2026-07-02','2026-07-02','publication','2026-09-25T23:59:59Z']]) {
 assert.deepEqual(browser.select(...args),selectView(data,...args));
}
''', str(tmp_path/'site/atlas-site.json'), (tmp_path/'site/view.mjs').as_uri(),
        (Path(__file__).parents[1]/'scripts/export_browser_transport.mjs').as_uri(),
        (Path(__file__).parents[1]/'src/atlas/assets/browser_transport.js').as_uri()], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_assessment_revision_preserves_review_history(tmp_path):
    paths,ann=assessment_inputs(tmp_path)
    revision=copy.deepcopy(ann['report_assessments'][1])
    revision.update(key='diagnosis-review',reviewed_at='2026-09-27T12:00:00Z',
                    reason='The reviewed source still supplies no confirmed cause.',supersedes=['diagnosis'])
    ann['report_assessments'].append(revision)
    write_json(paths['annotations'],ann)
    bundle=export_site(**paths,out=tmp_path/'site')
    assert len(bundle['report_assessments'])==5
    old=bundle['report_assessments'][1];new=bundle['report_assessments'][-1]
    assert new['supersedes']==[old['id']]
    script='''import fs from 'node:fs';import assert from 'node:assert/strict';
const data=JSON.parse(fs.readFileSync(process.argv[1]));const {selectView}=await import(process.argv[2]);
const view=cutoff=>selectView(data,'2026-07-02','2026-07-02','publication',cutoff);
assert.equal(view('2026-09-26T23:59:59Z').report_assessments[1].id,data.report_assessments[1].id);
assert.deepEqual(view(null).superseded_report_assessment_ids,[data.report_assessments[1].id]);
assert.equal(view(null).report_assessments.length,4);
'''
    subprocess.run(['node','--input-type=module','-e',script,str(tmp_path/'site/atlas-site.json'),
                    (tmp_path/'site/view.mjs').as_uri()],check=True,capture_output=True,text=True)


@pytest.mark.parametrize('change', [
    lambda rows: rows[0].update(status='source_confirmed'),
    lambda rows: rows[1].update(source_text_sha256='0'*64),
    lambda rows: rows[1].update(assertions=['missing']),
    lambda rows: rows[1].update(reviewed_at='2026-09-01T12:00:00Z'),
    lambda rows: rows[2].update(authority={'value':None,'status':'unknown'}),
    lambda rows: rows[1].update(supersedes=['response']),
])
def test_invalid_assessment_scope_and_history_are_rejected(tmp_path, change):
    paths, ann = assessment_inputs(tmp_path)
    change(ann['report_assessments'])
    write_json(paths['annotations'], ann)
    with pytest.raises((ValueError, KeyError)):
        export_site(**paths, out=tmp_path/'bad')


def test_explicit_article_title_excludes_related_story_headings():
    from atlas.sources import html_text, SourceError
    page='''<html><head><title>Official illness investigation</title>
    <meta property="article:published_time" content="2026-10-06 12:23:00"></head>
    <body><div class="story">The cause remains unconfirmed.</div>
    <aside><h1>Unrelated regional outbreak</h1></aside></body></html>'''
    text,title,published,precision=html_text(page,content_selector='.story',title_selector='title')
    assert title=='Official illness investigation'
    assert text=='The cause remains unconfirmed.'
    assert (published,precision)==('2026-10-06','day')
    with pytest.raises(SourceError,match='title selector'):
        html_text(page,content_selector='.story',title_selector='.missing')


def test_article_exclusions_remove_publisher_recirculation():
    from atlas.sources import html_text
    page='<article><p>Investigation remains open.</p><aside class="recirculation"><a href="https://example.org/other">Unrelated cases</a></aside></article>'
    text,*_=html_text(page,content_selector='article',content_exclude_selector='.recirculation')
    assert text=='Investigation remains open.'
