"""Private reviewer packets, explicit decisions, and application receipts."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

import httpx
from pydantic import Field, model_validator

from .models import StrictModel, Review
from .registry import apply_reviews, current_reviews, review_queue
from .util import canonical, digest, stamp, uid, utcnow, write_json

VERSION = '1.0.0'
MAX_JSON = 8_000_000
MAX_EVIDENCE = 16_000_000
Identifier = Annotated[str, Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')]
Hash = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
Timestamp = Annotated[str, Field(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$')]
Kind = Literal['registry', 'geography', 'longitudinal', 'chain', 'one_health', 'extraction', 'source', 'research']


class Evidence(StrictModel):
    document_id: Identifier
    source_id: Identifier
    title: str = Field(min_length=1, max_length=2000)
    url: str = Field(max_length=4000)
    published_at: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    captured_at: Timestamp
    sha256: Hash
    bytes: int = Field(ge=1, le=MAX_EVIDENCE)
    quotes: list[Annotated[str, Field(min_length=1, max_length=12000)]] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def dates_and_url(self):
        date.fromisoformat(self.published_at)
        stamp(self.captured_at)
        url = urlsplit(self.url)
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('Review evidence requires an HTTPS source URL')
        if any(not q.strip() or len(q) > 12000 for q in self.quotes):
            raise ValueError('Evidence quotations must contain 1 to 12000 characters')
        return self


class Issue(StrictModel):
    issue_id: Identifier
    revision: Hash
    kind: Kind
    title: str = Field(min_length=1, max_length=2000)
    question: str = Field(min_length=3, max_length=4000)
    impact: str = Field(min_length=3, max_length=4000)
    priority: Literal['high', 'normal', 'low'] = 'normal'
    first_seen: Timestamp
    changed_at: Timestamp
    candidate_id: Identifier | None = None
    affected_ids: list[Identifier] = Field(min_length=1, max_length=200)
    dependencies: dict[str, Hash] = Field(min_length=1, max_length=200)
    evidence: list[Evidence] = Field(min_length=1, max_length=40)
    context: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def binding(self):
        if (self.kind == 'registry') != bool(self.candidate_id):
            raise ValueError('Registry issues require a candidate; other issues use affected_ids')
        if stamp(self.changed_at) < stamp(self.first_seen):
            raise ValueError('Issue change time precedes first capture')
        if len(canonical(self.context).encode()) > 100_000:
            raise ValueError('Issue context exceeds 100000 bytes')
        return self


class SupplementalSource(Evidence):
    text: str = Field(min_length=1, max_length=MAX_EVIDENCE)


class SupplementalIssue(StrictModel):
    issue_id: Identifier
    kind: Literal['geography', 'longitudinal', 'chain', 'one_health', 'extraction', 'source', 'research']
    title: str = Field(min_length=1, max_length=2000)
    question: str = Field(min_length=3, max_length=4000)
    impact: str = Field(min_length=3, max_length=4000)
    priority: Literal['high', 'normal', 'low'] = 'normal'
    first_seen: Timestamp
    changed_at: Timestamp
    affected_ids: list[Identifier] = Field(min_length=1, max_length=200)
    dependencies: dict[str, Hash] = Field(min_length=1, max_length=200)
    evidence: list[Evidence] = Field(min_length=1, max_length=40)
    context: dict = Field(default_factory=dict)


class SupplementalPacket(StrictModel):
    inbox_version: Literal['1.0.0']
    sources: list[SupplementalSource] = Field(max_length=200)
    issues: list[SupplementalIssue] = Field(max_length=200)


class Packet(StrictModel):
    inbox_version: Literal['1.0.0']
    archive_id: Identifier
    snapshot_id: Hash
    sequence: int = Field(ge=1)
    generated_at: Timestamp
    ledger_head: Hash
    issues: list[Issue] = Field(max_length=200)


class Decision(StrictModel):
    inbox_version: Literal['1.0.0']
    archive_id: Identifier
    decision_id: Identifier
    snapshot_id: Hash
    issue_id: Identifier
    revision: Hash
    previous_decision_id: Identifier | None = None
    reviewer: str = Field(min_length=3, max_length=100)
    submitted_at: Timestamp
    action: Literal['accept', 'reject', 'defer', 'instruct']
    rationale: str = Field(min_length=3, max_length=800)
    event_key: str | None = Field(default=None, max_length=200)
    public_rationale: str = Field(default='Editorial review', min_length=3, max_length=300)
    supersedes_candidate_ids: list[Identifier] = Field(default_factory=list, max_length=100)
    allow_disease_reclassification: bool = False
    numeric_evidence_reviews: dict[str, str] = Field(default_factory=dict, max_length=30)

    @model_validator(mode='after')
    def action_fields(self):
        stamp(self.submitted_at)
        if (self.action == 'accept') != bool(self.event_key):
            raise ValueError('Only acceptance requires an event key')
        if self.action != 'accept' and (self.supersedes_candidate_ids or self.allow_disease_reclassification or self.numeric_evidence_reviews):
            raise ValueError('Acceptance fields require an acceptance decision')
        return self


class Decisions(StrictModel):
    inbox_version: Literal['1.0.0']
    decisions: list[Decision] = Field(max_length=200)


class Receipt(StrictModel):
    inbox_version: Literal['1.0.0']
    archive_id: Identifier
    decision_id: Identifier
    decision_sha256: Hash
    issue_id: Identifier
    revision: Hash
    status: Literal['applied', 'recorded', 'deferred', 'stale', 'invalid', 'completed']
    recorded_at: Timestamp
    ledger_record_ids: list[Identifier] = Field(default_factory=list, max_length=200)
    validation: Literal['pending', 'passed', 'not_required']
    export_id: Hash | None = None
    detail: str = Field(min_length=3, max_length=2000)

    @model_validator(mode='after')
    def completion(self):
        stamp(self.recorded_at)
        expected = 'passed' if self.status == 'completed' else 'pending' if self.status in ('applied', 'recorded') else 'not_required'
        if self.validation != expected or (self.status == 'completed') != bool(self.export_id):
            raise ValueError('Receipt validation and export must match its application status')
        return self


class Receipts(StrictModel):
    inbox_version: Literal['1.0.0']
    receipts: list[Receipt] = Field(max_length=200)


def bounded_json(path: Path):
    import json
    if path.stat().st_size > MAX_JSON:
        raise ValueError('Inbox JSON exceeds 8000000 bytes')
    return json.loads(path.read_text(encoding='utf-8'))


def issue_revision(value: dict) -> str:
    return digest({k: v for k, v in value.items() if k != 'revision'})


def checked_text(evidence: Evidence, raw: bytes) -> None:
    if len(raw) != evidence.bytes or digest(raw) != evidence.sha256:
        raise ValueError('Captured evidence differs from its hash or byte count')
    text = raw.decode('utf-8')
    if any(q not in text for q in evidence.quotes):
        raise ValueError('A review quotation is absent from its captured source')


def registry_issues(store) -> list[Issue]:
    reviews = current_reviews(store)
    documents = store.records('document')
    result = []
    for item in review_queue(store):
        candidate = store.get(item['candidate_id'])
        document = store.get(item['document_id'])
        doc = document['payload']
        if not doc.get('published_at'):
            continue
        quotes = [e['quote'] for e in item['mention']['evidence']]
        quotes += [o['evidence']['quote'] for o in item['mention']['observations']]
        path = (store.home / doc['text_object']).resolve()
        if not path.is_relative_to(store.home.resolve()):
            raise ValueError('Source object is outside the archive')
        evidence = Evidence(document_id=document['id'], source_id=doc['source_id'], title=doc['title'],
            url=doc['url'], published_at=doc['published_at'][:10], captured_at=document['recorded_at'],
            sha256=doc['text_sha256'], bytes=path.stat().st_size, quotes=list(dict.fromkeys(quotes)))
        checked_text(evidence, path.read_bytes())
        dependencies = {candidate['id']: candidate['record_hash'], document['id']: document['record_hash']}
        versions = [r for r in documents if r['payload']['source_id'] == doc['source_id'] and r['payload']['url'] == doc['url']]
        dependencies.update({r['id']: r['record_hash'] for r in versions})
        review = reviews.get(candidate['id'])
        if review:
            dependencies[review['id']] = review['record_hash']
        # Event suggestions depend on the reviewed candidates that establish those identities.
        keys = {m['event_key'] for m in item['suggested_matches']}
        for row in reviews.values():
            if row['payload'].get('event_key') in keys:
                dependencies[row['id']] = row['record_hash']
        data = dict(issue_id=uid('issue', candidate['id'], 'registry'), kind='registry',
            title=item['title'], question='Accept, reject or defer this finding and its proposed event identity?',
            impact='The decision determines membership in the event registry.',
            priority='high' if item['validation_errors'] else 'normal', first_seen=candidate['recorded_at'],
            changed_at=max([candidate['recorded_at']] + [store.get(r)['recorded_at'] for r in dependencies]),
            candidate_id=candidate['id'], affected_ids=[candidate['id']], dependencies=dependencies,
            evidence=[evidence.model_dump()], context={**{k: item[k] for k in ('mention', 'validation_errors', 'suggested_matches')},
                'captured_publication_versions': [dict(document_id=r['id'], published_at=r['payload']['published_at'],
                    captured_at=r['recorded_at'], text_sha256=r['payload']['text_sha256']) for r in versions]})
        data['revision'] = issue_revision(data)
        result.append(Issue.model_validate(data))
    return result


def supplemental_issues(store) -> dict[str, Issue]:
    return {r['payload']['issue_id']: Issue.model_validate(r['payload']) for r in store.records('inbox_issue')}


def register_supplement(store, packet: SupplementalPacket, config: dict) -> None:
    sources = {s.document_id: s for s in packet.sources}
    if len(sources) != len(packet.sources) or len({i.issue_id for i in packet.issues}) != len(packet.issues):
        raise ValueError('Duplicate source or issue identifier')
    hosts = {s['id']: set(s['allowed_hosts']) for s in config['sources']}
    for source in packet.sources:
        if urlsplit(source.url).hostname not in hosts.get(source.source_id, set()):
            raise ValueError('Supplemental source is outside its configured HTTPS host allowlist')
        checked_text(source, source.text.encode('utf-8'))
    previous = supplemental_issues(store)
    prepared = []
    for item in packet.issues:
        for evidence in item.evidence:
            source = sources.get(evidence.document_id)
            if not source or any(getattr(source, k) != getattr(evidence, k) for k in Evidence.model_fields if k != 'quotes'):
                raise ValueError('Issue evidence must identify a supplied captured source')
            checked_text(evidence, source.text.encode('utf-8'))
        data = {**item.model_dump(), 'candidate_id': None}
        data['revision'] = issue_revision(data)
        issue = Issue.model_validate(data)
        old = previous.get(issue.issue_id)
        if old and (old.first_seen != issue.first_seen or stamp(issue.changed_at) < stamp(old.changed_at)):
            raise ValueError('Issue history requires stable first_seen and increasing change times')
        if old and old.revision != issue.revision and stamp(issue.changed_at) <= stamp(old.changed_at):
            raise ValueError('A changed issue requires a later changed_at')
        prepared.append(issue)
    with store.transaction():
        for source in packet.sources:
            store.object(source.text.encode('utf-8'), 'txt')
        for issue in prepared:
            store.append('inbox_issue', issue.model_dump(), utcnow(), uid('inboxissue', issue.issue_id, issue.revision))


def current_issues(store) -> dict[str, Issue]:
    extra = supplemental_issues(store)
    for row in store.records('inbox_completion'):
        receipt = row['payload']
        issue = extra.get(receipt['issue_id'])
        if issue and issue.revision == receipt['revision']:
            del extra[issue.issue_id]
    for issue in registry_issues(store):
        if issue.issue_id in extra:
            raise ValueError('Supplemental issue collides with a registry issue')
        extra[issue.issue_id] = issue
    return extra


def export_inbox(store, archive_id: str, out: Path, *, supplemental: Path | None = None, config: dict) -> dict:
    store.verify()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use an empty inbox output directory')
    if supplemental:
        register_supplement(store, SupplementalPacket.model_validate(bounded_json(supplemental)), config)
    head = store.verify()
    issues = sorted(current_issues(store).values(), key=lambda i: i.issue_id)
    data = dict(inbox_version=VERSION, archive_id=archive_id, snapshot_id='0' * 64,
        sequence=head['records'] + 1, generated_at=utcnow(), ledger_head=head['head_hash'],
        issues=[i.model_dump() for i in issues])
    data['snapshot_id'] = digest({k: v for k, v in data.items() if k != 'snapshot_id'})
    packet = Packet.model_validate(data)
    if len(canonical(data).encode()) > MAX_JSON:
        raise ValueError('Inbox packet exceeds 8000000 bytes')
    for issue in packet.issues:
        for evidence in issue.evidence:
            raw = (store.home / 'objects' / (evidence.sha256 + '.txt')).read_bytes()
            checked_text(evidence, raw)
            from .util import atomic_write
            atomic_write(out / 'evidence' / (evidence.sha256 + '.txt'), raw)
    write_json(out / 'inbox.json', data)
    store.append('inbox_export', data, data['generated_at'], uid('inboxexport', packet.snapshot_id))
    return {'packet': str(out / 'inbox.json'), 'snapshot_id': packet.snapshot_id, 'issues': len(issues)}


def decision_receipt(store, decision_id: str) -> dict | None:
    result = None
    for row in store.records():
        if row['kind'] in ('inbox_receipt', 'inbox_completion') and row['payload']['decision_id'] == decision_id:
            result = row['payload']
    return result


def apply_decision(store, decision: Decision) -> dict:
    store.verify()
    data = decision.model_dump()
    hashed = digest(data)
    old = decision_receipt(store, decision.decision_id)
    if old:
        if old['decision_sha256'] != hashed:
            raise ValueError('Decision identity has different content')
        return old
    packet_row = store.get(uid('inboxexport', decision.snapshot_id))
    packet = Packet.model_validate(packet_row['payload'])
    if packet.archive_id != decision.archive_id:
        raise ValueError('Decision names a different archive')
    original = next((i for i in packet.issues if i.issue_id == decision.issue_id and i.revision == decision.revision), None)
    if not original:
        raise ValueError('Decision is not bound to an exported issue revision')
    prior = [r for r in store.records('inbox_decision') if r['payload']['issue_id'] == decision.issue_id and r['payload']['archive_id'] == decision.archive_id]
    if decision.previous_decision_id != (prior[-1]['payload']['decision_id'] if prior else None):
        raise ValueError('Decision does not follow the recorded decision history')
    if stamp(decision.submitted_at) < stamp(packet.generated_at) or stamp(decision.submitted_at) > stamp(utcnow()):
        raise ValueError('Decision time is outside its exported review interval')
    current = current_issues(store).get(decision.issue_id)
    at = utcnow()
    status, validation, detail, ids = 'stale', 'not_required', 'Evidence or review context changed; review the current issue.', []
    with store.transaction():
        store.append('inbox_decision', data, at, uid('inboxdecision', decision.decision_id))
        if current and current.revision == decision.revision:
            if original.kind == 'registry':
                if decision.action == 'instruct':
                    raise ValueError('Registry decisions use accept, reject or defer')
                fields = {k: v for k, v in data.items() if k in Review.model_fields}
                fields['candidate_id'] = original.candidate_id
                ids = apply_reviews(store, [Review.model_validate(fields)], at)
                status, validation = 'applied', 'pending'
                detail = 'Decision applied to the ledger. Rebuild and validate affected outputs before completion.'
            else:
                if decision.action not in ('instruct', 'defer'):
                    raise ValueError('This review type requires an explicit instruction or deferral')
                status = 'deferred' if decision.action == 'defer' else 'recorded'
                validation = 'not_required' if status == 'deferred' else 'pending'
                detail = 'Question remains pending.' if status == 'deferred' else 'Instruction recorded for its scientific review workflow; application remains pending.'
        receipt = Receipt(inbox_version=VERSION, archive_id=decision.archive_id, decision_id=decision.decision_id,
            decision_sha256=hashed, issue_id=decision.issue_id, revision=decision.revision, status=status,
            recorded_at=at, ledger_record_ids=ids, validation=validation, detail=detail).model_dump()
        store.append('inbox_receipt', receipt, at, uid('inboxreceipt', decision.decision_id))
    return receipt


def import_decisions(store, decisions: Decisions) -> Receipts:
    if len({d.decision_id for d in decisions.decisions}) != len(decisions.decisions):
        raise ValueError('Duplicate decision identity in import')
    results = []
    for decision in decisions.decisions:
        try:
            results.append(apply_decision(store, decision))
        except (ValueError, KeyError) as exc:
            if decision_receipt(store, decision.decision_id):
                raise
            receipt = Receipt(inbox_version=VERSION, archive_id=decision.archive_id, decision_id=decision.decision_id,
                decision_sha256=digest(decision.model_dump()), issue_id=decision.issue_id, revision=decision.revision,
                status='invalid', recorded_at=utcnow(), validation='not_required', detail=str(exc)[:2000])
            with store.transaction():
                store.append('inbox_decision', decision.model_dump(), receipt.recorded_at, uid('inboxdecision', decision.decision_id))
                store.append('inbox_receipt', receipt.model_dump(), receipt.recorded_at, uid('inboxreceipt', decision.decision_id))
            results.append(receipt.model_dump())
    return Receipts(inbox_version=VERSION, receipts=results)


def complete_decision(store, decision_id: str, bundle: Path, snapshot: Path | None, note: str) -> dict:
    from .handoff import inspect_export
    from .export import verify_bundle
    store.verify()
    receipt = decision_receipt(store, decision_id)
    if not receipt or receipt['status'] not in ('recorded', 'applied', 'completed'):
        raise ValueError('Completion requires a recorded or applied decision')
    decision = Decision.model_validate(store.get(uid('inboxdecision', decision_id))['payload'])
    packet = Packet.model_validate(store.get(uid('inboxexport', decision.snapshot_id))['payload'])
    issue = next(i for i in packet.issues if i.issue_id == receipt['issue_id'])
    if issue.kind == 'registry':
        latest = current_reviews(store).get(issue.candidate_id)
        if not latest or latest['id'] not in receipt['ledger_record_ids']:
            raise ValueError('A later editorial decision requires reassessment before completion')
        verify_bundle(bundle)
        report = bounded_json(bundle / 'report.json')
        head = report['metadata']['ledger_head_sha256']
        heads = {r['record_hash']: r['seq'] for r in store.records()}
        applied = store.get(uid('inboxreceipt', decision_id))
        if heads.get(head, -1) < applied['seq'] or stamp(report['metadata']['knowledge_cutoff']) < stamp(applied['recorded_at']):
            raise ValueError('Report was sealed before this decision was applied')
        reference = {'export_id': digest((bundle / 'dataset.zip').read_bytes())}
    else:
        current = supplemental_issues(store).get(issue.issue_id)
        if not current or current.revision != issue.revision:
            raise ValueError('Issue evidence changed before completion')
        if snapshot is None:
            raise ValueError('Scientific completion requires the exact map snapshot')
        reference = inspect_export(bundle, snapshot)
    if receipt['status'] == 'completed':
        if receipt['export_id'] != reference['export_id']:
            raise ValueError('Completion already identifies a different export')
        return receipt
    result = Receipt.model_validate({**receipt, 'status': 'completed', 'validation': 'passed',
        'export_id': reference['export_id'], 'recorded_at': utcnow(), 'detail': note}).model_dump()
    store.append('inbox_completion', result, result['recorded_at'], uid('inboxcomplete', decision_id))
    return result


class InboxClient:
    def __init__(self):
        self.url = os.environ.get('ATLAS_INBOX_URL', '').rstrip('/')
        parsed = urlsplit(self.url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('ATLAS_INBOX_URL requires the trusted HTTPS inbox address')
        self.headers = {'CF-Access-Client-Id': os.environ['ATLAS_INBOX_CLIENT_ID'],
            'CF-Access-Client-Secret': os.environ['ATLAS_INBOX_CLIENT_SECRET']}

    def request(self, method: str, path: str, *, data: bytes | None = None, json=None):
        with httpx.Client(timeout=60, follow_redirects=False, headers=self.headers) as client:
            with client.stream(method, self.url + '/api/sync/' + path, content=data, json=json) as response:
                if response.status_code >= 300:
                    raise ValueError(f'Inbox service returned HTTP {response.status_code}')
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_JSON:
                        raise ValueError('Inbox response exceeds 8000000 bytes')
                    chunks.append(chunk)
                import json as json_module
                return json_module.loads(b''.join(chunks))


def push_packet(path: Path) -> dict:
    packet = Packet.model_validate(bounded_json(path))
    if packet.snapshot_id != digest({k: v for k, v in packet.model_dump().items() if k != 'snapshot_id'}):
        raise ValueError('Inbox snapshot hash differs')
    client = InboxClient()
    uploaded = set()
    for issue in packet.issues:
        for evidence in issue.evidence:
            if evidence.sha256 in uploaded:
                continue
            raw = (path.parent / 'evidence' / (evidence.sha256 + '.txt')).read_bytes()
            checked_text(evidence, raw)
            client.request('PUT', 'evidence/' + evidence.sha256, data=raw)
            uploaded.add(evidence.sha256)
    return client.request('POST', 'snapshot', json=packet.model_dump())


def sync_decisions(store) -> dict:
    client = InboxClient()
    decisions = Decisions.model_validate(client.request('GET', 'decisions'))
    receipts = import_decisions(store, decisions)
    ids = {r.decision_id for r in receipts.receipts}
    ids.update(row['payload']['decision_id'] for row in store.records('inbox_completion'))
    # Application precedes completion even when both were recorded before the first sync.
    values = [Receipt.model_validate(row['payload']) for row in store.records()
              if row['kind'] in ('inbox_receipt', 'inbox_completion') and row['payload']['decision_id'] in ids]
    for start in range(0, len(values), 200):
        client.request('POST', 'receipts', json=Receipts(inbox_version=VERSION, receipts=values[start:start+200]).model_dump())
    latest = {row['payload']['decision_id']: row['payload'] for row in store.records()
              if row['kind'] in ('inbox_receipt', 'inbox_completion')}
    return {'received': len(decisions.decisions), 'receipts_sent': len(values),
        'pending_application': [key for key, receipt in latest.items() if receipt['status'] == 'recorded'],
        'pending_validation': [key for key, receipt in latest.items() if receipt['status'] == 'applied']}
