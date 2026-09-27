"""Compare a compact digest with captured sources without accepting registry events."""
from pathlib import Path
import argparse,json,sqlite3,time
from datetime import date
from typing import Literal
from html import escape
from collections import Counter
from pydantic import Field,model_validator
from atlas.models import StrictModel
from atlas.codex import CodexExtractor
from atlas.config import assets
from atlas.semantics import norm
from atlas.util import write_json,digest,utcnow

class Claim(StrictModel):
    text: str = Field(min_length=1,max_length=700)
    evidence: list[int] = Field(min_length=1)

class Item(StrictModel):
    title: str = Field(min_length=1,max_length=160)
    kind: Literal['outbreak','single_case','surveillance','prevention','research']
    claims: list[Claim] = Field(min_length=1)
    urls: list[str]

class Digest(StrictModel):
    outcome: Literal['extracted','no_relevant_content','needs_review']
    quotes: list[str]
    items: list[Item]
    omitted_detail: list[str]

    @model_validator(mode='after')
    def references(self):
        if (self.outcome=='extracted' and not self.items) or (self.outcome=='no_relevant_content' and self.items):
            raise ValueError('Outcome and digest items disagree')
        for item in self.items:
            for claim in item.claims:
                if any(i<0 or i>=len(self.quotes) for i in claim.evidence):
                    raise ValueError('Evidence reference outside quote table')
        return self

def validate_evidence(result,text,source_url=""):
    errors=[];source=norm(text)
    for i,quote in enumerate(result.quotes):
        if not quote.strip() or norm(quote) not in source:errors.append(f'Quote {i} absent from captured text')
    for item in result.items:
        for url in item.urls:
            if url!=source_url and url not in text:errors.append('Resource URL absent: '+url)
    return errors

def render(root,manifest,rows,active=None):
    total_tokens=Counter()
    for row in rows:
        for usage in row.get('receipt',{}).get('usage',[]):total_tokens.update(usage)
    status={'checked_at':utcnow(),'window':manifest['window'],'documents':len(manifest['documents']),
            'completed':sum(r['state']=='completed' for r in rows),'failed':sum(r['state']=='failed' for r in rows),
            'active':active,'usage':dict(total_tokens),
            'state':'running' if active else 'interrupted' if any(r['state']=='interrupted' for r in rows) else 'complete' if len(rows)==len(manifest['documents']) else 'incomplete'}
    write_json(root/'status.json',status)
    body=f'<h1>ATLAS · One-month compact digest trial</h1><p>Source publication window: {manifest["window"][0]} through {manifest["window"][1]}. Captured sources only; no fresh collection.</p><p>{status["completed"]} completed, {status["failed"]} failed, {len(manifest["documents"])} selected publications.</p>'
    body+='<p>Run state: '+escape(status['state'])+'</p>'
    if active:body+='<p>Active: '+escape(active['title'])+' · started '+escape(active['started_at'])+'</p>'
    body+='<p>Model proposals require source review. Exact quote checks do not establish scientific accuracy. These results are separate from the accepted event registry.</p><p>Usage: '+escape(json.dumps(dict(total_tokens)))+'</p>'
    for row in rows:
        body+='<article id="'+escape(row['document_id'],quote=True)+'"><h2>'+escape(row['document']['title'])+'</h2><p>'+escape(row['state'])+' · published '+escape(row['document']['published_at'][:10])+' · '+str(round(row['elapsed_seconds'],1))+' seconds · <a href="'+escape(row['document']['url'],quote=True)+'">Original source</a> · <a href="sources/'+row['document_id']+'.txt">Captured text</a></p>'
        if row.get('error'):body+='<pre>'+escape(row['error'])+'</pre>'
        result=row.get('result',{})
        if result:body+='<p>Extraction outcome: '+escape(result['outcome'].replace('_',' '))+'</p>'
        for item in result.get('items',[]):
            body+='<h3>'+escape(item['title'])+'</h3><ul>'
            for claim in item['claims']:
                body+='<li>'+escape(claim['text'])+'<details><summary>Source evidence</summary>'+''.join('<blockquote>'+escape(result['quotes'][i])+'</blockquote>' for i in claim['evidence'])+'</details></li>'
            body+='</ul>'
            for url in item['urls']:
                if url.startswith(('https://','http://')):body+='<p><a href="'+escape(url,quote=True)+'">'+escape(url)+'</a></p>'
        if result.get('omitted_detail'):body+='<p>Detail omitted: '+escape('; '.join(result['omitted_detail']))+'</p>'
        if row.get('evidence_errors'):body+='<pre>'+escape(json.dumps(row['evidence_errors']))+'</pre>'
        body+='</article>'
    from atlas.util import atomic_write
    atomic_write(root/'index.html','<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="15"><title>ATLAS compact digest trial</title><style>body{font:17px/1.6 system-ui;max-width:1050px;margin:40px auto;padding:0 20px;color:#183441}article{border-top:1px solid #ccd8dd;padding:20px 0}blockquote{font-size:15px}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}</style><main>'+body+'</main></html>')

def run(state,out,start,end):
    if date.fromisoformat(start)>date.fromisoformat(end):raise ValueError('Publication window is reversed')
    out.mkdir(parents=True,exist_ok=True);(out/'sources').mkdir(exist_ok=True)
    with sqlite3.connect(f'file:{state}/ledger.sqlite?mode=ro',uri=True) as db:
        latest={}
        for ident,payload in db.execute("SELECT id,payload FROM records WHERE kind='document' ORDER BY seq"):
            d=json.loads(payload);latest[d['source_id'],d['url']]=(ident,d)
    selected=[(i,d) for i,d in latest.values() if d.get('published_at') and start<=d['published_at'][:10]<=end]
    selected.sort(key=lambda x:(x[1]['source_id']!='who_don',x[1]['published_at'],x[0]))
    if len(selected)>36 or sum(len((state/d['text_object']).read_text()) for _,d in selected)>650000:
        raise ValueError('Trial exceeds 36 publications or 650,000 input characters')
    prompt=assets('digest.md');contract=Digest.model_json_schema()
    manifest={'contract_version':'digest-trial-1','window':[start,end],'prompt_sha256':digest(prompt.encode()),'schema_sha256':digest(contract),'documents':[{'id':i,**d} for i,d in selected]}
    write_json(out/'manifest.json',manifest);write_json(out/'schema.json',contract);(out/'prompt.md').write_text(prompt)
    rows=[];agent=CodexExtractor('',200000,600)
    for ident,doc in selected:
        text=(state/doc['text_object']).read_text();(out/'sources'/f'{ident}.txt').write_text(text)
        key=digest([ident,digest(text.encode()),manifest['prompt_sha256'],manifest['schema_sha256']]);saved=out/(key+'.json')
        if saved.exists():rows.append(json.loads(saved.read_text()));continue
        at=utcnow();active={'document_id':ident,'title':doc['title'],'started_at':at};render(out,manifest,rows,active)
        directory=out/'attempts'/f'{key}-{time.time_ns()}';write_json(out/'active.json',active);began=time.monotonic()
        row={'document_id':ident,'document':doc,'started_at':at,'diagnostics':str(directory)}
        try:
            if doc['parse_status']!='text_ready':raise ValueError('Source requires layout review')
            if len(text)>100000:raise ValueError('Source exceeds the 100,000 character trial limit; no text was truncated')
            result,receipt=agent.extract(text,doc,directory,contract=Digest,prompt=prompt)
            row.update(state='completed',result=result.model_dump(mode='json'),receipt=receipt,evidence_errors=validate_evidence(result,text,doc["url"]))
        except Exception as exc:row.update(state='failed',error=f'{type(exc).__name__}: {exc}')
        except BaseException as exc:
            row.update(state='interrupted',error=type(exc).__name__,elapsed_seconds=time.monotonic()-began)
            write_json(saved,row);rows.append(row);render(out,manifest,rows);raise
        row['elapsed_seconds']=time.monotonic()-began;write_json(saved,row);rows.append(row);render(out,manifest,rows)
    write_json(out/'results.json',rows);render(out,manifest,rows)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,default=Path('.runtime-state'));p.add_argument('--out',type=Path,required=True);p.add_argument('--since',required=True);p.add_argument('--until',required=True);a=p.parse_args();run(a.state,a.out,a.since,a.until)
