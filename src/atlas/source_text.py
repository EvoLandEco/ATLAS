"""English presentation bound to original titles and captured quotations."""
from copy import deepcopy
from pathlib import Path
from typing import Annotated, Literal

import pycountry
from pydantic import Field, model_validator

from . import __version__
from .models import StrictModel
from .util import digest, read_json, stamp, uid, utcnow, write_json

VERSION = '0.1.0'
Hash = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]


class Translation(StrictModel):
    text: str = Field(min_length=1)
    language_tag: Literal['en'] = 'en'
    origin: Literal['atlas_generated', 'publisher_provided']
    created_at: str
    created_by: str = Field(min_length=1)
    method_version: str = Field(min_length=1)
    review_status: Literal['unreviewed', 'source_checked', 'human_approved']
    reviewed_at: str | None
    reviewed_by: str | None
    review_note: str = Field(min_length=1)
    publisher_text_id: str | None = None
    pairing_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def provenance(self):
        stamp(self.created_at)
        if not self.text.strip():
            raise ValueError('Translation text is empty')
        if self.review_status == 'unreviewed':
            if self.reviewed_at is not None or self.reviewed_by is not None:
                raise ValueError('Unreviewed translation cannot carry a completed review')
        elif not self.reviewed_by or not self.reviewed_at or stamp(self.reviewed_at) < stamp(self.created_at):
            raise ValueError('Translation review requires a reviewer and a time after creation')
        if self.origin == 'publisher_provided':
            if not self.publisher_text_id or not self.pairing_evidence_ids or self.review_status == 'unreviewed':
                raise ValueError('Publisher translation requires reviewed source text and pairing evidence')
        elif self.publisher_text_id is not None or self.pairing_evidence_ids:
            raise ValueError('ATLAS translation cannot claim publisher provenance')
        return self


class TextReview(StrictModel):
    text_id: str
    language_tag: str = Field(pattern=r'^[a-z]{2,3}$')
    language_basis: Literal['text_review', 'publisher_metadata', 'unresolved']
    language_note: str = Field(min_length=1)
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)
    translation: Translation | None = None

    @model_validator(mode='after')
    def language(self):
        stamp(self.reviewed_at)
        if self.language_tag not in {'und', 'mul'} and pycountry.languages.get(**{
                'alpha_2' if len(self.language_tag) == 2 else 'alpha_3': self.language_tag}) is None:
            raise ValueError('Unknown language tag')
        if (self.language_tag == 'und') != (self.language_basis == 'unresolved'):
            raise ValueError('Undetermined language requires an unresolved review')
        if self.translation is not None and self.language_tag in {'en', 'eng', 'und'}:
            raise ValueError('English translation requires an identified non-English original')
        return self


class TextAnnotations(StrictModel):
    text_version: Literal['0.1.0']
    reviews: list[TextReview]


class OriginalText(StrictModel):
    id: str
    kind: Literal['document_title', 'record_title', 'evidence']
    target_ids: list[str] = Field(min_length=1)
    document_id: str
    source_text_sha256: Hash
    original_text_sha256: Hash
    start: int | None
    end: int | None


class PresentedText(OriginalText):
    language_tag: str
    language_status: Literal['reviewed', 'unresolved', 'not_reviewed']
    language_basis: Literal['text_review', 'publisher_metadata', 'unresolved', 'not_reviewed']
    language_note: str
    reviewed_at: str | None
    reviewed_by: str | None
    translation_status: Literal['available', 'pending', 'not_required', 'language_unresolved']
    english_translation_id: str | None


class BoundTranslation(Translation):
    id: str
    original_text_id: str


class TextPresentation(StrictModel):
    text_version: Literal['0.1.0']
    software_version: str
    generated_at: str
    source_export_id: Hash
    source_site_sha256: Hash
    source_manifest_sha256: Hash
    map_snapshot_sha256: Hash
    annotations_sha256: Hash
    selection_policy: Literal['attach_to_selected_original_only']
    texts: list[PresentedText]
    translations: list[BoundTranslation]
    coverage: dict[str, int]


def text_catalog(site):
    """Group exact source spans while retaining every scientific evidence identity."""
    documents = {d['id']: d for d in site['documents']}
    rows, originals = {}, {}

    def add(kind, target, did, text, start=None, end=None):
        sha = digest(text.encode('utf-8'))
        source_sha = documents[did]['text_sha256']
        identity = uid('text', kind, did, source_sha, sha, start, end)
        if identity not in rows:
            rows[identity] = dict(id=identity, kind=kind, target_ids=[], document_id=did,
                source_text_sha256=source_sha, original_text_sha256=sha, start=start, end=end)
            originals[identity] = text
        rows[identity]['target_ids'].append(target)

    for d in site['documents']:
        add('document_title', d['id'], d['id'], d['title'])
    for r in site['records']:
        add('record_title', r['id'], r['document_id'], r['title'])
    for e in site['evidence']:
        add('evidence', e['id'], e['document_id'], e['quote'], e['start'], e['end'])
    for r in rows.values():
        r['target_ids'].sort()
    return [rows[k] for k in sorted(rows)], originals


def reuse_daily_reviews(site, annotations, daily_reviews, daily_documents):
    """Reuse exact daily text reviews while preserving completed translations."""
    parsed = TextAnnotations.model_validate(annotations)
    reviews = {r['text_id']: deepcopy(r) for r in annotations['reviews']}
    if len(reviews) != len(parsed.reviews):
        raise ValueError('Duplicate text review')
    daily = {r['document_id']: r for r in daily_reviews}
    documents = {d['id']: d for d in daily_documents}
    if len(daily) != len(daily_reviews) or len(documents) != len(daily_documents):
        raise ValueError('Duplicate daily document or review')
    rows, originals = text_catalog(site)
    reused = []
    for row in rows:
        old = reviews.get(row['id'])
        if old and old.get('translation') is not None:
            continue
        daily_review = daily.get(row['document_id'])
        if not daily_review or daily_review['source_text_sha256'] != row['source_text_sha256']:
            continue
        original, binding = originals[row['id']], None
        if row['kind'] == 'document_title' and original == documents.get(row['document_id'], {}).get('title'):
            binding = dict(language_tag=daily_review['language_tag'], translation=daily_review['title_translation'])
        elif row['kind'] == 'evidence':
            matches = [e for f in daily_review['findings'] for e in f['evidence']
                       if e['quote'] == original and e['start'] == row['start']
                       and e['start'] + len(e['quote']) == row['end']]
            if matches:
                binding = {k: matches[0][k] for k in ('language_tag', 'translation')}
                if any({k: e[k] for k in binding} != binding for e in matches):
                    raise ValueError('Conflicting daily text reviews')
        if not binding or (old and binding['translation'] is None):
            continue
        if old and old['language_tag'] not in {'und', binding['language_tag']}:
            raise ValueError('Daily and retained text language reviews disagree')
        if old and old['language_tag'] != 'und':
            reviews[row['id']] = dict(old, translation=binding['translation'])
        else:
            reviews[row['id']] = dict(text_id=row['id'], **binding,
                language_basis='unresolved' if binding['language_tag'] == 'und' else 'text_review',
                language_note='Exact source hash, original text and quotation offsets match the daily review.',
                reviewed_at=daily_review['reviewed_at'], reviewed_by=daily_review['reviewed_by'])
        reused.append(dict(text_id=row['id'], kind=row['kind'], document_id=row['document_id'],
                           daily_review_sha256=digest(daily_review), translation_available=binding['translation'] is not None))
    result = dict(text_version=parsed.text_version, reviews=list(reviews.values()))
    TextAnnotations.model_validate(result)
    return result, reused


def prepare_text(site, annotations, source):
    annotations = TextAnnotations.model_validate(annotations)
    annotations.reviews.sort(key=lambda r: r.text_id)
    rows, originals = text_catalog(site)
    catalog = {r['id']: r for r in rows}
    reviews = {r.text_id: r for r in annotations.reviews}
    if len(reviews) != len(annotations.reviews) or not reviews.keys() <= catalog.keys():
        raise ValueError('Duplicate or stale text review')
    documents = {d['id']: d for d in site['documents']}
    organizations = {c['id']: c['organization_id'] for c in site['channels']}
    evidence = {e['id']: e for e in site['evidence']}
    translations, coverage = [], dict(available=0, pending=0, not_required=0, language_unresolved=0)
    for row in rows:
        review = reviews.get(row['id'])
        row.update(language_tag='und', language_status='not_reviewed', language_basis='not_reviewed',
            language_note='Language has not been reviewed for this exact text.', reviewed_at=None,
            reviewed_by=None, translation_status='language_unresolved', english_translation_id=None)
        if review:
            if stamp(review.reviewed_at) < stamp(documents[row['document_id']]['capture']):
                raise ValueError('Language review precedes capture')
            row.update(review.model_dump(exclude={'text_id', 'translation'}))
            row['language_status'] = 'unresolved' if review.language_tag == 'und' else 'reviewed'
            row['translation_status'] = ('language_unresolved' if review.language_tag == 'und' else
                'not_required' if review.language_tag in {'en', 'eng'} else 'pending')
            if review.translation:
                tr = review.translation
                if stamp(tr.created_at) < stamp(documents[row['document_id']]['capture']):
                    raise ValueError('Translation precedes capture')
                if tr.origin == 'publisher_provided':
                    other = catalog.get(tr.publisher_text_id)
                    english = reviews.get(tr.publisher_text_id)
                    if (not other or not english or english.language_tag not in {'en', 'eng'}
                            or other['kind'] != row['kind'] or originals[other['id']] != tr.text):
                        raise ValueError('Publisher translation differs from its captured English text')
                    publisher = lambda r: organizations[documents[r['document_id']]['channel_id']]
                    if publisher(other) != publisher(row):
                        raise ValueError('Publisher translation requires the same publisher')
                    if (len(set(tr.pairing_evidence_ids)) != len(tr.pairing_evidence_ids)
                            or any(e not in evidence for e in tr.pairing_evidence_ids)):
                        raise ValueError('Translation pairing evidence is absent or duplicated')
                    support = [other['document_id']] + [evidence[e]['document_id'] for e in tr.pairing_evidence_ids]
                    if any(stamp(tr.reviewed_at) < stamp(documents[d]['capture']) for d in support):
                        raise ValueError('Publisher pairing review precedes supporting capture')
                payload = dict(original_text_id=row['id'], **tr.model_dump(mode='json'))
                tid = uid('translation', payload)
                translations.append(dict(id=tid, **payload))
                row.update(translation_status='available', english_translation_id=tid)
        coverage[row['translation_status']] += 1
    coverage.update(texts=len(rows), translations=len(translations),
        evidence_bindings=sum(len(r['target_ids']) for r in rows if r['kind'] == 'evidence'),
        title_bindings=sum(len(r['target_ids']) for r in rows if r['kind'] != 'evidence'))
    return TextPresentation.model_validate(dict(text_version=VERSION, software_version=__version__,
        generated_at=utcnow(), **source, annotations_sha256=digest(annotations.model_dump(mode='json')),
        selection_policy='attach_to_selected_original_only', texts=rows,
        translations=translations, coverage=coverage)).model_dump(mode='json')


def validate_text(data, site, source):
    """Rebuild all bindings, review states and coverage from the original export."""
    parsed = TextPresentation.model_validate(data)
    stamp(parsed.generated_at)
    if any(data[k] != value for k, value in source.items()):
        raise ValueError('Text presentation refers to a different scientific export')
    translations = {t.id: t for t in parsed.translations}
    if len(translations) != len(parsed.translations):
        raise ValueError('Duplicate translation identity')
    reviews = []
    for row in parsed.texts:
        if row.language_status == 'not_reviewed':
            continue
        tr = translations.get(row.english_translation_id)
        if row.english_translation_id and (not tr or tr.original_text_id != row.id):
            raise ValueError('Original and translation binding differs')
        reviews.append(dict(text_id=row.id, language_tag=row.language_tag, language_basis=row.language_basis,
            language_note=row.language_note, reviewed_at=row.reviewed_at, reviewed_by=row.reviewed_by,
            translation=tr.model_dump(exclude={'id', 'original_text_id'}) if tr else None))
    expected = prepare_text(site, dict(text_version=VERSION, reviews=reviews), source)
    for name in ('texts', 'translations', 'coverage', 'annotations_sha256'):
        if data[name] != expected[name]:
            raise ValueError('Text presentation differs from original evidence or review: ' + name)
    return dict(status='valid', source_export_id=parsed.source_export_id, **parsed.coverage)


def _source(bundle, snapshot):
    from .handoff import inspect_export
    ref = inspect_export(bundle, snapshot)
    return read_json(bundle / 'atlas-site.json'), dict(source_export_id=ref['export_id'],
        source_site_sha256=ref['structured_data']['sha256'], source_manifest_sha256=ref['manifest_sha256'],
        map_snapshot_sha256=ref['map_snapshot_sha256'])


def export_text(bundle: Path, snapshot: Path, annotations: Path, out: Path):
    if out.exists() and any(out.iterdir()):
        raise ValueError('Text export target must be empty')
    if annotations.stat().st_size > 16_000_000:
        raise ValueError('Text annotations exceed the 16 MB input budget')
    site, source = _source(bundle, snapshot)
    data = prepare_text(site, read_json(annotations), source)
    receipt = validate_text(data, site, source)
    write_json(out / 'source-text.json', data)
    write_json(out / 'source-text.schema.json', TextPresentation.model_json_schema())
    write_json(out / 'annotations.schema.json', TextAnnotations.model_json_schema())
    write_json(out / 'validation.json', receipt)
    write_json(out / 'manifest.json', dict(text_version=VERSION, source_export_id=source['source_export_id'],
        files={p.name: dict(sha256=digest(p.read_bytes()), bytes=p.stat().st_size) for p in sorted(out.iterdir())}))
    return receipt


def verify_text(path: Path, bundle: Path, snapshot: Path):
    manifest = read_json(path / 'manifest.json')
    names = {'source-text.json', 'source-text.schema.json', 'annotations.schema.json', 'validation.json'}
    if manifest.get('text_version') != VERSION or set(manifest['files']) != names:
        raise ValueError('Unsupported text export')
    for name, ref in manifest['files'].items():
        p = path / name
        if p.stat().st_size != ref['bytes'] or digest(p.read_bytes()) != ref['sha256']:
            raise ValueError('Text export checksum mismatch: ' + name)
    for name, model in [('source-text.schema.json', TextPresentation), ('annotations.schema.json', TextAnnotations)]:
        if read_json(path / name) != model.model_json_schema():
            raise ValueError('Unsupported text schema')
    site, source = _source(bundle, snapshot)
    if manifest['source_export_id'] != source['source_export_id']:
        raise ValueError('Text manifest refers to a different scientific export')
    result = validate_text(read_json(path / 'source-text.json'), site, source)
    if result != read_json(path / 'validation.json'):
        raise ValueError('Text validation receipt differs')
    return result


class ClaimTextBinding(StrictModel):
    record_id: str
    claim_index: int = Field(ge=0)
    quote_index: int = Field(ge=0)
    text_id: str | None
    evidence_ids: list[str] = Field(min_length=1)
    status: Literal['bound', 'ambiguous_source_spans']


class TextDisplay(StrictModel):
    display_version: Literal['0.1.0', '0.1.1']
    source_text_version: Literal['0.1.0']
    source_export_id: Hash
    source_text_sha256: Hash
    selection_policy: Literal['attach_to_selected_original_only']
    catalogue_scope: Literal['site_document_titles_record_titles_and_evidence']
    omission_rule: Literal['only_language_status_not_reviewed']
    omitted_text_count: int = Field(ge=0)
    unlisted_language_tag: Literal['und']
    unlisted_language_status: Literal['not_reviewed']
    unlisted_translation_status: Literal['language_unresolved']
    unlisted_reason: Literal['Language has not been reviewed for this exact text.']
    unmapped_scopes: list[Literal['embedded_series_method_evidence', 'undated_supplement']]
    texts: list[PresentedText]
    translations: list[BoundTranslation]
    claim_bindings: list[ClaimTextBinding]
    full_coverage: dict[str, int]


def text_display_schema(version='0.1.1'):
    if version not in {'0.1.0', '0.1.1'}:
        raise ValueError('Unsupported text display version')
    schema = TextDisplay.model_json_schema()
    schema['properties']['display_version'].pop('enum')
    schema['properties']['display_version']['const'] = version
    return schema


def project_text(data, source_sha256, site, snapshot=None):
    """Retain complete reviewed rows and every translation for display."""
    full = TextPresentation.model_validate(data)
    if {d['id']:d['text_sha256'] for d in site['documents']} != {
            r.document_id:r.source_text_sha256 for r in full.texts}:
        raise ValueError('Text display source documents differ')
    known = {r.id for r in full.texts if r.language_status != 'not_reviewed'}
    text_ids = {eid:r.id for r in full.texts if r.kind == 'evidence' for eid in r.target_ids}
    evidence = {e['id']: e for e in site['evidence']}
    record_documents = {r['id']: r['document_id'] for r in site['records']}
    quotations = {(r['id'], c['claim_index'], qi): q
                  for r in snapshot['records'] for c in r['claims'] for qi, q in enumerate(c['quotes'])} if snapshot is not None else None
    claims = {}
    for e in site['evidence']:
        if e['claim_index'] is not None and e['quote_index'] is not None:
            claims.setdefault((e['record_id'],e['claim_index'],e['quote_index']),[]).append(e['id'])
    bindings = []
    for key, ids in sorted(claims.items()):
        if quotations is not None:
            if key not in quotations:
                raise ValueError('Claim quotation is absent from the bound snapshot')
            if any(evidence[e]['document_id'] != record_documents[key[0]] for e in ids):
                raise ValueError('Claim evidence belongs to a different document')
            exact = [e for e in ids if evidence[e]['quote'] == quotations[key]]
            if len({text_ids[e] for e in exact}) == 1:
                ids = exact
        tids = {text_ids[e] for e in ids}
        if not tids & known:
            continue
        bindings.append(dict(record_id=key[0], claim_index=key[1], quote_index=key[2],
            text_id=next(iter(tids)) if len(tids)==1 else None, evidence_ids=sorted(ids),
            status='bound' if len(tids)==1 else 'ambiguous_source_spans'))
    return TextDisplay.model_validate(dict(display_version='0.1.0' if snapshot is None else '0.1.1', source_text_version=full.text_version,
        source_export_id=full.source_export_id, source_text_sha256=source_sha256,
        selection_policy=full.selection_policy, catalogue_scope='site_document_titles_record_titles_and_evidence',
        omission_rule='only_language_status_not_reviewed',
        omitted_text_count=sum(r.language_status == 'not_reviewed' for r in full.texts),
        unlisted_language_tag='und', unlisted_language_status='not_reviewed',
        unlisted_translation_status='language_unresolved',
        unlisted_reason='Language has not been reviewed for this exact text.',
        unmapped_scopes=['embedded_series_method_evidence','undated_supplement'], claim_bindings=bindings,
        texts=[r for r in full.texts if r.language_status != 'not_reviewed'],
        translations=full.translations, full_coverage=full.coverage)).model_dump(mode='json')


def validate_text_display(data, full, source_sha256, site, snapshot=None):
    TextDisplay.model_validate(data)
    if data['display_version'] == '0.1.1' and snapshot is None:
        raise ValueError('Text display 0.1.1 requires its bound snapshot')
    if data != project_text(full, source_sha256, site, snapshot if data['display_version'] == '0.1.1' else None):
        raise ValueError('Text display differs from its complete presentation export')
    return dict(status='valid', source_export_id=data['source_export_id'],
        source_text_sha256=source_sha256, retained_texts=len(data['texts']),
        translations=len(data['translations']), omitted_texts=data['omitted_text_count'],
        claim_bindings=len(data['claim_bindings']))


def export_text_display(presentation: Path, bundle: Path, snapshot: Path, out: Path):
    if out.exists() and any(out.iterdir()):
        raise ValueError('Text display target must be empty')
    verify_text(presentation, bundle, snapshot)
    path = presentation / 'source-text.json'
    full = read_json(path)
    site = read_json(bundle / 'atlas-site.json')
    source_snapshot = read_json(snapshot)
    data = project_text(full, digest(path.read_bytes()), site, source_snapshot)
    receipt = validate_text_display(data, full, digest(path.read_bytes()), site, source_snapshot)
    write_json(out / 'source-text-display.json', data)
    write_json(out / 'source-text-display.schema.json', text_display_schema())
    write_json(out / 'validation.json', receipt)
    write_json(out / 'manifest.json', dict(display_version=data['display_version'], source_export_id=data['source_export_id'],
        files={p.name: dict(sha256=digest(p.read_bytes()), bytes=p.stat().st_size) for p in sorted(out.iterdir())}))
    return receipt


def verify_text_display(display: Path, presentation: Path, bundle: Path, snapshot: Path):
    verify_text(presentation, bundle, snapshot)
    manifest = read_json(display / 'manifest.json')
    names = {'source-text-display.json', 'source-text-display.schema.json', 'validation.json'}
    if manifest.get('display_version') not in {'0.1.0', '0.1.1'} or set(manifest['files']) != names:
        raise ValueError('Unsupported text display')
    for name, ref in manifest['files'].items():
        raw = (display / name).read_bytes()
        if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
            raise ValueError('Text display checksum mismatch: ' + name)
    if read_json(display / 'source-text-display.schema.json') != text_display_schema(manifest['display_version']):
        raise ValueError('Unsupported text display schema')
    full = presentation / 'source-text.json'
    result = validate_text_display(read_json(display / 'source-text-display.json'), read_json(full),
        digest(full.read_bytes()), read_json(bundle / 'atlas-site.json'), read_json(snapshot))
    if (read_json(display / 'source-text-display.json')['display_version'] != manifest['display_version']
            or manifest['source_export_id'] != result['source_export_id'] or read_json(display / 'validation.json') != result):
        raise ValueError('Text display receipt differs')
    return result
