"""Captured findings outside publication-date selections."""
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit
from pydantic import Field
from .models import StrictModel
from .metrics import CardMeasure, refs, validate_numeric_evidence
from .site_export import EvidenceSpan
from .semantics import norm
from .util import digest, stamp

Hash = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]


class SupplementDocument(StrictModel):
    id: str = Field(pattern=r'^doc_[a-f0-9]{24}$')
    publisher: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str
    content_url: str
    publication: None
    publication_status: Literal['not_reported']
    capture: str
    raw_sha256: Hash
    text_sha256: Hash


class SupplementClaim(StrictModel):
    claim_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class SupplementRecord(StrictModel):
    id: str
    document_id: str
    title: str = Field(min_length=1)
    claims: list[SupplementClaim] = Field(min_length=1)
    measures: list[CardMeasure]
    disclosures: list[str]
    reviewed_at: str
    reviewed_by: str = Field(min_length=1)


class SourceSupplement(StrictModel):
    supplement_version: Literal['0.1.0']
    source_export_id: Hash
    generated_at: str
    review_status: Literal['source_checked_draft']
    selection_policy: Literal['outside_dated_selection']
    documents: list[SupplementDocument] = Field(min_length=1)
    records: list[SupplementRecord] = Field(min_length=1)
    evidence: list[EvidenceSpan] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)


def validate_supplement(data: dict, *, source_dir: Path | None = None):
    bundle = SourceSupplement.model_validate(data)
    stamp(bundle.generated_at)
    def index(rows):
        result = {r.id: r for r in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate identity')
        return result
    documents, records, evidence = map(index, [bundle.documents, bundle.records, bundle.evidence])
    sources = {}
    for doc in documents.values():
        stamp(doc.capture)
        for url in [doc.url, doc.content_url]:
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('Expected a public HTTPS source URL')
        if source_dir is not None:
            path = source_dir / (doc.id + '.txt')
            if path.stat().st_size > 4_000_000:
                raise ValueError('Source text exceeds the evidence budget')
            raw = path.read_bytes()
            if digest(raw) != doc.text_sha256:
                raise ValueError('Source text hash differs')
            sources[doc.id] = raw.decode('utf-8')
    claims = {}
    for record in records.values():
        stamp(record.reviewed_at)
        if record.document_id not in documents:
            raise ValueError('Record document is absent')
        for claim in record.claims:
            key = (record.id, claim.claim_index)
            if key in claims or len(set(claim.evidence_ids)) != len(claim.evidence_ids):
                raise ValueError('Duplicate claim or evidence reference')
            claims[key] = claim
    slots = {}
    for span in evidence.values():
        record = records.get(span.record_id)
        claim = claims.get((span.record_id, span.claim_index))
        if not record or record.document_id != span.document_id or not claim or span.id not in claim.evidence_ids:
            raise ValueError('Evidence document and claim do not resolve')
        slot = (span.record_id, span.claim_index, span.quote_index)
        if span.quote_index is None or span.quote_index < 0 or slot in slots:
            raise ValueError('Invalid or duplicate quotation index')
        slots[slot] = span
        if (not span.quote.strip() or span.end - span.start != len(span.quote)
                or digest(span.quote.encode()) != span.quote_sha256
                or span.source_text_sha256 != documents[span.document_id].text_sha256):
            raise ValueError('Evidence hash or offsets differ')
        if source_dir is not None and sources[span.document_id][span.start:span.end] != span.quote:
            raise ValueError('Quotation differs from captured source')
    for key, claim in claims.items():
        if any(e not in evidence or (evidence[e].record_id, evidence[e].claim_index) != key
               for e in claim.evidence_ids):
            raise ValueError('Claim evidence is absent')
    measures = {}
    for record in records.values():
        for measure in record.measures:
            if measure.annotation_key in measures or measure.source_reference.record_id != record.id:
                raise ValueError('Duplicate measurement or wrong record')
            measures[measure.annotation_key] = measure
            quotes = []
            for ref in refs(measure):
                target = records.get(ref.record_id)
                if not target or target.document_id != ref.document_id:
                    raise ValueError('Measurement document does not resolve')
                for qi in ref.quote_indexes:
                    span = slots.get((ref.record_id, ref.claim_index, qi))
                    if span is None:
                        raise ValueError('Measurement quotation does not resolve')
                    quotes.append(span.quote)
            joined = ' '.join(quotes)
            if norm(measure.evidence.quote) not in norm(joined):
                raise ValueError('Measurement evidence is outside its quotations')
            validate_numeric_evidence(measure, joined)
    def visit(key, path):
        if key not in measures or key in path:
            raise ValueError('Invalid measurement revision')
        for previous in measures[key].supersedes:
            visit(previous, path | {key})
    for key in measures:
        visit(key, set())
    return dict(valid=True, documents=len(documents), records=len(records),
                claims=len(claims), measures=len(measures), evidence=len(evidence))
