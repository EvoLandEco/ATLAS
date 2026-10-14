"""Explicit report selections for source evidence follow-up."""
from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import Field

from . import __version__
from .models import StrictModel, TextValue
from .site_export import Eligibility
from .source_text import Hash, _source
from .util import digest, read_json, stamp, uid, utcnow, write_json


class WatchReview(StrictModel):
    key: str = Field(min_length=1)
    record_id: str
    label: str = Field(min_length=1, max_length=160)
    reason_for_attention: str = Field(min_length=12)
    follow_up_question: str = Field(min_length=12)
    assertion_ids: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    diagnostic_assessment_id: str | None
    source_text_hashes: dict[str, Hash]
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)
    review_state: Literal['source_checked_draft'] = 'source_checked_draft'


class WatchAnnotations(StrictModel):
    watch_version: Literal['0.1.0']
    review_scope: str = Field(min_length=12)
    limitations: list[str] = Field(min_length=1)
    reviews: list[WatchReview]


class WatchSource(StrictModel):
    document_id: str
    record_ids: list[str]
    title: str
    url: str
    channel_id: str
    publication: str
    publication_precision: str
    publication_basis: str
    capture: str


class WatchItem(WatchReview):
    id: str
    scope_kind: Literal['single_report']
    selection_status: Literal['selected']
    event_identity: Literal['not_assigned']
    diagnostic_status: TextValue
    diagnostic_label: str | None
    diagnostic_authority: TextValue
    record_ids: list[str]
    document_ids: list[str]
    eligibility: Eligibility
    sources: list[WatchSource]
    latest_publication: str
    latest_capture: str


class WatchExport(StrictModel):
    watch_version: Literal['0.1.0']
    software_version: str
    generated_at: str
    source_export_id: Hash
    source_site_sha256: Hash
    source_manifest_sha256: Hash
    map_snapshot_sha256: Hash
    annotations_sha256: Hash
    review_scope: str
    limitations: list[str]
    selection_policy: Literal['all_supporting_records_and_review_cutoff']
    ordering: Literal['review_input_order_no_risk_rank']
    items: list[WatchItem]


def prepare_watch(site, annotations, source):
    ann = WatchAnnotations.model_validate(annotations)
    if len({r.key for r in ann.reviews}) != len(ann.reviews) or len({r.record_id for r in ann.reviews}) != len(ann.reviews):
        raise ValueError('Duplicate watch selection')
    records = {r['id']:r for r in site['records']}
    documents = {d['id']:d for d in site['documents']}
    assertions = {a['id']:a for a in site['assertions']}
    evidence = {e['id']:e for e in site['evidence']}
    assessments = {a['id']:a for a in site['report_assessments']}
    items = []
    for review in ann.reviews:
        clock = stamp(review.reviewed_at)
        if review.record_id not in records:
            raise ValueError('Watch report is absent')
        support = {review.record_id}
        required_evidence = set()
        for name, ids, index in [('assertion', review.assertion_ids, assertions), ('evidence', review.evidence_ids, evidence)]:
            if len(ids) != len(set(ids)) or not set(ids) <= index.keys():
                raise ValueError('Invalid watch ' + name + ' references')
        if not any(assertions[a]['record_id'] == review.record_id for a in review.assertion_ids):
            raise ValueError('Watch selection requires an assertion from its report')
        for aid in review.assertion_ids:
            support.update(assertions[aid]['eligibility']['record_ids'])
            required_evidence.update(assertions[aid]['evidence_ids'])
        status = dict(value=None, status='not_extracted')
        authority, label = status, None
        if review.diagnostic_assessment_id is not None:
            assessment = assessments.get(review.diagnostic_assessment_id)
            if not assessment or assessment['kind'] != 'diagnostic_status' or assessment['record_id'] != review.record_id:
                raise ValueError('Watch diagnostic assessment has a different report scope')
            if not set(assessment['assertion_ids']) <= set(review.assertion_ids):
                raise ValueError('Watch diagnosis requires its exact assertions')
            if clock < stamp(assessment['reviewed_at']):
                raise ValueError('Watch review precedes its diagnostic assessment')
            if any(assessment['id'] in a['supersedes'] for a in assessments.values()):
                raise ValueError('Watch diagnosis has a superseding assessment')
            support.update(assessment['eligibility']['record_ids'])
            required_evidence.update(assessment['evidence_ids'])
            status = dict(value=assessment['status'], status='reported')
            authority, label = assessment['authority'], assessment['label']
        if not required_evidence <= set(review.evidence_ids):
            raise ValueError('Watch evidence omits assertion or diagnostic support')
        support.update(evidence[e]['record_id'] for e in review.evidence_ids)
        dids = sorted({records[r]['document_id'] for r in support})
        if review.source_text_hashes != {did:documents[did]['text_sha256'] for did in dids}:
            raise ValueError('Watch source dependencies differ')
        if any(clock < stamp(records[r]['capture']) for r in support):
            raise ValueError('Watch review precedes source capture')
        sources = [dict(document_id=did, record_ids=sorted(r for r in support if records[r]['document_id']==did),
            **{k:documents[did][k] for k in ['title','url','channel_id','publication','publication_precision','publication_basis','capture']}) for did in dids]
        payload = review.model_dump(mode='json')
        items.append(dict(**payload, id=uid('watch', payload), scope_kind='single_report',
            selection_status='selected', event_identity='not_assigned', diagnostic_status=status,
            diagnostic_label=label, diagnostic_authority=authority, record_ids=sorted(support), document_ids=dids,
            eligibility=Eligibility(record_ids=sorted(support)).model_dump(), sources=sources,
            latest_publication=max(s['publication'] for s in sources), latest_capture=max(s['capture'] for s in sources)))
    return WatchExport.model_validate(dict(watch_version='0.1.0', software_version=__version__, generated_at=utcnow(),
        **source, annotations_sha256=digest(ann.model_dump(mode='json')), review_scope=ann.review_scope,
        limitations=ann.limitations, selection_policy='all_supporting_records_and_review_cutoff',
        ordering='review_input_order_no_risk_rank', items=items)).model_dump(mode='json')


def validate_watch(data, site, source):
    parsed = WatchExport.model_validate(data)
    stamp(parsed.generated_at)
    if any(data[k] != v for k,v in source.items()):
        raise ValueError('Watch export refers to a different scientific export')
    annotations = dict(watch_version='0.1.0', review_scope=parsed.review_scope, limitations=parsed.limitations,
        reviews=[{k:row[k] for k in WatchReview.model_fields} for row in data['items']])
    expected = prepare_watch(site, annotations, source)
    if data['items'] != expected['items'] or data['annotations_sha256'] != expected['annotations_sha256']:
        raise ValueError('Watch selection differs from source evidence or review')
    return dict(status='valid', source_export_id=parsed.source_export_id, items=len(parsed.items))


def export_watch(bundle: Path, snapshot: Path, annotations: Path, out: Path):
    if out.exists() and any(out.iterdir()):
        raise ValueError('Watch export target must be empty')
    if annotations.stat().st_size > 1_000_000:
        raise ValueError('Watch annotations exceed the 1 MB input budget')
    site, source = _source(bundle, snapshot)
    data = prepare_watch(site, read_json(annotations), source)
    receipt = validate_watch(data, site, source)
    write_json(out/'watch.json', data)
    write_json(out/'watch.schema.json', WatchExport.model_json_schema())
    write_json(out/'annotations.schema.json', WatchAnnotations.model_json_schema())
    write_json(out/'validation.json', receipt)
    (out/'watch-view.mjs').write_text(files('atlas').joinpath('assets/watch_view.js').read_text())
    write_json(out/'manifest.json', dict(watch_version='0.1.0', source_export_id=source['source_export_id'],
        files={p.name:dict(sha256=digest(p.read_bytes()), bytes=p.stat().st_size) for p in sorted(out.iterdir())}))
    return receipt


def verify_watch(path: Path, bundle: Path, snapshot: Path):
    manifest = read_json(path/'manifest.json')
    names = {'watch.json','watch.schema.json','annotations.schema.json','validation.json','watch-view.mjs'}
    if manifest.get('watch_version') != '0.1.0' or set(manifest['files']) != names:
        raise ValueError('Unsupported watch export')
    for name, ref in manifest['files'].items():
        raw = (path/name).read_bytes()
        if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
            raise ValueError('Watch export checksum mismatch: ' + name)
    for name, model in [('watch.schema.json',WatchExport),('annotations.schema.json',WatchAnnotations)]:
        if read_json(path/name) != model.model_json_schema():
            raise ValueError('Unsupported watch schema')
    if (path/'watch-view.mjs').read_bytes() != files('atlas').joinpath('assets/watch_view.js').read_bytes():
        raise ValueError('Unsupported watch selection rules')
    site, source = _source(bundle, snapshot)
    result = validate_watch(read_json(path/'watch.json'), site, source)
    if manifest['source_export_id'] != source['source_export_id'] or read_json(path/'validation.json') != result:
        raise ValueError('Watch export receipt differs')
    return result
