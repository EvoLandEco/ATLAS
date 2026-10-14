import copy
import json
from pathlib import Path

import pytest

from atlas.config import in_publication_window
from atlas.daily import acquired_documents, prepare_daily
from test_daily import daily_inputs


CASES = json.loads((Path(__file__).parent / 'fixtures/report-publication-eligibility.json').read_text())


@pytest.mark.parametrize('case', CASES, ids=lambda c:c['name'])
def test_publication_required_for_report_selection(case):
    args = daily_inputs()
    args[0][0].update({k:v for k,v in case.items() if k not in {'name','eligible'}})
    doc = args[0][0]
    saved = copy.deepcopy(doc)
    for window in [None, ('2026-09-30','2026-10-06')]:
        assert in_publication_window(doc, window) == case['eligible']
    assert bool(acquired_documents(args[0], args[4])) == case['eligible']
    if not case['eligible']:
        args[2]['reviews'] = []
        args[2]['watch_assessments'] = []
        result = prepare_daily(*args)
        assert result['documents'] == result['findings'] == result['watch_items'] == []
        assert result['source_coverage'][0]['documents'] == 0
    assert doc == saved


def test_unbounded_extraction_and_review_preserve_excluded_sources(store, config):
    from atlas.extraction import add_extraction, extract_pending
    from atlas.models import Extraction, Review
    from atlas.registry import apply_reviews
    from atlas.sources import save_document
    from atlas.snapshot import build_snapshot
    from atlas.demo import sample_mention
    from atlas.workflow import export_review
    from atlas.util import digest

    mention = sample_mention()
    text = mention['evidence'][0]['quote']
    did = save_document(store, config['sources'][0], text=text, raw=text.encode(),
        title='Undated source', url='https://example.org/2026/10/01/report',
        content_url='https://example.org/2026/10/01/report', at='2026-10-02T00:00:00Z')
    assert extract_pending(store, config, 'none')['queued_chunks'] == 0
    extraction = Extraction.model_validate(dict(outcome='extracted',mentions=[mention]))
    ids = add_extraction(store, did, extraction, at='2026-10-02T01:00:00Z',
        extraction_key=digest([did, text]), provenance={'provider':'editorial'})
    assert export_review(store, config)['pending'] == 0
    apply_reviews(store, [Review(candidate_id=ids[0], action='accept', event_key='historical',
        reviewer='Fixture editor', rationale='Stored review history.')], '2026-10-02T02:00:00Z')
    head = store.verify()
    snapshot = build_snapshot(store, config, '2026-10-03T00:00:00Z')
    for name in ['documents','events','event_identities','observations','updates','opportunities','event_history']:
        assert snapshot['tables'][name] == [], name
    assert len(store.records('document')) == len(store.records('candidate')) == len(store.records('review')) == 1
    assert store.verify() == head
