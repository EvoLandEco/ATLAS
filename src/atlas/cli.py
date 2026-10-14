"""atlas command line. See --help for each explicit operation."""
from __future__ import annotations
import argparse,json,os,sys,shutil
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from filelock import FileLock
from . import __version__
from .config import load_config
from .store import Store
from .util import utcnow,read_json,write_json,digest,canonical
from .models import Extraction,Review,Relation,OpportunityDecision
from .sources import save_document,collect,canonical_url
from .extraction import add_extraction,extract_pending,strict_schema
from .registry import apply_reviews,add_relation
from .export import export_snapshot,verify_bundle,report_schema
from .workflow import run,seal,export_review,approve,approved_bundle,fingerprint


def parser():
    p=argparse.ArgumentParser(prog='atlas',description='ATLAS: Agentic Tracking and Longitudinal Analysis for Surveillance')
    p.add_argument('--version',action='version',version=__version__)
    p.add_argument('--config',type=Path,default=Path('config/atlas.yaml'))
    p.add_argument('--state',type=Path,default=Path('.runtime-state'))
    s=p.add_subparsers(dest='command',required=True)
    s.add_parser('init');s.add_parser('doctor')
    c=s.add_parser('collect');c.add_argument('--since',required=True);c.add_argument('--until');c.add_argument('--missing-only',action='store_true',help='Fetch uncaptured URLs and reuse existing documents without checking revisions')
    c=s.add_parser('extract');c.add_argument('--provider',choices=['none','openai','codex'],default=os.getenv('ATLAS_PROVIDER','none'));c.add_argument('--model',default=os.getenv('ATLAS_MODEL',''))
    c=s.add_parser('run');c.add_argument('--provider',choices=['none','openai','codex'],default=os.getenv('ATLAS_PROVIDER','none'));c.add_argument('--model',default=os.getenv('ATLAS_MODEL',''));c.add_argument('--report-date');c.add_argument('--force',action='store_true')
    c=s.add_parser('import-document');c.add_argument('path',type=Path)
    c=s.add_parser('import-extraction');c.add_argument('document_id');c.add_argument('path',type=Path);c.add_argument('--editor',required=True)
    s.add_parser('review-export')
    c=s.add_parser('inbox-export');c.add_argument('--archive-id',required=True);c.add_argument('--issues',type=Path);c.add_argument('--out',type=Path,required=True)
    c=s.add_parser('inbox-import');c.add_argument('path',type=Path);c.add_argument('--out',type=Path,required=True)
    c=s.add_parser('inbox-push');c.add_argument('packet',type=Path)
    s.add_parser('inbox-sync')
    c=s.add_parser('inbox-complete');c.add_argument('decision_id');c.add_argument('--bundle',type=Path,required=True);c.add_argument('--snapshot',type=Path);c.add_argument('--note',required=True);c.add_argument('--out',type=Path,required=True)
    for name in ['review-apply','relation-apply','opportunity-apply']:
        c=s.add_parser(name);c.add_argument('path',type=Path)
    c=s.add_parser('seal');c.add_argument('--as-of');c.add_argument('--report-date')
    c=s.add_parser('replay');c.add_argument('report',type=Path);c.add_argument('--out',type=Path,required=True)
    c=s.add_parser('verify');c.add_argument('--bundle',type=Path)
    c=s.add_parser('approve');c.add_argument('bundle',type=Path);c.add_argument('--editor',required=True);c.add_argument('--note',required=True);c.add_argument('--out',type=Path,required=True)
    c=s.add_parser('verify-approval');c.add_argument('bundle',type=Path);c.add_argument('approval',type=Path)
    c=s.add_parser('schemas');c.add_argument('--out',type=Path,default=Path('schemas'))
    c=s.add_parser('metrics');c.add_argument('--snapshot',type=Path,required=True);c.add_argument('--annotations',type=Path,required=True);c.add_argument('--source-dir',type=Path,required=True);c.add_argument('--out',type=Path,required=True);c.add_argument('--since',required=True);c.add_argument('--until',required=True);c.add_argument('--basis',choices=['publication','capture'],default='publication');c.add_argument('--knowledge-cutoff');c.add_argument('--max-annotation-bytes',type=int,default=16_000_000,help='Annotation input limit in bytes; default 16000000, maximum 512000000');c.add_argument('--max-snapshot-bytes',type=int,default=32_000_000,help='Snapshot input limit in bytes; default 32000000, maximum 128000000')
    c=s.add_parser('site-export')
    for flag in ['snapshot','results','metrics','annotations','source-dir','out','schedule']:
        c.add_argument('--'+flag,type=Path,required=True)
    c.add_argument('--max-input-bytes',type=int,default=64_000_000,help='Per-file input limit in bytes; default 64000000, maximum 2000000000')
    c=s.add_parser('site-verify');c.add_argument('bundle',type=Path)
    c=s.add_parser('supplement-collection');c.add_argument('--supplement',type=Path,action='append',required=True)
    c.add_argument('--source-export-id',required=True);c.add_argument('--source-dir',type=Path,required=True);c.add_argument('--out',type=Path,required=True)
    c=s.add_parser('supplement-collection-verify');c.add_argument('collection',type=Path);c.add_argument('--source-dir',type=Path)
    for name in ['text-export','text-verify']:
        c=s.add_parser(name)
        for flag in ['bundle','snapshot']:
            c.add_argument('--'+flag,type=Path,required=True)
        for flag in (['annotations','out'] if name=='text-export' else ['presentation']):
            c.add_argument('--'+flag,type=Path,required=True)
    for name in ['text-display-export','text-display-verify']:
        c=s.add_parser(name)
        for flag in ['bundle','snapshot','presentation', 'out' if name=='text-display-export' else 'display']:
            c.add_argument('--'+flag,type=Path,required=True)
    for name in ['watch-export','watch-verify']:
        c=s.add_parser(name)
        for flag in ['bundle','snapshot'] + (['annotations','out'] if name=='watch-export' else ['watch']):
            c.add_argument('--'+flag,type=Path,required=True)
    c=s.add_parser('daily-capture');c.add_argument('--daily-state',type=Path,required=True)
    c.add_argument('--since',required=True);c.add_argument('--until',required=True);c.add_argument('--force',action='store_true')
    c=s.add_parser('daily-extract');c.add_argument('--daily-state',type=Path,required=True)
    c.add_argument('--acquisition',type=Path,required=True);c.add_argument('--out',type=Path,required=True);c.add_argument('--model',default=os.getenv('ATLAS_MODEL',''))
    for name in ['daily-export','daily-verify']:
        c=s.add_parser(name)
        for flag in ['daily-state','acquisition','annotations','bundle','snapshot','out' if name=='daily-export' else 'daily']:
            c.add_argument('--'+flag,type=Path,required=True)
        c.add_argument('--weekly-handoff',type=Path)
    c=s.add_parser('handoff');c.add_argument('--cycle',required=True);c.add_argument('--out',type=Path,default=Path('reports/publication-handoff.json'))
    c.add_argument('--initial-bundle',type=Path);c.add_argument('--initial-snapshot',type=Path)
    c=s.add_parser('demo');c.add_argument('--out',type=Path,default=Path('demo-output'))
    return p


def execute(a):
    if a.command=='inbox-push':
        from .inbox import push_packet
        return push_packet(a.packet)
    if a.command=='supplement-collection':
        from .supplement_collection import export_collection
        return export_collection(a.supplement,a.source_export_id,a.source_dir,a.out)
    if a.command=='supplement-collection-verify':
        from .supplement_collection import verify_collection
        return verify_collection(a.collection,source_dir=a.source_dir)
    if a.command.startswith('daily-'):
        from .daily import capture_daily,extract_daily,export_daily,verify_daily
        config=load_config(a.config)
        if a.command=='daily-capture':return capture_daily(a.daily_state,a.state,config,a.since,a.until,force=a.force)
        if a.command=='daily-extract':return extract_daily(a.daily_state,a.acquisition,config,a.out,a.model)
        args=(a.daily_state,config,a.acquisition,a.annotations,a.bundle,a.snapshot)
        if a.command=='daily-export':return export_daily(*args,a.out,a.weekly_handoff)
        return verify_daily(a.daily,*args,a.weekly_handoff)
    if a.command=='watch-export':
        from .watch import export_watch
        return export_watch(a.bundle,a.snapshot,a.annotations,a.out)
    if a.command=='watch-verify':
        from .watch import verify_watch
        return verify_watch(a.watch,a.bundle,a.snapshot)
    if a.command=='text-display-export':
        from .source_text import export_text_display
        return export_text_display(a.presentation,a.bundle,a.snapshot,a.out)
    if a.command=='text-display-verify':
        from .source_text import verify_text_display
        return verify_text_display(a.display,a.presentation,a.bundle,a.snapshot)
    if a.command=='text-export':
        from .source_text import export_text
        return export_text(a.bundle,a.snapshot,a.annotations,a.out)
    if a.command=='text-verify':
        from .source_text import verify_text
        return verify_text(a.presentation,a.bundle,a.snapshot)
    if a.command=='site-export':
        from .site_export import export_site
        result=export_site(a.snapshot,a.results,a.metrics,a.annotations,a.source_dir,a.out,a.schedule,max_input_bytes=a.max_input_bytes)
        return {'out':str(a.out),'contract_version':result['contract_version'],'records':len(result['records']),'comparisons':len(result['comparisons'])}
    if a.command=='site-verify':
        from .site_export import verify_site
        return verify_site(a.bundle)
    if a.command=='metrics':
        from .metrics import export_metrics
        result=export_metrics(a.snapshot,a.annotations,a.source_dir,a.out,a.since,a.until,a.basis,a.knowledge_cutoff,max_annotation_bytes=a.max_annotation_bytes,max_snapshot_bytes=a.max_snapshot_bytes)
        return {'out':str(a.out),'contract_version':result['contract_version'],**result['coverage']}
    if a.command=='demo':
        from .demo import demo
        return demo(a.out)
    if a.command=='replay':return export_snapshot(read_json(a.report),a.out)
    if a.command=='approve':return approve(a.bundle,a.editor,a.note,a.out)
    if a.command=='verify-approval':return approved_bundle(a.bundle,a.approval)
    if a.command=='schemas':
        from .inbox import Packet,Decisions,Receipts,SupplementalPacket,Decision
        for name,model in [('inbox',Packet),('inbox-decisions',Decisions),('inbox-receipts',Receipts),('inbox-supplement',SupplementalPacket),('inbox-decision',Decision)]:
            write_json(a.out/(name+'.schema.json'),model.model_json_schema())
        from .network_analysis import schema as network_schema,transport_schema
        write_json(a.out/'network-analysis.schema.json',network_schema())
        write_json(a.out/'network-transport.schema.json',transport_schema())
        from .geography import Reviews
        write_json(a.out/'geographic-review.schema.json',Reviews.model_json_schema())
        from .handoff import WeeklyReceipt
        write_json(a.out/'weekly-receipt.schema.json',WeeklyReceipt.model_json_schema())
        from .site_export import SiteBundle,SiteAnnotations
        write_json(a.out/'atlas-site.schema.json',SiteBundle.model_json_schema())
        write_json(a.out/'site-annotations.schema.json',SiteAnnotations.model_json_schema())
        from .metrics import MetricsExport,MetricAnnotations
        from .source_supplement import SourceSupplement
        write_json(a.out/'source-supplement.schema.json',SourceSupplement.model_json_schema())
        from .supplement_collection import SupplementCollection,SupplementCatalogue
        write_json(a.out/'source-supplement-collection.schema.json',SupplementCollection.model_json_schema())
        write_json(a.out/'source-supplement-catalogue.schema.json',SupplementCatalogue.model_json_schema())
        from .source_text import TextPresentation,TextAnnotations,text_display_schema
        write_json(a.out/'source-text.schema.json',TextPresentation.model_json_schema())
        write_json(a.out/'text-annotations.schema.json',TextAnnotations.model_json_schema())
        write_json(a.out/'source-text-display.schema.json',text_display_schema())
        from .watch import WatchExport,WatchAnnotations
        write_json(a.out/'watch.schema.json',WatchExport.model_json_schema())
        write_json(a.out/'watch-annotations.schema.json',WatchAnnotations.model_json_schema())
        from .daily import DailyExport,DailyAnnotations
        write_json(a.out/'daily.schema.json',DailyExport.model_json_schema())
        write_json(a.out/'daily-annotations.schema.json',DailyAnnotations.model_json_schema())
        write_json(a.out/'metrics.schema.json',MetricsExport.model_json_schema())
        write_json(a.out/'metric-annotations.schema.json',MetricAnnotations.model_json_schema())
        write_json(a.out/'extraction.schema.json',Extraction.model_json_schema())
        write_json(a.out/'provider.schema.json',strict_schema(Extraction.model_json_schema()))
        write_json(a.out/'report.schema.json',report_schema())
        write_json(a.out/'review.schema.json',Review.model_json_schema())
        return {'schemas':str(a.out)}
    if a.command=='verify' and a.bundle:return verify_bundle(a.bundle)
    config=load_config(a.config)
    a.state.mkdir(parents=True,exist_ok=True)
    with FileLock(str(a.state/'.writer.lock'),timeout=5):
        store=Store(a.state)
        try:
            cmd=a.command
            if cmd.startswith('inbox-'):
                from .inbox import export_inbox,import_decisions,Decisions,bounded_json,sync_decisions,complete_decision
                if cmd=='inbox-export':return export_inbox(store,a.archive_id,a.out,supplemental=a.issues,config=config)
                if cmd=='inbox-import':
                    result=import_decisions(store,Decisions.model_validate(bounded_json(a.path))).model_dump()
                    write_json(a.out,result)
                    return result
                if cmd=='inbox-sync':return sync_decisions(store)
                if cmd=='inbox-complete':
                    result=complete_decision(store,a.decision_id,a.bundle,a.snapshot,a.note)
                    write_json(a.out,result)
                    return result
            if cmd=='handoff':
                from .handoff import build_handoff
                result=build_handoff(store,a.cycle,initial_bundle=a.initial_bundle,initial_snapshot=a.initial_snapshot)
                write_json(a.out,result)
                return {'handoff':str(a.out),'cycle':a.cycle,'weekly_ready':result['weekly_ready'],'blocking_reasons':result['blocking_reasons']}
            if cmd=='init':return {'state':str(a.state),'ledger':store.verify()}
            if cmd=='doctor':
                ZoneInfo(config['timezone'])
                return {'environment':fingerprint(),'ledger':store.verify(),'source_count':len(config['sources']),
                    'enabled_sources':[s['id'] for s in config['sources'] if s.get('enabled')],
                    'provider':os.getenv('ATLAS_PROVIDER','none'),'model_configured':bool(os.getenv('ATLAS_MODEL')),
                    'codex_available':shutil.which('codex') is not None,
                    'api_key_present':bool(os.getenv('OPENAI_API_KEY')),'network_check':'run collect explicitly'}
            if cmd=='collect':return collect(store,config,a.since,missing_only=a.missing_only,until=a.until)
            if cmd=='extract':return extract_pending(store,config,a.provider,a.model)
            if cmd=='run':return run(store,config,provider=a.provider,model=a.model,report_date=a.report_date,force=a.force)
            if cmd=='seal':return seal(store,config,as_of=a.as_of,report_date=a.report_date)
            if cmd=='verify':return store.verify()
            if cmd=='review-export':return export_review(store,config)
            if cmd=='import-document':
                item=read_json(a.path);source=next(s for s in config['sources'] if s['id']==item['source_id'])
                from urllib.parse import urlparse
                for field in ['url','content_url']:
                    url=item.get(field,item['url']);canonical_url(url)
                    if urlparse(url).hostname not in source['allowed_hosts']:raise ValueError('Imported source URL requires an allowed host')
                text=item['text']
                if not isinstance(text,str) or not text.strip():raise ValueError('Imported source requires captured text')
                at=utcnow()
                doc=save_document(store,source,text=text,raw=text.encode(),url=item['url'],content_url=item.get('content_url',item['url']),
                    title=item['title'],published_at=item.get('published_at'),publication_precision=item.get('publication_precision','unknown'),
                    modified_at=item.get('modified_at'),parse_status=item.get('parse_status','text_ready'),at=at)
                return {'document_id':doc}
            if cmd=='import-extraction':
                result=Extraction.model_validate(read_json(a.path))
                ids=add_extraction(store,a.document_id,result,at=utcnow(),extraction_key=digest([a.document_id,result.model_dump(mode='json'),a.editor]),
                                   provenance={'provider':'editorial','editor':a.editor})
                return {'candidate_ids':ids}
            if cmd=='review-apply':
                return {'review_ids':apply_reviews(store,[Review.model_validate(r) for r in read_json(a.path)],utcnow())}
            if cmd=='relation-apply':return {'relationship_ids':[add_relation(store,Relation.model_validate(r),utcnow()) for r in read_json(a.path)]}
            if cmd=='opportunity-apply':
                latest=read_json(store.home/'latest.json');snapshot=read_json(store.home/latest['path'])
                valid={o['opportunity_id'] for o in snapshot['tables']['opportunities']};ids=[]
                for raw in read_json(a.path):
                    item=OpportunityDecision.model_validate(raw)
                    if item.opportunity_id not in valid:raise ValueError('Opportunity must occur in the latest sealed report')
                    ids.append(store.append('opportunity_decision',item.model_dump(mode='json'),utcnow()))
                return {'decision_ids':ids}
            raise ValueError('Unknown command')
        finally:store.close()


def main():
    try:result=execute(parser().parse_args());print(json.dumps(result,indent=2,ensure_ascii=False));return 0
    except (ValueError,KeyError,OSError,RuntimeError,StopIteration) as exc:
        print(f'atlas: {type(exc).__name__}: {exc}',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
