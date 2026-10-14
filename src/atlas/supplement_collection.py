"""Export-bound catalogues of distinct undated source supplements."""
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from .models import StrictModel
from .source_supplement import Hash, SourceSupplement, SupplementDocument, validate_supplement
from .util import atomic_write, digest, stamp, utcnow, write_json

ComponentId = Annotated[str, Field(pattern=r'^supplement_[a-f0-9]{24}$')]
MAX_PART_BYTES = 16_000_000
MAX_TOTAL_BYTES = 128_000_000


class Counts(StrictModel):
    documents: int = Field(ge=0)
    records: int = Field(ge=0)
    claims: int = Field(ge=0)
    measures: int = Field(ge=0)
    evidence: int = Field(ge=0)


class Component(StrictModel):
    id: ComponentId
    version: Literal['0.1.0']
    source_export_id: Hash
    path: Literal['source-supplement.json']
    schema_path: Literal['source-supplement.schema.json']
    sha256: Hash
    bytes: int = Field(gt=0, le=MAX_PART_BYTES)
    schema_sha256: Hash
    counts: Counts


class CatalogueRecord(StrictModel):
    id: str
    title: str
    claims: int = Field(ge=0)
    measures: int = Field(ge=0)


class CatalogueDocument(SupplementDocument):
    component_id: ComponentId
    records: list[CatalogueRecord]


class SupplementCatalogue(StrictModel):
    catalogue_version: Literal['0.1.0']
    source_export_id: Hash
    selection_policy: Literal['outside_dated_selection']
    documents: list[CatalogueDocument] = Field(min_length=1)


class CatalogueFile(StrictModel):
    path: Literal['source-supplement-catalogue.json']
    sha256: Hash
    bytes: int = Field(gt=0, le=8_000_000)
    schema_path: Literal['source-supplement-catalogue.schema.json']
    schema_sha256: Hash


class SupplementCollection(StrictModel):
    collection_version: Literal['0.1.0']
    source_export_id: Hash
    generated_at: str
    selection_policy: Literal['outside_dated_selection']
    components: list[Component] = Field(min_length=1, max_length=128)
    counts: Counts
    catalogue: CatalogueFile


def _bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def _read(path, limit):
    if path.stat().st_size > limit:
        raise ValueError('Collection input exceeds its byte limit')
    raw = path.read_bytes()
    if len(raw) > limit:
        raise ValueError('Collection input exceeds its byte limit')
    return raw


def _project(payloads, export_id, source_dir):
    if not 1 <= len(payloads) <= 128 or sum(map(len, payloads)) > MAX_TOTAL_BYTES:
        raise ValueError('Collection exceeds its component or byte limit')
    components, documents = [], []
    seen = {key: set() for key in ['documents', 'records', 'evidence', 'measures']}
    totals = dict.fromkeys(Counts.model_fields, 0)
    for raw in payloads:
        data = json.loads(raw)
        validation = validate_supplement(data, source_dir=source_dir)
        if data['source_export_id'] != export_id:
            raise ValueError('Supplement export binding differs')
        identities = {key: [r['id'] for r in data[key]] for key in ['documents', 'records', 'evidence']}
        identities['measures'] = [m['annotation_key'] for r in data['records'] for m in r['measures']]
        for key, values in identities.items():
            if seen[key].intersection(values):
                raise ValueError('Duplicate collection identity: ' + key)
            seen[key].update(values)
        component_id = 'supplement_' + digest({key: sorted(identities[key]) for key in ['documents', 'records']})[:24]
        counts = {key: validation[key] for key in totals}
        components.append(Component(id=component_id, version='0.1.0', source_export_id=export_id,
            path='source-supplement.json', schema_path='source-supplement.schema.json',
            sha256=digest(raw), bytes=len(raw), schema_sha256=digest(_bytes(SourceSupplement.model_json_schema())),
            counts=counts).model_dump(mode='json'))
        for key, value in counts.items():
            totals[key] += value
        for doc in data['documents']:
            rows = [dict(id=r['id'], title=r['title'], claims=len(r['claims']), measures=len(r['measures']))
                    for r in data['records'] if r['document_id'] == doc['id']]
            documents.append(dict(doc, component_id=component_id, records=rows))
    catalogue = SupplementCatalogue(catalogue_version='0.1.0', source_export_id=export_id,
        selection_policy='outside_dated_selection', documents=sorted(documents, key=lambda d: d['id']))
    return sorted(components, key=lambda c: c['id']), catalogue.model_dump(mode='json'), totals


def export_collection(paths: list[Path], export_id: str, source_dir: Path, out: Path):
    if not 1 <= len(paths) <= 128 or sum(path.stat().st_size for path in paths) > MAX_TOTAL_BYTES:
        raise ValueError('Collection exceeds its component or byte limit')
    payloads = [_read(path, MAX_PART_BYTES) for path in paths]
    components, catalogue, counts = _project(payloads, export_id, source_dir)
    catalogue_bytes = _bytes(catalogue)
    manifest = SupplementCollection(collection_version='0.1.0', source_export_id=export_id,
        generated_at=utcnow(), selection_policy='outside_dated_selection', components=components, counts=counts,
        catalogue=CatalogueFile(path='source-supplement-catalogue.json', sha256=digest(catalogue_bytes),
            bytes=len(catalogue_bytes), schema_path='source-supplement-catalogue.schema.json',
            schema_sha256=digest(_bytes(SupplementCatalogue.model_json_schema()))))
    out.mkdir(parents=True, exist_ok=False)
    for raw in payloads:
        directory = out / 'supplements' / digest(raw)
        atomic_write(directory / 'source-supplement.json', raw)
        write_json(directory / 'source-supplement.schema.json', SourceSupplement.model_json_schema())
    atomic_write(out / 'source-supplement-catalogue.json', catalogue_bytes)
    write_json(out / 'source-supplement-catalogue.schema.json', SupplementCatalogue.model_json_schema())
    write_json(out / 'source-supplement-collection.schema.json', SupplementCollection.model_json_schema())
    write_json(out / 'source-supplement-collection.json', manifest.model_dump(mode='json'))
    return verify_collection(out, source_dir=source_dir)


def verify_collection(directory: Path, *, source_dir: Path | None = None):
    path = directory / 'source-supplement-collection.json'
    raw = _read(path, 2_000_000)
    manifest = SupplementCollection.model_validate_json(raw)
    stamp(manifest.generated_at)
    if sum(c.bytes for c in manifest.components) > MAX_TOTAL_BYTES:
        raise ValueError('Collection exceeds its byte limit')
    for filename, model in [('source-supplement-collection.schema.json', SupplementCollection),
                            ('source-supplement-catalogue.schema.json', SupplementCatalogue)]:
        if _read(directory / filename, 1_000_000) != _bytes(model.model_json_schema()):
            raise ValueError('Collection schema differs')
    payloads = []
    for component in manifest.components:
        root = directory / 'supplements' / component.sha256
        payload = _read(root / component.path, MAX_PART_BYTES)
        if digest(payload) != component.sha256 or len(payload) != component.bytes:
            raise ValueError('Supplement checksum or size differs')
        schema = _read(root / component.schema_path, 1_000_000)
        if schema != _bytes(SourceSupplement.model_json_schema()) or digest(schema) != component.schema_sha256:
            raise ValueError('Supplement schema differs')
        payloads.append(payload)
    components, catalogue, counts = _project(payloads, manifest.source_export_id, source_dir)
    file = manifest.catalogue
    catalogue_raw = _read(directory / file.path, 8_000_000)
    if digest(catalogue_raw) != file.sha256 or len(catalogue_raw) != file.bytes:
        raise ValueError('Catalogue checksum or size differs')
    if digest(_read(directory / file.schema_path, 1_000_000)) != file.schema_sha256:
        raise ValueError('Catalogue schema differs')
    saved_catalogue = SupplementCatalogue.model_validate_json(catalogue_raw).model_dump(mode='json')
    if (components != [c.model_dump(mode='json') for c in manifest.components]
            or counts != manifest.counts.model_dump() or saved_catalogue != catalogue):
        raise ValueError('Collection descriptors, counts or catalogue differ from their payloads')
    return dict(valid=True, components=len(components), counts=counts,
        captured_sources_checked=source_dir is not None, descriptor=dict(version='0.1.0',
            source_export_id=manifest.source_export_id, path=path.name,
            schema_path='source-supplement-collection.schema.json', sha256=digest(raw), bytes=len(raw),
            schema_sha256=digest(_bytes(SupplementCollection.model_json_schema()))))
