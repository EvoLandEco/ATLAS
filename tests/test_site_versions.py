"""Sealed contract 1.2 bundles retain their schema and scientific checks."""
from pathlib import Path
import pytest
from atlas.site_export import export_site, verify_site, validate_bundle
from atlas.handoff import inspect_export
from atlas.util import read_json, write_json, digest
from test_chains import chain_inputs


def legacy_bundle(tmp_path):
    paths, _ = chain_inputs(tmp_path)
    out = tmp_path / 'site'
    data = export_site(**paths, out=out)
    # Synthetic contract 1.2 fixture, with the released schema and selector.
    data.pop('diseases'); data.pop('disease_reviews')
    for name in ('one_health_reviews','one_health_nodes','one_health_relations','one_health_timings','one_health_sampling_assessments','one_health_contexts'): data.pop(name)
    data.update(contract_version='1.2.0', software_version='0.1.0a21')
    write_json(out / 'atlas-site.json', data)
    fixture = Path(__file__).parent / 'fixtures/site-1.2.0'
    for name in ('atlas-site.schema.json', 'annotations.schema.json'):
        (out / name).write_bytes((fixture / name).read_bytes())
    (out / 'view.mjs').write_bytes((Path(__file__).parents[1] / 'src/atlas/assets/site_view_v1_2.js').read_bytes())
    reseal(out, '1.2.0')
    return out, paths, data


def reseal(out, version):
    write_json(out / 'manifest.json', dict(contract_version=version,
        files={p.name:digest(p.read_bytes()) for p in out.iterdir() if p.name != 'manifest.json'}))


def test_contract_12_handoff_preserves_bytes(tmp_path):
    out, paths, data = legacy_bundle(tmp_path)
    before = {p.name:p.read_bytes() for p in out.iterdir()}
    assert verify_site(out)['contract_version'] == '1.2.0'
    result = inspect_export(out, paths['snapshot'])
    assert result['integrity']['status'] == 'valid'
    assert result['contract_version'] == '1.2.0'
    assert validate_bundle(data) is data
    assert before == {p.name:p.read_bytes() for p in out.iterdir()}


@pytest.mark.parametrize('target', ['schema', 'annotations', 'selector', 'manifest_version', 'data_version', 'evidence', 'chain', 'temporal', 'extra_field'])
def test_resealed_contract_12_tampering_is_rejected(tmp_path, target):
    out, paths, data = legacy_bundle(tmp_path)
    if target in {'schema', 'annotations'}:
        name = 'atlas-site.schema.json' if target == 'schema' else 'annotations.schema.json'
        schema = read_json(out / name); schema['title'] = 'Untrusted schema'; write_json(out / name, schema)
    elif target == 'selector':
        (out / 'view.mjs').write_text('export function selectView() { return {}; }')
    elif target == 'data_version': data['contract_version'] = '1.3.0'
    elif target == 'evidence': data['evidence'][0]['quote_sha256'] = '0' * 64
    elif target == 'chain': data['reviewed_chains'][0]['edges'][0]['from_node_id'] = 'missing'
    elif target == 'temporal': data['comparisons'][0]['eligibility']['record_ids'].pop()
    elif target == 'extra_field': data['diseases'] = []
    write_json(out / 'atlas-site.json', data)
    reseal(out, '1.3.0' if target == 'manifest_version' else '1.2.0')
    with pytest.raises(ValueError): verify_site(out)


def test_contract_13_handoff_keeps_sealed_content(tmp_path):
    paths,_=chain_inputs(tmp_path);out=tmp_path/'site'
    data=export_site(**paths,out=out)
    for name in ('one_health_reviews','one_health_nodes','one_health_relations','one_health_timings','one_health_sampling_assessments','one_health_contexts'):data.pop(name)
    data.update(contract_version='1.3.0',software_version='0.1.0a22');write_json(out/'atlas-site.json',data)
    fixture=Path(__file__).parent/'fixtures/site-1.3.0'
    for name in ('atlas-site.schema.json','annotations.schema.json'):(out/name).write_bytes((fixture/name).read_bytes())
    (out/'view.mjs').write_bytes((Path(__file__).parents[1]/'src/atlas/assets/site_view_v1_3.js').read_bytes())
    reseal(out,'1.3.0');before={p.name:p.read_bytes() for p in out.iterdir()}
    assert verify_site(out)['contract_version']=='1.3.0'
    assert inspect_export(out,paths['snapshot'])['integrity']['status']=='valid'
    assert before=={p.name:p.read_bytes() for p in out.iterdir()}


def test_contract_14_handoff_keeps_sealed_content(tmp_path):
    from test_one_health import one_health_inputs
    paths,_=one_health_inputs(tmp_path);out=tmp_path/'site';data=export_site(**paths,out=out)
    for name in ('one_health_timings','one_health_sampling_assessments','one_health_contexts'):data.pop(name)
    data.update(contract_version='1.4.0',software_version='0.1.0a25');write_json(out/'atlas-site.json',data)
    fixture=Path(__file__).parent/'fixtures/site-1.4.0'
    for name in ('atlas-site.schema.json','annotations.schema.json'):(out/name).write_bytes((fixture/name).read_bytes())
    (out/'view.mjs').write_bytes((Path(__file__).parents[1]/'src/atlas/assets/site_view_v1_4.js').read_bytes())
    reseal(out,'1.4.0');before={p.name:p.read_bytes() for p in out.iterdir()}
    assert verify_site(out)['contract_version']=='1.4.0'
    assert inspect_export(out,paths['snapshot'])['integrity']['status']=='valid'
    assert before=={p.name:p.read_bytes() for p in out.iterdir()}
