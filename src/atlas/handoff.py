"""Bind completed weekly jobs to a verified local export."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .site_export import verify_site
from .util import digest, read_json, stamp, utcnow

JOBS = ('review', 'production', 'inbox')
SHA256 = r'^[a-f0-9]{64}$'


class ExportReference(BaseModel):
    model_config = ConfigDict(extra='forbid')
    bundle_path: str
    map_snapshot_path: str
    manifest_sha256: str = Field(pattern=SHA256)
    map_snapshot_sha256: str = Field(pattern=SHA256)
    export_id: str = Field(pattern=SHA256)


class WeeklyReceipt(BaseModel):
    """Required handoff fields alongside a job's counts, checks and findings."""
    model_config = ConfigDict(extra='allow')
    schema_version: Literal['1.0.0']
    cycle: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    job: Literal['review', 'production', 'inbox']
    status: Literal['running', 'completed', 'partial', 'blocked']
    completed_at: str | None = None
    ledger_head: str = Field(pattern=SHA256)
    dependencies: dict[str, str] = Field(default_factory=dict)
    export: ExportReference | None = None
    unresolved_issue_ids: list[str] = Field(default_factory=list)
    unapplied_decision_ids: list[str] = Field(default_factory=list)
    reviewed_export_id: str | None = Field(default=None, pattern=SHA256)
    post_review_validation: Literal['passed', 'pending', 'failed'] | None = None

    @model_validator(mode='after')
    def completion(self):
        if date.fromisoformat(self.cycle).weekday() != 2:
            raise ValueError('Cycle must be a Wednesday')
        if self.status == 'completed' and not self.completed_at:
            raise ValueError('Completed receipt requires completed_at')
        if self.completed_at:
            completed = datetime.fromisoformat(stamp(self.completed_at)).astimezone(ZoneInfo('Europe/Amsterdam')).date()
            if completed < date.fromisoformat(self.cycle):
                raise ValueError('Completion precedes the scheduled cycle')
        return self


def file_reference(path: Path) -> dict:
    path = path.resolve(strict=True)
    return {'path': str(path), 'sha256': digest(path.read_bytes()), 'bytes': path.stat().st_size}


def inspect_export(bundle: Path, snapshot: Path) -> dict:
    verified = verify_site(bundle)
    data = read_json(bundle / 'atlas-site.json')
    manifest = file_reference(bundle / 'manifest.json')
    source = file_reference(snapshot)
    if source['sha256'] != data['snapshot']['source_snapshot_sha256']:
        raise ValueError('Map snapshot differs from the structured export input')
    original = read_json(snapshot)
    if 'geographic_review' in original:
        from .geography import validate_coverage
        validate_coverage(original)
    if digest(original['records']) != data['snapshot']['records_sha256']:
        raise ValueError('Map records differ from the structured export')
    files = read_json(bundle / 'manifest.json')['files']
    assets = {name: file_reference(bundle / name) for name in files}
    if any(assets[name]['sha256'] != expected for name, expected in files.items()):
        raise ValueError('Export changed during handoff validation')
    export_id = digest({'manifest_sha256': manifest['sha256'], 'map_snapshot_sha256': source['sha256']})
    return {
        'export_id': export_id, 'bundle_path': str(bundle.resolve()),
        'map_snapshot_path': source['path'], 'manifest_sha256': manifest['sha256'],
        'map_snapshot_sha256': source['sha256'], 'manifest': manifest,
        'structured_data': assets['atlas-site.json'], 'map_snapshot': source,
        'selector': assets['view.mjs'], 'files': assets,
        'contract_version': data['contract_version'],
        'metric_contract_version': data['metrics']['contract_version'],
        'software_version': data['software_version'], 'release_status': data['release_status'],
        'captured_at': data['snapshot']['captured_at'],
        'publication_window': [data['snapshot']['publication_from'], data['snapshot']['publication_until']],
        'integrity': verified,
    }


def build_handoff(store, cycle: str, *, initial_bundle: Path | None = None,
                  initial_snapshot: Path | None = None) -> dict:
    if date.fromisoformat(cycle).isoformat() != cycle or date.fromisoformat(cycle).weekday() != 2:
        raise ValueError('Cycle must be a Wednesday')
    if (initial_bundle is None) != (initial_snapshot is None):
        raise ValueError('Initial export requires both bundle and map snapshot')
    ledger = store.verify()
    receipts = {}; summaries = {}; reasons = []
    for job in JOBS:
        path = store.home / 'weekly' / cycle / (job + '.json')
        if not path.exists():
            summaries[job] = {'status': 'missing', 'receipt': None}
            reasons.append(job + ':missing')
            continue
        ref = file_reference(path)
        try:
            receipt = WeeklyReceipt.model_validate(read_json(path))
            if receipt.cycle != cycle or receipt.job != job:
                raise ValueError('Receipt cycle or job mismatch')
        except (ValueError, TypeError) as exc:
            summaries[job] = {'status': 'invalid', 'receipt': ref, 'error': str(exc)}
            reasons.append(job + ':invalid')
            continue
        receipts[job] = receipt
        summaries[job] = {'status': receipt.status, 'completed_at': receipt.completed_at, 'receipt': ref}
        if receipt.status != 'completed':
            reasons.append(job + ':' + receipt.status)
    for job, predecessors in [('production', ['review']), ('inbox', ['review', 'production'])]:
        if job not in receipts:
            continue
        for predecessor in predecessors:
            ref = summaries[predecessor]['receipt']
            if ref is None or receipts[job].dependencies.get(predecessor) != ref['sha256']:
                reasons.append(job + ':dependency_mismatch:' + predecessor)
            prior = receipts.get(predecessor)
            if prior and prior.completed_at and receipts[job].completed_at and stamp(receipts[job].completed_at) < stamp(prior.completed_at):
                reasons.append(job + ':completion_precedes:' + predecessor)
    production = receipts.get('production'); inbox = receipts.get('inbox'); current = None
    if production and production.status == 'completed' and production.export is None:
        reasons.append('production:export_missing')
    if inbox:
        if inbox.ledger_head != ledger['head_hash']:
            reasons.append('inbox:ledger_changed')
        if inbox.unapplied_decision_ids:
            reasons.append('inbox:unapplied_decisions')
        if inbox.post_review_validation != 'passed':
            reasons.append('inbox:validation_not_passed')
        if inbox.export is None:
            reasons.append('inbox:export_missing')
        else:
            try:
                current = inspect_export(Path(inbox.export.bundle_path), Path(inbox.export.map_snapshot_path))
                if any(current[key] != value for key, value in inbox.export.model_dump().items()):
                    raise ValueError('Receipt export reference differs from validated files')
                if inbox.reviewed_export_id != current['export_id']:
                    raise ValueError('Inbox review refers to a different export')
            except (ValueError, KeyError, OSError) as exc:
                current = None
                reasons.append('inbox:invalid_export:' + str(exc))
    initial = None
    if initial_bundle is not None:
        initial = inspect_export(initial_bundle, initial_snapshot)
        initial['mode'] = 'initial_publication_candidate'
        initial['counts_as_weekly_completion'] = False
    ready = not reasons and current is not None
    return {
        'handoff_version': '1.0.0', 'generated_at': utcnow(), 'cycle': cycle,
        'timezone': 'Europe/Amsterdam', 'weekly_ready': ready,
        'execution_status': 'completed' if ready else 'not_ready',
        'jobs': summaries, 'blocking_reasons': reasons, 'ledger': ledger,
        'current_export': current if ready else None, 'initial_candidate': initial,
        'unresolved_issue_ids': inbox.unresolved_issue_ids if inbox else [],
        'unapplied_decision_ids': inbox.unapplied_decision_ids if inbox else [],
        'publication_approval': 'not_evaluated',
    }
