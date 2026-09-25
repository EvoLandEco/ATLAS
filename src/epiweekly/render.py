"""Fixed report layout rendered from sealed data, with source-linked evidence."""
from __future__ import annotations
from markdown_it import MarkdownIt


def esc(value) -> str:
    if value is None: return "N/A"
    text=str(value).replace("\n"," ").replace("\r"," ")
    for ch in ["\\","`","*","_","[","]","|","<",">"]:
        text=text.replace(ch,"\\"+ch)
    return text


def human_value(row: dict, key: str) -> str:
    value=row.get(key)
    if value is None: return "N/A ("+row.get(key+"_status","not_reported")+")"
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        return f"{value:g}"
    return esc(value)


def table(headers: list[str], rows: list[list]) -> str:
    lines=["| "+" | ".join(headers)+" |", "| "+" | ".join("---" for _ in headers)+" |"]
    if not rows: rows=[["N/A (not_applicable)"]*len(headers)]
    lines += ["| "+" | ".join(str(v) for v in row)+" |" for row in rows]
    return "\n".join(lines)


def render_markdown(snapshot: dict) -> str:
    meta=snapshot["metadata"];data=snapshot["tables"];quality=meta["quality"]
    docs={d["document_id"]:d for d in data["documents"]}
    updates={u["candidate_id"]:u for u in data["updates"]}
    def refs(candidate_ids):
        ids=sorted({updates[c]["document_id"] for c in candidate_ids if c in updates})
        return "; ".join(f"[{esc(docs[d]['source_id'])} · {esc(d[:12])}]({docs[d]['url']})" for d in ids) or "N/A (not_reported)"
    events=sorted(data["events"],key=lambda e:(e["update_class"]=="carried_forward",e["disease"],e["event_id"]))
    lines=[f"# EpiWeekly | {meta['report_date']}",
           f"**{esc(meta['release_status'].upper())} · Experimental {esc(meta['software_version'])} · {esc(meta['timezone'])}**",
           f"Knowledge cutoff: `{meta['knowledge_cutoff']}`  \nReport ID: `{meta['report_id']}`"]
    if meta.get("dataset_mode")=="synthetic_demo":
        lines.append("**Synthetic demonstration: all event narratives, organizations, and counts in this report are fictional.**")
    lines += ["## 1. Weekly scan",
       f"Reviewed event records: {len(events)}. New to this registry: {sum(e['update_class']=='new_to_registry' for e in events)}. "
       f"With reviewed changes: {sum(e['update_class'] in {'updated_measurements','status_change','additional_reporting'} for e in events)}. "
       f"Mentions awaiting review: {quality['pending_review_mentions']}. Unresolved measurement series: {quality['conflicting_current_series']}.",
       "New to the registry describes discovery by this workflow. Source-reported outbreak dates appear in the event evidence.",
       table(["Event","Scope / host","Weekly change","Source-reported status"],
             [[esc(e["title"]),f"{human_value(e,'location')} / {human_value(e,'host')}",esc(e["update_class"]),esc(e["lifecycle_status"])] for e in events[:6]]),
       "## 2. Event developments"]
    for event in events:
        eid=event["event_id"]
        lines.extend([f"### {esc(event['title'])}",
            f"`{eid}` · {esc(event['kind'])} · {esc(event['disease'])}",
            esc(event["summary"]),
            table(["Field","Value"],[
                ["Host / pathogen",human_value(event,"host")+" / "+human_value(event,"pathogen")],
                ["Geography",human_value(event,"country_code")+" · "+human_value(event,"location")+" · "+esc(event["geographic_scope"])],
                ["Source-reported event start",human_value(event,"event_start")],
                ["Epidemiological as-of date",human_value(event,"as_of")],
                ["Source publication",human_value(event,"last_source_publication")],
                ["Status / freshness",esc(event["lifecycle_status"])+" / "+esc(event["freshness_status"])],
                ["Authority event identifier",human_value(event,"authority_namespace")+" / "+human_value(event,"authority_event_id")],
            ])])
        metrics=sorted([m for m in data["event_metrics"] if m["event_id"]==eid],key=lambda m:(m["metric"],m["count_kind"],m["series_id"]))
        lines.append(table(["Metric / classification","Value / unit","Count meaning / dates","Scope / definition","Change in reported cumulative"],
            [[esc(m["metric"])+" / "+esc(m["case_class"]),human_value(m,"value")+" "+esc(m["unit"])+" · "+esc(m["qualifier"]),
              esc(m["count_kind"])+"; "+human_value(m,"period_start")+" to "+human_value(m,"period_end")+"; "+esc(m["date_basis"]),
              human_value(m,"location")+"; "+human_value(m,"host")+"; "+human_value(m,"population")+"; "+human_value(m,"stratum")+"; "+human_value(m,"case_definition"),
              human_value(m,"change_in_reported_cumulative")+(" · "+esc(m["change_label"]) if m["change_label"] else "")]
             for m in metrics]))
        lines.append("Evidence: "+refs(event["evidence_candidate_ids"])+".")
    if not events: lines.append("N/A (pending_verification). Captured source documents and review counts are listed in the coverage and quality sections.")
    lines.extend(["## 3. Continuing watchlist",table(["Event","Last source publication","Status","This week"],
        [[esc(e["title"]),human_value(e,"last_source_publication"),esc(e["lifecycle_status"]),esc(e["update_class"])]
         for e in events if e["lifecycle_status"]!="resolved"]),
        "## 4. Learning and contribution opportunities"])
    opportunities=sorted(data["opportunities"],key=lambda o:(o["status"] in {"completed","declined"},-o["rank_score"],o["opportunity_id"]))
    for opp in opportunities[:8]:
        lines.extend([f"### {esc(opp['theme'])} · {esc(opp['status'])}",
            f"**Question:** {esc(opp['question'])}",f"**Next action:** {esc(opp['next_action'])}",
            f"Basis: {esc(opp['basis'])}. Relevance score: {opp['rank_score']}. Owner: {human_value(opp,'owner')}.",
            (f"Resource: [{esc(opp['resource_access'])}]({opp['resource_url']})." if opp["resource_url"] else "Resource: N/A (not_reported)."),
            "Supporting event evidence: "+refs(opp["evidence_candidate_ids"])+"."])
    if not opportunities: lines.append("N/A (not_applicable). Opportunities are generated from reviewed evidence and the configured research profile.")
    lines.extend(["## 5. Review and data-quality queue",table(["Check","Result"],[
        ["Mentions awaiting editorial review",quality["pending_review_mentions"]],
        ["Mentions with evidence validation flags",quality["evidence_flagged_mentions"]],
        ["Captured document versions",quality["captured_documents"]],
        ["Documents with some completed extraction",quality["documents_with_some_extraction"]],
        ["Documents awaiting any extraction",quality["documents_awaiting_extraction"]],
        ["Conflicting current measurement series",quality["conflicting_current_series"]],
        ["Core-source gaps",", ".join(quality["core_source_gaps"]) or "0"],
        ["Future-dated candidates excluded",len(quality["future_dated_candidates_excluded"])],
    ]),"N/A values retain a reason such as not_reported, unknown, not_applicable, conflicting, or not_comparable. "
       "Reported zeros remain numeric zeros. The private review queue contains evidence spans and candidate event matches.",
       "## 6. Source coverage",table(["Source","Role","Collection status","Retrieved / discovered","Newest source publication"],
        [[esc(s["source_name"]),esc(s["source_role"]),esc(s["status"]),f"{s['retrieved']} / {s['discovered']}",human_value(s,"newest_publication")]
         for s in data["source_coverage"]])])
    for source in data["source_coverage"]:
        if source["notes"]: lines.append("**"+esc(source["source_name"])+":** "+"; ".join(esc(n) for n in source["notes"])+".")
    lines.extend(["## 7. Dataset and analysis",
        "The accompanying bundle contains report.json, one CSV per documented table, a data dictionary, JSON Schema, "
        "a tabular data-package descriptor, analysis examples, and checksums. Observations preserve individual source claims; "
        "event_metrics selects comparable current measurements. event_history preserves previous weekly views.",
        "Cumulative differences are labeled changes in reported cumulative totals. Incident observations retain the source's interval and date basis. "
        "Source-derived figures that overlap remain separate claims linked to one event and measurement context.",
        "## 8. Methods and version record",
        f"Schema `{meta['schema_version']}` · Template `{meta['template_version']}` · Config `{meta['config_sha256']}`.",
        f"Ledger head `{meta['ledger_head_sha256']}`.",
        "Accepted source evidence, editorial event assignments, vocabulary mappings, and deterministic measurement rules produce this report. "
        "Evidence capture times and epidemiological dates remain separate. Missing weekly reporting carries the last reviewed event state forward."])
    return "\n\n".join(lines)+"\n"


def render_html(snapshot: dict) -> str:
    body=MarkdownIt("commonmark",{"html":False}).enable("table").render(render_markdown(snapshot))
    css="""
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#172c38;background:#edf2f4;line-height:1.58}
body{margin:0}main{max-width:1120px;margin:36px auto;background:white;padding:52px 58px;border-radius:18px;box-shadow:0 12px 38px #1232}
h1{font-size:2.25rem;letter-spacing:-.04em;line-height:1.2;margin:0 0 16px}h2{font-size:1.4rem;border-top:2px solid #dce7eb;padding-top:28px;margin-top:40px;color:#174f61}h3{font-size:1.1rem;margin-top:28px}
p{margin:12px 0}table{border-collapse:collapse;width:100%;font-size:.88rem;table-layout:auto;margin:18px 0 24px}th{text-align:left;background:#e9f1f4}td,th{padding:10px 12px;border-bottom:1px solid #dce7eb;vertical-align:top;overflow-wrap:anywhere}a{color:#096c86;text-decoration-thickness:1px;text-underline-offset:3px}code{font-size:.8em;overflow-wrap:anywhere;background:#f0f4f5;padding:2px 4px;border-radius:4px}strong{font-weight:650}
@media(max-width:760px){main{margin:0;padding:26px 18px;border-radius:0}table{font-size:.78rem}td,th{padding:8px 5px}h1{font-size:1.7rem}}
@media print{:root{background:white;font-size:10pt}main{margin:0;max-width:none;padding:0;box-shadow:none}h2,h3{break-after:avoid}tr{break-inside:avoid}a{color:inherit}h1{font-size:24pt}}
"""
    return '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'+\
      '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'+\
      '<title>EpiWeekly '+snapshot["metadata"]["report_date"]+'</title><style>'+css+'</style></head><body><main>'+body+'</main></body></html>\n'
