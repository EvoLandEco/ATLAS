import copy
from pathlib import Path

import pytest

from atlas.source_text import export_text, prepare_text, text_catalog, validate_text, verify_text
from atlas.util import digest, read_json, write_json


def translation(text, **extra):
    return dict(text=text, origin='atlas_generated', created_at='2026-10-07T10:00:00Z',
        created_by='Synthetic translator', method_version='atlas-translation-0.1.0',
        review_status='unreviewed', reviewed_at=None, reviewed_by=None,
        review_note='Synthetic translation awaiting review.', **extra)


def review(row, tag='ru', translated=None):
    return dict(text_id=row['id'], language_tag=tag, language_basis='text_review',
        language_note='Language identified from this exact text.', reviewed_at='2026-10-07T10:00:00Z',
        reviewed_by='Synthetic language review', translation=translated)


def inputs(tmp_path):
    from test_one_health import one_health_inputs
    from atlas.site_export import export_site
    paths, ann = one_health_inputs(tmp_path)
    fixture = read_json(Path(__file__).parent / 'fixtures/source-text.json')
    acquired = read_json(paths['results'])
    acquired[0]['document']['title'] = fixture['title']
    did = acquired[0]['document_id']
    source_file = paths['source_dir'] / (did + '.txt')
    source_file.write_text(source_file.read_text() + '\n' + fixture['quote'])
    acquired[0]['document']['text_sha256'] = digest(source_file.read_bytes())
    write_json(paths['results'], acquired)
    rid = read_json(paths['snapshot'])['records'][0]['id']
    ref = dict(record_id=rid, quote=fixture['quote'], section='Illness statement')
    ann['assertions'].append(dict(key='illness', record_id=rid, claim_index=0, kind='statement',
        text='The cause remains unestablished.', evidence=[ref]))
    ann['one_health_nodes'][0]['evidence'].append(ref)
    ann['one_health_relations'][0]['evidence'].append(ref)
    ann.update(contract_version='1.5.0', report_assessments=[dict(key='illness',record_id=rid,
        kind='diagnostic_status',status='unconfirmed',authority=dict(value=None,status='not_reported'),
        label='Cause unestablished',scope='Cause of the reported illness.',reason='The source states that the cause is not established.',
        source_text_sha256=digest(source_file.read_bytes()),reviewed_at='2026-10-07T10:00:00Z',
        reviewed_by='Synthetic review',assertions=['illness'],evidence=[dict(ref,section='Assessment')])])
    write_json(paths['annotations'], ann)
    bundle = tmp_path / 'site'
    site = export_site(**paths, out=bundle)
    from atlas.source_text import _source
    _, source = _source(bundle, paths['snapshot'])
    return paths, bundle, site, source, fixture


def test_exact_bindings_reuse_and_sealed_export(tmp_path):
    paths, bundle, site, source, fixture = inputs(tmp_path)
    rows, originals = text_catalog(site)
    title = next(r for r in rows if originals[r['id']] == fixture['title'])
    shared = next(r for r in rows if r['kind'] == 'evidence' and originals[r['id']] == fixture['quote'])
    assert len(shared['target_ids']) > 1
    ann = dict(text_version='0.1.0', reviews=[review(title, translated=translation(fixture['title_en'])),
        review(shared, translated=translation(fixture['quote_en']))])
    before = {p.name: digest(p.read_bytes()) for p in bundle.iterdir()}
    data = prepare_text(site, ann, source)
    assert validate_text(data, site, source)['status'] == 'valid'
    assert len(data['translations']) == 2
    tr = next(t for t in data['translations'] if t['original_text_id'] == title['id'])
    assert tr['original_text_id'] == title['id']
    assert next(t for t in data['texts'] if t['id'] == title['id'])['english_translation_id'] == tr['id']
    assert sum(len(t['target_ids']) for t in data['texts'] if t['kind'] == 'evidence') == len(site['evidence'])
    assert site['one_health_nodes'] and site['one_health_relations'] and site['comparisons']
    assert set(site['report_assessments'][0]['evidence_ids']) <= set(shared['target_ids'])
    references = {e for n in site['one_health_nodes'] for e in n['evidence_ids']}
    assert references <= {e for t in rows if t['kind'] == 'evidence' for e in t['target_ids']}
    write_json(tmp_path / 'annotations.json', ann)
    out = tmp_path / 'text'
    assert export_text(bundle, paths['snapshot'], tmp_path / 'annotations.json', out)['status'] == 'valid'
    assert verify_text(out, bundle, paths['snapshot'])['status'] == 'valid'
    assert before == {p.name: digest(p.read_bytes()) for p in bundle.iterdir()}
    with pytest.raises(ValueError, match='empty'):
        export_text(bundle, paths['snapshot'], tmp_path / 'annotations.json', out)
    for mutate in [lambda d: d['texts'][0]['target_ids'].append('missing'),
                   lambda d: d['translations'][0].update(original_text_id='missing'),
                   lambda d: d['texts'][0].update(original_text_sha256='a'*64),
                   lambda d: d.update(source_export_id='b'*64),
                   lambda d: d['coverage'].update(available=99),
                   lambda d: d['texts'].pop(),
                   lambda d: d['translations'].append(copy.deepcopy(d['translations'][0]))]:
        invalid = copy.deepcopy(data); mutate(invalid)
        with pytest.raises(ValueError):
            validate_text(invalid, site, source)
    invalid = copy.deepcopy(ann); invalid['reviews'][0]['text_id'] = 'stale'
    with pytest.raises(ValueError, match='stale'):
        prepare_text(site, invalid, source)
    invalid = copy.deepcopy(ann); invalid['reviews'][0]['language_tag'] = 'RU'
    with pytest.raises(ValueError):
        prepare_text(site, invalid, source)
    assert any(t['language_tag'] == 'und' and t['translation_status'] == 'language_unresolved' for t in data['texts'])


def test_publisher_pairing_requires_captured_english_and_review(tmp_path):
    paths, bundle, site, source, fixture = inputs(tmp_path)
    rows, originals = text_catalog(site)
    title = next(r for r in rows if originals[r['id']] == fixture['title'])
    english = next(r for r in rows if r['kind'] == 'document_title' and r['id'] != title['id'])
    tr = translation(originals[english['id']])
    tr.update(origin='publisher_provided', publisher_text_id=english['id'],
        pairing_evidence_ids=[site['evidence'][0]['id']], review_status='source_checked',
        reviewed_at='2026-10-07T11:00:00Z', reviewed_by='Synthetic bilingual review')
    ann = dict(text_version='0.1.0', reviews=[review(title, translated=tr), review(english, 'en')])
    data = prepare_text(site, ann, source)
    assert validate_text(data, site, source)['status'] == 'valid'
    assert data['translations'][0]['origin'] == 'publisher_provided'
    for field, value in [('text', 'An unrelated English report'), ('publisher_text_id', None),
                         ('pairing_evidence_ids', ['missing']), ('review_status', 'unreviewed')]:
        invalid = copy.deepcopy(ann); invalid['reviews'][0]['translation'][field] = value
        with pytest.raises(ValueError):
            prepare_text(site, invalid, source)


def test_shared_span_identity_does_not_merge_sources():
    fixture = read_json(Path(__file__).parent / 'fixtures/source-text.json')
    quote = fixture['quote']
    site = dict(documents=[dict(id=did, title=fixture['title'], text_sha256=sha*64)
                          for did, sha in [('a','a'), ('b','b')]], records=[],
        evidence=[dict(id=eid, document_id=did, quote=quote, start=start, end=start+len(quote))
                  for eid, did, start in [('e1','a',0), ('e2','a',0), ('e3','a',50), ('e4','b',0)]])
    rows, originals = text_catalog(site)
    spans = [r for r in rows if r['kind'] == 'evidence']
    assert len(spans) == 3
    assert any(r['target_ids'] == ['e1','e2'] for r in spans)
    assert all(originals[r['id']] == quote for r in spans)


def test_display_projection_retains_pairs_and_exact_claim_bindings(tmp_path):
    from atlas.source_text import project_text, validate_text_display, export_text_display, verify_text_display
    paths, bundle, site, source, fixture = inputs(tmp_path)
    rows, originals = text_catalog(site)
    shared = next(r for r in rows if r['kind']=='evidence' and len(r['target_ids'])>1 and originals[r['id']]!=fixture['quote'])
    title = next(r for r in rows if originals[r['id']]==fixture['title'])
    ann=dict(text_version='0.1.0',reviews=[review(title,translated=translation(fixture['title_en'])),review(shared,'en')])
    full=prepare_text(site,ann,source)
    data=project_text(full,'a'*64,site)
    assert len(data['texts'])==2 and len(data['translations'])==1
    assert data['omitted_text_count']==len(full['texts'])-2
    assert data['unmapped_scopes']==['embedded_series_method_evidence','undated_supplement']
    assert data['claim_bindings']
    evidence={e['id']:e for e in site['evidence']}
    for binding in data['claim_bindings']:
        assert binding['text_id']==shared['id']
        assert binding['status']=='bound'
        assert all((evidence[e]['record_id'],evidence[e]['claim_index'],evidence[e]['quote_index'])==(
            binding['record_id'],binding['claim_index'],binding['quote_index']) for e in binding['evidence_ids'])
    assert validate_text_display(data,full,'a'*64,site)['status']=='valid'
    for mutate in [lambda d:d['texts'].pop(),lambda d:d['claim_bindings'][0].update(quote_index=99),
                   lambda d:d.update(unlisted_language_tag='en'),lambda d:d['translations'].clear()]:
        broken=copy.deepcopy(data);mutate(broken)
        with pytest.raises(ValueError):validate_text_display(broken,full,'a'*64,site)
    write_json(tmp_path/'text-annotations.json',ann)
    export_text(bundle,paths['snapshot'],tmp_path/'text-annotations.json',tmp_path/'text')
    export_text_display(tmp_path/'text',bundle,paths['snapshot'],tmp_path/'display')
    assert verify_text_display(tmp_path/'display',tmp_path/'text',bundle,paths['snapshot'])['status']=='valid'


def test_daily_translation_reuse_fills_existing_language_review():
    from atlas.source_text import reuse_daily_reviews
    fixture = read_json(Path(__file__).parent / 'fixtures/source-text.json')
    title, quote = fixture['title'], fixture['quote']
    site = dict(documents=[dict(id='doc', title=title, text_sha256='a'*64)], records=[],
                evidence=[dict(id='e', document_id='doc', quote=quote, start=10, end=10+len(quote))])
    rows, _ = text_catalog(site)
    annotations = dict(text_version='0.1.0', reviews=[review(r) for r in rows])
    daily = dict(document_id='doc', source_text_sha256='a'*64, language_tag='ru',
                 title_translation=translation(fixture['title_en']), reviewed_at='2026-10-07T10:00:00Z',
                 reviewed_by='Synthetic daily review', findings=[dict(evidence=[dict(quote=quote,
                 start=10, language_tag='ru', translation=translation(fixture['quote_en']))])])
    original = copy.deepcopy(annotations)
    completed, reused = reuse_daily_reviews(site, annotations, [daily], site['documents'])
    assert len(reused) == 2
    assert annotations == original
    assert all(r['translation'] for r in completed['reviews'])
    assert all(r['reviewed_by'] == 'Synthetic language review' for r in completed['reviews'])
    again, repeated = reuse_daily_reviews(site, completed, [daily], site['documents'])
    assert again == completed and repeated == []
    for mutate in [lambda d: d.update(source_text_sha256='b'*64),
                   lambda d: d['findings'][0]['evidence'][0].update(start=11)]:
        changed = copy.deepcopy(daily); mutate(changed)
        result, reused = reuse_daily_reviews(site, annotations, [changed], site['documents'])
        assert len(reused) < 2
    conflicting = copy.deepcopy(daily); conflicting['language_tag'] = 'nl'
    with pytest.raises(ValueError, match='language'):
        reuse_daily_reviews(site, annotations, [conflicting], site['documents'])
    different_title = copy.deepcopy(site['documents']); different_title[0]['title'] = 'Other edition'
    _, reused = reuse_daily_reviews(site, annotations, [daily], different_title)
    assert [r['kind'] for r in reused] == ['evidence']


def test_display_exact_snapshot_quote_disambiguates_only_its_claim(tmp_path):
    from atlas.source_text import project_text, validate_text_display
    paths, _, site, source, _ = inputs(tmp_path)
    snapshot = read_json(paths['snapshot'])
    e = next(e for e in site['evidence'] if e['claim_index'] is not None and e['quote_index'] is not None)
    key = (e['record_id'], e['claim_index'], e['quote_index'])
    claim = next(c for r in snapshot['records'] if r['id'] == key[0]
                 for c in r['claims'] if c['claim_index'] == key[1])
    claim['quotes'][key[2]] = e['quote']
    spaced = dict(e, id='spaced', start=100000, end=100000+len(e['quote'])+1,
                  quote=e['quote'].replace(' ', '  ', 1))
    site['evidence'].append(spaced)
    def full():
        rows, _ = text_catalog(site)
        return prepare_text(site, dict(text_version='0.1.0', reviews=[review(r,'en') for r in rows]), source)
    def binding(data):
        return next(b for b in data['claim_bindings'] if (b['record_id'],b['claim_index'],b['quote_index']) == key)
    parent = full()
    old = project_text(parent, 'a'*64, site)
    assert binding(old)['status'] == 'ambiguous_source_spans'
    exact = project_text(parent, 'a'*64, site, snapshot)
    assert exact['display_version'] == '0.1.1'
    assert binding(exact)['status'] == 'bound'
    assert 'spaced' not in binding(exact)['evidence_ids']
    assert validate_text_display(old,parent,'a'*64,site,snapshot)['status']=='valid'
    assert validate_text_display(exact,parent,'a'*64,site,snapshot)['status']=='valid'
    repeat = dict(e, id='repeat', start=200000, end=200000+len(e['quote']))
    site['evidence'].append(repeat)
    repeated = binding(project_text(full(),'a'*64,site,snapshot))
    assert repeated['status']=='ambiguous_source_spans'
    assert {'spaced','repeat'} <= set(repeated['evidence_ids'])
    absent = copy.deepcopy(snapshot)
    absent['records'] = [r for r in absent['records'] if r['id'] != key[0]]
    with pytest.raises(ValueError,match='snapshot'):
        project_text(full(),'a'*64,site,absent)
    foreign = copy.deepcopy(site)
    foreign['evidence'][-1]['document_id'] = 'foreign-document'
    with pytest.raises(ValueError,match='different document'):
        project_text(full(),'a'*64,foreign,snapshot)


def test_sealed_text_display_schema_retains_its_version():
    from atlas.source_text import text_display_schema
    old = read_json(Path(__file__).parent/'fixtures/source-text-display-0.1.0.schema.json')
    assert text_display_schema('0.1.0') == old
    current = text_display_schema()
    assert current['properties']['display_version']['const'] == '0.1.1'
    current['properties']['display_version']['const'] = '0.1.0'
    assert current == old
