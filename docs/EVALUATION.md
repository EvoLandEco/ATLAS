# Evaluation protocol

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
