# Structured research export

ATLAS produces structured, analysis-ready outputs for evidence review, research and visualization. A versioned bundle connects documents, source assertions, measurements, comparisons and reporting locations through stable identifiers and exact evidence. This shared representation lets researchers and applications reuse the prepared data with consistent scientific definitions.

The structured export contract is **1.2.0** and embeds metric contract **0.2.0**. A `research_preview` release contains extracted findings and annotations checked against captured sources, with editorial acceptance pending. Review status and coverage describe which uses the data can support. Statistical analysis requires an assessment of measurement compatibility and completeness for the research question.

## Build and validate

Complete [geographic assessment](GEOGRAPHIC_REVIEW.md) before preparing the map release. In the commands below, `INPUT`, `PREPARED` and `BATCH` denote the chosen private input, assessed snapshot and collection directories. Set both date bounds to cover the intended snapshot. The export processes saved inputs and captured source text locally. It validates and packages reviewed annotations for reuse. Event acceptance and publication approval remain separate editorial steps.

```bash
atlas metrics \
  --snapshot PREPARED/snapshot.json \
  --annotations INPUT/metrics-annotations.json \
  --source-dir BATCH/sources \
  --since 2026-03-26 --until 2026-09-26 \
  --out /tmp/atlas-metrics

atlas site-export \
  --snapshot PREPARED/snapshot.json \
  --results BATCH/results.json \
  --metrics /tmp/atlas-metrics/metrics.json \
  --annotations PREPARED/annotations.json \
  --source-dir BATCH/sources \
  --schedule .github/workflows/weekly.yml \
  --out /tmp/atlas-research

atlas site-verify /tmp/atlas-research
```

Output directories must be empty. The metric export must cover every record in the selected snapshot. Store authored annotations and captured source text privately. The export checks the snapshot identity, acquisition text hashes and each quoted source span before writing the bundle.

The bundle contains:

| File | Purpose |
| --- | --- |
| `atlas-site.json` | Documents, records, assertions, comparisons, places, organizations, memberships and embedded metrics |
| `atlas-site.schema.json` | JSON Schema for the full export |
| `annotations.schema.json` | Schema for the private export annotations |
| `view.mjs` | Portable JavaScript selector for reporting windows and scoped figures |
| `review.html` | Readable comparison participants, source sections and review limits |
| `manifest.json` | SHA-256 checksums of the bundle files |

Run `atlas site-verify` before loading a bundle into an analysis or application, using the ATLAS release that produced it. The command checks the supported schema, file checksums, reference integrity, memberships and temporal support. It exits with an error for an incompatible or inconsistent export. A JSON Schema check alone cannot check references between entities. The manifest checks consistency; it is not a digital signature or publication approval.

## Entities and memberships

`documents` contain canonical acquisition titles, source URLs, attachment URLs, publication dates, publication precision, capture timestamps, channel IDs and record membership. A selection's editorial title remains in `records.title`. Document metadata never comes from an arbitrary first selection.

`channels` identify reporting channels and their parent `organizations`. The publisher is distinct from an authority quoted by a source. `quoted_authority_status` and `authority_review` identify the latter as unextracted in this release. Consumers must not copy the channel organization into an originating-authority field. Source titles and evidence quotations retain their attributed wording.

`topics` are reporting selections, not accepted outbreak identities. Their record and place memberships are explicit. `source_coverage` edges contain channel, topic, record and document memberships; they describe reporting coverage. Count distinct selected document IDs for source coverage figures.

`places` provide stable reference locations, coordinates, precision, geographic codes, topics, records, relationships and supporting location memberships. A reference point can represent a region or a country summary. It does not locate a patient. Context endpoints have no independent record membership and appear through an eligible geographic relationship.

`display_groups` group coincident reference points for map layout. Their membership does not merge topics, source observations or events. A display group contains only the places visible in the current selection.

`location_memberships` supply the geographic code, record, document, claim where applicable, role, reason, evidence and temporal support. Roles include reporting scope, occurrence, exposure, context, travel origin and travel destination. Record and document membership indexes refer to these same entities. Claim membership is indexed by `record_id` and `claim_index`; a null claim index identifies record-level reporting scope. An empty membership list is pending or unextracted geography, not evidence of absence.

Use neutral reporting names such as **Taiwan**. `areas.code` uses ISO 3166-1 alpha-2 identifiers for data linkage; `meaning` is `reporting_location_identifier`. A code does not establish statehood. Names, codes, precision, source wording and geographic roles remain separate. Visualizations can use a consistent map-pin and geographic-code treatment for all locations. Geographic presentation must not silently merge or split observations to impose a political classification.

The accompanying map snapshot supplies `map_places` for every assessed topic location and `geographic_review` for per-entry coverage outcomes. Use these locations or their matching structured `places` when drawing pins. A topic without a primary coordinate can still have several supported locations. Filter by eligible records, preserve topic IDs and combine coincident points only for display. The structured record field `geographic_review: pending` means no location membership is available; the snapshot coverage outcome distinguishes an assessed broad region from an unresolved source question.

## Assertions and evidence

An assertion identifies a finding, a numerical measure, a reviewed statement or a reported date. Every assertion has its record ID, document ID, original claim index, evidence IDs, temporal support and review state. Several assertions can share one claim: the two DRC death totals are separate participants within claim 0 of one report.

Measure assertions point to the embedded `metrics.measures` entry. That entry retains metric, unit, case class, case definition, population, geography, host, pathogen, disease, cumulative or interval basis, reporting period, denominator, authority and missingness states. The field `value` on a non-measure assertion is text with an explicit status. Structured values and observation dates not extracted from a qualitative finding use `not_extracted`.

Each evidence entity gives the source text hash, exact captured quote, quote hash, half-open Unicode character offsets, page when available, section label, record, document, claim index and original quote index. Additional reviewed source spans can have a null quote index. Page numbers refer to captured PDF page markers. Web pages can have a null page. Offsets refer to captured source text, not PDF bytes or JavaScript UTF-16 indexes.

Assertion IDs derive from their key and content. Unchanged inputs produce the same IDs regardless of export time. An assertion whose interpretation or supporting evidence changes receives a different ID. Document and record IDs retain the existing snapshot identities. Comparison IDs identify the authored comparison; its participants remain explicit.

## Comparison rules

| Kind | Required interpretation | Status and display |
| --- | --- | --- |
| `contradiction` | Reviewed assertions disagree about the same sufficiently specified quantity or proposition | `unresolved`; separate branches with source-section labels |
| `correction`, `supersession` | A source statement or reviewed revision evidence establishes which assertion replaces another | `documented`; directed lineage with evidence |
| `corroboration` | Independent evidence supports the assertion, with an independence review | `documented`; agreement without a revision connector |
| `republication` | Records repeat the same underlying reporting | `documented`; repeated source lineage, no independence claim |
| `different_scope` | Period, population, classification, definition or denominator differs | `documented`; show the scope distinction |
| `unresolved_association` | Available evidence does not settle the proposed relationship | `unresolved`; retain the open question |

Every comparison supplies participant assertion IDs, section labels, reason, scope review, evidence, review author/time and eligibility. A source-checked relationship is still a draft editorial decision. Numerical differences, recency, matching topic labels and shared bulletins do not create comparisons automatically.

`lineage` occurs only for corrections or supersessions. Each edge identifies the replaced and replacement assertion and its revision evidence. Cycles and revisions published before their originals are rejected. Unresolved contradictions do not merge. The consumer must not average participants, choose a preferred value or treat the last published assertion as correct.

## Reporting windows and figures

```javascript
import { selectView } from './view.mjs';
const view = selectView(bundle, '2026-07-01', '2026-07-31', 'publication');
```

Use the supplied selector after bundle validation. It accepts an inclusive `from` and `until`, either `publication` or `capture`, and a source-knowledge cutoff timestamp when needed. It returns eligible record, document, assertion, comparison, relationship, place and location-membership IDs, filtered source coverage and metric card groups. A sixth argument can supply an array of record IDs selected by channel or other selection filters. Evidence eligibility and metric cards then use that subset as well as the date window. The same bundle supports arbitrary reporting windows through its indexed memberships.

An assertion appears when every record supporting its evidence is in the selected window. A comparison appears only when all participant and relationship evidence is present. With partial support, hide the relationship and keep eligible individual assertions. A later assessment needs its own support and its parent's support. Correction lineage changes the visible card selection only when that correction is eligible. An old assertion is not globally overwritten.

Use `view.panels` for cards. The embedded metric export's `card_groups` and `superseded` fields describe its whole export window; they are not the state of a narrower view. The selector groups eligible measures by their ATLAS context ID, selects the latest reported observation date within each context, preserves same-date conflicts and selects up to three contexts by the authored priority. If dates are missing, it retains the individual assertions without placing them at publication dates. A zero remains zero. Unknown, unverified, unextracted and unreported values retain their distinct statuses.

Topic and report figures use their declared panel memberships. Geographic links and assessments provide `metric_panel_id`; pair it with their `category` to find the panel. Relationship figures require exact claim support, including context claims. A measurement elsewhere in the same report is not sufficient. Record and topic panels retain all reviewed measures for fuller disclosure. Context groups in `metrics.series` retain `connect_points: false`. Source-reviewed count connections are supplied separately in `metrics.reviewed_series`. Do not derive rates, growth, reproduction numbers or case fatality ratios from the cards.

### Compact figures

For a small information card, use `view.panels[].compact_groups`. The selector supplies `compact_grouping_version: "1.0.0"` and each panel's `compact_group_count` before the three-figure limit. This display interface accompanies the bundle's `view.mjs` and is independent of the reviewed-series permissions. The existing `card_groups` retain their context-based selection rules.

Compact figures use the latest eligible observation in each source context. They group equal reported values only when the recorded label, metric, unit, disease, pathogen, host, geography, population, stratum, case classification and definition, date basis, observation date, periods, cumulative baseline, denominator, qualifier, acquisition, transmission role, originating authority, reporting topic and review status match exactly. Missingness states and source-date warnings must also match. Reporting channel, publication/capture timestamp and evidence identifiers remain provenance attached to the individual measures.

An unknown value or observation date stays separate. A measure with a conflict flag or participation in an eligible contradiction, different-scope comparison or unresolved association stays separate. Equal numbers alone do not establish a group. Equal unspecified fields describe the same recorded missingness, not proof that the underlying populations or outbreaks coincide. Every group retains `comparability_status: "not_established"` and `basis: "matching_recorded_scope_and_value"`.

Grouping happens after record selection, date filtering, evidence eligibility and applicable correction lineage, and before the compact-card limit. Groups are ordered by authored priority, latest observation date, metric and group ID. The metric tie order is cases, deaths, hospitalizations, affected holdings, affected animals, samples tested, positive samples, test positivity and other measures. A consumer can display the first two of the three supplied groups while keeping all panel measures accessible in the detailed view.

Each group contains:

| Field | Meaning |
| --- | --- |
| `id` | Deterministic display ID derived from the selected measure IDs; it changes when group membership changes |
| `label`, `metric`, `value`, `value_status`, `unit` | The shared recorded figure and its description |
| `observation_date`, `priority` | Observation date and authored display priority |
| `measure_ids` | All eligible source measures represented by the figure |
| `context_ids` | The retained source-specific measurement contexts |
| `source_ids` | Reporting channel keys, matched to `channels.snapshot_source` for display names |
| `basis`, `comparability_status` | Display grouping rule and retained uncertainty about comparability |

```javascript
const panel = view.panels.find(p => p.kind === 'topic' && p.id === topicId);
const figures = panel.compact_groups.slice(0, 2);
// Render each figure once, with its reporting channels and links to every measure.
```

Keep all source measure and assertion IDs for provenance. Display grouping does not merge observations, infer independent corroboration, resolve disagreements, accept an event or sum values. A source filter can reduce a group's contributing sources, so consume groups from the selector for the active view rather than saving a global deduplicated list.

Publication, capture and observation dates have separate meanings. Publication mode includes the publisher's edition date for some sources, even when that date precedes the reporting week's end. The source-date warning remains available in metrics. A source-knowledge cutoff checks capture time and publication date; it does not reconstruct historical extraction or editorial decisions. Current review annotations remain retrospective.

`snapshot.captured_at` is the latest capture timestamp in the selected corpus. `next_update_date`, `next_update_status`, `schedule_timezone` and `schedule_local_time` describe the next planned collection after that capture, derived from the supplied weekly workflow file. `schedule_activation: not_verified` distinguishes a plan from an enabled scheduler. Public release also depends on review and approval. These fields are independent of the analysis window and the time at which someone opens the output.

## Coverage and interpretation

Each bundle records document and record coverage, the number of reviewed measures, pending candidates and material limitations. Qualitative findings remain available where numerical extraction is incomplete. Geographic memberships and quoted authorities carry their own review or extraction status.

Read coverage alongside the selected measurements. A reviewed comparison establishes the stated relationship among its participants; it does not establish that every possible conflict or revision in the corpus has been examined. Report-level geographic scope also does not imply that every claim has a reviewed occurrence or travel role.

Keep source questions and snapshot-specific findings with the exported review artifact. A contradiction remains unresolved until evidence supports an explicit resolution. Record tests actually executed in a validation receipt, separately from proposed evaluations. The [evaluation guide](EVALUATION.md) describes software checks and the source review needed to assess scientific performance.

## Verification

Run `python -m pytest -q`, `node tests/test_site_view.cjs` and `atlas site-verify <bundle>` for the Python contracts, browser selector and delivered bundle. Fixtures cover within-document disagreements, cross-document corrections and republication, independence requirements, different scopes, evidence identity, missing values, zero, inclusive dates, source-knowledge cutoffs, revision visibility, invalid references and checksums. A passing test establishes software behavior; editorial agreement and epidemiological performance require a separately reviewed reference set.

## Longitudinal comparability

`metrics.reviewed_series` exports reviewed reported-count series. Each includes `series_id`, `label`, `operation`, `scope`, `reason`, `limitations`, review provenance, `members`, `connections` and `evidence`. Members refer to measurement IDs; connections identify exact endpoint pairs with stable IDs. Both carry evidence IDs and complete record eligibility. Method evidence includes the document, record, exact quote, section, page, Unicode offsets and source hashes.

Use `selectView(...).reviewed_series` for Trends. Draw only its explicit connections and retain unconnected points. Select the relevant series members through the same record selection used by other panels. A source filter or a narrow window can remove a connection without removing both endpoint values. The selector never bridges that gap. Show the reviewed operation, scope, reporting period and quoted support alongside each series. `reported_interval_counts` describes published interval counts; `cumulative_reporting_totals` describes successive reported totals. Neither permits incidence calculations from cumulative differences.

`selectView(...).numeric_coverage` supplies selected record, measurement-coverage, reviewed-series and connection counts. `records_without_reviewed_measures` means unknown numeric review coverage, not no cases or no numeric information. Do not label these records as reviewed without numbers or unavailable. Count distinct document IDs separately for collection coverage.

The TypeScript declarations describe site 1.2.0 and metrics 0.2.0. The selector also accepts site 1.0.0 and 1.1.0, returning empty lists for chain or series fields absent from those contracts. A producer verifies bundles with its matching release; consumers must explicitly support each accepted schema version. See [Longitudinal analysis](LONGITUDINAL_ANALYSIS.md) for review and maintenance rules.

## Selection cost

The portable selector builds temporary record indexes for each call. It validates a supplied record selection against known IDs and resolves source coverage through declared memberships. Output record lists keep membership order; document lists keep the selected record order. Place export uses topic, endpoint and record-location indexes with the same evidence checks. These indexes have no persistent state to invalidate. Neither step changes source assertions, review permissions, schema fields or measurement identifiers.

Use `scripts/benchmark_view.mjs` to measure the selector on a saved bundle and compare complete results with a reference selector. Its independent graph replicas test algorithm growth; they do not estimate the source mix or browser rendering cost of a future archive.


## Reviewed chains

`reviewed_chains` contains source-reviewed graphs for a defined episode. Each chain has a stable ID, label, scope, membership review, uncertainty, reviewer and review time. Nodes represent explicitly identified cases, groups, travel stops or reports. They are not inferred from shared disease labels, topic membership or coordinates.

| Kind | Meaning | Direction |
| --- | --- | --- |
| `established_transmission` | The source establishes transmission between the named cases or case groups. | Only a source-described direction. |
| `contact_exposure` | The source reports contact or exposure. Infection or transmission may remain unknown. | Only a source-described direction; contact alone is undirected. |
| `travel_itinerary` | Ordered stops in the same source-described journey. | Source-reported travel order. |
| `reporting_sequence` | Reviewed reports about the same named episode. | Publication order on distinct dates, without an implication of spread. |

Nodes and edges carry record, document, assertion and evidence IDs. Evidence IDs resolve to exact quotes and captured source spans in `evidence`. An edge's record eligibility includes its own evidence and both endpoint dependencies. Node `membership_basis` states why the node belongs to this episode; chain `membership_review` records the identity assessment. These reviews do not merge registry events or constitute editorial acceptance.

`event_date` is separate from publication and capture times on supporting records. `date_basis` and `date_note` describe its meaning. A partial or unreported day remains null with a missingness state and a note. Never substitute publication time for an unknown exposure or travel date. A node's nullable `place_id` references `places`; `coordinate_precision` repeats that place's stated precision. Country reference points retain country precision even when the source names a town. Unknown or geographically broad locations remain unplaced.

Use `selectView(...).reviewed_chains` for presentation. Supply the same selected record IDs used for source and topic filters. The selector retains only supported nodes and explicit edges whose endpoints and full evidence remain eligible. It preserves branches and unplaced nodes and never creates a connection across an excluded intermediate node. `selection_complete` identifies a partial view. `drawable_edge_ids` contains only retained edges with two located endpoints; geographic projection, extent fitting and presentation belong to the consumer. Coincident coordinates do not establish shared identity.

Site annotations use contract `1.1.0` when they contain chains. Declare stable keys, explicit endpoint keys, typed relationships, direction, certainty, membership evidence and review provenance. Empty chain collections mean no chain was supplied for that review scope. Validation checks references, source spans, dependency completeness, place provenance, stable IDs, connectivity, directed cycles and reporting order. Semantic review establishes whether the quotations support the interpretation. Follow [Chain review](CHAIN_REVIEW.md) for production and reassessment.
