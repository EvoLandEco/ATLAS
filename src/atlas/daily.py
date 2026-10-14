"""Daily source findings and their separate weekly reconciliation record."""
from datetime import date, datetime, timedelta
from importlib.resources import files
from pathlib import Path
import sqlite3
import json
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator
from . import __version__
from .models import StrictModel, TextValue
from .source_text import Hash, Translation, _source
from .util import digest, read_json, stamp, uid, utcnow, write_json

VERSION = '0.2.2'
WATCH_METHOD = 'daily-watch-1.0.2'


class QuoteInput(StrictModel):
    quote: str = Field(min_length=1)
    start: int | None = Field(default=None, ge=0)
    language_tag: str = Field(pattern=r'^[a-z]{2,3}$')
    translation: Translation | None = None


class PlaceInput(StrictModel):
    name: str = Field(min_length=1)
    country_code: str | None = Field(pattern=r'^[A-Z]{2}$')
    role: Literal['reporting_scope', 'occurrence', 'exposure', 'travel_origin', 'travel_destination', 'context']


class FindingInput(StrictModel):
    key: str = Field(min_length=1)
    kind: Literal['suspected_disease', 'diagnostic_status', 'reported_count', 'geographic_extent',
                  'spatial_link', 'response_measure', 'potential_source', 'development']
    text: str = Field(min_length=1, max_length=1000)
    status: Literal['reported', 'source_suspected', 'source_probable', 'source_confirmed',
                    'source_ruled_out', 'unconfirmed', 'disputed', 'unresolved']
    statement_kind: Literal['source_statement', 'attributed_hypothesis', 'analyst_hypothesis']
    attribution: TextValue
    observation_period: TextValue
    places: list[PlaceInput]
    evidence: list[QuoteInput] = Field(min_length=1)


class DailyReview(StrictModel):
    document_id: str
    source_text_sha256: Hash
    language_tag: str = Field(pattern=r'^[a-z]{2,3}$')
    title_translation: Translation | None
    outcome: Literal['relevant', 'no_relevant_content', 'needs_review']
    findings: list[FindingInput]
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)
    review_state: Literal['source_checked_draft']
    limitations: list[str]

    @model_validator(mode='after')
    def scope(self):
        stamp(self.reviewed_at)
        if self.outcome == 'relevant' and not self.findings:
            raise ValueError('Relevant daily review needs supported findings')
        if self.outcome != 'relevant' and self.findings:
            raise ValueError('Unresolved or irrelevant review cannot publish findings')
        if len({f.key for f in self.findings}) != len(self.findings):
            raise ValueError('Duplicate daily finding key')
        return self


class WatchCriterion(StrictModel):
    kind: Literal['severe_impact', 'spread_change', 'unusual_event', 'response_gap', 'time_sensitive_action']
    finding_keys: list[str] = Field(min_length=1)
    reason: str = Field(min_length=12, max_length=240)


class WatchFact(StrictModel):
    label: str = Field(min_length=1, max_length=28)
    text: str = Field(min_length=1, max_length=110)
    finding_keys: list[str] = Field(min_length=1)


class WatchInput(StrictModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1, max_length=160)
    finding_keys: list[str] = Field(min_length=1)
    reason_for_attention: str = Field(min_length=12, max_length=260)
    follow_up_question: str = Field(min_length=12)
    temporal_status: Literal['current', 'routine', 'retrospective', 'unknown', 'resolved']
    development_date: str | None
    date_basis: Literal['source_event_date', 'source_report_date', 'unknown']
    development_finding_keys: list[str]
    follow_up_finding_keys: list[str]
    counterevidence_finding_keys: list[str]
    criteria: list[WatchCriterion]
    decision_reason: str = Field(min_length=12, max_length=500)
    location_label: str = Field(max_length=80)
    diagnostic_label: str = Field(max_length=100)
    key_facts: list[WatchFact] = Field(max_length=3)
    review_due_at: str
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)
    review_state: Literal['source_checked_draft']

    @model_validator(mode='after')
    def scope(self):
        reviewed = datetime.fromisoformat(stamp(self.reviewed_at))
        due = datetime.fromisoformat(stamp(self.review_due_at))
        if not reviewed < due <= reviewed + timedelta(hours=24):
            raise ValueError('Watch review is due within 24 hours')
        if (self.development_date is None) != (self.date_basis == 'unknown'):
            raise ValueError('Watch development date needs its source basis')
        if self.development_date is not None:
            date.fromisoformat(self.development_date)
            if not self.development_finding_keys:
                raise ValueError('Watch development date needs evidence')
        if len({c.kind for c in self.criteria}) != len(self.criteria):
            raise ValueError('Duplicate watch criterion')
        refs = [self.development_finding_keys, self.follow_up_finding_keys, self.counterevidence_finding_keys,
                *[c.finding_keys for c in self.criteria],
                *[f.finding_keys for f in self.key_facts]]
        if any(len(set(keys)) != len(keys) or not set(keys) <= set(self.finding_keys) for keys in refs):
            raise ValueError('Watch assessment requires exact supporting finding references')
        return self


def watch_decision(w):
    """Assign editorial attention from reviewed current evidence, without a risk score."""
    if w.temporal_status != 'current' or w.development_date is None or not w.follow_up_finding_keys:
        return 'not_selected'
    age = (date.fromisoformat(publication_day(w.reviewed_at)) - date.fromisoformat(w.development_date)).days
    if age < 0:
        return 'not_selected'
    criteria = {c.kind for c in w.criteria}
    if 'time_sensitive_action' in criteria:
        return 'urgent'
    if 'severe_impact' in criteria and criteria & {'spread_change', 'response_gap'}:
        return 'heightened'
    return 'watch' if criteria else 'not_selected'


class Reconciliation(StrictModel):
    review_id: str
    weekly_export_id: Hash
    record_ids: list[str]
    disposition: Literal['integrated', 'reviewed_not_exported', 'pending']
    reason: str = Field(min_length=12)
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)
    weekly_inbox_sha256: Hash


class PublicationVersion(StrictModel):
    document_id: str
    source_text_sha256: Hash
    raw_sha256: Hash


class PublicationBinding(StrictModel):
    document_versions: list[PublicationVersion] = Field(min_length=2)
    assertion_ids: list[str] = Field(min_length=1)
    comparison_ids: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    reason: str = Field(min_length=12)
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)


class DailyAnnotations(StrictModel):
    daily_version: Literal['0.2.1', '0.2.2']
    reviews: list[DailyReview]
    watch_assessments: list[WatchInput]
    reconciliations: list[Reconciliation] = Field(default_factory=list)
    publication_bindings: list[PublicationBinding] = Field(default_factory=list)


def annotation_payload(annotations):
    excluded = {'publication_bindings'} if not annotations.publication_bindings else set()
    return annotations.model_dump(mode='json', exclude=excluded)


def publication_bindings(reviews, site, daily_documents):
    """Validate explicit whole-publication reviews without merging scientific records."""
    documents = {d['id']: d for d in site['documents']}
    daily = {d['id']: d for d in daily_documents}
    assertions = {a['id']: a for a in site.get('assertions', [])}
    comparisons = {c['id']: c for c in site.get('comparisons', [])}
    evidence = {e['id']: e for e in site.get('evidence', [])}
    bindings, used = {}, set()
    for review in reviews:
        ids = [v.document_id for v in review.document_versions]
        if len(set(ids)) != len(ids) or used.intersection(ids) or not set(ids) <= documents.keys():
            raise ValueError('Publication binding has duplicate, overlapping or missing documents')
        used.update(ids)
        if not set(ids).intersection(daily):
            raise ValueError('Publication binding requires an eligible daily document')
        versions = [documents[i] for i in ids]
        if len({(d['channel_id'], date.fromisoformat(d['publication']).isoformat()
                 if len(d['publication']) == 10 else stamp(d['publication'])) for d in versions}) != 1:
            raise ValueError('Publication binding spans different publishers or dated editions')
        for v in review.document_versions:
            doc = documents[v.document_id]
            if (doc['text_sha256'] != v.source_text_sha256 or doc['raw_sha256'] != v.raw_sha256
                    or stamp(review.reviewed_at) < stamp(doc['capture'])):
                raise ValueError('Publication binding has stale source hashes or review time')
            if v.document_id in daily:
                captured = daily[v.document_id]
                if (captured['text_sha256'] != v.source_text_sha256
                        or captured['raw_sha256'] != v.raw_sha256):
                    raise ValueError('Publication binding differs from the daily capture')
        expected = {a['id'] for a in assertions.values() if a['document_id'] in ids}
        if set(review.assertion_ids) != expected or len(review.assertion_ids) != len(expected):
            raise ValueError('Publication binding requires review of every assertion and measure')
        supporting = {eid for aid in expected for eid in assertions[aid]['evidence_ids']}
        if (set(review.evidence_ids) != supporting or len(review.evidence_ids) != len(supporting)
                or any(eid not in evidence or evidence[eid]['document_id'] not in ids
                       or evidence[eid]['source_text_sha256'] != documents[evidence[eid]['document_id']]['text_sha256']
                       for eid in supporting)):
            raise ValueError('Publication binding has missing or foreign source evidence')
        if len(set(review.comparison_ids)) != len(review.comparison_ids):
            raise ValueError('Publication binding repeats a comparison')
        covered, neighbours = set(), {i: set() for i in ids}
        for cid in review.comparison_ids:
            comparison = comparisons.get(cid)
            if (not comparison or comparison['kind'] != 'republication'
                    or comparison['status'] != 'documented'
                    or stamp(review.reviewed_at) < stamp(comparison['reviewed_at'])
                    or not set(comparison['participant_ids']) <= expected):
                raise ValueError('Publication binding has missing, foreign or unreviewed comparison evidence')
            covered.update(comparison['participant_ids'])
            participants = {assertions[i]['document_id'] for i in comparison['participant_ids']}
            for did in participants: neighbours[did].update(participants - {did})
        findings = {i for i in expected if assertions[i]['kind'] == 'finding'}
        if not findings or not findings <= covered:
            raise ValueError('Publication binding comparisons cover only part of the findings')
        reached, pending = set(), [ids[0]]
        while pending:
            did = pending.pop()
            if did not in reached:
                reached.add(did); pending.extend(neighbours[did] - reached)
        if reached != set(ids):
            raise ValueError('Publication binding comparison evidence does not connect its documents')
        for did in set(ids).intersection(daily): bindings[did] = set(ids)
    return bindings


class LegacyDailyDocument(StrictModel):
    id: str
    source_id: str
    channel_id: str | None
    base_document_ids: list[str]
    source_name: str
    source_role: str
    url: str
    content_url: str
    title: str
    title_translation: Translation | None
    language_tag: str
    publication: str | None
    publication_precision: str
    modified_at: str | None
    capture: str
    source_text_sha256: Hash
    raw_sha256: Hash
    parse_status: str
    review_id: str | None
    review_state: Literal['not_reviewed', 'source_checked_draft']
    reviewed_at: str | None
    reviewed_by: str | None
    outcome: Literal['pending', 'relevant', 'no_relevant_content', 'needs_review']
    processing_status: Literal['weekly_review_pending', 'weekly_reviewed']
    finding_ids: list[str]
    country_codes: list[str]
    limitations: list[str]


class DailyDocument(LegacyDailyDocument):
    publication: str


class DailyEvidence(StrictModel):
    id: str
    document_id: str
    source_text_sha256: Hash
    quote_sha256: Hash
    quote: str
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    offset_basis: Literal['unicode_code_points_half_open']
    language_tag: str
    translation: Translation | None


class DailyFinding(StrictModel):
    id: str
    key: str
    document_id: str
    review_id: str
    kind: FindingInput.model_fields['kind'].annotation
    text: str
    status: FindingInput.model_fields['status'].annotation
    statement_kind: FindingInput.model_fields['statement_kind'].annotation
    attribution: TextValue
    observation_period: TextValue
    places: list[PlaceInput]
    evidence_ids: list[str]
    reviewed_at: str
    reviewed_by: str
    review_state: Literal['source_checked_draft']


class DailyWatchFact(WatchFact):
    finding_ids: list[str]


class DailyWatch(WatchInput):
    id: str
    finding_ids: list[str]
    evidence_ids: list[str]
    document_ids: list[str]
    scope_kind: Literal['report_selection']
    event_identity: Literal['not_assigned']
    latest_publication: str | None
    latest_capture: str
    attention: Literal['urgent', 'heightened', 'watch', 'not_selected']
    method_version: Literal['daily-watch-1.0.2']
    key_facts: list[DailyWatchFact]


class DailyCoverage(StrictModel):
    source_id: str
    source_name: str
    source_role: str
    status: str
    notes: list[str]
    checked_at: str | None
    documents: int
    reviewed: int
    relevant: int
    pending: int


class LegacyDailyExport(StrictModel):
    daily_version: Literal['0.2.1']
    daily_id: Hash
    software_version: str
    generated_at: str
    base_source_export_id: Hash
    base_site_sha256: Hash
    base_manifest_sha256: Hash
    base_map_snapshot_sha256: Hash
    acquisition_sha256: Hash
    annotations_sha256: Hash
    publication_from: str
    publication_until: str
    knowledge_cutoff: str
    timezone: Literal['Europe/Amsterdam']
    selection_policy: Literal['all_supporting_documents_in_window']
    documents: list[LegacyDailyDocument]
    evidence: list[DailyEvidence]
    findings: list[DailyFinding]
    watch_items: list[DailyWatch]
    watch_assessments: list[DailyWatch]
    reconciliations: list[Reconciliation]
    source_coverage: list[DailyCoverage]


class DailyExport(LegacyDailyExport):
    daily_version: Literal['0.2.2']
    documents: list[DailyDocument]


def read_documents(state: Path, cutoff: str):
    """Read captured versions without opening a writer on the source ledger."""
    with sqlite3.connect(f'file:{state.resolve()}/ledger.sqlite?mode=ro', uri=True) as db:
        rows = [dict(id=i, capture=at, **json.loads(p)) for i, at, p in db.execute(
            "SELECT id,recorded_at,payload FROM records WHERE kind='document' AND recorded_at<=? ORDER BY seq", (stamp(cutoff),))]
    return rows


def reuse_documents(source_state, target_store, since, until, cutoff, source_ids=None):
    if source_state.resolve() == target_store.home.resolve():
        raise ValueError('Daily and weekly archives require separate directories')
    copied=[]
    for doc in selected_documents(read_documents(source_state,cutoff),since,until):
        if source_ids is not None and doc['source_id'] not in source_ids:continue
        if target_store.has(doc['id']):continue
        for field, suffix in [('text','txt'),('raw','bin')]:
            raw=(source_state/doc[field+'_object']).read_bytes()
            if digest(raw)!=doc[field+'_sha256']:raise ValueError('Captured object differs during archive transfer')
            if target_store.object(raw,suffix)!=doc[field+'_object']:raise ValueError('Captured object path differs')
        target_store.append('document',{k:v for k,v in doc.items() if k not in {'id','capture'}},doc['capture'],doc['id'])
        copied.append(doc['id'])
    return copied


def capture_daily(state, weekly_state, config, since, until, *, force=False):
    from filelock import FileLock
    from .store import Store
    from .sources import collect
    date.fromisoformat(since);date.fromisoformat(until)
    if since>until:raise ValueError('Daily publication window is reversed')
    if state.resolve()==weekly_state.resolve() or (state/'latest.json').exists():
        raise ValueError('Daily capture requires a separate archive from weekly production')
    state.mkdir(parents=True,exist_ok=True)
    with FileLock(str(state/'.writer.lock'),timeout=5):
        store=Store(state)
        try:
            key=digest([publication_day(utcnow()),since,until,config])
            previous=[r['payload'] for r in store.records('daily_acquisition') if r['payload']['key']==key]
            if previous and not force:return previous[-1]
            if not force and any(r['payload']['key']==key for r in store.records('daily_acquisition_started')):
                raise ValueError('Interrupted daily acquisition requires review before an explicit force run')
            started=utcnow(); run_id=uid('daily_run',key,started)
            store.append('daily_acquisition_started',dict(key=key,run_id=run_id),started)
            prior=read_json(Path(read_json(state/'daily-latest.json')['acquisition'])) if (state/'daily-latest.json').exists() else {}
            source_ids=sorted(set(prior.get('source_ids',[])) | {s['id'] for s in config.get('sources',[]) if s.get('enabled')})
            reused=reuse_documents(weekly_state,store,since,until,started,source_ids if config.get('sources') else None)
            totals=collect(store,config,since,until=until)
            completed=utcnow()
            check_times={r['payload']['source_id']:r['recorded_at'] for r in store.records('source_check')
                         if stamp(started)<=stamp(r['recorded_at'])<=stamp(completed)}
            for check in totals['sources']:
                check['checked_at']=check_times.get(check['source_id'])
            receipt=dict(run_id=run_id,key=key,started_at=started,completed_at=completed,
                discovery_from=since,discovery_until=until,publication_from=min(since,prior.get('publication_from',since)),publication_until=until,
                source_ids=source_ids,
                config_sha256=digest(config),reused_document_ids=reused,**totals,ledger=store.verify())
            store.append('daily_acquisition',receipt,completed,run_id)
            write_json(state/'acquisitions'/(run_id+'.json'),receipt)
            write_json(state/'daily-latest.json',dict(acquisition=str((state/'acquisitions'/(run_id+'.json')).resolve()),run_id=run_id))
            return receipt
        finally:store.close()


class DailyDraft(StrictModel):
    outcome: Literal['relevant','no_relevant_content','needs_review']
    language_tag: str = Field(pattern=r'^[a-z]{2,3}$')
    findings: list[FindingInput]
    limitations: list[str]


def extract_daily(state, acquisition_path, config, out, model=''):
    from .codex import CodexExtractor
    from .config import assets
    from time import time_ns
    acquisition=read_json(acquisition_path)
    captured=read_documents(state,acquisition['completed_at'])
    docs=acquired_documents(captured,acquisition)
    exclusions=publication_exclusions(captured,acquisition)
    prompt=assets('daily.md');schema=DailyDraft.model_json_schema();limits=config['limits']
    agent=CodexExtractor(model,limits['codex_output_bytes'],limits['codex_timeout_seconds'])
    rows=[];calls=0;characters=0
    out.mkdir(parents=True,exist_ok=True)
    for doc in docs:
        text=(state/doc['text_object']).read_text()
        if digest(text.encode())!=doc['text_sha256']:raise ValueError('Daily extraction source differs')
        key=digest([doc,model,digest(prompt.encode()),schema]);saved=out/(key+'.json')
        if saved.exists():rows.append(read_json(saved));continue
        row=dict(document_id=doc['id'],source_text_sha256=doc['text_sha256'],key=key,
            prompt_sha256=digest(prompt.encode()),schema_sha256=digest(schema),requested_model=model or None,started_at=utcnow())
        if doc['parse_status']!='text_ready' or len(text)>100000:
            row.update(status='source_review_required',reason='Source layout or the 100,000 character input bound requires review.')
        elif calls>=limits['max_model_calls'] or characters+len(text)>limits['max_input_characters']:
            row.update(status='budget_pending',reason='The run reached its configured extraction bound.')
        else:
            calls+=1;characters+=len(text)
            try:
                result,receipt=agent.extract(text,doc,out/'attempts'/f'{key}-{time_ns()}',contract=DailyDraft,prompt=prompt)
                for f in result.findings:
                    for q in f.evidence:
                        if q.quote not in text:raise ValueError('Daily draft quotation is absent from captured text')
                row.update(status='draft',result=result.model_dump(mode='json'),receipt=receipt)
            except (ValueError,OSError) as exc:row.update(status='failed',reason=str(exc))
        row['completed_at']=utcnow()
        if row['status']!='budget_pending':write_json(saved,row)
        rows.append(row)
        write_json(out/'results.json',dict(acquisition_sha256=digest(acquisition),calls=calls,input_characters=characters,rows=rows,excluded_documents=exclusions))
    result=dict(acquisition_sha256=digest(acquisition),calls=calls,input_characters=characters,rows=rows,excluded_documents=exclusions)
    write_json(out/'results.json',result)
    return dict(documents=len(rows),model_calls=calls,input_characters=characters,
        drafts=sum(r['status']=='draft' for r in rows),results=str(out/'results.json'))


def publication_day(value):
    if value is None:
        return None
    if len(value) == 10:
        return date.fromisoformat(value).isoformat()
    return datetime.fromisoformat(stamp(value)).astimezone(ZoneInfo('Europe/Amsterdam')).date().isoformat()


def latest_documents(rows):
    latest = {}
    for d in rows:
        key = (d['source_id'], d['url'])
        if key not in latest or stamp(d['capture']) > stamp(latest[key]['capture']):
            latest[key] = d
    return list(latest.values())


def selected_documents(rows, since, until):
    if date.fromisoformat(since) > date.fromisoformat(until):
        raise ValueError('Daily publication window is reversed')
    return sorted((d for d in latest_documents(rows) if publication_day(d['published_at']) is not None
        and since <= publication_day(d['published_at']) <= until), key=lambda d:d['id'])


def acquired_documents(rows, acquisition, *, _legacy=False):
    scope=acquisition.get('source_ids')
    chosen=latest_documents([d for d in rows if scope is None or d['source_id'] in scope])
    since,until=acquisition['publication_from'],acquisition['publication_until']
    dated=selected_documents(chosen,since,until)
    undated=[d for d in chosen if _legacy and d['published_at'] is None and since<=publication_day(d['capture'])<=until]
    return sorted(dated+undated,key=lambda d:d['id'])


def publication_exclusions(rows, acquisition):
    scope=acquisition.get('source_ids')
    return [dict(document_id=d['id'],source_text_sha256=d['text_sha256'],reason='missing_publication_date')
            for d in latest_documents(rows) if d['published_at'] is None
            and (scope is None or d['source_id'] in scope)]


def dated_annotations(rows, annotations, acquisition):
    ann=DailyAnnotations.model_validate(annotations)
    excluded=publication_exclusions(rows,acquisition)
    ids={d['document_id'] for d in excluded}
    reviews=[r for r in ann.reviews if r.document_id in ids]
    keys={r.document_id+':'+f.key for r in reviews for f in r.findings}
    review_ids={uid('daily_review',r.model_dump(mode='json')) for r in reviews}
    watches=[]
    for w in ann.watch_assessments:
        overlap=set(w.finding_keys)&keys
        if overlap and overlap!=set(w.finding_keys):
            raise ValueError('Watch assessment '+w.key+' mixes excluded and dated reports; reassess its dated findings')
        if overlap:watches.append(w.key)
    retained=ann.model_copy(update=dict(reviews=[r for r in ann.reviews if r.document_id not in ids],
        watch_assessments=[w for w in ann.watch_assessments if w.key not in watches],
        reconciliations=[r for r in ann.reconciliations if r.review_id not in review_ids]))
    receipt=dict(policy='dated-reports-1.0.0',acquisition_sha256=digest(acquisition),
        annotations_sha256=digest(annotations),retained_annotations_sha256=digest(annotation_payload(retained)),
        excluded_documents=excluded,excluded_review_ids=sorted(review_ids),excluded_watch_keys=watches,
        excluded_reconciliations=[r.model_dump(mode='json') for r in ann.reconciliations if r.review_id in review_ids])
    return retained,receipt


def _translation(tr, language, capture, reviewed_at):
    import pycountry
    if language not in {'und', 'mul'} and pycountry.languages.get(**{
            'alpha_2' if len(language) == 2 else 'alpha_3': language}) is None:
        raise ValueError('Unknown daily language tag')
    if tr is not None and (tr.origin != 'atlas_generated' or language in {'en', 'eng', 'und'}
                           or stamp(tr.created_at) < stamp(capture) or stamp(tr.created_at)>stamp(reviewed_at)
                           or (tr.reviewed_at is not None and stamp(tr.reviewed_at)>stamp(reviewed_at))):
        raise ValueError('Daily translation requires a captured non-English original and ATLAS provenance')


def prepare_daily(rows, texts, annotations, config, acquisition, site, source, weekly_handoff=None, *, _legacy=False):
    cutoff = stamp(acquisition['completed_at'])
    rows = [d for d in rows if stamp(d['capture']) <= cutoff]
    ann = DailyAnnotations.model_validate(annotations) if _legacy else dated_annotations(rows,annotations,acquisition)[0]
    start, end = acquisition['publication_from'], acquisition['publication_until']
    docs = acquired_documents(rows, acquisition, _legacy=_legacy)
    if _legacy and ann.publication_bindings:
        raise ValueError('Publication binding reviews require daily contract 0.2.2')
    bindings = publication_bindings(ann.publication_bindings, site, docs)
    sources = {s['id']:s for s in config['sources']}
    channels={}
    for channel in site.get('channels',[]):
        channels.setdefault(channel['acquisition_source'],[]).append(channel['id'])
    from .util import canonical_url
    base_documents={}
    for doc in site['documents']:
        base_documents.setdefault((doc['channel_id'],canonical_url(doc['url']),publication_day(doc['publication'])),[]).append(doc['id'])
    if len({r.document_id for r in ann.reviews}) != len(ann.reviews):
        raise ValueError('Duplicate daily document review')
    reviews = {r.document_id:r for r in ann.reviews}
    if not reviews.keys() <= {d['id'] for d in docs}:
        raise ValueError('Daily review is outside the captured selection')
    evidence, findings, documents, lookup = {}, [], [], {}
    for d in docs:
        text = texts[d['id']]
        if digest(text.encode()) != d['text_sha256']:
            raise ValueError('Daily captured text differs')
        src = sources[d['source_id']]
        for url in (d['url'], d['content_url']):
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or parsed.hostname not in src['allowed_hosts'] or parsed.username or parsed.password:
                raise ValueError('Daily source is outside its HTTPS host allowlist')
        review = reviews.get(d['id']); review_id = None; ids = []; codes = set()
        if review:
            if review.source_text_sha256 != d['text_sha256'] or stamp(review.reviewed_at) < stamp(d['capture']):
                raise ValueError('Daily review has stale source text or predates capture')
            _translation(review.title_translation, review.language_tag, d['capture'], review.reviewed_at)
            review_id = uid('daily_review', review.model_dump(mode='json'))
            for finding in review.findings:
                eids = []
                for q in finding.evidence:
                    offset = q.start
                    if offset is None:
                        offset = text.find(q.quote)
                        if offset < 0 or text.find(q.quote, offset + 1) >= 0:
                            raise ValueError('Daily quotation requires an exact, unambiguous source span')
                    if text[offset:offset+len(q.quote)] != q.quote:
                        raise ValueError('Daily quotation differs from captured text')
                    _translation(q.translation, q.language_tag, d['capture'], review.reviewed_at)
                    ep = dict(document_id=d['id'], source_text_sha256=d['text_sha256'],
                        quote_sha256=digest(q.quote.encode()), quote=q.quote, start=offset, end=offset+len(q.quote),
                        offset_basis='unicode_code_points_half_open', language_tag=q.language_tag,
                        translation=q.translation.model_dump(mode='json') if q.translation else None)
                    eid = uid('daily_evidence', ep); evidence[eid] = dict(id=eid, **ep); eids.append(eid)
                for place in finding.places:
                    if place.country_code is not None:
                        import pycountry
                        if pycountry.countries.get(alpha_2=place.country_code) is None:
                            raise ValueError('Unknown reporting country code')
                        codes.add(place.country_code)
                if finding.statement_kind == 'attributed_hypothesis' and finding.attribution.value is None:
                    raise ValueError('Attributed hypothesis requires its named source')
                payload = dict(**finding.model_dump(mode='json', exclude={'evidence'}), document_id=d['id'],
                    review_id=review_id, evidence_ids=sorted(set(eids)), reviewed_at=review.reviewed_at,
                    reviewed_by=review.reviewed_by, review_state=review.review_state)
                fid = uid('daily_finding', payload); findings.append(dict(id=fid, **payload)); ids.append(fid)
                lookup[d['id']+':'+finding.key] = findings[-1]
        channel_ids=channels.get(d['source_id'],[])
        channel_id=channel_ids[0] if len(channel_ids)==1 else None
        base_ids=sorted({ident for ch in channel_ids for ident in base_documents.get((ch,canonical_url(d['url']),publication_day(d['published_at'])),[])})
        base_ids=sorted(set(base_ids) | bindings.get(d['id'], set()))
        documents.append(dict(id=d['id'], source_id=d['source_id'], channel_id=channel_id, base_document_ids=base_ids,
            source_name=src['name'], source_role=src['role'],
            url=d['url'], content_url=d['content_url'], title=d['title'],
            title_translation=review.title_translation if review else None, language_tag=review.language_tag if review else 'und',
            publication=d['published_at'], publication_precision=d['publication_precision'], modified_at=d.get('modified_at'),
            capture=d['capture'], source_text_sha256=d['text_sha256'], raw_sha256=d['raw_sha256'], parse_status=d['parse_status'],
            review_id=review_id, review_state=review.review_state if review else 'not_reviewed',
            reviewed_at=review.reviewed_at if review else None, reviewed_by=review.reviewed_by if review else None,
            outcome=review.outcome if review else 'pending', processing_status='weekly_review_pending',
            finding_ids=ids, country_codes=sorted(codes),
            limitations=(review.limitations if review else ['Daily evidence review pending.'])+
                (['Publication date is not reported; select by capture date.'] if d['published_at'] is None else [])))
    index = {d['id']:d for d in documents}; assessments = []
    if len({w.key for w in ann.watch_assessments}) != len(ann.watch_assessments):
        raise ValueError('Duplicate daily watch key')
    assessed = {k for w in ann.watch_assessments for k in w.finding_keys}
    if assessed != lookup.keys():
        raise ValueError('Watch screening must account for every reviewed daily finding')
    for w in ann.watch_assessments:
        if len(set(w.finding_keys)) != len(w.finding_keys) or not set(w.finding_keys) <= lookup.keys():
            raise ValueError('Daily watch requires exact distinct finding references')
        support = [lookup[k] for k in w.finding_keys]
        for criterion in w.criteria:
            refs = [lookup[k] for k in criterion.finding_keys]
            if any(f['statement_kind'] == 'analyst_hypothesis' for f in refs):
                raise ValueError('Watch significance requires source evidence')
            if criterion.kind == 'time_sensitive_action' and not any(
                f['kind'] == 'response_measure' and f['statement_kind'] == 'source_statement'
                and f['attribution']['value'] is not None and f['status'] in {'reported','source_confirmed'} for f in refs):
                raise ValueError('Urgent watch needs an attributed source response measure')
        if any(stamp(w.reviewed_at) < stamp(f['reviewed_at']) for f in support):
            raise ValueError('Watch review precedes its supporting findings')
        dids = sorted({f['document_id'] for f in support})
        if w.date_basis == 'source_report_date' and w.development_date not in {
            publication_day(index[lookup[k]['document_id']]['publication']) for k in w.development_finding_keys}:
            raise ValueError('Watch report date differs from its supporting publication')
        attention = watch_decision(w)
        if attention != 'not_selected' and not w.key_facts:
            raise ValueError('Selected watch assessment needs concise supported facts')
        card_text = ' '.join([w.label, w.location_label, w.diagnostic_label, w.reason_for_attention]
                             + [f.label + ' ' + f.text for f in w.key_facts])
        if attention != 'not_selected' and len(card_text.split()) > 55:
            raise ValueError('Selected watch card exceeds its 55-word editorial budget')
        payload = w.model_dump(mode='json')
        payload['key_facts'] = [dict(**f.model_dump(mode='json'), finding_ids=[lookup[k]['id'] for k in f.finding_keys])
                                for f in w.key_facts]
        assessments.append(dict(id=uid('daily_watch', payload), **payload,
            attention=attention, method_version=WATCH_METHOD,
            finding_ids=[f['id'] for f in support], evidence_ids=sorted({e for f in support for e in f['evidence_ids']}),
            document_ids=dids, scope_kind='report_selection', event_identity='not_assigned',
            latest_publication=max((index[d]['publication'] for d in dids if index[d]['publication'] is not None),default=None),
            latest_capture=max(index[d]['capture'] for d in dids)))
    watches = sorted((w for w in assessments if w['attention'] != 'not_selected'),
        key=lambda w:({'urgent':0, 'heightened':1, 'watch':2}[w['attention']],
                      -date.fromisoformat(w['development_date']).toordinal(), w['key']))
    if ann.reconciliations:
        if not weekly_handoff or not weekly_handoff['weekly_ready'] or weekly_handoff['current_export']['export_id'] != source['source_export_id']:
            raise ValueError('Daily reconciliation requires the matching completed weekly handoff')
        from .handoff import file_reference, WeeklyReceipt
        receipts={}
        for job in ['review', 'production', 'inbox']:
            ref = weekly_handoff['jobs'][job]['receipt']
            if file_reference(Path(ref['path'])) != ref:
                raise ValueError('Weekly reconciliation receipt changed')
            receipt=WeeklyReceipt.model_validate(read_json(Path(ref['path'])))
            if receipt.status!='completed' or receipt.job!=job or receipt.cycle!=weekly_handoff['cycle'] or receipt.completed_at!=weekly_handoff['jobs'][job]['completed_at']:
                raise ValueError('Weekly reconciliation requires completed matching receipts')
            receipts[job]=receipt
        for job, predecessors in [('production',['review']),('inbox',['review','production'])]:
            for predecessor in predecessors:
                if receipts[job].dependencies.get(predecessor)!=weekly_handoff['jobs'][predecessor]['receipt']['sha256'] or stamp(receipts[job].completed_at)<stamp(receipts[predecessor].completed_at):
                    raise ValueError('Weekly reconciliation dependency differs')
        inbox=receipts['inbox']
        if (receipts['production'].export is None or inbox.export is None or inbox.unapplied_decision_ids
            or inbox.post_review_validation!='passed' or inbox.reviewed_export_id!=source['source_export_id']
            or inbox.ledger_head!=weekly_handoff['ledger']['head_hash']
            or inbox.export.export_id!=source['source_export_id']
            or inbox.export.manifest_sha256!=source['source_manifest_sha256']
            or inbox.export.map_snapshot_sha256!=source['map_snapshot_sha256']):
            raise ValueError('Weekly reconciliation export validation differs')
        review_docs = {d['review_id']:d for d in documents if d['review_id']}
        records = {r['id']:r for r in site['records']}
        scientific_docs = {d['id']:d for d in site['documents']}
        if len({r.review_id for r in ann.reconciliations}) != len(ann.reconciliations):
            raise ValueError('Duplicate daily reconciliation')
        for r in ann.reconciliations:
            if r.review_id not in review_docs or r.weekly_export_id != source['source_export_id'] or r.weekly_inbox_sha256 != weekly_handoff['jobs']['inbox']['receipt']['sha256']:
                raise ValueError('Daily reconciliation differs from the reviewed version or weekly release')
            doc = review_docs[r.review_id]
            if stamp(r.reviewed_at) < stamp(reviews[doc['id']].reviewed_at) or stamp(r.reviewed_at) < stamp(weekly_handoff['jobs']['inbox']['completed_at']):
                raise ValueError('Reconciliation precedes required review')
            if r.disposition == 'integrated':
                if not r.record_ids or len(set(r.record_ids)) != len(r.record_ids):
                    raise ValueError('Integrated daily review requires distinct weekly records')
                for rid in r.record_ids:
                    if rid not in records or records[rid]['document_id'] != doc['id'] or scientific_docs[doc['id']]['text_sha256'] != doc['source_text_sha256']:
                        raise ValueError('Reconciliation records differ from the captured document')
            elif r.record_ids:
                raise ValueError('Only an integrated review can name weekly records')
            if r.disposition != 'pending':doc['processing_status'] = 'weekly_reviewed'
    checks = {s['source_id']:s for s in acquisition['sources']}
    coverage = []
    for sid, src in sources.items():
        selected = [d for d in documents if d['source_id'] == sid]; check = checks.get(sid, {})
        status=check.get('status','not_checked')
        notes=list(check.get('notes',['Source was not checked in this run.']))
        checked_at=stamp(check['checked_at']) if check.get('checked_at') else None
        if checked_at and checked_at>cutoff:
            raise ValueError('Source check follows acquisition cutoff')
        if status=='disabled' and src.get('enabled'):
            status='not_checked';checked_at=None
            notes.append('Source is enabled in this configuration and was not checked in this acquisition.')
        coverage.append(dict(source_id=sid, source_name=src['name'], source_role=src['role'],
            status=status, notes=notes, checked_at=checked_at, documents=len(selected),
            reviewed=sum(d['review_id'] is not None for d in selected), relevant=sum(d['outcome']=='relevant' for d in selected),
            pending=sum(d['outcome'] in {'pending','needs_review'} for d in selected)))
    payload = dict(daily_version='0.2.1' if _legacy else VERSION, software_version=__version__,
        base_source_export_id=source['source_export_id'], base_site_sha256=source['source_site_sha256'],
        base_manifest_sha256=source['source_manifest_sha256'], base_map_snapshot_sha256=source['map_snapshot_sha256'],
        acquisition_sha256=digest(acquisition), annotations_sha256=digest(annotation_payload(ann)),
        publication_from=start, publication_until=end,
        knowledge_cutoff=max([cutoff]+[stamp(r.reviewed_at) for r in [*ann.reviews,*ann.watch_assessments,*ann.reconciliations]]),
        timezone='Europe/Amsterdam',
        selection_policy='all_supporting_documents_in_window', documents=documents,
        evidence=sorted(evidence.values(),key=lambda e:e['id']), findings=findings, watch_items=watches,
        watch_assessments=assessments,
        reconciliations=ann.reconciliations, source_coverage=coverage)
    model = LegacyDailyExport if _legacy else DailyExport
    result = model.model_validate(dict(daily_id='0'*64, generated_at=utcnow(), **payload)).model_dump(mode='json')
    result['daily_id'] = digest({k:v for k,v in result.items() if k not in {'daily_id','generated_at'}})
    return result


def export_daily(state, config, acquisition_path, annotations_path, bundle, snapshot, out, weekly_handoff=None):
    if out.exists() and any(out.iterdir()):raise ValueError('Daily export target must be empty')
    if annotations_path.stat().st_size > 16_000_000:raise ValueError('Daily annotations exceed 16 MB')
    site, source = _source(bundle,snapshot)
    acquisition = read_json(acquisition_path)
    rows = read_documents(state, acquisition['completed_at'])
    selected = acquired_documents(rows,acquisition)
    _,exclusions=dated_annotations(rows,read_json(annotations_path),acquisition)
    write_json(state/'review'/'publication-exclusions'/(digest(exclusions)+'.json'),exclusions)
    texts = {d['id']:(state/d['text_object']).read_text() for d in selected}
    data = prepare_daily(rows,texts,read_json(annotations_path),config,acquisition,site,source,
        read_json(weekly_handoff) if weekly_handoff else None)
    write_json(out/'daily.json',data);write_json(out/'daily.schema.json',DailyExport.model_json_schema())
    (out/'daily-view.mjs').write_text(files('atlas').joinpath('assets/daily_view.js').read_text())
    receipt = dict(status='valid',daily_id=data['daily_id'],base_source_export_id=data['base_source_export_id'],
        documents=len(data['documents']),findings=len(data['findings']),watch_items=len(data['watch_items']),
        weekly_review_pending=sum(d['processing_status']=='weekly_review_pending' for d in data['documents']))
    write_json(out/'validation.json',receipt)
    write_json(out/'manifest.json',dict(daily_version=VERSION,daily_id=data['daily_id'],base_source_export_id=data['base_source_export_id'],
        files={p.name:dict(sha256=digest(p.read_bytes()),bytes=p.stat().st_size) for p in sorted(out.iterdir())}))
    return receipt


def verify_daily(path, state, config, acquisition_path, annotations_path, bundle, snapshot, weekly_handoff=None):
    manifest = read_json(path/'manifest.json')
    names = {'daily.json','daily.schema.json','daily-view.mjs','validation.json'}
    version=manifest.get('daily_version')
    if version not in {'0.2.1',VERSION} or set(manifest['files']) != names:
        raise ValueError('Unsupported daily manifest')
    for name, expected in manifest['files'].items():
        raw = (path/name).read_bytes()
        if len(raw) != expected['bytes'] or digest(raw) != expected['sha256']:
            raise ValueError('Daily asset differs: '+name)
    schema=(json.loads(files('atlas').joinpath('assets/daily_schema_v0_2_1.json').read_text())
            if version=='0.2.1' else DailyExport.model_json_schema())
    if read_json(path/'daily.schema.json') != schema:raise ValueError('Unsupported daily schema')
    selector='daily_view_v0_2_1.js' if version=='0.2.1' else 'daily_view.js'
    if (path/'daily-view.mjs').read_bytes() != files('atlas').joinpath('assets',selector).read_bytes():
        raise ValueError('Unsupported daily selector')
    model = LegacyDailyExport if version=='0.2.1' else DailyExport
    data = model.model_validate(read_json(path/'daily.json')).model_dump(mode='json')
    if data['daily_version']!=version:raise ValueError('Daily contract differs from manifest')
    stamp(data['generated_at'])
    site, source = _source(bundle,snapshot); acquisition = read_json(acquisition_path)
    rows = read_documents(state,acquisition['completed_at'])
    chosen = acquired_documents(rows,acquisition,_legacy=version=='0.2.1')
    texts = {d['id']:(state/d['text_object']).read_text() for d in chosen}
    for d in chosen:
        if digest((state/d['raw_object']).read_bytes()) != d['raw_sha256']:
            raise ValueError('Daily raw source object differs')
    expected = prepare_daily(rows,texts,read_json(annotations_path),config,acquisition,site,source,
        read_json(weekly_handoff) if weekly_handoff else None,_legacy=version=='0.2.1')
    expected.update(generated_at=data['generated_at'],software_version=data['software_version'])
    expected['daily_id'] = digest({k:v for k,v in expected.items() if k not in {'daily_id','generated_at'}})
    if data != expected or manifest['daily_id'] != data['daily_id'] or manifest['base_source_export_id'] != data['base_source_export_id']:
        raise ValueError('Daily export differs from captured evidence or review')
    receipt = dict(status='valid',daily_id=data['daily_id'],base_source_export_id=data['base_source_export_id'],
        documents=len(data['documents']),findings=len(data['findings']),watch_items=len(data['watch_items']),
        weekly_review_pending=sum(d['processing_status']=='weekly_review_pending' for d in data['documents']))
    if receipt != read_json(path/'validation.json'):raise ValueError('Daily receipt differs')
    return receipt
