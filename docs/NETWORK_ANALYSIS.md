# Reporting network analysis

ATLAS exports descriptive network statistics separately from map geometry. A unit is a source-supported geographic relationship statement between two known, different countries. Movement and shared events retain separate summaries. Hypotheses, domestic relationships and ambiguous country endpoints are excluded with their record references. A statement can describe one traveller, several travellers or an aggregate surveillance period; its weight is one statement, not one case or journey.

## Target quantities

Country strength counts incident units. Pair multiplicity counts units for an unordered country pair. Incoming travel counts directed statements explicitly reviewed as movement by living travellers. Product shipments, human remains, vessel-only itineraries and unresolved movement subjects are excluded. Vessel movements can carry passengers, but an itinerary alone does not identify a traveller observation. Movement category and observation granularity are separate fields. Country strength and pair multiplicity retain all eligible relationship statements, including product movements; they are reporting-network measures. Ties share a rank; an empty selection has no winner. These quantities describe the captured reporting corpus. Country labels are reporting locations, with Namibia's code `NA` preserved.

Repeat-report reviews identify statements about the same journey or episode using exact source evidence. Reviews name all member relationships, supporting evidence, reviewer, time and source lineage. Review the observation granularity before grouping: an aggregate and one of its members are not interchangeable. Country, disease and date proximity alone do not establish identity. Different group identifiers do not establish independent epidemiological episodes. Keep repeated aggregates separate from their individual members and from aggregates at other cutoffs. A closed cohort can support a repeat-report group when source accounts establish its membership and scope; equal counts alone do not. Preserve known aggregate/member overlaps as unresolved episode comparisons. A repeat-report group requires at least two statements; absence of a matching report does not justify a singleton episode. Research groupings do not accept registry events or authorize merges.

The export supplies three descriptive views:

- Raw statements: one unit per eligible relationship ID.
- Repeat-report corrected statements: one unit per fully eligible reviewed group, plus statements outside those groups counted separately. The correction is partial wherever identity review remains incomplete.
- Reviewed group subset: counts within the explicit reviewed groups. Coverage accompanies this subset; it does not represent every observed episode.

The full episode ranking remains unavailable when group membership, distinctness or observation granularity is unresolved. Partially corrected counts have null ranks and an explicit unavailable ranking status. A reviewed-group scope can show the supported correction without assigning a global corrected winner. Do not label a partial repeat-report correction as surveillance adjustment.

## Coverage and identification

The coverage ledger joins supplied collection receipts to selected documents by configured source and canonical publication URL. It preserves receipt hashes, historical statuses and dates, selected document and record IDs, reporting topics, geographic mentions and stage-specific missingness. A selected captured document establishes retrieval and parsed text; selected findings do not establish exhaustive extraction. An earlier download failure remains in history even when a selected capture establishes recovery. Alternative URLs require documented lineage before joining. Documents absent from the export retain unknown eligibility and current completion; a historical failure alone does not settle their current state.

Geographic mentions describe report content, not a sampling frame. Discovered URLs provide a within-receipt denominator, not the number of documents a publisher could have issued. Source independence is not established by different channel names. Exact reused source spans are indexed for investigation without assigning episode identity.

Collection-adjusted estimates require a defined document population, known or estimable positive inclusion probabilities, and a justified relationship between missingness and the target observations. Assess support within each proposed source, topic, geography and period stratum. Missing strata, content-dependent selection and unknown discovery completeness prevent identification. Counts of collected country reports are outcomes of the same reporting process and cannot serve as automatic inverse weights.

Surveillance-adjusted estimates additionally need a validated measure of detection or reporting effort and a model appropriate to the target population. State the exposure denominator, source dependence, assumptions, validation design and uncertainty before fitting. With absent inputs, export unavailable and the data needed. A missing report does not establish zero disease occurrence.

## Selection and sensitivity

Use the validated site selector for inclusive publication or capture bounds, knowledge cutoff, source and topic selection. A relationship requires all supporting records. Apply a repeat-report group only while all its member relationships remain eligible; otherwise preserve the raw eligible statements and mark their identity review unresolved in that view. Filtering never constructs a new journey or bridges intermediate nodes.

The sidecar contains explicit full-window, source omission, organization omission, publication-month and reporting-topic scopes. Each scope carries raw and partially corrected rankings, type-specific results, relationship IDs and review coverage. Precomputed results require an exact matching scope. Other selections must recompute descriptive counts using the same rules; they cannot reuse a global fitted estimate.

Omission removes complete reporting blocks. It measures sensitivity to reporting composition, not sampling uncertainty. Repeated reports and copied source statements prevent treating links as independent observations. Confidence intervals remain unavailable until dependence units and a valid sampling model are established. A future bootstrap must resample reviewed independent clusters and record the seed, design and support diagnostics. No random sampling or fitted surveillance model is used by this descriptive method.

## Run and verify

```bash
PYTHONPATH=src python -m atlas.network_analysis \
  --bundle /path/to/validated/site-bundle \
  --reviews /path/to/repeat-report-reviews.json \
  --collection /path/to/collection.json \
  --out /path/to/network-candidate
```

Repeat `--collection` for compatible source collection receipts. Reconcile acquisition and recovery receipts by exact publication URL and configured source; check selected document identifiers and supplied content hashes. A normalized receipt retains its original receipt SHA-256 and entry index. Keep failures and later recoveries in history. Captures outside the selected export remain distinct from selected findings; retrieval does not establish eligibility or complete extraction. The review input has three arrays: `repeat_report_reviews`, `granularity_reviews` and `identity_reviews`. Empty arrays represent work not performed. Each identity assessment binds the exact relationship, quoted evidence and full candidate set sharing its relationship kind and unordered country endpoints. This broad lookup includes reverse and unspecified directions; it proposes comparisons without deciding identity. Changed membership requires reassessment. Completed assessment and resolved repeat-report membership have separate coverage counts. Granularity reviews distinguish individual journeys, aggregate travellers, shared episodes, product consignments, transfers of human remains, vessel voyages and unresolved units. They also record the movement subject with evidence references. One traveller can have several journeys; preserve unresolved journey granularity when the source cannot separate them. The exported schema defines the sidecar structure; replay checks its scientific references, counts and memberships against the validated input bundle. Repeat the command with `--verify` to compare exact regenerated objects and checksums. The output directory contains `network-analysis.json`, its schema, `coverage-ledger.json` and a manifest. It contains no map geometry or copied report bodies.

The analysis identity includes exact data, review and receipt hashes, software and method fingerprints. Inputs are read once; entity and evidence indexes support membership lookup. Endpoint blocks support candidate lookup in O(E log E + C), where C is the number of exported candidate memberships. A dense block can require quadratic output because every proposed comparison is retained. For S supplied scopes and E eligible relationships, counting costs O(S × E), plus ranking sorts and record selection. Export validation still reads the full source bundle. Unchanged inputs require no model calls. Assess every eligible statement, including those with unresolved identity. Record source date and classification conflicts without silently resolving them. Review only changed source dependencies and candidate sets under [Link reassessment](LINK_REASSESSMENT.md); retain unresolved work with its IDs.

Weekly production and historical expansion prepare this sidecar after geographic review and before handoff. Reassess repeat-report membership when a supporting source, relationship, granularity assessment or source-lineage decision changes. Compare raw and corrected counts, all ties, source and organization omission, and period/topic composition. Validate missing endpoints, direction, partial support, empty selections and unchanged replay. Keep source interpretation separate from consumer presentation, and release the candidate only through the publication procedure.

## Research basis

[Barrat, Barthélemy, Pastor-Satorras and Vespignani (2004), PNAS 101:3747–3752](https://doi.org/10.1073/pnas.0400087101) define node strength as the sum of incident edge weights. Their analysis motivates the weighted summary; it does not correct surveillance bias.

[Jones et al. (2008), Nature 451:990–993](https://doi.org/10.1038/nature06536) studied emergence events. Their temporal Poisson model used annual Journal of Infectious Diseases article totals as an offset; spatial logistic models included country-level author-address frequency as an effort covariate. That event definition and effort proxy differ from ATLAS relationship statements.

[Allen et al. (2017), Nature Communications 8:1124](https://doi.org/10.1038/s41467-017-00923-8) used a literature-derived reporting-effort surface, boosted regression trees and effort-weighted sampling. Factoring bias out involved assumptions about reporting effort relative to human population. Their validation and resampling address their emergence model; neither that model nor its uncertainty can be transferred to ATLAS rankings without supporting data and evaluation.

## Consumer contract and transport

Network analysis contract `0.2.0` has closed nested schemas for records, scopes, coverage, definitions, counts, rank status and uncertainty. The validator checks the content identity, scope identity, selected-record fingerprint, raw and corrected counts, review coverage and relationship-type partitions. Incomplete identity review requires unavailable corrected rankings and null rank values. Unestimated uncertainty has null bounds and a stated reason. A schema check alone does not replace the exact source-bundle replay.

Supply `--map /path/to/snapshot.json --release-id RELEASE_SHA256` to prepare a transport descriptor bound to the site release. The map must match the source snapshot hash in that site bundle. `network-transport.json` and its schema identify the exact site, map, selector, analysis, schema and coverage file hashes and byte sizes. Asset paths are relative to a consumer-configured trusted dataset service root: `releases/RELEASE_ID/` for the site assets and `network-analysis/ANALYSIS_ID/` for the separate analytical assets. Local filesystem paths and automatic publication are absent from this transport contract. Deployment needs its own approval and upload receipt.

An explicitly attached analysis is declared by `assets["network-transport.json"]` in a consumer release descriptor, with its exact byte count and SHA-256. Consumers fetch this file at `releaseRoot/network-transport.json` when the methods panel opens. Without that declaration, consumers make no analysis request. Use a separate serving descriptor for this attachment; preserve sealed release descriptors and bundles. Publishing an attachment follows the publication procedure.

Consumers validate the descriptor and both identifiers, verify each downloaded asset's byte length and SHA-256 before parsing or using it, and require the analysis input site hash to match the descriptor's site hash. Resolve analytical asset paths against the configured trusted service root. Use the bound selector. Reject incompatible releases, malformed nested fields, mismatched scopes and unsupported statuses. The producer replay validates the complete scientific derivation; a consumer must not manufacture a replacement estimate when an asset fails validation. Display a reviewed repeat-report group only when every member is included in the selection. Arbitrary filters do not inherit full-scope corrected values or rankings.

`coverage.ledger_content_sha256` hashes the ledger's canonical JSON object using ATLAS serialization. Manifest and transport SHA-256 values hash exact file bytes. These identities serve different purposes and need not be equal. Exact replay checks both.

The identity coverage fields are `assessed_relationships`, `unassessed_relationships`, `grouped_relationships` and `ungrouped_relationships`. Assessment completion does not imply resolved identity. `movement_coverage` counts every selected statement by its reviewed category, including exclusions and unresolved categories.
