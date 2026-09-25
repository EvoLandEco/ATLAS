import pytest
from epiweekly import sources


class Pages:
    def __init__(self,pages):self.pages=pages;self.calls=[]
    def get(self,url,*args):
        self.calls.append(url)
        return self.pages[url].encode(),{},url,200


def test_paginated_archive_and_page_cap():
    source={'adapter':'html_index','index_url':'https://example.org/archive',
            'row_selector':'article','entry_link_selector':'a','date_selector':'time',
            'next_selector':'a[rel=next]','date_order':'descending','link_pattern':'/report/'}
    pages=Pages({'https://example.org/archive':'<article><a href="/report/new">New</a><time datetime="2026-09-20"/></article><a rel="next" href="?page=1">Next</a>',
                 'https://example.org/archive?page=1':'<article><a href="/report/old">Old</a><time datetime="2024-09-20"/></article><a rel="next" href="?page=2">Next</a>'})
    entries,notes=sources.discover(source,pages,'2024-09-25',{'max_index_pages':4})
    assert len(entries)==1 and not notes and len(pages.calls)==2
    entries,notes=sources.discover(source,pages,'2024-09-25',{'max_index_pages':1})
    assert 'index_page_cap' in notes


def test_feed_links_exclude_navigation():
    source={'adapter':'rss_discovery','index_url':'https://example.org/rss',
            'feed_labels':['News'],'feed_link_selector':'table a[href]'}
    pages=Pages({'https://example.org/rss':'<nav><a href="/news">News</a></nav><table><tr><td><a href="/feed">News</a></td></tr></table>',
                 'https://example.org/feed':'<rss><channel><item><title>News</title><link>https://example.org/item</link><pubDate>Fri, 25 Sep 2026 00:00:00 GMT</pubDate></item></channel></rss>'})
    entries,notes=sources.discover(source,pages,'2026-09-01',{})
    assert len(entries)==1 and 'https://example.org/news' not in pages.calls


def test_pdf_selection_decodes_path_and_rejects_ambiguity(store,monkeypatch):
    source={'id':'ecdc','primary_pdf':r'communicable[-\s]+disease[-\s]+threats[-\s]+report|cdtr',
            'exclude_pdf':'maps|graphs|visualisation'}
    url='https://example.org/report'
    pages=Pages({url:'<h1>Report</h1><a href="/CDTR-visualisation.pdf">Charts</a><a href="/Communicable%20disease%20threats%20report.pdf">Download</a>',
                 'https://example.org/Communicable%20disease%20threats%20report.pdf':'PDF'})
    monkeypatch.setattr(sources,'pdf_text',lambda raw:('Synthetic report text. '*10,'text_ready'))
    did=sources.retrieve_entry(store,source,{'url':url},pages)
    assert store.get(did)['payload']['content_url'].endswith('report.pdf')
    pages.pages[url]+='<a href="/CDTR-another.pdf">Another</a>'
    with pytest.raises(sources.SourceError,match='exactly one'):
        sources.retrieve_entry(store,source,{'url':url},pages)


def test_explicit_edition_date_and_static_coverage(store):
    source={'id':'fao','name':'Situation update','adapter':'static','urls':['https://example.org/update'],
            'publication_date_selector':'#edition','publication_date_format':'%d %B %Y'}
    pages=Pages({'https://example.org/update':'<h1>Update</h1><p id="edition">27 August 2026</p><p>'+('Source evidence. '*20)+'</p>'})
    entries,notes=sources.discover(source,pages,'2024-09-25',{})
    assert 'current_snapshot_only' in notes
    did=sources.retrieve_entry(store,source,entries[0],pages)
    assert store.get(did)['payload']['published_at']=='2026-08-27'
    assert store.get(did)['payload']['title']=='Situation update'


def test_robots_query_rules_wildcards_and_merged_groups():
    import httpx
    policy='User-agent: *\nDisallow: /nieuws?\n\nUser-agent: *\nDisallow: /private/*\nAllow: /private/public$\n'
    def handler(req):
        return httpx.Response(200,text=policy if req.url.path=='/robots.txt' else 'feed')
    f=sources.Fetcher(['example.org'],user_agent='EpiWeekly',min_interval=0,
                      client=httpx.Client(transport=httpx.MockTransport(handler)),resolve=lambda host:None)
    assert f.get('https://example.org/nieuws/rss.xml')[0]==b'feed'
    assert f.get('https://example.org/private/public')[0]==b'feed'
    for url in ['https://example.org/nieuws?page=1','https://example.org/private/record']:
        with pytest.raises(sources.SourceError,match='robots.txt'):f.get(url)
    f.close()


def test_multiple_topic_archives_deduplicate_and_keep_partial_routes():
    source={'adapter':'html_index','row_selector':'article','entry_link_selector':'a',
            'date_selector':'time','next_selector':'a[rel=next]','link_pattern':'/item/',
            'indexes':[{'index_url':'https://example.org/animal'},{'index_url':'https://example.org/bio'}]}
    page='<article><a href="/item/shared">Shared</a><time datetime="2026-09-20"/></article>'
    pages=Pages({'https://example.org/animal':page,'https://example.org/bio':page})
    entries,notes=sources.discover(source,pages,'2024-09-25',{'max_index_pages':4})
    assert len(entries)==1 and not notes
    pages.pages['https://example.org/bio']='Contract changed'
    entries,notes=sources.discover(source,pages,'2024-09-25',{'max_index_pages':4})
    assert len(entries)==1 and len(notes)==1 and 'https://example.org/bio' in notes[0]


def test_collection_stops_on_rate_limit(store,monkeypatch):
    import httpx
    source={'id':'test','adapter':'html_index','enabled':True,'allowed_hosts':['example.org']}
    config={'sources':[source],'user_agent':'test','limits':{'max_response_bytes':1000,'max_documents_per_source':10}}
    monkeypatch.setattr(sources,'discover',lambda *args:([{'url':'https://example.org/one'},{'url':'https://example.org/two'}],[]))
    calls=[]
    def limited(*args):
        calls.append(args[2]['url'])
        r=httpx.Response(429,headers={'Retry-After':'120'},request=httpx.Request('GET',calls[-1]))
        r.raise_for_status()
    monkeypatch.setattr(sources,'retrieve_entry',limited)
    result=sources.collect(store,config,'2024-09-25')
    assert len(calls)==1
    assert any('rate_limited' in note and '120' in note for note in result['sources'][0]['notes'])


def test_document_scope_uses_publisher_topic_links(store):
    source={'id':'efsa','topic_selector':'main .topics a[href]',
            'topic_urls':['https://example.org/topics/animal-health']}
    url='https://example.org/call'
    pages=Pages({url:'<main><h1>Call</h1><p>'+('Evidence. '*30)+'</p><div class="topics"><a href="/topics/chemicals">Chemicals</a></div></main>'})
    assert sources.retrieve_entry(store,source,{'url':url},pages) is None
    assert not store.records('document')
    pages.pages[url]=pages.pages[url].replace('/topics/chemicals','/topics/animal-health')
    assert sources.retrieve_entry(store,source,{'url':url},pages)
    pages.pages[url]='<main><h1>Missing topic labels</h1></main>'
    with pytest.raises(sources.SourceError,match='topic'):sources.retrieve_entry(store,source,{'url':url},pages)


def test_sitemap_discovery_uses_modification_not_publication_date():
    source={'adapter':'sitemap','index_url':'https://example.org/sitemap.xml','link_pattern':r'^https://example.org/news/'}
    pages=Pages({'https://example.org/sitemap.xml':'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://example.org/news.xml</loc></sitemap></sitemapindex>',
                 'https://example.org/news.xml':'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.org/news/revised</loc><lastmod>2026-09-01</lastmod></url><url><loc>https://example.org/news/old</loc><lastmod>2020-01-01</lastmod></url><url><loc>https://example.org/news/unknown</loc></url><url><loc>https://example.org/other</loc></url></urlset>'})
    entries,notes=sources.discover(source,pages,'2024-09-25',{'max_index_pages':3})
    assert len(entries)==2 and all(e['published_at'] is None for e in entries)
    assert entries[0]['modified_at']=='2026-09-01' and 'sitemap_modified_window' in notes
    entries,notes=sources.discover(source,pages,'2024-09-25',{'max_index_pages':1})
    assert 'index_page_cap' in notes


def test_primary_pdf_uses_attachment_title_not_filename(store,monkeypatch):
    source={'id':'ecdc','pdf_card_selector':'.ecdc-file-download',
            'primary_pdf':'communicable disease threats report','exclude_pdf':'maps|graphs'}
    url='https://example.org/report'
    pages=Pages({url:'<h1>Report</h1><div class="ecdc-file-download">Communicable disease threats report, week 33<a href="/2026-WCP-0045.pdf">Download</a></div><div class="ecdc-file-download">CDTR maps and graphs<a href="/charts.pdf">Download</a></div>',
                 'https://example.org/2026-WCP-0045.pdf':'PDF'})
    monkeypatch.setattr(sources,'pdf_text',lambda raw:('Source report text. '*10,'text_ready'))
    did=sources.retrieve_entry(store,source,{'url':url},pages)
    assert store.get(did)['payload']['content_url'].endswith('2026-WCP-0045.pdf')


def test_missing_only_collection_reuses_captures(store,monkeypatch):
    source={'id':'test','adapter':'html_index','enabled':True,'allowed_hosts':['example.org']}
    config={'sources':[source],'user_agent':'test','limits':{'max_response_bytes':1000,'max_documents_per_source':10}}
    old=sources.save_document(store,source,text='Evidence',raw=b'Evidence',url='https://example.org/one',content_url='https://example.org/one',title='One',at='2026-09-25T00:00:00Z',published_at='2025-01-01')
    monkeypatch.setattr(sources,'discover',lambda *args:([{'url':'https://example.org/one'},{'url':'https://example.org/two'}],[]))
    calls=[]
    def retrieve(*args):
        calls.append(args[2]['url'])
        return sources.save_document(store,source,text='New evidence',raw=b'New evidence',url=args[2]['url'],content_url=args[2]['url'],title='Two',at='2026-09-25T00:00:00Z',published_at='2026-01-01')
    monkeypatch.setattr(sources,'retrieve_entry',retrieve)
    result=sources.collect(store,config,'2024-09-25',missing_only=True)['sources'][0]
    assert calls==['https://example.org/two']
    assert result['retrieved']==2 and result['reused_documents']==1 and result['new_documents']==1
    assert result['oldest_publication']=='2025-01-01'


def test_sitemap_rejects_entities_and_reports_format_error():
    source={'adapter':'sitemap','index_url':'https://example.org/map','link_pattern':'/news/'}
    pages=Pages({'https://example.org/map':'<!DOCTYPE urlset [<!ENTITY x SYSTEM "file:///private">]><urlset>&x;</urlset>'})
    with pytest.raises(sources.SourceError,match='XML'):sources.discover(source,pages,'2024-09-25',{})


def test_source_content_selector_captures_report_outside_first_main(store):
    source={'id':'fao','content_selector':'#situation'}
    pages=Pages({'https://example.org/report':'<main>Header</main><main><section id="situation"><p>'+('Full situation evidence. '*20)+'</p></section></main>'})
    did=sources.retrieve_entry(store,source,{'url':'https://example.org/report'},pages)
    p=store.get(did)['payload'];text=(store.home/p['text_object']).read_text()
    assert 'Full situation evidence' in text and 'Header' not in text and p['parse_status']=='text_ready'
    source['content_selector']='#absent'
    with pytest.raises(sources.SourceError,match='content'):sources.retrieve_entry(store,source,{'url':'https://example.org/report'},pages)


def test_parser_revision_does_not_reuse_stale_conditional_text(store,monkeypatch):
    source={'id':'fao','content_selector':'#situation'};url='https://example.org/report'
    class Conditional(Pages):
        def get(self,url,headers=None):
            if headers:return b'',{},url,304
            raw,_,_,_=super().get(url)
            return raw,{'etag':'same-source-body'},url,200
    pages=Conditional({url:'<main>Heading</main><div id="situation">'+('Evidence. '*30)+'</div>'})
    monkeypatch.setattr(sources,'ADAPTER_VERSION','old-parser')
    old=sources.retrieve_entry(store,{'id':'fao'},{'url':url},pages)
    monkeypatch.setattr(sources,'ADAPTER_VERSION','new-parser')
    new=sources.retrieve_entry(store,source,{'url':url},pages)
    assert old!=new and store.get(new)['payload']['parse_status']=='text_ready'
