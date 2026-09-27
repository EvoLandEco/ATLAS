# Understanding the data

## Units of analysis and keys
The sealed registry dataset contains eleven public tables: `event_identities`, `events`, `updates`, `observations`, `event_metrics`, `relationships`, `opportunities`, `documents`, `source_coverage`, `changes`, and `event_history`.

`event_identities` retains each stable identity even after reassignment. `events` is the currently reviewed event view. `updates` links each accepted mention to its current event assignment. `observations` retains individual source assertions, including explicitly superseded assertions. `event_metrics` represents the latest selected measurement for each exact context. Remaining tables describe relationships, research opportunities, source versions, collection coverage, report changes, and prior weekly event views.

A document is a captured version of a canonical source URL. A candidate is an immutable extraction of part of that document. The authority's persistent outbreak ID and its namespace are distinct from local IDs and publisher article IDs. Repeated facts can appear in several documents and candidates while supporting one event and measurement.

## Dates and times
Publication time belongs to the publisher; modification time describes a declared source revision. `known_at` records the first local capture of that source or extracted claim. `reviewed_at` records the effective editorial decision. `event_start` is the explicit source event start. `as_of` describes the epidemiological evidence cutoff. Observation start/end dates use the declared date basis, such as onset or notification. A sealed report has its own knowledge cutoff and local report date.

Unknown source dates remain missing. Date-only publication values remain dates. Future-publication and future-observation candidates are excluded from an earlier knowledge-time view and counted in its quality record. Historical backfills retain the current first-capture time; they do not create knowledge that the system possessed before capture.

## Missing values
An available scalar carries `reported`, including numeric zero. An unavailable scalar carries null in JSON or `N/A` in CSV and a reason:

| Status | Meaning |
| --- | --- |
| `not_reported` | The source provides no value for this field. |
| `unknown` | The source explicitly describes the value as unknown. |
| `not_applicable` | The field is structurally inapplicable. |
| `pending_verification` | The value awaits resolution. |
| `conflicting` | Current supporting claims disagree. |
| `not_extracted` | Extraction of the field is outstanding. |
| `not_comparable` | The requested comparison lacks a compatible basis. |
| `access_restricted` | A documented access condition prevents obtaining the value. |

Arrays use `[]` for an empty collection. Metadata containers such as the latest extraction-run receipt use null when no such operation exists. `source_coverage.status` describes access and collection, rather than epidemiological missingness. Country code `NA` denotes Namibia. The analysis examples explicitly select `N/A` as the CSV missing-value sentinel.

## Comparing measurements
Each series hashes the event, disease, host, country, location, scope, metric, unit, count kind, case class and definition, date basis, population, stratum, cumulative baseline, interval-window duration, denominator, and qualifier. Different contexts stay separate. Publication source and originating count authority are recorded separately so mirrored reports are distinguishable from independent measurements.

Selection uses the latest reported period end where available, then an explicit mention-level as-of date, then a capture date identified as the date basis. Equal same-context values at the selected time coordinate provide supporting claims; a fixed source-priority and ID order chooses one representative. Different values at the same coordinate produce `conflicting`. Source priority resolves representation among equal claims, not disagreement.

The report builder retains the latest measurement for each historical context until an explicit supersession changes its evidence. Definition changes may therefore leave multiple series visible with their own dates and definitions. Counted people, animals, holdings, and samples use integer values; percentages and proportions retain their stated units and bounds.

## Weekly change
A cumulative reporting difference is produced only when both snapshots have compatible series IDs, known originating authorities, a known baseline, ordered end dates, known case classification/definition, a known population, exact numeric qualifiers, and reported values. Positive, zero, and negative differences receive explicit reporting-change labels. An interval incident count comes directly from a source assertion with `count_kind=interval`; its interval and date basis remain attached.

A correction explicitly supersedes prior candidates in the same event. The initial implementation supersedes the complete candidate; use separate candidate mentions for independently correctable scopes. Superseded observations remain downloadable. Mirrored incorrect claims should be superseded together when the correction applies to their common originating authority.

`new_to_registry` means newly accepted here. `updated_measurements`, `status_change`, `additional_reporting`, and `carried_forward` describe other weekly changes. Source silence retains the last explicit lifecycle state; freshness is a separate editorial indicator based on publication age.

## Research opportunities
Each opportunity has a stable event-plus-rule or event-plus-resource ID, basis, theme, evidence, resource access, owner, next action, status, and a transparent relevance score. The score is a prioritization rule, not an outbreak-risk probability or evidence-confidence estimate. Analyst-generated questions and source-reported calls have separate basis values. Older opportunities remain trackable as their underlying evidence develops.

## Analysis and provenance
Use `event_metrics` for selected scoped values and `observations` for claim-level investigations. Filter context and time before aggregation. Use archived bundles for earlier quantitative views and the event history table for earlier weekly event summaries. The included data dictionary is generated from the same table definitions as the CSV exporter. Checksums cover each exported member; approval identifies the exact ZIP hash.

## Structured assertion bundles

The [structured research export](SITE_EXPORT.md) provides documents, selected records, assertions, exact evidence spans, comparisons, reporting locations and indexed memberships in JSON. It also embeds scoped metrics and their review coverage. These research selections retain their review status separately from accepted registry events.

One source claim can support several assertions. Comparison groups identify the exact participants and distinguish contradictory values, explicit revisions, independent corroboration, repeated reporting, different scope and unresolved associations. Revision edges preserve the original assertion and cite the evidence for its replacement. Matching values or repeated publication alone do not establish independent corroboration.

The export's metric contexts preserve case classification, definition, population, geography, host, period, count kind and denominator. Compact figures select the latest observation date within an eligible context and retain competing assertions at that date. Missing observation dates remain missing. Series with `connect_points: false` have no established basis for a connected trend; analysis requires further comparability review.

Publication and capture dates control reporting-window eligibility. Observation dates retain their epidemiological meaning. All supporting records must be eligible for a comparison or relationship to appear, including the evidence for later corrections. A retrospective source window does not reconstruct the editorial state at that historical date.

Geographic identifiers describe reporting locations. Neutral labels, coordinate precision and roles remain explicit. Codes do not express sovereignty, and geographic presentation does not change the scope of source observations. Source coverage memberships describe which documents report each topic and remain separate from epidemiological links.
