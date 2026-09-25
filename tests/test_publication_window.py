from pathlib import Path
import json
from epiweekly.sources import save_document
from epiweekly.extraction import extract_pending
from epiweekly.demo import sample_mention,add_example
from epiweekly.snapshot import build_snapshot
from epiweekly.export import validate_snapshot


def test_six_calendar_months():
    from epiweekly.config import publication_window
    c={'timezone':'Europe/Amsterdam','publication_window_months':6}
    assert publication_window(c,'2026-09-25') == ('2026-03-25','2026-09-25')
    assert publication_window(c,'2024-08-31') == ('2024-02-29','2024-08-31')


def test_extraction_excludes_old_future_and_undated_documents(store,config):
    config={**config,'publication_window_months':6}
    for i,day in enumerate(['2026-03-24','2026-03-25','2026-09-25','2026-09-26',None]):
        save_document(store,{'id':'example_authority'},text='Captured complete source text.'*10,raw=b'evidence',
                      url=f'https://example.org/window/{i}',content_url=f'https://example.org/window/{i}',
                      title='Source',at='2026-09-25T10:00:00Z',published_at=day,publication_precision='day' if day else 'unknown')
    result=extract_pending(store,config,'none',as_of='2026-09-25')
    assert result['queued_chunks']==2
    tasks=json.loads((store.home/'review/extraction_tasks.json').read_text())
    assert {store.get(t['document_id'])['payload']['published_at'] for t in tasks}=={'2026-03-25','2026-09-25'}
    assert len(store.records('document'))==5


def test_snapshot_and_review_share_publication_window(store,config):
    from epiweekly.workflow import export_review
    for day,key in [('2026-03-24','old'),('2026-03-25','inside')]:
        add_example(store,config,sample_mention(key=key),at=day+'T10:00:00Z',event_key=key)
        add_example(store,config,sample_mention(key=key+'-pending'),at=day+'T10:00:00Z')
    previous=build_snapshot(store,config,'2026-09-24T12:00:00Z')
    c={**config,'publication_window_months':6}
    snap=build_snapshot(store,c,'2026-09-25T12:00:00Z',previous=previous)
    validate_snapshot(snap)
    assert len(snap['tables']['events'])==1
    assert len(snap['tables']['documents'])==2
    assert len(snap['tables']['event_identities'])==1
    present={e['event_id'] for e in snap['tables']['events']}
    assert all(o['event_id'] in present for o in snap['tables']['opportunities'])
    assert all(h['event_id'] in present for h in snap['tables']['event_history'])
    assert snap['metadata']['quality']['pending_review_mentions']==1
    assert export_review(store,c,as_of='2026-09-25')['pending']==1
    assert len(store.records('document'))==4


def test_collection_clamps_discovery_and_skips_known_old_publications(store,config,monkeypatch):
    from epiweekly import config as config_module, sources
    monkeypatch.setattr(config_module,'utcnow',lambda:'2026-09-25T12:00:00Z')
    c={**config,'user_agent':'EpiWeekly test','limits':{**config['limits'],'max_response_bytes':16000000,'max_documents_per_source':10},'publication_window_months':6,'sources':[{'id':'example','adapter':'rss_discovery','enabled':True,'allowed_hosts':['example.org']}]}
    def discover(source,fetcher,since,limits):
        assert since=='2026-03-25'
        return [{'url':'https://example.org/'+d,'published_at':d} for d in ['2026-03-24','2026-03-25']],[]
    def retrieve(s,source,entry,fetcher):
        return save_document(s,source,text='Source evidence',raw=b'evidence',url=entry['url'],content_url=entry['url'],title='Source',at='2026-09-25T12:00:00Z',published_at=entry['published_at'])
    monkeypatch.setattr(sources,'discover',discover);monkeypatch.setattr(sources,'retrieve_entry',retrieve)
    result=sources.collect(store,c,'2024-09-25')
    assert result['documents_seen']==1
    assert result['sources'][0]['window_start']=='2026-03-25'


def test_outside_window_metric_is_not_a_change_baseline(store,config):
    c={**config,'publication_window_months':6}
    for publication,measurement,count in [('2026-03-24','2026-03-23',10),('2026-09-25','2026-09-24',20)]:
        m=sample_mention(count,key='same')
        m['as_of']['value']=measurement;m['observations'][0]['period_end']['value']=measurement
        quote=f'Example Authority reports {count} cumulative confirmed cases as of {measurement}.'
        m['evidence'][0]['quote']=quote;m['observations'][0]['evidence']['quote']=quote
        m['event_start']['value']='2026-01-01';m['observations'][0]['period_start']['value']='2026-01-01'
        add_example(store,config,m,at=publication+'T10:00:00Z',event_key='same')
        if publication=='2026-03-24':previous=build_snapshot(store,c,'2026-09-24T12:00:00Z')
    result=build_snapshot(store,c,'2026-09-25T12:00:00Z',previous=previous)
    assert result['tables']['event_metrics'][0]['change_in_reported_cumulative'] is None


def test_fourteen_inclusive_publication_days():
    import pytest
    from epiweekly.config import publication_window
    c={'timezone':'Europe/Amsterdam','publication_window_days':14}
    assert publication_window(c,'2026-09-25') == ('2026-09-12','2026-09-25')
    with pytest.raises(ValueError):publication_window({**c,'publication_window_months':6})
    with pytest.raises(ValueError):publication_window({**c,'publication_window_days':0})
