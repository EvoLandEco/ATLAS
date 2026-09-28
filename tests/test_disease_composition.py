"""Disease composition counts reviewed reporting entries with exact source support."""
import copy
import pytest
from atlas.site_export import export_site, validate_bundle
from atlas.util import read_json, write_json
from test_site_export import site_inputs


def disease_inputs(tmp_path):
    paths, ann = site_inputs(tmp_path)
    records = read_json(paths['snapshot'])['records']
    ann.update(contract_version='1.2.0', diseases=[dict(id='disease:fixture', label='Fixture disease')],
        disease_reviews=[dict(record_id=records[0]['id'], kind='single_disease', disease_ids=['disease:fixture'],
            reason='The reviewed entry concerns the named fixture disease.', reviewed_at=ann['reviewed_at'], reviewed_by='Fixture',
            evidence=[dict(record_id=r['id'], claim_index=0, quote_index=0, section='Disease scope') for r in records])])
    write_json(paths['annotations'], ann)
    return paths, ann


def test_disease_review_support_and_stable_identity(tmp_path):
    paths, ann = disease_inputs(tmp_path)
    bundle = export_site(**paths, out=tmp_path/'site')
    review = bundle['disease_reviews'][0]
    assert len(review['eligibility']['record_ids']) == 2
    assert len(review['evidence_ids']) == 2
    ann['diseases'][0]['label'] = 'Readable fixture label'
    write_json(paths['annotations'], ann)
    again = export_site(**paths, out=tmp_path/'again')
    assert again['disease_reviews'][0]['id'] == review['id']
    assert len(bundle['disease_reviews']) == 1


@pytest.mark.parametrize('change', [
    lambda b: b['disease_reviews'].append(copy.deepcopy(b['disease_reviews'][0])),
    lambda b: b['disease_reviews'][0].update(disease_ids=['disease:missing']),
    lambda b: b['disease_reviews'][0].update(kind='multiple_diseases'),
    lambda b: b['disease_reviews'][0].update(kind='not_disease_specific'),
    lambda b: b['disease_reviews'][0]['eligibility']['record_ids'].pop(),
    lambda b: b['disease_reviews'][0].update(evidence_ids=[]),
])
def test_disease_partition_rejects_invalid_reviews(tmp_path, change):
    paths, _ = disease_inputs(tmp_path)
    bundle = export_site(**paths, out=tmp_path/'site'); change(bundle)
    with pytest.raises((ValueError, KeyError)):
        validate_bundle(bundle)
