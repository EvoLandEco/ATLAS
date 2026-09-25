"""Bounded extraction agent. Captured outputs are immutable replay inputs."""
from __future__ import annotations
import json
import os
from pathlib import Path
import httpx
from .config import assets, vocabulary, publication_window, in_publication_window
from .models import Extraction, Mention
from .codex import CodexExtractor
from .semantics import normalize_mention, evidence_errors
from .store import Store
from .util import digest, uid, utcnow, write_json, read_json


def strict_schema(node):
    """OpenAI strict structured-output objects require every declared property."""
    if isinstance(node,list):
        return [strict_schema(x) for x in node]
    if not isinstance(node,dict):
        return node
    out={k:strict_schema(v) for k,v in node.items() if k!="default"}
    if out.get("type")=="object":
        out["additionalProperties"]=False
        out["required"]=list(out.get("properties",{}))
    return out


def chunks(text: str, size: int = 18000, overlap: int = 1000):
    if size <= overlap or overlap < 0:
        raise ValueError("Chunk size must exceed its nonnegative overlap")
    start=0
    while start<len(text):
        end=min(len(text),start+size)
        if end<len(text):
            boundary=text.rfind("\n",start+size//2,end)
            if boundary>start: end=boundary
        yield start,end,text[start:end]
        if end==len(text): break
        start=max(start+1,end-overlap)


class OpenAIExtractor:
    def __init__(self, model: str, max_output_tokens: int, client: httpx.Client | None = None):
        if not model.strip():
            raise ValueError("Set EPIWEEKLY_MODEL to a model available in the deployment API project")
        self.model=model;self.max_output_tokens=max_output_tokens
        self.client=client or httpx.Client(timeout=120,follow_redirects=False)

    def extract(self, text: str, document: dict) -> tuple[Extraction,dict]:
        key=os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY is required for provider=openai")
        schema=strict_schema(Extraction.model_json_schema())
        payload={"model":self.model,"store":False,"max_output_tokens":self.max_output_tokens,
            "input":[{"role":"developer","content":assets("extract.md")},
                     {"role":"user","content":json.dumps({"document_title":document["title"],
                        "publication_date":document["published_at"],"source_url":document["url"],
                        "captured_source_text":text},ensure_ascii=False)}],
            "text":{"format":{"type":"json_schema","name":"outbreak_extraction","strict":True,"schema":schema}}}
        response=self.client.post("https://api.openai.com/v1/responses",json=payload,
                                  headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
        # Exceptions report status and request URL; authorization headers remain private.
        response.raise_for_status(); data=response.json()
        if data.get("status")!="completed":
            raise ValueError("Extraction response is incomplete; retain the document in the review queue")
        texts=[]
        for item in data.get("output",[]):
            for part in item.get("content",[]):
                if part.get("type")=="refusal":
                    raise ValueError("Provider returned a refusal; document requires editorial extraction")
                if part.get("type")=="output_text": texts.append(part["text"])
        result=Extraction.model_validate_json("".join(texts))
        receipt={"provider":"openai","requested_model":self.model,"returned_model":data.get("model",self.model),
                 "response_id":data.get("id"),"usage":data.get("usage",{}),"status":data.get("status")}
        return result,receipt

    def close(self):
        self.client.close()


def add_extraction(store: Store, document_id: str, result: Extraction, *, at: str,
                   extraction_key: str, provenance: dict, chunk_start: int = 0, chunk_end: int | None = None) -> list[str]:
    row=store.get(document_id)
    if row["kind"]!="document": raise ValueError("Expected a document record")
    doc=row["payload"]
    text=(store.home/doc["text_object"]).read_text(encoding="utf-8")
    candidate_ids=[]
    for raw_mention in result.mentions:
        mention=normalize_mention(raw_mention,vocabulary())
        errors=evidence_errors(mention,text)
        payload={"document_id":document_id,"mention":mention.model_dump(mode="json"),
                 "raw_mention":raw_mention.model_dump(mode="json"),"validation_errors":errors,
                 "extraction_key":extraction_key,"provenance":provenance,
                 "chunk_start":chunk_start,"chunk_end":chunk_end if chunk_end is not None else len(text)}
        candidate_id=uid("cand",document_id,payload)
        store.append("candidate",payload,at,candidate_id)
        candidate_ids.append(candidate_id)
    payload={"document_id":document_id,"extraction_key":extraction_key,"outcome":result.outcome,
             "notes":result.notes,"candidate_ids":candidate_ids,"provenance":provenance,
             "chunk_start":chunk_start,"chunk_end":chunk_end if chunk_end is not None else len(text)}
    store.append("extraction",payload,at,uid("extract",extraction_key))
    return candidate_ids


def extract_pending(store: Store, config: dict, provider: str = "none", model: str = "", *, as_of: str | None = None) -> dict:
    if provider not in {"none","openai","codex"}: raise ValueError("Unknown extraction provider")
    limits=config["limits"]
    window=publication_window(config,as_of)
    completed={r["payload"]["extraction_key"] for r in store.records("extraction")}
    summary={"provider":provider,"calls":0,"cache_hits":0,"completed_chunks":0,"queued_chunks":0,
             "failed_chunks":0,"candidate_count":0,"input_characters":0}
    # A reviewed local extraction can cover a whole document.
    editorial_docs={r["payload"]["document_id"] for r in store.records("extraction")
                    if r["payload"]["provenance"].get("provider")=="editorial"}
    agent=OpenAIExtractor(model,limits["max_output_tokens"]) if provider=="openai" else None
    if provider=="codex":
        agent=CodexExtractor(model,limits.get("codex_output_bytes",1000000),limits.get("codex_timeout_seconds",180))
    tasks=[]
    prompt_sha=digest(assets("extract.md").encode());schema_sha=digest(Extraction.model_json_schema())
    try:
        for row in store.records("document"):
            doc=row["payload"]
            if not in_publication_window(doc,window):continue
            if row["id"] in editorial_docs: continue
            text=(store.home/doc["text_object"]).read_text(encoding="utf-8")
            for start,end,piece in chunks(text,limits["chunk_characters"],limits["chunk_overlap"]):
                key=digest([row["id"],digest(piece.encode()),provider,model,prompt_sha,schema_sha,vocabulary()])
                if key in completed: continue
                task={"document_id":row["id"],"extraction_key":key,"start":start,"end":end}
                if doc["parse_status"]!="text_ready":
                    tasks.append({**task,"reason":"source_layout_review"});summary["queued_chunks"]+=1;continue
                cache=store.home/"extractions"/(key+".json")
                provenance={"provider":provider,"model":model or None,"prompt_sha256":prompt_sha,
                            "schema_sha256":schema_sha,"vocabulary_sha256":digest(vocabulary())}
                if cache.exists():
                    cached=read_json(cache); result=Extraction.model_validate(cached["result"])
                    provenance.update(cached["receipt"]);summary["cache_hits"]+=1
                elif agent is None or summary["calls"]>=limits["max_model_calls"] or summary["input_characters"]+len(piece)>limits["max_input_characters"]:
                    tasks.append({**task,"reason":"provider_none" if agent is None else "model_budget"})
                    summary["queued_chunks"]+=1; continue
                else:
                    summary["calls"]+=1;summary["input_characters"]+=len(piece)
                    try:
                        result,receipt=agent.extract(piece,doc)
                        write_json(cache,{"result":result.model_dump(mode="json"),"receipt":receipt})
                        provenance.update(receipt)
                    except (httpx.HTTPError,ValueError,KeyError) as exc:
                        summary["failed_chunks"]+=1
                        tasks.append({**task,"reason":type(exc).__name__+":"+str(exc)[:180]})
                        continue
                ids=add_extraction(store,row["id"],result,at=utcnow(),extraction_key=key,
                                   provenance=provenance,chunk_start=start,chunk_end=end)
                summary["completed_chunks"]+=1;summary["candidate_count"]+=len(ids)
        write_json(store.home/"review"/"extraction_tasks.json",tasks)
        store.append("extraction_check",summary,utcnow())
        return summary
    finally:
        if agent: agent.close()
