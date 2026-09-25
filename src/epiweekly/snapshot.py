"""Deterministic event and measurement views at an explicit knowledge cutoff."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from . import __version__, SCHEMA_VERSION, TEMPLATE_VERSION
from .config import assets, vocabulary, config_hash
from .models import Extraction
from .registry import accepted_candidates, current_reviews, review_queue
from .semantics import series_key, cumulative_change
from .store import Store
from .tables import TABLES, complete_row
from .util import digest, uid, stamp

RULES={
 "cross_border": ("spatiotemporal_networks","Can time-stamped geographic observations distinguish spatial expansion from reporting delay?",
                  "Check available aggregate dates and locations; scope a reproducible spatial or mobility analysis."),
 "one_health_interface": ("one_health","Which host-interface observations would clarify the reported exposure pathways?",
                         "Map the available human, animal, and environmental evidence and identify a validation partner."),
 "transmission_uncertain": ("inference","Which competing transmission explanations can the available observations distinguish?",
                          "List the competing explanations and the minimum observations needed to compare them."),
 "genomic_data": ("phylodynamics","Do the available sequences and sampling metadata support a useful evolutionary or transmission analysis?",
                 "Check access, sample dates, geographic coverage, and sampling bias before defining an analysis."),
 "network_question": ("temporal_networks","Can a temporal contact representation answer a prevention or control question for this event?",
                     "Identify the public contact or movement variables and specify a small sensitivity analysis."),
 "public_data": ("reproducible_analysis","What question can the linked public observations answer reproducibly?",
                "Inspect the data dictionary, dates, coverage, and reuse terms; prepare an analysis notebook."),
 "reporting_revision": ("observation_process","How much of the reported change follows revision, delay, or a definition change?",
                       "Compare preserved report versions and document changes in ascertainment or case definitions."),
}


def _value_fields(target: dict, field: str, value: dict):
    target[field]=value["value"];target[field+"_status"]=value["status"]


def build_snapshot(store: Store, config: dict, as_of: str, *, report_date: str | None = None,
                   previous: dict | None = None, build_fingerprint: dict | None = None) -> dict:
    as_of=stamp(as_of)
    local=datetime.fromisoformat(as_of.replace("Z","+00:00")).astimezone(ZoneInfo(config["timezone"]))
    report_date=report_date or local.date().isoformat()
    if previous and previous["metadata"]["knowledge_cutoff"]>=as_of:
        raise ValueError("The preceding snapshot must have an earlier knowledge cutoff")
    visible=store.records(as_of=as_of)
    head=visible[-1]["record_hash"] if visible else "0"*64
    run_id=uid("report",report_date,as_of,head,config_hash(config),build_fingerprint or {},
               (previous or {}).get("metadata",{}).get("report_id"))
    docs={r["id"]:r for r in store.records("document",as_of)}
    all_accepted=accepted_candidates(store,as_of)
    excluded_future=[]
    accepted=[]
    for row in all_accepted:
        doc=docs.get(row["payload"]["document_id"])
        if doc is None: continue
        pub=doc["payload"]["published_at"]
        if pub and ((doc["payload"]["publication_precision"]=="instant" and stamp(pub)>as_of)
                    or (doc["payload"]["publication_precision"]=="day" and pub>as_of[:10])):
            excluded_future.append(row["id"]);continue
        mention=row["payload"]["mention"]
        if (mention["as_of"]["value"] and mention["as_of"]["value"]>local.date().isoformat()) or any(
            o["period_end"]["value"] and o["period_end"]["value"]>local.date().isoformat() for o in mention["observations"]):
            excluded_future.append(row["id"]);continue
        accepted.append(row)
    superseded={cid for r in accepted for cid in r["review"]["payload"].get("supersedes_candidate_ids",[])}
    data={name:[] for name in TABLES}
    identity_times={}
    for r in store.records("review",as_of):
        if r["payload"]["action"]=="accept":
            key=r["payload"]["event_key"]
            identity_times.setdefault(key,r["recorded_at"])
    for key,first in sorted(identity_times.items()):
        data["event_identities"].append({"event_id":uid("evt",key),"event_key":key,"first_assigned_at":first,
            "current_candidate_count":sum(r["event_key"]==key for r in accepted)})
    grouped=defaultdict(list);observations=[]
    for row in accepted:
        m=row["payload"]["mention"];doc=docs[row["payload"]["document_id"]]["payload"]
        grouped[row["event_id"]].append(row)
        update={"candidate_id":row["id"],"event_id":row["event_id"],"document_id":row["payload"]["document_id"],
                "source_id":doc["source_id"],"known_at":row["recorded_at"],"reviewed_at":row["review"]["recorded_at"],
                "summary":m["summary"],"superseded":row["id"] in superseded,"review_id":row["review"]["id"]}
        _value_fields(update,"as_of",m["as_of"]);data["updates"].append(update)
        for index,o in enumerate(m["observations"]):
            obs={"observation_id":uid("obs",row["id"],index,o),"series_id":uid("series",row["event_id"],series_key(m,o)),
                 "event_id":row["event_id"],"candidate_id":row["id"],"document_id":row["payload"]["document_id"],
                 "source_id":doc["source_id"],"known_at":row["recorded_at"],"source_publication":doc["published_at"],
                 "source_publication_status":doc["published_at_status"],"superseded":row["id"] in superseded,
                 "selected_current":False,"evidence_locator":o["evidence"]["locator"],
                 "geographic_scope":m["geographic_scope"],"disease":m["disease"]["value"]}
            for key in ["metric","value","value_status","unit","count_kind","case_class","date_basis",
                        "denominator","denominator_status","qualifier"]: obs[key]=o[key]
            for key in ["period_start","period_end","case_definition","population","stratum","origin_authority"]: _value_fields(obs,key,o[key])
            for key in ["as_of","host","country_code","location"]: _value_fields(obs,key,m[key])
            observations.append(obs)
    source_priorities={s["id"]:s.get("priority",10) for s in config["sources"]}
    byseries=defaultdict(list)
    for obs in observations:
        if not obs["superseded"]: byseries[obs["series_id"]].append(obs)
    old_metrics={r["series_id"]:r for r in (previous or {}).get("tables",{}).get("event_metrics",[])}
    for series,rows in sorted(byseries.items()):
        dated=[r for r in rows if r["period_end"]]
        asof_dated=[r for r in rows if r["as_of"]]
        if dated:
            coordinate=max(r["period_end"] for r in dated)
            current=[r for r in dated if r["period_end"]==coordinate]
            selection_basis="latest_known_period_end"
        elif asof_dated:
            coordinate=max(r["as_of"] for r in asof_dated)
            current=[r for r in asof_dated if r["as_of"]==coordinate]
            selection_basis="latest_explicit_as_of"
        else:
            coordinate=max(r["known_at"][:10] for r in rows)
            current=[r for r in rows if r["known_at"][:10]==coordinate]
            selection_basis="latest_capture_date_with_unknown_measurement_time"
        current.sort(key=lambda r:(source_priorities.get(r["source_id"],10),r["source_id"],r["observation_id"]))
        rep=current[0]
        numeric={r["value"] for r in current if r["value_status"]=="reported"}
        conflict=len(numeric)>1
        # A missing report does not override a same-coordinate explicit numeric report.
        if numeric and not conflict:
            rep=next(r for r in current if r["value_status"]=="reported")
        if not conflict and rep["value_status"]=="reported": rep["selected_current"]=True
        metric={key:rep[key] for key in ["series_id","event_id","metric","unit","count_kind","case_class","date_basis",
            "disease","host","host_status","country_code","country_code_status","location","location_status","geographic_scope",
            "qualifier","denominator","denominator_status",
            "period_start","period_start_status","period_end","period_end_status","population","population_status",
            "stratum","stratum_status","case_definition","case_definition_status","origin_authority","origin_authority_status"]}
        metric.update(value=None if conflict else rep["value"],value_status="conflicting" if conflict else rep["value_status"],
                      selected_observation_id=None if conflict or rep["value"] is None else rep["observation_id"],
                      selected_observation_id_status="conflicting" if conflict else "reported" if rep["value"] is not None else "not_reported",
                      supporting_observation_ids=sorted(r["observation_id"] for r in current),selection_basis=selection_basis)
        delta,status=cumulative_change(metric,old_metrics.get(series))
        label=None if delta is None else "downward_revision" if delta<0 else "increase_in_reported_total" if delta>0 else "unchanged_reported_total"
        metric.update(change_in_reported_cumulative=delta,change_in_reported_cumulative_status=status,
                      change_label=label,change_label_status="reported" if label else "not_comparable")
        data["event_metrics"].append(metric)
    data["observations"]=observations
    old_events={r["event_id"]:r for r in (previous or {}).get("tables",{}).get("events",[])}
    current_metrics_by_event=defaultdict(list);old_metrics_by_event=defaultdict(list)
    for metric in data["event_metrics"]: current_metrics_by_event[metric["event_id"]].append(metric)
    for metric in old_metrics.values(): old_metrics_by_event[metric["event_id"]].append(metric)
    def measurement_fingerprint(rows):
        return sorted((m["series_id"],str(m["value"]),m["value_status"],m["period_end"] or "") for m in rows)
    for event_id,rows in sorted(grouped.items()):
        current=[r for r in rows if r["id"] not in superseded]
        if not current: continue
        current.sort(key=lambda r:(r["payload"]["mention"]["as_of"]["value"] or "",
                         docs[r["payload"]["document_id"]]["payload"]["published_at"] or "",r["review"]["recorded_at"],r["id"]))
        latest=current[-1];m=latest["payload"]["mention"]
        explicit=[r for r in current if r["payload"]["mention"]["reported_status"]!="unknown"]
        lifecycle=explicit[-1]["payload"]["mention"]["reported_status"] if explicit else "unknown"
        pubs=[docs[r["payload"]["document_id"]]["payload"]["published_at"] for r in current]
        pub=max([p for p in pubs if p],default=None)
        freshness=(datetime.fromisoformat(as_of.replace("Z","+00:00")).date()-datetime.fromisoformat(pub.replace("Z","+00:00")).date()).days if pub else None
        event={"event_id":event_id,"event_key":latest["event_key"],"title":m["title"],"kind":m["kind"],
               "disease":m["disease"]["value"],"geographic_scope":m["geographic_scope"],"lifecycle_status":lifecycle,
               "first_seen_at":min(docs[r["payload"]["document_id"]]["recorded_at"] for r in rows),
               "last_reviewed_at":max(r["review"]["recorded_at"] for r in current),"last_source_publication":pub,
               "freshness_days":freshness,"freshness_status":"unknown" if freshness is None else "stale" if freshness>config.get("event_stale_days",21) else "current",
               "summary":m["summary"],"evidence_candidate_ids":sorted(r["id"] for r in current),
               "tags":sorted({tag for r in current for tag in r["payload"]["mention"]["tags"]})}
        for key in ["pathogen","host","country_code","location","event_start","as_of","authority_event_id","authority_namespace"]: _value_fields(event,key,m[key])
        if event["event_start"] is None:
            earlier=[r["payload"]["mention"]["event_start"] for r in current if r["payload"]["mention"]["event_start"]["value"]]
            if earlier:_value_fields(event,"event_start",earlier[-1])
        old=old_events.get(event_id)
        if old is None: change="new_to_registry";description="Newly entered in the local registry; the outbreak start remains the source-reported date."
        elif old["lifecycle_status"]!=lifecycle: change="status_change";description=f"Reviewed status changed from {old['lifecycle_status']} to {lifecycle}."
        elif measurement_fingerprint(current_metrics_by_event[event_id])!=measurement_fingerprint(old_metrics_by_event[event_id]):
            change="updated_measurements";description="At least one reviewed measurement, definition, time coordinate, or conflict status changed."
        elif old["evidence_candidate_ids"]!=event["evidence_candidate_ids"]: change="additional_reporting";description="Supporting reporting changed while selected measurement values remained the same."
        else: change="carried_forward";description="Retained on the watchlist with the previous reviewed evidence."
        event["update_class"]=change
        data["changes"].append({"event_id":event_id,"change_type":change,"description":description})
        data["events"].append(event)
    present={e["event_id"] for e in data["events"]}
    for old_id in sorted(set(old_events)-present):
        data["changes"].append({"event_id":old_id,"change_type":"removed_after_review",
                                "description":"The current editorial assignment or acceptance changed; earlier sealed snapshots retain their original representation."})
    for row in store.records("relation",as_of):
        r=row["payload"]
        data["relationships"].append({"relationship_id":row["id"],"from_event_id":uid("evt",r["from_event_key"]),
            "to_event_id":uid("evt",r["to_event_key"]),"relation":r["relation"],"basis":r["basis"],
            "evidence_candidate_id":r["evidence_candidate_id"],"rationale":r["rationale"],"recorded_at":row["recorded_at"]})
    opportunity_decisions={r["payload"]["opportunity_id"]:r["payload"] for r in store.records("opportunity_decision",as_of)}
    old_opportunities={r["opportunity_id"]:r for r in (previous or {}).get("tables",{}).get("opportunities",[])}
    for event in data["events"]:
        rows=[r for r in grouped[event["event_id"]] if r["id"] not in superseded]
        proposals=[]
        for tag in event["tags"]:
            if tag in RULES:
                theme,question,action=RULES[tag]
                support=[r for r in rows if tag in r["payload"]["mention"]["tags"]]
                resources=[res for r in support for res in r["payload"]["mention"]["resources"]]
                resource=next((r for r in resources if r["kind"] in {"dataset","sequences","software"}),None)
                proposals.append((tag,theme,question,action,"analyst_generated",support,resource))
        for row in rows:
            for resource in row["payload"]["mention"]["resources"]:
                if resource["kind"]=="data_call":
                    proposals.append((resource["url"],"data_call",resource["title"],
                        "Read the official call, verify its deadline and eligibility, and assess a group contribution.",
                        "source_reported_call",[row],resource))
        unique_proposals={p[0]:p for p in proposals}
        for rule,theme,question,action,basis,support,resource in unique_proposals.values():
            oid=uid("opp",event["event_id"],rule)
            decision=opportunity_decisions.get(oid,{})
            old=old_opportunities.get(oid)
            entry={"opportunity_id":oid,"event_id":event["event_id"],"basis":basis,"theme":theme,"question":question,
                   "next_action":decision.get("next_action",action),"status":decision.get("status","suggested"),
                   "rank_score":int(config["research_profile"].get("weights",{}).get(theme,1))+(2 if resource else 0),
                   "evidence_candidate_ids":sorted(r["id"] for r in support),
                   "resource_url":resource["url"] if resource else None,
                   "resource_access":resource["access"] if resource else "unknown",
                   "first_surfaced_at":old["first_surfaced_at"] if old else as_of,
                   "last_evidence_at":max(r["review"]["recorded_at"] for r in support)}
            _value_fields(entry,"owner",decision.get("owner",{"value":None,"status":"not_reported"}))
            data["opportunities"].append(entry)
    # Preserve triaged opportunities even after their motivating tag is superseded.
    existing_opportunities={o["opportunity_id"] for o in data["opportunities"]}
    for oid,old in old_opportunities.items():
        if oid not in existing_opportunities:
            retained=dict(old);decision=opportunity_decisions.get(oid,{})
            retained["status"]=decision.get("status",retained["status"])
            retained["next_action"]=decision.get("next_action",retained["next_action"])
            if "owner" in decision:_value_fields(retained,"owner",decision["owner"])
            data["opportunities"].append(retained)
    for doc_id,row in docs.items():
        p=row["payload"]
        data["documents"].append({"document_id":doc_id,"known_at":row["recorded_at"],**p})
    checks={r["payload"]["source_id"]:r for r in store.records("source_check",as_of)}
    for source in config["sources"]:
        check=checks.get(source["id"])
        p=check["payload"] if check else {}
        data["source_coverage"].append({"source_id":source["id"],"source_name":source["name"],
            "source_role":source["role"],"enabled":source.get("enabled",False),"required":source.get("required",False),
            "status":p.get("status","not_checked" if source.get("enabled") else "disabled"),
            "checked_at":check["recorded_at"] if check else None,"window_start":p.get("window_start"),
            "discovered":p.get("discovered",0),"retrieved":p.get("retrieved",0),"new_documents":p.get("new_documents",0),
            "oldest_publication":p.get("oldest_publication"),"newest_publication":p.get("newest_publication"),"notes":p.get("notes",[])})
    data["event_history"]=(previous or {}).get("tables",{}).get("event_history",[])+[
        {"report_id":run_id,"report_date":report_date,"knowledge_cutoff":as_of,"event_id":e["event_id"],
         "lifecycle_status":e["lifecycle_status"],"update_class":e["update_class"],"summary":e["summary"]} for e in data["events"]]
    queue=review_queue(store,as_of)
    extraction_checks=store.records("extraction_check",as_of)
    latest_extraction=extraction_checks[-1]["payload"] if extraction_checks else None
    extraction_docs={r["payload"]["document_id"] for r in store.records("extraction",as_of)}
    metadata={"report_id":run_id,"report_date":report_date,"knowledge_cutoff":as_of,"timezone":config["timezone"],
              "release_status":"draft","dataset_mode":config.get("dataset_mode","operational"),"software_version":__version__,"schema_version":SCHEMA_VERSION,
              "template_version":TEMPLATE_VERSION,"config_sha256":config_hash(config),"ledger_head_sha256":head,
              "prompt_sha256":digest(assets("extract.md").encode()),"extraction_schema_sha256":digest(Extraction.model_json_schema()),
              "vocabulary_sha256":digest(vocabulary()),"previous_report_id":(previous or {}).get("metadata",{}).get("report_id"),
              "previous_report_id_status":"reported" if previous else "not_applicable",
              "build_fingerprint":build_fingerprint or {},"research_profile":config["research_profile"],
              "quality":{"pending_review_mentions":len(queue),"evidence_flagged_mentions":sum(bool(q["validation_errors"]) for q in queue),
                         "captured_documents":len(docs),"documents_with_some_extraction":len(extraction_docs),
                         "documents_awaiting_extraction":len(set(docs)-extraction_docs),
                         "future_dated_candidates_excluded":excluded_future,
                         "conflicting_current_series":sum(m["value_status"]=="conflicting" for m in data["event_metrics"]),
                         "latest_extraction_check":latest_extraction,
                         "core_source_gaps":[s["source_id"] for s in data["source_coverage"] if s["required"] and s["status"]!="ok"]}}
    completed={}
    for name,rows in data.items():
        completed[name]=sorted([complete_row(name,r) for r in rows],key=lambda r:tuple(str(r[f[0]]) for f in TABLES[name][:2]))
    return {"metadata":metadata,"tables":completed}
