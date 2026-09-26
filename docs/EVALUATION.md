# Evaluation protocol

## Compact digest comparison

The [weekly digest design](WORKFLOW.md) requires a paired comparison against full extraction using identical captured sources and the same provider and model. Start with four source types: a WHO outbreak report, an ECDC bulletin, a relevant EFSA or RIVM article, and an irrelevant article. Include repeated captures and difficult measurement scope. Do not use batch completion or smaller output alone as the quality criterion.

An editor marks the developments and measurements essential to each briefing before comparing results. Check every retained claim for numeric value, date basis, scope, uncertainty, and evidence. List omitted details and distinguish acceptable analytical detail from a missed important development. Reject unsupported claims, invented dates, lost corrections, false event merges, and duplicate cumulative aggregation. A deliberately unextracted field must not become `not_reported` during expansion.

For retained information, require exact reconstruction from the compact encoding and valid evidence references. Test changed publication metadata as well as identical text. Cache reuse must respect interpretation context. Run the ordinary registry, review, and frozen-report checks against the expanded records.

Record input tokens, output tokens, elapsed time, completion status, correction counts, and editor time for each source. Report per-source results alongside totals. Evaluate another model only after this comparison, using the same corpus. The larger chronological study below assesses sustained operation rather than blocking the initial compact-contract experiment.

## Measured baseline

A saved WHO extraction contained 17 mentions, 43 observations, and 82,921 characters of emitted JSON. Its usage receipt recorded 20,762 output tokens, including 292 reasoning tokens. The call took about 10.5 minutes.

An offline encoding experiment replaced redundant value/status wrappers and shared repeated quote text. The representation contained 51,759 characters and reconstructed the full saved result exactly: 37.6% fewer characters. This is a measurement on one saved response, not a measured reduction in model tokens, runtime, or extraction errors. No model call was made for this encoding comparison.

The paused 12–25 September 2026 queue contained 14 chunks from 12 captured versions of 8 distinct publications. Four older versions had text identical to the selected latest version of their publication. Selecting only the latest versions would leave 10 chunks; interpretation context still governs extraction reuse.

## Captured month trial

The isolated digest trial processed 22 captured publications dated 26 August through 26 September 2026. All 22 calls completed in a total of 17.1 minutes, recording 342,477 input tokens and 30,704 output tokens. Thirteen outputs contained relevant material, eight reported no relevant content, and one requested review of source contradictions. The outputs contained 80 topics and 194 claims. No fresh collection or registry acceptance was performed.

Two publications had saved full extraction results for comparison. Their compact outputs used 90.4% fewer output tokens and 43.9% fewer total tokens. The WHO report took 59 seconds, compared with about 10.5 minutes for its full extraction. Both comparisons used the Codex provider route and CLI default; the returned model identifier was not recorded. These observations are not a pinned model benchmark or a corpus wide savings estimate.

Mechanical checks found every quote in the captured text and every resource URL in the supplied text or document metadata. Selected source review found retained key developments, explicit zeros, reporting periods, and source contradictions. It also found omitted low risk statements, an overly broad outbreak label on a single case and surveillance item, and excessive routine training detail in the FAO digest. Anchoring does not establish semantic accuracy, completeness, or editorial acceptance. The remaining claims require source review.

The executed suite passed 113 tests, including the supplied extraction contract and digest evidence boundaries. Selective detailed extraction and expansion into registry records remain unimplemented and untested. The trial supports further digest evaluation; it does not establish publication readiness.

## Acceptance layers
The synthetic suite verifies implementation invariants: explicit missingness and zeros; preserved Namibia codes; field types and dates; evidence anchoring; immutable record history; review-time cutoffs; source-failure reporting; identity continuity; host and aggregate separation; duplicate total handling; contradictions; definition changes; negative cumulative revisions; continued monitoring; opportunity persistence; content-bound approval; deterministic bundle replay; and bounded source/model interfaces.

These tests establish expected behavior on known fixtures. External source extraction, event linkage quality, and group utility require an annotated chronological evaluation.

## Chronological reference corpus
As a pilot design choice, collect eight consecutive weeks across the enabled sources, including quiet periods and several continuing events. Two group members independently annotate event identity, entity type, dates, hosts, geographic scope, count basis, values, revisions, originating authorities, and uncertainty. Adjudicate disagreements and retain the original labels. Include hard examples: a new outbreak in a previously affected place; multi-country summaries; linked hosts; repeated official counts; late revisions; definition changes; event resolution; source outages; and relevant information embedded in a PDF table or figure.

Partition by time and event family. Fit or tune prompts and matching rules on earlier families; evaluate later unseen families and later reports of known families separately. Preserve first-capture times. Evaluate knowledge available at each Wednesday cutoff, rather than granting the earlier system access to later corrections. Keep source licensing and privacy requirements attached to the corpus.

## Metrics
Report document-discovery coverage against the manually enumerated eligible source window, source availability, ingestion delay, and extraction completion. For extraction, measure numeric exact match, date-basis accuracy, case-definition/scope accuracy, missingness accuracy, evidence-span correctness, and the fraction of claims requiring correction. Stratify by source, language, PDF layout, and measure type.

For identity, report pairwise precision/recall, false merges, false splits, continuing-event recall, same-place/new-outbreak errors, and review workload. Evaluate cross-host relationships separately from same-event assignments. False merges have their own acceptance criterion because their downstream cumulative-count errors can be substantial.

For weekly output, measure unsupported claims, duplicated totals, unflagged contradictions, missed explicit corrections, inappropriate incidence derivation, incorrect closures, and publication with missing provenance. Audit denominators and time spans, not only an aggregate accuracy score. Use event-level resampling for uncertainty intervals when repeated reports share an event.

For research utility, record editor time, number of opportunities triaged, data-access success, whether a question leads to a documented analysis or collaboration, and user-rated novelty/relevance. Preserve declined suggestions to measure repetitive or irrelevant proposals. Relevance scores are rule weights to be evaluated against the group's decisions.

## Pilot gates and extensions
Require every public numeric claim and transmission relationship to pass editorial verification during the alpha. Treat any unflagged duplicate cumulative aggregation, unsupported incidence estimate, or incorrect event merge as a blocking pilot defect. Measure acquisition success and editorial effort over at least four successive weekly runs before increasing automation. These are proposed operating gates, not empirical performance claims.

Only consider automatic acceptance after a source- and error-stratified evaluation supports a predefined threshold and a review fallback. Future semantic embeddings should propose candidates rather than establish transmission links. A future published software/workflow paper should include a locked evaluation corpus where redistribution permits, annotation guidance, chronological splits, per-source diagnostics, compute/usage receipts, ablations, and a full error taxonomy.
