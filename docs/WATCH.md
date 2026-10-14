# Reviewed reports to watch

Watch contract 0.1.0 supplies explicit report selections for an Events to watch view. Each inclusion is reviewed against captured evidence and records a reason for attention and a follow-up question. Selection does not assign clinical urgency, an outbreak identity or a hazard rank.

The contract binds the exact scientific export ID, site checksum, manifest checksum and map snapshot checksum. It is a separate attachment to the scientific release. `items` contains the selected report reviews in their input order; `review_scope` and `limitations` state what the selection covers. A small or empty list is valid.

## Review and source bindings

Each item names one subject `record_id`, its exact `assertion_ids` and `evidence_ids`, and all source text hashes needed by that support. `scope_kind` is `single_report`; `event_identity` is `not_assigned`. Source statements cited by a report can involve other records, so `record_ids`, `document_ids` and `eligibility` carry the full dependency set. The contract does not combine reports into an episode.

`label`, `reason_for_attention` and `follow_up_question` are presentation and review text. An agent or editor must inspect the complete captured passage, preserve attribution and uncertainty, and record `reviewed_at`, `reviewed_by` and `review_state: source_checked_draft`. A chosen reason must be supported by the cited assertions. A text match, a large report count or a disease label cannot supply the review decision. Numerical comparison claims require their existing comparison review; a source value alone does not establish an increase in hazard.

`diagnostic_assessment_id` identifies a diagnostic assessment with the same report scope. The export copies its exact status, label and authority. Every assertion and evidence span supporting that assessment must be included. A missing assessment leaves diagnostic status `not_extracted`, with a null value. Source authentication cannot supply a diagnostic status. A superseded diagnostic assessment requires a fresh selection review.

`sources` retains each document's title, URL, channel, publication date, publication precision and basis, capture time and supporting record IDs. `latest_publication` and `latest_capture` summarize those separate source dates. Neither is an onset date or a review date. Observation dates remain on the referenced scientific assertions. A selected report with an unresolved cause does not establish an urgent event.

## Build and verify

Prepare private annotations under `WatchAnnotations`, preserving each immutable input and released export as review history. Reuse exact scientific references. Reassess selections whose sources, assertions, diagnostic assessments or named questions change. Removing a selection from a subsequent export is an explicit review decision; missing follow-up does not establish resolution.

```bash
atlas watch-export --bundle RELEASE/structured --snapshot RELEASE/snapshot.json \
  --annotations PRIVATE/watch-annotations.json --out RELEASE/watch
atlas watch-verify --bundle RELEASE/structured --snapshot RELEASE/snapshot.json \
  --watch RELEASE/watch
```

The commands require an empty output directory and bound annotation input to 1 MB. They make no collection or model calls. `atlas schemas` writes `watch.schema.json` and `watch-annotations.schema.json`. Validation checks exact source references, full evidence support, source hashes, diagnostic scope, review times and derived dates. Semantic review determines whether the stated reason follows from the evidence.

## Display selection

Use the scientific selector for both date boundaries, source filters and the knowledge cutoff. Pass its `record_ids` to the supplied, trusted `selectWatch` function:

```js
const featured = selectWatch(watch, view.record_ids, knowledgeCutoff).slice(0, 3);
const featuredDocuments = new Set(featured.flatMap(item => item.document_ids));
```

`selectWatch` requires every supporting record to be selected. When a knowledge cutoff is supplied, the watch review must also exist by that time. The function preserves explicit review order and performs no ranking. Vendor the reviewed selector with consumer code; do not execute downloaded code. Apply the three-item display limit after eligibility. Exclude only the displayed items' records or documents from a separate chronological Latest reports list.

Each card shows its label, reason, source diagnostic status, follow-up question, publication and review dates, and links to the supporting sources. Open the exact evidence IDs for quotations; English presentation uses the source text bindings. Preserve the original and draft translation labels. The watch list and Latest reports have different meanings: inclusion is an explicit review choice, while chronology describes reporting recency.

The handoff supplies every watch asset's bytes and checksum, the source export ID, schema, selector and validation receipt. Consumer rendering, adoption and public activation retain separate receipts. Scientific source identity and the underlying counts remain intact.
