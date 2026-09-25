"""Deterministic three-Wednesday synthetic longitudinal demonstration."""
from __future__ import annotations
from pathlib import Path
from .models import Mention,Extraction,Review,Relation,reported
from .sources import save_document
from .extraction import add_extraction
from .registry import apply_reviews,add_relation
from .snapshot import build_snapshot
from .export import export_snapshot,verify_bundle
from .store import Store
from .util import digest,write_json
from .workflow import export_review,fingerprint


def demo_config():
    sources=[{'id':s,'name':name,'role':role,'adapter':'manual','enabled':True,'required':True,'priority':p,
              'allowed_hosts':['example.org']} for s,name,role,p in [
              ('example_authority','Example National Authority (synthetic)','official_primary_reporting',1),
              ('example_digest','Example Regional Digest (synthetic)','regional_synthesis',2)]]
    return {'timezone':'Europe/Amsterdam','dataset_mode':'synthetic_demo','event_stale_days':21,
            'limits':{'max_output_tokens':6000,'chunk_characters':28000,'chunk_overlap':1200,
                      'max_model_calls':2,'max_input_characters':100000},'sources':sources,
            'research_profile':{'name':'One Health research demonstration','weights':{'one_health':5,'phylodynamics':4,
                'observation_process':4,'temporal_networks':5,'reproducible_analysis':3,'inference':4}}}


def sample_mention(value=120,as_of='2026-09-08',*,key='example-febrile',disease='Example febrile syndrome',
                   host='human',kind='outbreak',metric='cases',unit='people',status='active',tags=None,
                   country='NL',quote=None,case_definition='Example laboratory definition v1') -> dict:
    quote=quote or f'Example Authority reports {value} cumulative confirmed {metric} as of {as_of}.'
    return Mention.model_validate({'local_key':key,'title':f'{disease} — synthetic example','kind':kind,
      'disease':reported(disease),'pathogen':{'value':None,'status':'not_reported'},'host':reported(host),
      'country_code':reported(country),'location':reported('Example surveillance area'),'geographic_scope':'subnational',
      'authority_event_id':reported('EX-2026-'+key),'authority_namespace':reported('Example Authority'),
      'reported_status':status,'event_start':reported('2026-09-01'),'as_of':reported(as_of),
      'summary':f'Example Authority reports a cumulative total of {value} confirmed {metric}. This is a fictional training record.',
      'tags':tags or ['transmission_uncertain'],
      'observations':[{'metric':metric,'value':value,'value_status':'reported','unit':unit,'count_kind':'cumulative',
        'case_class':'confirmed','case_definition':reported(case_definition),'date_basis':'notification',
        'period_start':reported('2026-09-01'),'period_end':reported(as_of),'population':reported('Example monitored population'),
        'stratum':reported('All ages'),'qualifier':'exact','origin_authority':reported('Example Authority'),
        'evidence':{'field':metric,'quote':quote,'locator':'paragraph 1'}}],
      'evidence':[{'field':'event','quote':quote,'locator':'paragraph 1'}]}).model_dump(mode='json')


def add_example(store,config,mention,*,at,source_id='example_authority',event_key=None,supersedes=None,
                extra_text='',label=None):
    source=next(s for s in config['sources'] if s['id']==source_id)
    text='SYNTHETIC TRAINING SOURCE.\n'+'\n'.join(dict.fromkeys([e['quote'] for e in mention['evidence']]+
         [o['evidence']['quote'] for o in mention['observations']]))+'\n'+extra_text
    url='https://example.org/'+(label or digest([mention,at,source_id])[:18])
    doc=save_document(store,source,text=text,raw=text.encode(),url=url,content_url=url,title=mention['title'],
                      published_at=at[:10],publication_precision='day',at=at)
    result=Extraction.model_validate({'outcome':'extracted','mentions':[mention]})
    ids=add_extraction(store,doc,result,at=at,extraction_key=digest([doc,result.model_dump(mode='json')]),
                       provenance={'provider':'editorial','editor':'Synthetic fixture'})
    if event_key:
        apply_reviews(store,[Review(candidate_id=ids[0],action='accept',event_key=event_key,reviewer='Demo editor',
            rationale='Synthetic reference assignment.',supersedes_candidate_ids=supersedes or [])],at)
    return ids[0]


def demo(out: Path) -> dict:
    out=Path(out)
    if out.exists() and any(out.iterdir()):raise ValueError('Use an empty demonstration output directory')
    store=Store(out/'private-state');config=demo_config();previous=None;reports=[];ids={}
    try:
        for week,day,asof in [(1,'2026-09-09','2026-09-08'),(2,'2026-09-16','2026-09-15'),(3,'2026-09-23','2026-09-22')]:
            at=day+'T06:00:00Z';cutoff=day+'T06:37:00Z'
            if week==1:
                m=sample_mention(tags=['transmission_uncertain','public_data'])
                # Include a real zero and an explicitly absent metric in the fixture.
                missing=dict(m['observations'][0]);missing.update(metric='deaths',value=None,value_status='not_reported')
                missing['evidence']={'field':'deaths','quote':'Mortality is not included in this synthetic bulletin.','locator':'paragraph 2'}
                m['observations'].append(missing)
                resource={'kind':'dataset','title':'Synthetic observations','url':'https://example.org/data/example.csv',
                    'access':'public','evidence':{'field':'resource','quote':'Synthetic observations: https://example.org/data/example.csv','locator':'paragraph 3'}}
                m['resources']=[resource]
                ids['febrile1']=add_example(store,config,m,at=at,event_key='example-febrile-2026',extra_text=resource['evidence']['quote'])
                ids['animal1']=add_example(store,config,sample_mention(4,asof,key='animal-aiv',disease='Avian influenza',host='pig',
                    metric='affected_holdings',unit='holdings',tags=['one_health_interface','network_question']),at=at,event_key='example-animal-aiv-2026')
            elif week==2:
                m=sample_mention(135,asof)
                ids['febrile2']=add_example(store,config,m,at=at,event_key='example-febrile-2026')
                ids['febrile2mirror']=add_example(store,config,m,at=at,source_id='example_digest',event_key='example-febrile-2026')
                ids['animal2']=add_example(store,config,sample_mention(6,asof,key='animal-aiv',disease='Avian influenza',host='pig',
                    metric='affected_holdings',unit='holdings',tags=['one_health_interface','network_question']),at=at,event_key='example-animal-aiv-2026')
                ids['human2']=add_example(store,config,sample_mention(1,asof,key='human-aiv',disease='Avian influenza',host='human',
                    kind='single_case',tags=['one_health_interface']),at=at,event_key='example-human-aiv-2026')
                add_relation(store,Relation(from_event_key='example-animal-aiv-2026',to_event_key='example-human-aiv-2026',
                    relation='possible_link',basis='analyst_hypothesis',evidence_candidate_id=ids['human2'],reviewer='Demo editor',
                    rationale='Synthetic co-occurrence motivates a host-interface evidence review; epidemiological linkage is a hypothesis.'),at)
            else:
                m=sample_mention(132,'2026-09-15',tags=['reporting_revision'])
                m['summary']='The synthetic authority corrects the earlier total from 135 to 132 after record review.'
                ids['febrile3']=add_example(store,config,m,at=at,event_key='example-febrile-2026',
                    supersedes=[ids['febrile2'],ids['febrile2mirror']])
                m=sample_mention(1,asof,key='human-aiv',disease='Avian influenza',host='human',kind='single_case',status='resolved',tags=['one_health_interface'])
                zero=dict(m['observations'][0]);zero.update(value=0,count_kind='interval',period_start=reported('2026-09-16'),
                    evidence={'field':'cases','quote':'There were 0 newly notified confirmed cases from 2026-09-16 to 2026-09-22.','locator':'paragraph 2'})
                m['observations'].append(zero)
                ids['human3']=add_example(store,config,m,at=at,event_key='example-human-aiv-2026')
                m=sample_mention(3,asof,key='ambiguous',tags=['transmission_uncertain'])
                m['authority_event_id']={'value':None,'status':'not_reported'};m['authority_namespace']={'value':None,'status':'not_reported'}
                m['ambiguity_reasons']=['The source does not establish whether this signal belongs to the known event.']
                ids['pending']=add_example(store,config,m,at=at)
            for source in config['sources']:
                rows=[r for r in store.records('document') if r['payload']['source_id']==source['id']]
                store.append('source_check',{'source_id':source['id'],'status':'ok','enabled':True,'window_start':'2026-09-01',
                  'discovered':len(rows),'retrieved':len(rows),'new_documents':len(rows),'oldest_publication':min([r['payload']['published_at'] for r in rows],default=None),
                  'newest_publication':max([r['payload']['published_at'] for r in rows],default=None),'notes':['Synthetic offline fixtures.']},at)
            snapshot=build_snapshot(store,config,cutoff,report_date=day,previous=previous,
                build_fingerprint={'fixture_version':'0.1.0','execution_mode':'synthetic_offline','source_tree_sha256':fingerprint()['source_tree_sha256']})
            folder=out/'reports'/day;export_snapshot(snapshot,folder);verify_bundle(folder)
            previous=snapshot;reports.append(str(folder));
        queue=export_review(store)
        result={'dataset_mode':'synthetic_demo','reports':reports,'latest':reports[-1],'ledger':store.verify(),'review':queue}
        write_json(out/'demo-results.json',result);return result
    finally:store.close()
