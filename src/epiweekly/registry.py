"""Editorial decisions, event identity, temporal review, and relationship history."""
from __future__ import annotations
from datetime import date
from .models import Review, Relation, OpportunityDecision
from .semantics import identity_signature
from .store import Store
from .util import uid, stamp, canonical


def current_reviews(store: Store, as_of: str | None = None) -> dict:
    out={}
    for row in store.records("review",as_of):
        out[row["payload"]["candidate_id"]]=row
    return out


def accepted_candidates(store: Store, as_of: str | None = None) -> list[dict]:
    reviews=current_reviews(store,as_of)
    result=[]
    for row in store.records("candidate",as_of):
        review=reviews.get(row["id"])
        if review and review["payload"]["action"]=="accept":
            result.append({**row,"review":review,"event_key":review["payload"]["event_key"],
                           "event_id":uid("evt",review["payload"]["event_key"])})
    return result


def apply_reviews(store: Store, reviews: list[Review], at: str) -> list[str]:
    at=stamp(at);ids=[]
    # Validate the whole batch before applying it, including same-batch event assignments.
    if len({r.candidate_id for r in reviews}) != len(reviews):
        raise ValueError("Each candidate occurs once in a review batch")
    accepted={r["id"]:r for r in accepted_candidates(store,at)}
    pending=[]
    for review in reviews:
        row=store.get(review.candidate_id)
        if row["kind"]!="candidate" or row["recorded_at"]>at:
            raise ValueError("Review must refer to an already captured candidate")
        doc=store.get(row["payload"]["document_id"])
        if doc["recorded_at"]>at: raise ValueError("Review predates its source")
        if review.action=="accept":
            errors=set(row["payload"]["validation_errors"])
            verified=set(review.numeric_evidence_reviews)
            if verified-errors or any(not flag.startswith("Numeric evidence needs review:") for flag in verified):
                raise ValueError("An editor can verify only existing numeric anchoring flags")
            if errors-verified:
                raise ValueError("Correct evidence/number anchoring through a new editorial extraction before acceptance")
            mention=row["payload"]["mention"]
            if not mention["disease"]["value"]:
                raise ValueError("An accepted event requires a disease or explicit unknown-syndrome label")
            for other in accepted.values():
                if other["event_key"]!=review.event_key or other["id"]==row["id"]: continue
                a=other["payload"]["mention"]
                for field in ("disease","host"):
                    if a[field]["value"] and mention[field]["value"] and a[field]["value"]!=mention[field]["value"]:
                        if field!="disease" or not review.allow_disease_reclassification:
                            raise ValueError(f"{field} differs across event identity; disease reclassification requires an explicit review flag")
                aggregate={"surveillance_aggregate","context"}
                if a["kind"]!=mention["kind"] and (a["kind"] in aggregate or mention["kind"] in aggregate):
                    raise ValueError("Keep outbreak entities and surveillance aggregates in distinct event identities")
            for superseded in review.supersedes_candidate_ids:
                if superseded==row["id"] or superseded not in accepted:
                    raise ValueError("Supersession requires an earlier accepted candidate")
                if accepted[superseded]["event_key"]!=review.event_key:
                    raise ValueError("Supersession stays within the same event identity")
                # A reversal of a previous supersession is represented by a new corrected candidate.
                old_review=accepted[superseded].get("review",{}).get("payload",{})
                if row["id"] in old_review.get("supersedes_candidate_ids",[]):
                    raise ValueError("Supersession must be acyclic")
            accepted[row["id"]]={**row,"event_key":review.event_key,
                                   "review":{"payload":review.model_dump(mode="json")}}
        else:
            accepted.pop(row["id"],None)
        pending.append(review.model_dump(mode="json"))
    graph={cid:r["review"]["payload"].get("supersedes_candidate_ids",[]) for cid,r in accepted.items()}
    def visit(node,trail,done):
        if node in trail: raise ValueError("Supersession must be acyclic")
        if node in done:return
        for target in graph.get(node,[]):visit(target,trail|{node},done)
        done.add(node)
    done=set()
    for node in graph:visit(node,set(),done)
    for payload in pending:
        previous=current_reviews(store).get(payload["candidate_id"])
        if previous and canonical(previous["payload"])==canonical(payload):
            ids.append(previous["id"]);continue
        ids.append(store.append("review",payload,at))
    return ids


def add_relation(store: Store, relation: Relation, at: str) -> str:
    current=accepted_candidates(store,at)
    event_keys={r["payload"]["event_key"] for r in store.records("review",at) if r["payload"]["action"]=="accept"}
    if relation.from_event_key==relation.to_event_key:
        raise ValueError("A relationship connects distinct identities")
    if not {relation.from_event_key,relation.to_event_key}<=event_keys:
        raise ValueError("Both relationship endpoints require accepted event identities")
    if relation.evidence_candidate_id not in {r["id"] for r in current}:
        raise ValueError("A relationship cites an accepted evidence candidate")
    editorial={"merged_into","split_from","part_of"}
    if relation.relation in {"merged_into","split_from"} and relation.basis!="editorial_identity":
        raise ValueError("Identity changes use editorial_identity")
    if relation.relation=="reported_link" and relation.basis!="source_reported":
        raise ValueError("reported_link requires source_reported evidence")
    # A merge is represented by explicit reassignment decisions plus an audit relation.
    # This keeps old snapshots stable and gives splits the same reversible operation.
    return store.append("relation",relation.model_dump(mode="json"),at)


def match_candidates(store: Store, candidate: dict, as_of: str | None = None) -> list[dict]:
    mention=candidate["payload"]["mention"];out={}
    for row in accepted_candidates(store,as_of):
        other=row["payload"]["mention"]
        if mention["disease"]["value"]!=other["disease"]["value"]: continue
        if mention["host"]["value"]!=other["host"]["value"]: continue
        if mention["kind"]!=other["kind"] and ({mention["kind"],other["kind"]}&{"surveillance_aggregate","context"}): continue
        same_id=(mention["authority_event_id"]["value"] is not None and
                 mention["authority_event_id"]["value"]==other["authority_event_id"]["value"] and
                 mention["authority_namespace"]["value"]==other["authority_namespace"]["value"])
        same_scope=identity_signature(mention)==identity_signature(other)
        if same_id or same_scope:
            reason="same_explicit_authority_event_id" if same_id else "same_scope_requires_event_review"
            out[row["event_id"]]={"event_id":row["event_id"],"event_key":row["event_key"],"reason":reason,
                                  "rank":2 if same_id else 1,"decision":"review_required"}
    return sorted(out.values(),key=lambda x:(-x["rank"],x["event_id"]))


def review_queue(store: Store, as_of: str | None = None) -> list[dict]:
    latest=current_reviews(store,as_of);result=[]
    for row in store.records("candidate",as_of):
        review=latest.get(row["id"])
        if not review or review["payload"]["action"]=="defer":
            doc=store.get(row["payload"]["document_id"])["payload"]
            result.append({"candidate_id":row["id"],"document_id":row["payload"]["document_id"],
                "source_id":doc["source_id"],"url":doc["url"],"title":row["payload"]["mention"]["title"],
                "mention":row["payload"]["mention"],"validation_errors":row["payload"]["validation_errors"],
                "suggested_matches":match_candidates(store,row,as_of)})
    return result
