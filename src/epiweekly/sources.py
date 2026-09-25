"""Bounded public-source retrieval. Provider endpoints are allowlisted configuration."""
from __future__ import annotations
import io
import ipaddress
import json
import re
import socket
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit, urlencode
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import ParseError
import httpx
from pypdf import PdfReader
from .store import Store
from .util import canonical_url, digest, stamp, uid, utcnow, canonical

ADAPTER_VERSION = "0.1.0"


class SourceError(RuntimeError):
    pass


def public_host(host: str) -> None:
    addresses = socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise SourceError("The source hostname must resolve to public addresses")


class Fetcher:
    def __init__(self, hosts: list[str], *, user_agent: str, timeout: float = 30,
                 max_bytes: int = 16_000_000, min_interval: float = 1.0,
                 client: httpx.Client | None = None, resolve=public_host):
        self.hosts = set(hosts)
        self.ua = user_agent
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.min_interval = min_interval
        self.client = client or httpx.Client(timeout=timeout,follow_redirects=False)
        self.resolve = resolve
        self.robots = {}
        self.last_request = {}

    def close(self):
        self.client.close()

    def validate(self,url: str) -> str:
        url = canonical_url(url)
        p = urlsplit(url)
        if p.scheme != "https" or p.hostname not in self.hosts or p.port not in (None,443):
            raise SourceError("URL is outside the configured HTTPS host allowlist")
        self.resolve(p.hostname)
        return url

    def _request(self,url: str, headers: dict | None = None, *, enforce_robots: bool = False) -> tuple[bytes,dict,str,int]:
        for _ in range(5):
            url = self.validate(url)
            if enforce_robots:self._robots_allowed(url)
            host = urlsplit(url).hostname
            delay = self.min_interval - (time.monotonic()-self.last_request.get(host,0))
            if delay > 0:
                time.sleep(delay)
            self.last_request[host] = time.monotonic()
            with self.client.stream("GET",url,headers={"User-Agent":self.ua,**(headers or {})},timeout=self.timeout) as r:
                if r.status_code in (301,302,303,307,308):
                    url = urljoin(url,r.headers.get("location",""))
                    # The next iteration validates the redirect before another request.
                    continue
                if r.status_code == 304:
                    return b"",dict(r.headers),url,304
                r.raise_for_status()
                chunks=[]; total=0
                for chunk in r.iter_bytes():
                    total += len(chunk)
                    if total > self.max_bytes:
                        raise SourceError("Source response exceeds configured byte limit")
                    chunks.append(chunk)
                return b"".join(chunks),dict(r.headers),url,r.status_code
        raise SourceError("Source exceeded redirect limit")

    def _robots_allowed(self,url: str) -> None:
        p=urlsplit(url); origin=f"{p.scheme}://{p.netloc}"
        if origin not in self.robots:
            try:
                raw,_,_,_=self._request(origin+"/robots.txt")
                parser=RobotFileParser(); parser.parse(raw.decode("utf-8",errors="replace").splitlines())
                self.robots[origin]=parser
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (404,410):
                    self.robots[origin]=None
                else:
                    raise SourceError("robots.txt access requires review") from exc
        if self.robots[origin] is not None and not self.robots[origin].can_fetch(self.ua,url):
            raise SourceError("robots.txt requests a different access route")
    def get(self,url: str, headers: dict | None = None) -> tuple[bytes,dict,str,int]:
        url=self.validate(url)
        # At most two attempts; quota and authorization responses go to source health.
        for attempt in range(2):
            try:
                return self._request(url,headers,enforce_robots=True)
            except (httpx.TimeoutException,httpx.ConnectError):
                if attempt:
                    raise
                time.sleep(1)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and not attempt:
                    time.sleep(1); continue
                raise
        raise SourceError("Retrieval attempts exhausted")


def parse_date(value: str | None) -> tuple[str | None,str]:
    if not value:
        return None,"unknown"
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}",value.strip()):
            datetime.strptime(value,"%Y-%m-%d")
            return value,"day"
        try:
            dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        except ValueError:
            dt=parsedate_to_datetime(value)
        if dt.tzinfo is None:
            return dt.date().isoformat(),"day"
        return stamp(dt.isoformat()),"instant"
    except (ValueError,TypeError,OverflowError):
        return None,"unknown"


def html_text(raw: bytes | str, *, main_only: bool = True) -> tuple[str,str,str | None,str]:
    soup=BeautifulSoup(raw,"html.parser")
    title_node=soup.find("h1") or soup.find("title")
    title=title_node.get_text(" ",strip=True) if title_node else "Untitled source document"
    published=None; precision="unknown"
    time_node=soup.select_one("time[datetime]")
    if time_node:
        published,precision=parse_date(time_node.get("datetime"))
    for key in ["article:published_time","datePublished","DC.date.issued","dcterms.date"]:
        node=soup.find("meta",attrs={"property":key}) or soup.find("meta",attrs={"name":key})
        if node and not published:
            published,precision=parse_date(node.get("content"))
    for node in soup.select("script[type='application/ld+json']"):
        try:
            obj=json.loads(node.string or "{}")
            items=obj if isinstance(obj,list) else [obj]
            for item in items:
                if isinstance(item,dict) and not published:
                    published,precision=parse_date(item.get("datePublished"))
        except (ValueError,TypeError):
            pass
    content=(soup.find("main") or soup.find("article") or soup.body or soup) if main_only else soup
    for node in content.select("script,style,nav,footer,header,form,noscript,svg"):
        node.decompose()
    links=sorted({urljoin("",a.get("href","")) for a in content.select("a[href]")
                  if a.get("href","").startswith("https://")})
    text="\n".join(line.strip() for line in content.get_text("\n",strip=True).splitlines() if line.strip())
    if links:
        text += "\n\nSOURCE LINKS\n"+"\n".join(links)
    return text,title,published,precision


def pdf_text(raw: bytes) -> tuple[str,str]:
    reader=PdfReader(io.BytesIO(raw))
    if len(reader.pages)>150:
        raise SourceError("PDF exceeds the 150-page extraction budget")
    pages=[]; sparse=0
    for n,page in enumerate(reader.pages,1):
        text=page.extract_text() or ""
        if len(text.strip())<30:
            sparse+=1
        pages.append(f"[[PAGE {n}]]\n{text.strip()}")
    status="needs_review" if sparse or not pages else "text_ready"
    return "\n\n".join(pages),status


def parse_feed(raw: bytes, base_url: str) -> list[dict]:
    try:
        root=ET.fromstring(raw)
    except (ParseError, DefusedXmlException) as exc:
        raise SourceError("Source feed is not valid XML; access route requires review") from exc
    entries=[e for e in root.iter() if e.tag.split("}")[-1] in ("item","entry")]
    out=[]
    for entry in entries:
        fields={}
        for ch in entry:
            name=ch.tag.split("}")[-1]
            if name=="link":
                if ch.attrib.get("rel","alternate")=="alternate":
                    fields["url"]=ch.attrib.get("href") or ch.text
            elif name in ("title","pubDate","published","updated","guid"):
                fields[name]="".join(ch.itertext()).strip()
        if not fields.get("url"):
            continue
        published,precision=parse_date(fields.get("published") or fields.get("pubDate"))
        modified,_=parse_date(fields.get("updated"))
        out.append({"url":urljoin(base_url,fields["url"].strip()),"title":fields.get("title","Untitled source document"),
                    "published_at":published,"publication_precision":precision,"modified_at":modified})
    if not out:
        raise SourceError("Feed parsed with zero usable entries; source contract review required")
    return out


def save_document(store: Store, source: dict, *, text: str, raw: bytes, url: str, content_url: str,
                  title: str, at: str, published_at: str | None = None, publication_precision: str = "unknown",
                  modified_at: str | None = None, mime: str = "text/html", parse_status: str = "text_ready") -> str:
    url=canonical_url(url); content_url=canonical_url(content_url)
    text=text.strip()+"\n"
    doc_id=uid("doc",source["id"],url,digest(text.encode()),published_at,modified_at,title,parse_status,ADAPTER_VERSION)
    if store.has(doc_id):
        return doc_id
    payload={"source_id":source["id"],"url":url,"content_url":content_url,"title":title,
             "published_at":published_at,"published_at_status":"reported" if published_at else "not_reported",
             "publication_precision":publication_precision,"modified_at":modified_at,
             "modified_at_status":"reported" if modified_at else "not_reported",
             "mime":mime,"parse_status":parse_status,"adapter_version":ADAPTER_VERSION,
             "text_object":store.object(text.encode(),"txt"),"text_sha256":digest(text.encode()),
             "raw_object":store.object(raw,"bin"),"raw_sha256":digest(raw)}
    store.append("document",payload,at,doc_id)
    return doc_id


def discover(source: dict, fetcher: Fetcher, since: str, limits: dict) -> tuple[list[dict],list[str]]:
    adapter=source["adapter"]; notes=[]
    if adapter=="manual":
        return [],["manual_access"]
    if adapter=="static":
        return [{"url":u,"title":source["name"],"published_at":None,"publication_precision":"unknown"}
                for u in source["urls"]],notes
    if adapter=="who_odata":
        entries={}
        # Editorial publication time is separate from migration/last-modified time.
        for ordering in ["PublicationDateAndTime","LastModified"]:
            reached=False
            for page in range(limits.get("max_index_pages",3)):
                query=urlencode({"$orderby":ordering+" desc","$top":50,"$skip":page*50})
                raw,_,_,_=fetcher.get(source["index_url"]+"?"+query)
                data=json.loads(raw)
                if not isinstance(data.get("value"),list):
                    raise SourceError("WHO OData value collection changed")
                rows=data["value"]
                if not rows:
                    reached=True; break
                for item in rows:
                    date_string=item.get(ordering) or ""
                    if date_string and date_string[:10]<since[:10]:
                        reached=True; continue
                    url="https://www.who.int/emergencies/disease-outbreak-news/item/"+item["UrlName"].lstrip("/")
                    entries[item["Id"]]={"url":url,"who_item":item,"title":item.get("Title","WHO DON"),
                        "published_at":item.get("PublicationDateAndTime"),"publication_precision":"instant",
                        "modified_at":item.get("LastModified")}
                if reached or len(rows)<50:
                    reached=True; break
            if not reached:
                notes.append("index_page_cap:"+ordering)
        if not entries:
            notes.append("empty_window")
        return list(entries.values()),notes
    raw,_,index_url,_=fetcher.get(source["index_url"])
    soup=BeautifulSoup(raw,"html.parser")
    if adapter=="rss_discovery":
        labels={x.casefold() for x in source["feed_labels"]}
        feeds=sorted({urljoin(index_url,a["href"]) for a in soup.select("a[href]")
                      if a.get_text(" ",strip=True).casefold() in labels})
        found_labels={a.get_text(" ",strip=True).casefold() for a in soup.select("a[href]")}
        missing_labels=labels-found_labels
        if missing_labels:notes.append("missing_feed_labels:"+",".join(sorted(missing_labels)))
        if not feeds:
            raise SourceError("Published RSS feed labels changed")
        entries=[]
        for feed in feeds:
            data,_,final,_=fetcher.get(feed)
            found=parse_feed(data,final)
            dated=[x["published_at"] for x in found if x["published_at"]]
            if not dated or min(dated)[:10]>since[:10]:
                notes.append("feed_window_incomplete")
            entries.extend(found)
    elif adapter=="html_index":
        pattern=re.compile(source["link_pattern"])
        entries=[{"url":urljoin(index_url,a["href"]),"title":a.get_text(" ",strip=True),
                  "published_at":None,"publication_precision":"unknown"}
                 for a in soup.select("a[href]") if pattern.search(urljoin(index_url,a["href"]))]
        notes.append("index_window_unverified")
    else:
        raise SourceError("Unknown adapter")
    unique={x["url"]:x for x in entries if not x.get("published_at") or x["published_at"][:10]>=since[:10]}
    return list(unique.values()), sorted(set(notes))


def retrieve_entry(store: Store, source: dict, entry: dict, fetcher: Fetcher) -> str:
    if "who_item" in entry:
        item=entry["who_item"]
        pieces=[f"<h1>{item.get('OverrideTitle') or item.get('Title','WHO DON')}</h1>"]
        pieces.extend(f"<h2>{key}</h2>"+(item.get(key) or "") for key in
                      ["Summary","Overview","Epidemiology","Assessment","Response","Advice","FurtherInformation"])
        text,title,_,_=html_text("\n".join(pieces),main_only=False)
        published,precision=parse_date(entry.get("published_at"))
        return save_document(store,source,text=text,raw=canonical(item).encode(),url=entry["url"],content_url=entry["url"],
            title=title,at=utcnow(),published_at=published,publication_precision=precision,
            modified_at=item.get("LastModified"),mime="application/json")
    prior=[r for r in store.records("document") if r["payload"]["source_id"]==source["id"]
           and r["payload"]["url"]==canonical_url(entry["url"])]
    previous=prior[-1] if prior else None
    receipts=[r["payload"] for r in store.records("fetch_receipt") if r["payload"].get("url")==canonical_url(entry["url"])]
    conditional={}
    if receipts and previous and not source.get("primary_pdf"):
        if receipts[-1].get("etag"):
            conditional["If-None-Match"]=receipts[-1]["etag"]
        elif receipts[-1].get("last_modified"):
            conditional["If-Modified-Since"]=receipts[-1]["last_modified"]
    raw,headers,final,status=fetcher.get(entry["url"],conditional)
    if status==304:
        if previous is None:
            raise SourceError("304 received without a cached document")
        return previous["id"]
    mime=headers.get("content-type","").split(";")[0]
    title=entry.get("title") or "Untitled source document"
    published=entry.get("published_at"); precision=entry.get("publication_precision","unknown")
    parse_status="text_ready"
    if mime=="application/pdf" or raw.startswith(b"%PDF"):
        text,parse_status=pdf_text(raw); mime="application/pdf"
    else:
        text,parsed_title,parsed_date,parsed_precision=html_text(raw)
        title=parsed_title if parsed_title!="Untitled source document" else title
        if parsed_date:
            published,precision=parsed_date,parsed_precision
        if source.get("primary_pdf"):
            soup=BeautifulSoup(raw,"html.parser")
            pdfs=[urljoin(final,a["href"]) for a in soup.select("a[href]")
                  if ".pdf" in a["href"].lower() and re.search(source["primary_pdf"],a["href"])
                  and not re.search(r"maps|graphs",a["href"],re.I)]
            if not pdfs:
                raise SourceError("The primary bulletin PDF link needs adapter review")
            raw,headers,final,_=fetcher.get(pdfs[0]); mime="application/pdf"
            text,parse_status=pdf_text(raw)
        if len(text.strip())<120:
            parse_status="needs_review"
    doc=save_document(store,source,text=text,raw=raw,url=entry["url"],content_url=final,title=title,
                      at=utcnow(),published_at=published,publication_precision=precision,
                      modified_at=entry.get("modified_at"),mime=mime,parse_status=parse_status)
    store.append("fetch_receipt",{"url":canonical_url(entry["url"]),"document_id":doc,
        "etag":headers.get("etag"),"last_modified":headers.get("last-modified"),"http_status":status},utcnow())
    return doc


def collect(store: Store, config: dict, since: str) -> dict:
    totals={"documents_seen":0,"documents_new":0,"sources":[]}
    for source in config["sources"]:
        check={"source_id":source["id"],"enabled":source.get("enabled",False),
               "required":source.get("required",False),"discovered":0,"retrieved":0,"new_documents":0,
               "status":"disabled","notes":[],"window_start":since,
               "oldest_publication":None,"newest_publication":None}
        if not source.get("enabled",False):
            store.append("source_check",check,utcnow()); totals["sources"].append(check); continue
        if source["adapter"]=="manual":
            check.update(status="manual_access",notes=["Import a provider-authorized document or export"])
            store.append("source_check",check,utcnow()); totals["sources"].append(check); continue
        fetcher=Fetcher(source["allowed_hosts"],user_agent=config["user_agent"],
                        max_bytes=config["limits"]["max_response_bytes"],
                        min_interval=config["limits"].get("request_interval_seconds",1))
        try:
            entries,notes=discover(source,fetcher,since,config["limits"])
            # Revisit a bounded set of previously seen source URLs to detect old-page revisions.
            recent={}
            for row in store.records("document"):
                p=row["payload"]
                if p["source_id"]==source["id"]:
                    recent[p["url"]]={"url":p["url"],"title":p["title"],"published_at":p["published_at"],
                                     "publication_precision":p["publication_precision"]}
            if source["adapter"]!="who_odata":
                known_urls={e["url"] for e in entries}
                entries.extend(e for e in list(recent.values())[-config["limits"].get("revisit_documents",8):]
                               if e["url"] not in known_urls)
            entries.sort(key=lambda x:(x.get("published_at") or "",x["url"]),reverse=True)
            check["discovered"]=len(entries)
            cap=config["limits"]["max_documents_per_source"]
            if len(entries)>cap:
                notes.append("document_cap_reached")
            check["notes"]=sorted(set(notes))
            dates=[]
            for entry in entries[:cap]:
                before=len(store.records("document"))
                try:
                    doc=retrieve_entry(store,source,entry,fetcher)
                    check["retrieved"]+=1
                    check["new_documents"]+=len(store.records("document"))-before
                    published=store.get(doc)["payload"]["published_at"]
                    if published: dates.append(published)
                except (httpx.HTTPError,SourceError,ValueError,KeyError,OSError) as exc:
                    check["notes"].append(f"document_error:{type(exc).__name__}:{str(exc)[:180]}")
            if dates:
                check["oldest_publication"]=min(dates);check["newest_publication"]=max(dates)
            check["status"]="ok" if check["retrieved"] and not check["notes"] else "partial" if check["retrieved"] else "failed" if check["notes"] else "empty"
        except (httpx.HTTPError,SourceError,ValueError,KeyError,OSError) as exc:
            check.update(status="failed",notes=[f"{type(exc).__name__}:{str(exc)[:240]}"])
        finally:
            fetcher.close()
        store.append("source_check",check,utcnow())
        totals["documents_seen"]+=check["retrieved"];totals["documents_new"]+=check["new_documents"]
        totals["sources"].append(check)
    return totals
