"""Stable public table contracts. Nullable fields always have a status column."""
from __future__ import annotations
# Each field is name, primitive type, description, nullable.
TABLES = {
 "event_identities": [
  ("event_id","string","Persistent identity, including reassigned historical identities.",False),
  ("event_key","string","Stable editorial identity key.",False),
  ("first_assigned_at","datetime","First accepted identity assignment.",False),
  ("current_candidate_count","integer","Currently accepted mentions assigned to this identity.",False),
 ],
 "events": [
  ("event_id","string","Persistent local event identity.",False),
  ("event_key","string","Editor-assigned stable identity key.",False),
  ("title","string","Current reviewed event label.",False),
  ("kind","string","outbreak, cluster, single_case, surveillance_aggregate, signal, or context.",False),
  ("disease","string","Versioned canonical disease label.",False),
  ("pathogen","string","Source-reported pathogen, with subtype retained.",True),
  ("host","string","Population or host species for this event.",True),
  ("country_code","string","ISO 3166-1 alpha-2; NA is Namibia.",True),
  ("location","string","Source-reported geographic scope label.",True),
  ("geographic_scope","string","subnational, national, multinational, global, or unknown.",False),
  ("lifecycle_status","string","Most recent explicit reviewed source status; silence preserves the prior state.",False),
  ("update_class","string","Change relative to the preceding sealed report.",False),
  ("first_seen_at","datetime","Earliest evidence capture associated with this event as known now.",False),
  ("last_reviewed_at","datetime","Latest effective editorial acceptance timestamp.",False),
  ("last_source_publication","string","Latest source publication date or instant, separate from capture time.",True),
  ("event_start","date","Latest explicit source-reported event start, separate from registry discovery.",True),
  ("as_of","date","Latest reported epidemiological as-of date.",True),
  ("freshness_days","integer","Days since latest source publication, not inferred transmission inactivity.",True),
  ("freshness_status","string","current, stale, or unknown under configured editorial threshold.",False),
  ("summary","string","Reviewed source-derived paraphrase.",False),
  ("evidence_candidate_ids","array","IDs of current accepted report mentions.",False),
  ("tags","array","Evidence-backed research relevance tags.",False),
  ("authority_event_id","string","Explicit persistent ID assigned by the source authority.",True),
  ("authority_namespace","string","Issuer namespace for the source event ID.",True),
 ],
 "updates": [
  ("candidate_id","string","Immutable extracted or editorial mention identity.",False),
  ("event_id","string","Current editorial event assignment at the knowledge cutoff.",False),
  ("document_id","string","Immutable source document version.",False),
  ("source_id","string","Configured publisher/source identifier.",False),
  ("known_at","datetime","First capture of this extracted mention.",False),
  ("reviewed_at","datetime","Timestamp of effective review.",False),
  ("as_of","date","Reported epidemiological as-of date.",True),
  ("summary","string","Reviewed source-derived paraphrase.",False),
  ("superseded","boolean","True when an accepted correction explicitly replaces this candidate.",False),
  ("review_id","string","Immutable decision ID in the private audit ledger.",False),
 ],
 "observations": [
  ("observation_id","string","Immutable individual source claim identity.",False),
  ("series_id","string","Hash of event and exact measurement context.",False),
  ("event_id","string","Persistent event ID.",False),
  ("candidate_id","string","Parent reviewed mention.",False),
  ("document_id","string","Parent document version.",False),
  ("source_id","string","Publisher identity, distinct from originating authority.",False),
  ("disease","string","Disease label at this source assertion, preserving reclassification history.",False),
  ("origin_authority","string","Source-stated origin of the underlying counts; unknown origins remain missing.",True),
  ("metric","string","cases, deaths, hospitalizations, affected_holdings, affected_animals, samples_tested, positive_samples, test_positivity, or other.",False),
  ("value","number","Source claim, with its explicit missingness reason.",True),
  ("unit","string","people, holdings, animals, samples, percent, proportion, other, or unknown.",False),
  ("count_kind","string","cumulative, interval, point, or unknown.",False),
  ("case_class","string","Source case classification; combined classifications remain separate.",False),
  ("case_definition","string","Explicit source definition or definition identifier.",True),
  ("date_basis","string","onset, notification, specimen, death, report, or unknown.",False),
  ("period_start","date","Beginning of the observation period or cumulative baseline.",True),
  ("period_end","date","End of the source observation period.",True),
  ("as_of","date","Mention-level epidemiological as-of date.",True),
  ("population","string","Population denominator/scope label.",True),
  ("stratum","string","Age, sex, occupational, subtype, or other source-defined stratum.",True),
  ("denominator","number","Explicit numeric denominator, when supplied.",True),
  ("qualifier","string","exact, approximately, at_least, at_most, or unknown.",False),
  ("host","string","Host population for the claim.",True),
  ("country_code","string","Country for the claim; NA is Namibia.",True),
  ("location","string","Geographic scope of the claim.",True),
  ("geographic_scope","string","Resolution of the source claim.",False),
  ("known_at","datetime","First capture of the extracted claim.",False),
  ("source_publication","string","Source publication date/instant.",True),
  ("superseded","boolean","True when its parent claim has been explicitly replaced.",False),
  ("selected_current","boolean","One deterministic representative of a consistent current measurement.",False),
  ("evidence_locator","string","Page/section supplied during extraction and checked in editorial review.",False),
 ],
 "event_metrics": [
  ("series_id","string","Exact measurement-context identity; joins observations.",False),
  ("event_id","string","Persistent event identity.",False),
  ("metric","string","Measurement type.",False),
  ("disease","string","Disease label for the measurement context.",False),
  ("host","string","Host population for this measurement.",True),
  ("country_code","string","Country of this measurement; NA is Namibia.",True),
  ("location","string","Geographic label for this measurement.",True),
  ("geographic_scope","string","Geographic resolution for this measurement.",False),
  ("qualifier","string","Source numeric qualifier, including at_least and approximately.",False),
  ("denominator","number","Explicit denominator, when supplied.",True),
  ("value","number","Current selected source value; conflicting values remain missing here.",True),
  ("unit","string","Measurement unit.",False),
  ("count_kind","string","Cumulative, interval, point, or unknown.",False),
  ("case_class","string","Case classification.",False),
  ("case_definition","string","Explicit source definition or definition identifier.",True),
  ("date_basis","string","Time axis of the underlying measurement.",False),
  ("period_start","date","Start of source measurement period.",True),
  ("period_end","date","End of source measurement period.",True),
  ("population","string","Population to which the measurement refers.",True),
  ("stratum","string","Source stratum.",True),
  ("origin_authority","string","Underlying count origin used for conservative comparability.",True),
  ("selected_observation_id","string","Representative source assertion; missing when unresolved.",True),
  ("supporting_observation_ids","array","All equal or conflicting claims at the selected time coordinate.",False),
  ("selection_basis","string","Period end, explicit as-of, or capture fallback; see methods.",False),
  ("change_in_reported_cumulative","number","Difference from the previous sealed comparable cumulative value; this is a reporting change.",True),
  ("change_label","string","increase_in_reported_total, downward_revision, unchanged_reported_total, or N/A.",True),
 ],
 "relationships": [
  ("relationship_id","string","Immutable relationship decision.",False),
  ("from_event_id","string","Source endpoint.",False),
  ("to_event_id","string","Target endpoint.",False),
  ("relation","string","part_of, possible_link, reported_link, shared_exposure, cross_host_link, merged_into, or split_from.",False),
  ("basis","string","source_reported, analyst_hypothesis, or editorial_identity.",False),
  ("evidence_candidate_id","string","Accepted supporting mention.",False),
  ("rationale","string","Editor-reviewed public explanation.",False),
  ("recorded_at","datetime","Knowledge time of relationship decision.",False),
 ],
 "opportunities": [
  ("opportunity_id","string","Persistent event-plus-rule or external-resource opportunity identity.",False),
  ("event_id","string","Related reviewed event.",False),
  ("basis","string","analyst_generated or source_reported_call.",False),
  ("theme","string","Research-profile rule that surfaced the opportunity.",False),
  ("question","string","Proposed learning or contribution question.",False),
  ("next_action","string","Concrete next step, with analyst ownership after triage.",False),
  ("status","string","suggested, triaged, investigating, completed, or declined.",False),
  ("owner","string","Assigned group member or team.",True),
  ("rank_score","integer","Transparent sum of configured relevance weights and explicit resource bonus.",False),
  ("evidence_candidate_ids","array","Reviewed source evidence that motivated the proposal.",False),
  ("resource_url","string","Source-linked resource or data call.",True),
  ("resource_access","string","public, registration, controlled, or unknown as stated by source.",False),
  ("first_surfaced_at","datetime","First weekly report in which the opportunity was generated.",False),
  ("last_evidence_at","datetime","Latest accepted evidence supporting this rule.",False),
 ],
 "documents": [
  ("document_id","string","Immutable source document version ID.",False),
  ("source_id","string","Configured source.",False),
  ("url","string","Canonical public landing page.",False),
  ("content_url","string","Actual content URL, including primary PDF when used.",False),
  ("title","string","Source document title.",False),
  ("published_at","string","Source publication date or timestamp.",True),
  ("publication_precision","string","day, instant, or unknown; date-only values remain dates.",False),
  ("modified_at","string","Source-declared last modification date/instant.",True),
  ("known_at","datetime","First successful local capture of this version.",False),
  ("text_sha256","string","SHA-256 of normalized captured text.",False),
  ("raw_sha256","string","SHA-256 of captured original source bytes.",False),
  ("parse_status","string","text_ready or needs_review.",False),
 ],
 "source_coverage": [
  ("source_id","string","Configured source identifier.",False),
  ("source_name","string","Publisher/source name.",False),
  ("source_role","string","Official synthesis, official national reporting, animal health, or curated discovery.",False),
  ("enabled","boolean","Whether this source participates in automated collection.",False),
  ("required","boolean","Whether this source is in the editorial core.",False),
  ("status","string","ok, partial, empty, failed, disabled, manual_access, or not_checked.",False),
  ("checked_at","datetime","Time of last collection check.",True),
  ("window_start","date","Requested discovery lookback boundary.",True),
  ("discovered","integer","Discovered items within adapter scope, including bounded revisits.",False),
  ("retrieved","integer","Documents successfully read in this check.",False),
  ("new_documents","integer","New immutable document versions captured.",False),
  ("oldest_publication","string","Oldest source publication among retrieved documents.",True),
  ("newest_publication","string","Newest source publication among retrieved documents.",True),
  ("notes","array","Coverage gaps, limits, access requirements, or retrieval errors.",False),
 ],
 "changes": [
  ("event_id","string","Persistent event identity.",False),
  ("change_type","string","new_to_registry, updated_measurements, status_change, additional_reporting, carried_forward, or removed_after_review.",False),
  ("description","string","Deterministic explanation of the snapshot difference.",False),
 ],
 "event_history": [
  ("report_id","string","Sealed weekly snapshot identity.",False),
  ("report_date","date","Local editorial report date.",False),
  ("knowledge_cutoff","datetime","Ledger knowledge cutoff for this historical snapshot.",False),
  ("event_id","string","Persistent event identity as represented then.",False),
  ("lifecycle_status","string","Reviewed state in that snapshot.",False),
  ("update_class","string","Weekly change classification at the time.",False),
  ("summary","string","Reviewed source summary as represented then.",False),
 ],
}


def fields_for(table: str) -> list[dict]:
    out=[]
    for name,typ,description,nullable in TABLES[table]:
        out.append({"name":name,"type":typ,"description":description,"nullable":nullable})
        if nullable:
            out.append({"name":name+"_status","type":"string","description":"Value presence or explicit missingness reason for "+name+".","nullable":False})
    return out


def complete_row(table: str, row: dict) -> dict:
    out={}
    for name,typ,description,nullable in TABLES[table]:
        if name not in row and not nullable:
            raise ValueError(f"Missing required export field {table}.{name}")
        value=row.get(name)
        if not nullable and value is None:
            raise ValueError(f"Null in required export field {table}.{name}")
        out[name]=value
        if nullable:
            status=row.get(name+"_status") or ("reported" if value is not None else "not_reported")
            if (value is not None)!=(status=="reported"):
                raise ValueError(f"Value/status mismatch in {table}.{name}")
            out[name+"_status"]=status
    return out


def dictionary() -> dict:
    return {table:fields_for(table) for table in TABLES}
