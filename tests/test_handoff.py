from pathlib import Path

import pytest

from atlas.handoff import build_handoff, inspect_export, file_reference
from atlas.site_export import export_site
from atlas.store import Store
from atlas.util import read_json, write_json
from test_site_export import site_inputs

CYCLE = '2026-09-30'


@pytest.fixture
def ready(tmp_path):
    paths, _ = site_inputs(tmp_path)
    bundle = tmp_path / 'site'
    export_site(**paths, out=bundle)
    asset = inspect_export(bundle, paths['snapshot'])
    reference = {k: asset[k] for k in ['bundle_path', 'map_snapshot_path', 'manifest_sha256', 'map_snapshot_sha256', 'export_id']}
    store = Store(tmp_path / 'state')
    directory = store.home / 'weekly' / CYCLE
    dependencies = {}
    for job in ['review', 'production', 'inbox']:
        receipt = dict(schema_version='1.0.0', cycle=CYCLE, job=job, status='completed',
                       completed_at='2026-09-30T12:00:00Z', ledger_head=store.verify()['head_hash'],
                       dependencies=dict(dependencies), unresolved_issue_ids=['needs-editor'])
        if job != 'review':
            receipt['export'] = reference
        if job == 'inbox':
            receipt.update(reviewed_export_id=reference['export_id'], post_review_validation='passed')
        write_json(directory / (job + '.json'), receipt)
        dependencies[job] = file_reference(directory / (job + '.json'))['sha256']
    yield store, paths, bundle, directory
    store.close()


def test_complete_gate_keeps_editorial_issues_pending(ready):
    store, paths, bundle, _ = ready
    result = build_handoff(store, CYCLE)
    assert result['weekly_ready'] and result['execution_status'] == 'completed'
    assert result['unresolved_issue_ids'] == ['needs-editor']
    assert result['publication_approval'] == 'not_evaluated'
    assert result['current_export']['map_snapshot']['path'] == str(paths['snapshot'])
    assert result['current_export']['selector']['sha256'] == file_reference(bundle / 'view.mjs')['sha256']


@pytest.mark.parametrize('change', [
    {'status': 'running'}, {'status': 'partial'}, {'status': 'blocked'},
    {'cycle': '2026-09-23'}, {'job': 'production'}, {'completed_at': None},
    {'completed_at': '2026-09-29T12:00:00Z'}, {'completed_at': '2026-09-30T11:00:00Z'},
    {'ledger_head': 'a' * 64}, {'dependencies': {}}, {'export': None},
    {'reviewed_export_id': 'a' * 64}, {'post_review_validation': 'failed'},
    {'unapplied_decision_ids': ['decision-1']},
])
def test_incomplete_or_stale_gate_is_not_ready(ready, change):
    store, _, _, directory = ready
    path = directory / 'inbox.json'
    receipt = read_json(path); receipt.update(change); write_json(path, receipt)
    result = build_handoff(store, CYCLE)
    assert not result['weekly_ready'] and result['blocking_reasons']
    assert result['current_export'] is None


def test_initial_export_does_not_manufacture_weekly_completion(ready):
    store, paths, bundle, directory = ready
    for job in ['review', 'production', 'inbox']:
        (directory / (job + '.json')).unlink()
    result = build_handoff(store, CYCLE, initial_bundle=bundle, initial_snapshot=paths['snapshot'])
    assert not result['weekly_ready']
    assert all(j['status'] == 'missing' for j in result['jobs'].values())
    assert result['initial_candidate']['counts_as_weekly_completion'] is False
    assert result['initial_candidate']['integrity']['status'] == 'valid'


def test_changes_to_evidence_receipts_or_ledger_invalidate_handoff(ready):
    store, paths, _, directory = ready
    review = directory / 'review.json'; saved = review.read_bytes()
    review.write_bytes(saved + b'\n')
    assert not build_handoff(store, CYCLE)['weekly_ready']
    review.write_bytes(saved)
    snapshot = paths['snapshot']; saved = snapshot.read_bytes(); snapshot.write_bytes(saved + b'\n')
    assert not build_handoff(store, CYCLE)['weekly_ready']
    snapshot.write_bytes(saved)
    store.append('test', {'changed': True}, '2026-09-30T13:00:00Z')
    assert 'inbox:ledger_changed' in build_handoff(store, CYCLE)['blocking_reasons']


def test_cycle_must_be_explicit_wednesday(ready):
    with pytest.raises(ValueError):
        build_handoff(ready[0], '2026-10-01')
