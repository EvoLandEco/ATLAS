import json,io
import httpx,pytest
from pypdf import PdfWriter
from epiweekly.sources import Fetcher,SourceError,parse_date,parse_feed,html_text,pdf_text,collect,discover,save_document
from epiweekly.extraction import OpenAIExtractor,strict_schema,chunks,extract_pending
from epiweekly.models import Extraction
from epiweekly.demo import sample_mention,add_example
from epiweekly.config import load_config
from epiweekly.util import canonical_url
from pathlib import Path


def client(handler):return httpx.Client(transport=httpx.MockTransport(handler))

def test_feed_relative_links_and_publication():
    raw=b'<rss><channel><item><title>Test</title><link>/item</link><pubDate>Tue, 08 Sep 2026 10:00:00 +0200</pubDate></item></channel></rss>'
    result=parse_feed(raw,'https://example.org/feed')
    assert result[0]['url']=='https://example.org/item'
    assert result[0]['published_at'].startswith('2026-09-08T08:00:00')

def test_atom_updated_not_publication():
    raw=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Test</title><link href="https://example.org/item"/><updated>2026-09-08T10:00:00Z</updated></entry></feed>'
    result=parse_feed(raw,'https://example.org/feed')
    assert result[0]['published_at'] is None

def test_xml_external_entity_rejected():
    raw=b'<!DOCTYPE rss [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><rss><channel><item><title>&xxe;</title></item></channel></rss>'
    with pytest.raises(Exception):parse_feed(raw,'https://example.org/feed')

def test_empty_feed_explicit():
    with pytest.raises(SourceError):parse_feed(b'<rss><channel/></rss>','https://example.org/feed')

def test_html_captured_main():
    text,title,pub,precision=html_text(b'<html><head><title>Example</title><meta property="article:published_time" content="2026-09-08T10:00:00Z"></head><body><nav>Skip</nav><main><p>12 cases reported.</p><script>do_bad()</script></main></body></html>')
    assert '12 cases' in text and 'do_bad' not in text and 'Skip' not in text
    assert title=='Example'

def test_image_only_pdf_queued():
    pdf=PdfWriter();pdf.add_blank_page(612,792);b=io.BytesIO();pdf.write(b)
    text,status=pdf_text(b.getvalue())
    assert status=='needs_review'

def test_allowlist_rejects_untrusted_redirect():
    calls=[]
    def handler(req):
        calls.append(str(req.url))
        if req.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nAllow: /')
        return httpx.Response(302,headers={'location':'https://evil.example/secret'})
    f=Fetcher(['example.org'],user_agent='Test',client=client(handler),resolve=lambda h:None,min_interval=0)
    with pytest.raises(SourceError):f.get('https://example.org/page')
    assert all('evil.example' not in u for u in calls)

def test_robots_honored():
    def handler(req):return httpx.Response(200,text='User-agent: *\nDisallow: /private')
    f=Fetcher(['example.org'],user_agent='Test',client=client(handler),resolve=lambda h:None,min_interval=0)
    with pytest.raises(SourceError):f.get('https://example.org/private')

def test_response_size_bound():
    def handler(req):return httpx.Response(404) if req.url.path=='/robots.txt' else httpx.Response(200,text='x'*100)
    f=Fetcher(['example.org'],user_agent='Test',client=client(handler),resolve=lambda h:None,min_interval=0,max_bytes=20)
    with pytest.raises(SourceError):f.get('https://example.org/large')

@pytest.mark.parametrize('url',['http://example.org/x','https://example.org:444/x','https://user:password@example.org/x','https://evil.org/x'])
def test_url_access_boundaries(url):
    f=Fetcher(['example.org'],user_agent='Test',resolve=lambda h:None)
    with pytest.raises((SourceError,ValueError)):f.validate(url)
    f.close()

def test_canonical_tracking_removed():
    assert canonical_url('https://example.org/x?utm_source=a&id=1#top')=='https://example.org/x?id=1'

def test_source_outage_is_coverage(store,config,monkeypatch):
    cfg=dict(config);cfg['sources']=[dict(config['sources'][0],adapter='static',urls=['https://example.org/x'])]
    cfg['user_agent']='Test';cfg['limits']={**cfg['limits'],'max_response_bytes':1000,'max_documents_per_source':2}
    monkeypatch.setattr(Fetcher,'get',lambda *a,**k:(_ for _ in ()).throw(SourceError('fixture outage')))
    result=collect(store,cfg,'2026-09-01')
    assert result['sources'][0]['status']=='failed'
    assert store.records('source_check')

def test_none_provider_creates_queue(store,config):
    add_example(store,config,sample_mention(),at='2026-09-09T06:00:00Z')
    # Existing editorial extraction is already complete, requiring zero API calls.
    result=extract_pending(store,config,'none')
    assert result['calls']==0

def test_strict_schema_all_object_keys_required():
    s=strict_schema(Extraction.model_json_schema())
    def walk(x):
        if isinstance(x,dict):
            if x.get('type')=='object':
                assert x.get('additionalProperties') is False
                assert set(x.get('required',[]))==set(x.get('properties',{}))
            for y in x.values():walk(y)
        elif isinstance(x,list):
            for y in x:walk(y)
    walk(s)

def test_model_output_recorded_and_validated(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','TEST_KEY')
    def handler(request):
        data=json.loads(request.content)
        assert data['store'] is False and 'tools' not in data
        assert data['text']['format']['strict'] is True
        return httpx.Response(200,json={'status':'completed','id':'fixture-response','model':'fixture-model',
              'output':[{'content':[{'type':'output_text','text':json.dumps({'outcome':'no_relevant_content','mentions':[],'notes':[]})}]}]})
    agent=OpenAIExtractor('fixture-model',2000,client(handler))
    result,receipt=agent.extract('Untrusted source text.',{'title':'Test','published_at':None,'url':'https://example.org/test'})
    assert result.outcome=='no_relevant_content' and receipt['response_id']=='fixture-response'

def test_model_refusal_is_review(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','TEST_KEY')
    agent=OpenAIExtractor('fixture',2000,client(lambda r:httpx.Response(200,json={'status':'completed','output':[{'content':[{'type':'refusal'}]}]})))
    with pytest.raises(ValueError):agent.extract('x',{'title':'Test','published_at':None,'url':'https://example.org'})

def test_chunk_coverage():
    text='abc\n'*1000;parts=list(chunks(text,1200,100))
    assert parts[0][0]==0 and parts[-1][1]==len(text)
    assert all(a[1]>=b[0] for a,b in zip(parts,parts[1:]))
    assert all(end-start<=1200 for start,end,_ in parts)

def test_configuration_contract():
    c=load_config(Path('config/epiweekly.yaml'))
    assert c['timezone']=='Europe/Amsterdam'
    assert next(s for s in c['sources'] if s['id']=='beacon')['adapter']=='manual'

def test_who_ordering_and_modified_followup():
    calls=[]
    class Fake:
        def get(self,url,*args):
            calls.append(url)
            row={'Id':'one','UrlName':'2026-DON-fixture','Title':'Fixture','PublicationDateAndTime':'2026-08-01T00:00:00Z','LastModified':'2026-09-08T00:00:00Z'}
            return json.dumps({'value':[row]}).encode(),{},url,200
    source={'adapter':'who_odata','index_url':'https://www.who.int/api/news/diseaseoutbreaknews'}
    entries,notes=discover(source,Fake(),'2026-09-01',{'max_index_pages':2})
    assert len(calls)==2 and len(entries)==1
    assert entries[0]['published_at'].startswith('2026-08-01')
    assert 'PublicationDateAndTime' in calls[0] and 'LastModified' in calls[1]

def test_rss_discovery_marks_missing_requested_labels():
    class Fake:
        def get(self,url,*args):
            raw=b'<a href="https://example.org/feed">News</a>' if url.endswith('/index') else b'<rss><channel><item><title>One</title><link>https://example.org/one</link><pubDate>Tue, 08 Sep 2026 00:00:00 +0000</pubDate></item></channel></rss>'
            return raw,{},url,200
    entries,notes=discover({'adapter':'rss_discovery','index_url':'https://example.org/index','feed_labels':['News','Calls for data']},Fake(),'2026-09-01',{})
    assert len(entries)==1
    assert 'missing_feed_labels:calls for data' in notes

def test_budget_queue_and_cached_model_result(store,config,monkeypatch):
    calls=[]
    class Agent:
        def __init__(self,*args):pass
        def close(self):pass
        def extract(self,text,document):
            calls.append(document['title'])
            return Extraction(outcome='no_relevant_content'),{'model':'fixture','response_id':'fixture-result'}
    from epiweekly import extraction
    monkeypatch.setattr(extraction,'OpenAIExtractor',Agent)
    config['limits']['max_model_calls']=1
    for i in range(2):
        text=('Synthetic source content. '*10)+str(i)
        save_document(store,config['sources'][0],text=text,raw=text.encode(),url=f'https://example.org/{i}',content_url=f'https://example.org/{i}',title=f'Doc {i}',at='2026-09-09T06:00:00Z')
    first=extract_pending(store,config,'openai','fixture')
    assert first['calls']==1 and first['queued_chunks']==1
    second=extract_pending(store,config,'openai','fixture')
    assert second['calls']==1 and len(calls)==2
    third=extract_pending(store,config,'openai','fixture')
    assert third['calls']==0

def test_redirect_respects_target_robots():
    calls=[]
    def handler(req):
        calls.append(req.url.path)
        if req.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nDisallow: /restricted')
        if req.url.path=='/start':return httpx.Response(302,headers={'location':'/restricted'})
        return httpx.Response(200,text='should not be fetched')
    f=Fetcher(['example.org'],user_agent='Test',client=client(handler),resolve=lambda h:None,min_interval=0)
    with pytest.raises(SourceError):f.get('https://example.org/start')
    assert '/restricted' not in calls


def test_malformed_feed_reports_source_error():
    with pytest.raises(SourceError, match='valid XML'):
        parse_feed(b'<html>News & publications</html>', 'https://example.org/feed')
