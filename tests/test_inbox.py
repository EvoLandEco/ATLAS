import copy
from pathlib import Path

import pytest

from atlas.demo import add_example, sample_mention
from atlas.inbox import (Decision, Decisions, Packet, SupplementalPacket, apply_decision,
                         current_issues, export_inbox, import_decisions, register_supplement,
                         complete_decision, sync_decisions)
from atlas.models import Review
from atlas.registry import apply_reviews
from atlas.util import digest, read_json, utcnow

AT = '2026-09-09T06:00:00Z'


def packet_and_decision(store, config, tmp_path, **changes):
    cid = add_example(store, config, sample_mention(), at=AT)
    export_inbox(store, 'atlas', tmp_path / 'packet', config=config)
    packet = Packet.model_validate(read_json(tmp_path / 'packet/inbox.json'))
    issue = packet.issues[0]
    decision = Decision(inbox_version='1.0.0', archive_id='atlas', decision_id='decision-test',
        snapshot_id=packet.snapshot_id, issue_id=issue.issue_id, revision=issue.revision,
        reviewer='reviewer@example.org', submitted_at=utcnow(), action='accept',
        event_key='synthetic-event', rationale='The captured source supports this event identity.', **changes)
    return cid, packet, decision


def test_registry_packet_has_historical_captured_evidence(store, config, tmp_path):
    _, packet, _ = packet_and_decision(store, config, tmp_path)
    e = packet.issues[0].evidence[0]
    assert e.published_at == '2026-09-09'
    assert (tmp_path / 'packet/evidence' / (e.sha256 + '.txt')).exists()
    assert packet.snapshot_id == digest({k: v for k, v in packet.model_dump().items() if k != 'snapshot_id'})
    assert not any('/Users/' in str(i) for i in packet.model_dump().values())


@pytest.mark.parametrize('publication', read_json(Path(__file__).parent / 'fixtures/inbox-publication-times.json'))
def test_registry_source_publication_time_retains_its_calendar_date(store, config, tmp_path, publication):
    from atlas.sources import save_document
    from atlas.extraction import add_extraction
    from atlas.models import Extraction
    mention = sample_mention()
    text = mention['evidence'][0]['quote']
    document = save_document(store, config['sources'][0], text=text, raw=text.encode(),
        url='https://example.org/timestamped-report', content_url='https://example.org/timestamped-report',
        title=mention['title'], published_at=publication['published_at'], publication_precision='instant', at=AT)
    add_extraction(store, document, Extraction(outcome='extracted', mentions=[mention]),
        at=AT, extraction_key='timestamped-report', provenance={'provider': 'editorial'})
    export_inbox(store, 'atlas', tmp_path / 'packet', config=config)
    issue = Packet.model_validate(read_json(tmp_path / 'packet/inbox.json')).issues[0]
    assert issue.evidence[0].published_at == publication['date']
    assert issue.context['captured_publication_versions'][0]['published_at'] == publication['published_at']
    assert store.get(document)['payload']['published_at'] == publication['published_at']


def test_apply_once_including_retry_after_other_reviews(store, config, tmp_path):
    cid, _, decision = packet_and_decision(store, config, tmp_path)
    receipt = apply_decision(store, decision)
    assert receipt['status'] == 'applied' and receipt['validation'] == 'pending'
    apply_reviews(store, [Review(candidate_id=cid, action='defer', reviewer='Another editor', rationale='Check scope.')], utcnow())
    before = store.verify()
    assert apply_decision(store, decision) == receipt
    assert store.verify() == before
    changed = decision.model_copy(update={'rationale': 'Another instruction'})
    with pytest.raises(ValueError, match='different content'):
        apply_decision(store, changed)


def test_stale_review_cannot_overwrite_a_decision(store, config, tmp_path):
    cid, _, decision = packet_and_decision(store, config, tmp_path)
    apply_reviews(store, [Review(candidate_id=cid, action='defer', reviewer='Another editor', rationale='Check scope.')], utcnow())
    receipt = apply_decision(store, decision)
    assert receipt['status'] == 'stale'
    assert len(store.records('review')) == 1


def test_interrupted_receipt_rolls_back_scientific_change(store, config, tmp_path, monkeypatch):
    _, _, decision = packet_and_decision(store, config, tmp_path)
    before = store.verify()
    append = store.append
    def interrupted(kind, *args, **kwargs):
        if kind == 'inbox_receipt':
            raise RuntimeError('Interrupted before acknowledgement')
        return append(kind, *args, **kwargs)
    monkeypatch.setattr(store, 'append', interrupted)
    with pytest.raises(RuntimeError):
        apply_decision(store, decision)
    assert store.verify() == before
    monkeypatch.setattr(store, 'append', append)
    assert apply_decision(store, decision)['status'] == 'applied'


def test_validation_failure_is_retained_without_applying(store, config, tmp_path):
    _, _, decision = packet_and_decision(store, config, tmp_path)
    bad = decision.model_copy(update={'snapshot_id': 'f' * 64})
    receipts = import_decisions(store, Decisions(inbox_version='1.0.0', decisions=[bad]))
    assert receipts.receipts[0].status == 'invalid'
    assert not store.records('review')


def test_sync_reports_pending_work_after_the_service_acknowledges_it(store, config, tmp_path, monkeypatch):
    _, _, decision = packet_and_decision(store, config, tmp_path)
    apply_decision(store, decision)
    class Client:
        def request(self, method, path, **kwargs):
            return {'inbox_version': '1.0.0', 'decisions': []}
    monkeypatch.setattr('atlas.inbox.InboxClient', Client)
    result = sync_decisions(store)
    assert result['received'] == 0
    assert result['pending_validation'] == [decision.decision_id]


def test_source_tampering_fails_export(store, config, tmp_path):
    cid = add_example(store, config, sample_mention(), at=AT)
    doc = store.get(store.get(cid)['payload']['document_id'])['payload']
    (store.home / doc['text_object']).write_text('Different evidence')
    with pytest.raises(ValueError, match='hash or byte count'):
        export_inbox(store, 'atlas', tmp_path / 'packet', config=config)


def supplemental():
    text = 'The observation period requires review.\n'
    evidence = dict(document_id='historical-document', source_id='example_authority', title='Historical evidence',
        url='https://example.org/report', published_at='2020-01-01', captured_at=AT,
        sha256=digest(text.encode()), bytes=len(text.encode()), quotes=[text.strip()])
    return dict(inbox_version='1.0.0', sources=[{**evidence, 'text': text}], issues=[dict(
        issue_id='numeric-period-question', kind='longitudinal', title='Confirm observation period',
        question='Do these observations cover the same period?', impact='Series comparison remains pending.',
        first_seen=AT, changed_at=AT, affected_ids=['measurement-1'], dependencies={'measurement-1': 'a' * 64}, evidence=[evidence])])


def test_other_review_types_record_instructions_and_keep_backlog(store, config, tmp_path):
    register_supplement(store, SupplementalPacket.model_validate(supplemental()), config)
    export_inbox(store, 'atlas', tmp_path / 'packet', config=config)
    packet = Packet.model_validate(read_json(tmp_path / 'packet/inbox.json'))
    issue = packet.issues[0]
    decision = Decision(inbox_version='1.0.0', archive_id='atlas', decision_id='instruction-test',
        snapshot_id=packet.snapshot_id, issue_id=issue.issue_id, revision=issue.revision,
        reviewer='reviewer@example.org', submitted_at=utcnow(), action='instruct',
        rationale='Review the two observation periods using the captured table headings.')
    assert apply_decision(store, decision)['status'] == 'recorded'
    assert issue.issue_id in current_issues(store)
    assert not store.records('review')
    register_supplement(store, SupplementalPacket(inbox_version='1.0.0', sources=[], issues=[]), config)
    assert issue.issue_id in current_issues(store)


def test_supplement_rejects_unsupported_quotes_and_host(store, config):
    value = supplemental()
    value['issues'][0]['evidence'][0]['quotes'] = ['Invented quotation']
    with pytest.raises(ValueError, match='absent'):
        register_supplement(store, SupplementalPacket.model_validate(value), config)
    value = supplemental()
    value['sources'][0]['url'] = 'https://unapproved.example/report'
    with pytest.raises(ValueError, match='allowlist'):
        register_supplement(store, SupplementalPacket.model_validate(value), config)


def test_ledger_transaction_rolls_back_all_appends(store):
    with pytest.raises(RuntimeError):
        with store.transaction():
            store.append('test', {'a': 1}, AT)
            store.append('test', {'a': 2}, AT)
            raise RuntimeError('Interrupted')
    assert store.verify()['records'] == 0


def test_source_revision_invalidates_an_exported_decision(store, config, tmp_path):
    from atlas.sources import save_document
    cid, _, decision = packet_and_decision(store, config, tmp_path)
    original = store.get(store.get(cid)['payload']['document_id'])['payload']
    save_document(store, config['sources'][0], text='A revised source report.', raw=b'A revised source report.',
        url=original['url'], content_url=original['url'], title=original['title'],
        published_at=original['published_at'], at=utcnow())
    assert apply_decision(store, decision)['status'] == 'stale'
    assert not store.records('review')


def test_completion_requires_report_after_application_and_sync_sends_both_receipts(store, config, tmp_path, monkeypatch):
    from atlas.workflow import seal
    cid, _, decision = packet_and_decision(store, config, tmp_path)
    before = seal(store, config)
    apply_decision(store, decision)
    with pytest.raises(ValueError, match='before'):
        complete_decision(store, decision.decision_id, Path(before['bundle']), None, 'Reviewed the scientific output.')
    old_cutoff = seal(store, config, as_of=AT)
    with pytest.raises(ValueError, match='before'):
        complete_decision(store, decision.decision_id, Path(old_cutoff['bundle']), None, 'Reviewed the scientific output.')
    after = seal(store, config)
    completion = complete_decision(store, decision.decision_id, Path(after['bundle']), None, 'Reviewed the scientific output.')
    assert completion['status'] == 'completed' and completion['export_id']
    assert complete_decision(store, decision.decision_id, Path(after['bundle']), None, 'Same output.') == completion
    sent = []
    class Client:
        def request(self, method, path, **kwargs):
            if method == 'GET':
                return Decisions(inbox_version='1.0.0', decisions=[decision]).model_dump()
            sent.extend(kwargs['json']['receipts'])
            return {'received': len(kwargs['json']['receipts'])}
    monkeypatch.setattr('atlas.inbox.InboxClient', Client)
    sync_decisions(store)
    assert [r['status'] for r in sent] == ['applied', 'completed']


def test_cli_inbox_commands(tmp_path):
    from atlas.cli import parser
    assert parser().parse_args(['inbox-export', '--archive-id', 'atlas', '--out', str(tmp_path)]).archive_id == 'atlas'
    assert parser().parse_args(['inbox-import', 'decisions.json', '--out', 'receipts.json']).command == 'inbox-import'
    assert parser().parse_args(['inbox-push', 'inbox.json']).command == 'inbox-push'
