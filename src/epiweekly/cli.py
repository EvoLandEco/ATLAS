"""epiweekly command line. See --help for each explicit operation."""
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
    p=argparse.ArgumentParser(prog='epiweekly',description='Versioned weekly outbreak intelligence and event registry')
    p.add_argument('--version',action='version',version=__version__)
    p.add_argument('--config',type=Path,default=Path('config/epiweekly.yaml'))
    p.add_argument('--state',type=Path,default=Path('.runtime-state'))
    s=p.add_subparsers(dest='command',required=True)
    s.add_parser('init');s.add_parser('doctor')
    c=s.add_parser('collect');c.add_argument('--since',required=True)
    c=s.add_parser('extract');c.add_argument('--provider',choices=['none','openai'],default=os.getenv('EPIWEEKLY_PROVIDER','none'));c.add_argument('--model',default=os.getenv('EPIWEEKLY_MODEL',''))
    c=s.add_parser('run');c.add_argument('--provider',choices=['none','openai'],default=os.getenv('EPIWEEKLY_PROVIDER','none'));c.add_argument('--model',default=os.getenv('EPIWEEKLY_MODEL',''));c.add_argument('--report-date');c.add_argument('--force',action='store_true')
    c=s.add_parser('import-document');c.add_argument('path',type=Path)
    c=s.add_parser('import-extraction');c.add_argument('document_id');c.add_argument('path',type=Path);c.add_argument('--editor',required=True)
    s.add_parser('review-export')
    for name in ['review-apply','relation-apply','opportunity-apply']:
        c=s.add_parser(name);c.add_argument('path',type=Path)
    c=s.add_parser('seal');c.add_argument('--as-of');c.add_argument('--report-date')
    c=s.add_parser('replay');c.add_argument('report',type=Path);c.add_argument('--out',type=Path,required=True)
    c=s.add_parser('verify');c.add_argument('--bundle',type=Path)
    c=s.add_parser('approve');c.add_argument('bundle',type=Path);c.add_argument('--editor',required=True);c.add_argument('--note',required=True);c.add_argument('--out',type=Path,required=True)
    c=s.add_parser('verify-approval');c.add_argument('bundle',type=Path);c.add_argument('approval',type=Path)
    c=s.add_parser('schemas');c.add_argument('--out',type=Path,default=Path('schemas'))
    c=s.add_parser('demo');c.add_argument('--out',type=Path,default=Path('demo-output'))
    return p


def execute(a):
    if a.command=='demo':
        from .demo import demo
        return demo(a.out)
    if a.command=='replay':return export_snapshot(read_json(a.report),a.out)
    if a.command=='approve':return approve(a.bundle,a.editor,a.note,a.out)
    if a.command=='verify-approval':return approved_bundle(a.bundle,a.approval)
    if a.command=='schemas':
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
            if cmd=='init':return {'state':str(a.state),'ledger':store.verify()}
            if cmd=='doctor':
                ZoneInfo(config['timezone'])
                return {'environment':fingerprint(),'ledger':store.verify(),'source_count':len(config['sources']),
                    'enabled_sources':[s['id'] for s in config['sources'] if s.get('enabled')],
                    'provider':os.getenv('EPIWEEKLY_PROVIDER','none'),'model_configured':bool(os.getenv('EPIWEEKLY_MODEL')),
                    'api_key_present':bool(os.getenv('OPENAI_API_KEY')),'network_check':'run collect explicitly'}
            if cmd=='collect':return collect(store,config,a.since)
            if cmd=='extract':return extract_pending(store,config,a.provider,a.model)
            if cmd=='run':return run(store,config,provider=a.provider,model=a.model,report_date=a.report_date,force=a.force)
            if cmd=='seal':return seal(store,config,as_of=a.as_of,report_date=a.report_date)
            if cmd=='verify':return store.verify()
            if cmd=='review-export':return export_review(store)
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
        print(f'epiweekly: {type(exc).__name__}: {exc}',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
