"""Operational boundaries: collection, editorial review, sealed output, and approval."""
from __future__ import annotations
import os
import platform
from pathlib import Path
from datetime import datetime, timedelta
from importlib.metadata import version, PackageNotFoundError
from zoneinfo import ZoneInfo
from filelock import FileLock
from . import __version__
from .util import digest,read_json,write_json,utcnow,stamp,uid
from .store import Store
from .snapshot import build_snapshot
from .export import export_snapshot,verify_bundle
from .registry import review_queue
from .sources import collect
from .extraction import extract_pending


def fingerprint() -> dict:
    package=Path(__file__).parent
    sources={p.relative_to(package).as_posix():digest(p.read_bytes()) for p in sorted(package.rglob('*'))
             if p.is_file() and p.suffix in {'.py','.yaml','.md'}}
    deps={}
    for name in ['pydantic','httpx','beautifulsoup4','pypdf','PyYAML','filelock','defusedxml','markdown-it-py','pycountry','tzdata','jsonschema']:
        try:deps[name]=version(name)
        except PackageNotFoundError:deps[name]='unavailable'
    return {'python':platform.python_version(),'software':__version__,'source_tree_sha256':digest(sources),
            'dependencies':deps,'commit':os.environ.get('GITHUB_SHA','local_checkout')}


def preceding_snapshot(store: Store, report_date: str) -> dict | None:
    # Same-date editorial revisions compare with the previous report date, not the earlier draft.
    choices=[r for r in store.records('snapshot') if r['payload']['report_date']<report_date]
    if not choices:return None
    latest=max(choices,key=lambda r:(r['payload']['report_date'],r['recorded_at']))
    return read_json(store.home/latest['payload']['path'])


def seal(store: Store, config: dict, *, as_of: str | None=None, report_date: str | None=None) -> dict:
    as_of=stamp(as_of or utcnow())
    report_date=report_date or datetime.fromisoformat(as_of.replace('Z','+00:00')).astimezone(ZoneInfo(config['timezone'])).date().isoformat()
    prior=preceding_snapshot(store,report_date)
    snapshot=build_snapshot(store,config,as_of,report_date=report_date,previous=prior,build_fingerprint=fingerprint())
    rid=snapshot['metadata']['report_id']
    out=store.home/'reports'/report_date/rid
    if out.exists():verify_bundle(out)
    else:export_snapshot(snapshot,out)
    payload={'report_id':rid,'report_date':report_date,'path':str((out/'report.json').relative_to(store.home)),
             'cutoff':as_of,'bundle_sha256':digest((out/'dataset.zip').read_bytes())}
    store.append('snapshot',payload,utcnow(),uid('sealed',rid))
    write_json(store.home/'latest.json',payload)
    return {'report_id':rid,'report_date':report_date,'bundle':str(out),'release_status':'draft',
            'quality':snapshot['metadata']['quality']}


def export_review(store: Store) -> dict:
    queue=review_queue(store)
    path=store.home/'review'/'queue.json';write_json(path,queue)
    # Source text is private; local pointers let the reviewing editor inspect full context.
    template=[{'candidate_id':q['candidate_id'],'action':'defer','event_key':None,'reviewer':'EDITOR',
               'rationale':'Review source context and proposed event identity.','public_rationale':'Editorial review',
               'supersedes_candidate_ids':[]} for q in queue]
    write_json(store.home/'review'/'decisions.template.json',template)
    return {'pending':len(queue),'queue':str(path),'decision_template':str(path.with_name('decisions.template.json'))}


def run(store: Store, config: dict, *, provider='none',model='',report_date=None,force=False) -> dict:
    today=report_date or datetime.now(ZoneInfo(config['timezone'])).date().isoformat()
    # A completed run receipt prevents additional network/model work on an automatic retry.
    receipts=[r for r in store.records('run_receipt') if r['payload']['report_date']==today]
    if receipts and not force:return {'status':'already_completed',**receipts[-1]['payload']}
    since=(datetime.fromisoformat(today)-timedelta(days=config.get('lookback_days',21))).date().isoformat()
    collection=collect(store,config,since)
    extraction=extract_pending(store,config,provider,model)
    review=export_review(store)
    result=seal(store,config,report_date=today)
    payload={'report_date':today,'report_id':result['report_id'],'bundle':result['bundle'],
             'collection':collection,'extraction':extraction,'review':review}
    store.append('run_receipt',payload,utcnow())
    return {'status':'completed',**payload}


def approve(bundle: Path, editor: str, note: str, target: Path) -> dict:
    verify_bundle(bundle)
    snapshot=read_json(bundle/'report.json')
    manifest={'report_id':snapshot['metadata']['report_id'],'bundle_sha256':digest((bundle/'dataset.zip').read_bytes()),
              'approved_at':utcnow(),'editor':editor,'public_note':note,'approval_version':'0.1.0'}
    if not editor.strip() or not note.strip():raise ValueError('Approval requires an editor and public note')
    write_json(target,manifest);return manifest


def approved_bundle(bundle: Path, approval: Path) -> dict:
    verify_bundle(bundle);manifest=read_json(approval)
    if manifest['bundle_sha256']!=digest((bundle/'dataset.zip').read_bytes()):raise ValueError('Approval identifies a different bundle')
    if manifest['report_id']!=read_json(bundle/'report.json')['metadata']['report_id']:raise ValueError('Approval report ID differs')
    return {'approved':True,**manifest}
