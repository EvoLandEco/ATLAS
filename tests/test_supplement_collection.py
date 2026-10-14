import json

import pytest

from atlas.supplement_collection import export_collection, verify_collection
from atlas.source_supplement import SourceSupplement
from atlas.util import digest, write_json


def parts(tmp_path):
    sources = tmp_path / 'sources'
    sources.mkdir()
    paths = []
    for n in [1, 2]:
        did, rid, quote = f'doc_{n:024x}', f'record{n}', 'The investigation remains open.'
        (sources / (did + '.txt')).write_text(quote)
        data = dict(supplement_version='0.1.0', source_export_id='a' * 64,
            generated_at='2026-10-08T00:00:00Z', review_status='source_checked_draft',
            selection_policy='outside_dated_selection',
            documents=[dict(id=did, publisher='Authority', title=f'Investigation {n}',
                url=f'https://example.org/{n}', content_url=f'https://example.org/{n}',
                publication=None, publication_status='not_reported', capture='2026-10-08T00:00:00Z',
                raw_sha256='b' * 64, text_sha256=digest(quote.encode()))],
            records=[dict(id=rid, document_id=did, title='Investigation', measures=[],
                claims=[dict(claim_index=0, text=quote, evidence_ids=[f'e{n}'])],
                disclosures=['Publication date is unknown.'], reviewed_at='2026-10-08T00:00:00Z',
                reviewed_by='Fixture')],
            evidence=[dict(id=f'e{n}', document_id=did, record_id=rid, claim_index=0,
                quote_index=0, section='Investigation', quote=quote, start=0, end=len(quote), page=None,
                source_text_sha256=digest(quote.encode()), quote_sha256=digest(quote.encode()))],
            limitations=['Outside dated selections.'])
        path = tmp_path / f'part{n}.json'
        write_json(path, SourceSupplement.model_validate(data).model_dump(mode='json'))
        paths.append(path)
    return paths, sources


def test_collection_preserves_payloads_and_projects_complete_catalogue(tmp_path):
    paths, sources = parts(tmp_path)
    out = tmp_path / 'collection'
    result = export_collection(paths, 'a' * 64, sources, out)
    assert result['counts'] == dict(documents=2, records=2, claims=2, measures=0, evidence=2)
    manifest = json.loads((out / 'source-supplement-collection.json').read_text())
    originals = {digest(path.read_bytes()): path.read_bytes() for path in paths}
    for component in manifest['components']:
        assert (out / 'supplements' / component['sha256'] / component['path']).read_bytes() == originals[component['sha256']]
    catalogue = json.loads((out / 'source-supplement-catalogue.json').read_text())
    assert [d['id'] for d in catalogue['documents']] == [f'doc_{n:024x}' for n in [1, 2]]
    assert all(d['publication'] is None for d in catalogue['documents'])
    assert verify_collection(out, source_dir=sources)['valid']
    from atlas.cli import execute, parser
    assert execute(parser().parse_args(['supplement-collection-verify', str(out)]))['captured_sources_checked'] is False
    second = tmp_path / 'second'
    export_collection(list(reversed(paths)), 'a' * 64, sources, second)
    assert json.loads((second / 'source-supplement-catalogue.json').read_text()) == catalogue


@pytest.mark.parametrize('case', ['duplicate', 'export', 'missing', 'tamper', 'catalogue'])
def test_collection_rejects_incomplete_or_mixed_evidence(tmp_path, case):
    paths, sources = parts(tmp_path)
    out = tmp_path / 'collection'
    if case in {'duplicate', 'export'}:
        if case == 'duplicate':
            paths[1] = paths[0]
        else:
            data = json.loads(paths[1].read_text()); data['source_export_id'] = 'c' * 64
            write_json(paths[1], data)
        with pytest.raises(ValueError):
            export_collection(paths, 'a' * 64, sources, out)
        assert not out.exists()
        return
    export_collection(paths, 'a' * 64, sources, out)
    manifest_path = out / 'source-supplement-collection.json'
    manifest = json.loads(manifest_path.read_text())
    component = manifest['components'][0]
    payload = out / 'supplements' / component['sha256'] / component['path']
    if case == 'missing':
        payload.unlink()
    elif case == 'tamper':
        payload.write_bytes(payload.read_bytes() + b' ')
    else:
        catalogue_path = out / manifest['catalogue']['path']
        catalogue = json.loads(catalogue_path.read_text())
        catalogue['documents'].pop()
        write_json(catalogue_path, catalogue)
        manifest['catalogue'].update(sha256=digest(catalogue_path.read_bytes()), bytes=catalogue_path.stat().st_size)
        write_json(manifest_path, manifest)
    with pytest.raises((ValueError, FileNotFoundError)):
        verify_collection(out, source_dir=sources)
