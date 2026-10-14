import copy
import pytest
from atlas.util import digest
from atlas.source_supplement import SourceSupplement, validate_supplement


def test_undated_source_identity_and_evidence(tmp_path):
    from test_metrics import inputs
    _, _, sources, batch, snapshot = inputs(tmp_path)
    record = snapshot['records'][0]
    did, rid = record['document_id'], record['id']
    text = (sources / (did + '.txt')).read_text()
    quote = record['claims'][0]['quotes'][0]
    data = dict(supplement_version='0.1.0', source_export_id='a' * 64,
        generated_at='2026-10-07T07:00:00Z', review_status='source_checked_draft',
        selection_policy='outside_dated_selection',
        documents=[dict(id=did, publisher='Example Authority', title='Undated report',
            url=record['url'], content_url=record['url'], publication=None,
            publication_status='not_reported', capture=record['capture'], raw_sha256='b' * 64,
            text_sha256=digest(text.encode()))],
        records=[dict(id=rid, document_id=did, title='Reported count',
            claims=[dict(claim_index=0, text=quote, evidence_ids=['e'])],
            measures=batch['measures'], disclosures=['The publication date is not reported.'],
            reviewed_at='2026-10-07T07:00:00Z', reviewed_by='Fixture')],
        evidence=[dict(id='e', document_id=did, record_id=rid, claim_index=0,
            quote_index=0, section='Reported count', quote=quote, source_text_sha256=digest(text.encode()),
            start=0, end=len(quote), page=None, quote_sha256=digest(quote.encode()))],
        limitations=['Outside dated selections and analytical model inputs.'])
    data = SourceSupplement.model_validate(data).model_dump(mode='json')
    assert validate_supplement(data, source_dir=sources)['records'] == 1
    assert validate_supplement(data)['measures'] == 1
    for mutate in [lambda d: d['documents'][0].update(publication='2026-07-02'),
                   lambda d: d['evidence'][0].update(quote='A changed quotation'),
                   lambda d: d['records'][0]['claims'][0].update(evidence_ids=['missing']),
                   lambda d: d['records'][0]['measures'][0]['source_reference'].update(claim_index=1),
                   lambda d: d['records'][0]['measures'][0].update(value=999)]:
        invalid = copy.deepcopy(data); mutate(invalid)
        with pytest.raises(ValueError): validate_supplement(invalid, source_dir=sources)
