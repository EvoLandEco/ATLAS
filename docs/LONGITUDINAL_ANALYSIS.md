# Longitudinal analysis and comparability

Comparability is a reviewed permission to perform a particular analysis on specified observations. Matching context fields supplies candidates for review. It does not establish a continuous series, a common outbreak or a common surveillance process.

The metric exporter retains exact-context groups as separate observations and exports source-reviewed count series in `reviewed_series`. Each series has a stable ID, an analytical scope, method evidence, ordered members and explicitly permitted connections. Review status remains `source_checked_draft`; editorial acceptance is a separate decision.

## Define the analytical use

| Use | Evidence needed | Display or calculation |
| --- | --- | --- |
| Reported counts within one surveillance programme | Stable metric, unit, case category, reporting geography and population; known reporting periods; review of method changes and revisions | Dated observations or interval bars. Reviewed connections describe reported counts, with breaks at missing periods or method changes. |
| Cumulative totals within an episode or surveillance year | Explicit common episode/baseline, compatible scope, dated totals and revision history | Cumulative observations. A connection can show the sequence of reported totals; it supplies no daily values between observations. |
| Incident case series | Explicit interval counts or event-dated records, with reporting completeness and delay assessed | Counts by the stated interval and date basis. Differences between cumulative publications are reporting changes unless additional evidence establishes incidence. |
| Rates or standardized comparisons | Compatible numerator and denominator populations, periods, units and sampling frames; relevant age/sex structure or other standardization inputs | A reviewed rate with its formula and denominator lineage. Counts alone do not establish relative risk between populations. |
| Case fatality comparisons | Case and death definitions, denominator cohort, outcome follow-up and delays, reporting coverage and formula | Preserve source-reported ratios. A common percentage label alone does not establish comparable fatality risk. |
| Comparisons across sources | Originating data authority, reporting system, shared definitions and reference periods, assessed duplication and explicit harmonization | Reviewed observations with provenance. Repeated publication of one official total is one reported value with several citations, not independent replication. |

A population denominator is not required to describe reported counts. Missing subtype detail need not block a case-count series when the published disease definition establishes its scope. Unknowns block the analyses that depend on them; they do not create a blanket rejection of every use.

## Review a source method once, with evidence

Start with one programme and reporting cadence. Capture the method sections for case definitions, national or local reporting scope, date basis, reporting completeness, revisions and count conventions. Give the reviewed method a stable ID and retain its exact source references and validity interval. Compare each added report with that method and record exceptions. Identical method text supports continuity of the documented definition; it does not prove unchanged testing, ascertainment or reporting completeness.

A changing list of places with cases is not necessarily a changing surveillance catchment. Distinguish the two before splitting a series. Likewise, onset, diagnosis, notification, publication and capture dates have different roles. An epidemiological week label needs its stated calendar and start/end dates; preserve the publisher's convention.

Read tables with their headers, footnotes and adjacent explanation. Some PDF text exports omit columns or scramble figures. Page inspection is required for affected measurements. Review the full captured report when a digest omitted methodological context. Mark an unextracted definition as such rather than asserting that the source did not report it.

Method evidence outside existing extracted claims needs a source-referenced enrichment record. Preserve the original extraction and its identifiers. Keep series review separate from source measurements so approving a chart connection does not change a reported value or its measurement ID.

## Review annotations and export rules

Metric annotations accept `series_reviews`. A review identifies measurements by their existing `annotation_key`, supplies a stable `series_id`, and describes its scope, reason, limitations, reviewer and review time. Every member names captured method evidence. Each connection names its two endpoint annotations and any additional evidence needed for that pair.

Method quotations may come from any section of the captured source. The exporter requires one exact occurrence after whitespace normalization, then records the original quote, Unicode offsets, page, source hash and quote hash. This evidence enriches the analysis without rewriting extracted claims or their identifiers. Individual measurement fields retain their source assertions; a series method review can supply definitions absent from those fields.

The implemented permissions are `reported_interval_counts` and `cumulative_reporting_totals` for case and death counts in people. Connections require increasing observation dates and adjacent reviewed observations, matching count scope and no unresolved metric conflict or superseded endpoint. Interval counts require consecutive, equal-duration periods. Cumulative totals require the same explicit baseline. A missing week leaves a break in interval connections. A year or episode reset requires a separate review and series. Rates, inferred incidence and fatality-risk comparisons have no permission in this contract.

The selector requires every supporting record for members and connections to survive the reporting window, source selection and capture cutoff. An eligible contradiction blocks connections through either disputed value. A different-scope comparison or unresolved association blocks the exact compared pair; it does not disqualify either measurement from other reviewed pairs. It never creates a shortcut across an excluded observation. Consumers draw only exported connections and show each point's reported period and source. A connection supplies neither interpolation nor a daily value between observations. Stable connection IDs refer to specific endpoint measurement IDs; filtering retains these IDs.

Collection, numeric extraction and comparability review have separate coverage. `numeric_coverage` counts selected records with and without reviewed measurements and the eligible reviewed series and connections. A record without reviewed measurements has unknown numeric coverage. The export does not classify it as zero, reviewed without relevant numbers, or inaccessible. A record with measurements can still contain unextracted figures. The proposal candidate count is a separate queue count, not a count of unreviewed reports.

## Completing identified opportunities

For each concrete opportunity, extract supported observations from the captured source and record the sections reviewed. Review the analytical scope separately from the value. Export single-report figures, exposure indicators and conflicting alternatives even when they cannot support a continuous series. A completed opportunity can contain an unresolved comparison, provided that its supported observations and the exact unresolved question are preserved. Human decisions govern acceptance and disputed interpretation.

Add series and connections only after reviewing their definitions, periods and source methods. Preserve existing measurement IDs and decisions. Rebuild metrics, structured data and the geographic preview from the same reviewed snapshot, then validate the consumer handoff. Report extraction, comparison review, export generation and consumer adoption as separate outcomes.

## Validation and release

1. Inspect the table, column headings, reporting dates and source method. State the analytical use and material uncertainties.
2. Add missing measurements with exact claim references. Reuse existing measurement annotations without changing their IDs. Add method quotations to the series review.
3. Declare only the reviewed connections. Keep conflicting alternatives available as separate observations. Geographic links and shared topic labels do not establish numeric comparability.
4. Run the metric export, structured export and bundle verification. Check preserved IDs, source spans, zero values, gaps, overlaps, scope changes, year resets, conflict visibility and evidence removed by filters.
5. Test the consumer with the exported selector, record the release identity and distribute through the publication handoff. Preserve earlier bundles and their producer versions.

Publication and observation dates remain distinct, including a publisher edition label that precedes its stated reporting period end. The capture cutoff selects sources known by that time. It does not reconstruct historical editorial decisions; the bundle carries the review time explicitly.

## Efficient maintenance

Index candidate measurements by programme/authority, disease definition, metric, unit, population/geography, case category, count basis and baseline. Missing values retain their reasons and do not imply equivalence. Record the evidence supporting an approved segment and its method version. Reassess the affected segments when a report, method, revision or editorial decision changes, following the [reassessment procedure](LINK_REASSESSMENT.md).

New reports normally require their own measurement review and comparison with the existing method, plus the neighbouring observations relevant to the permitted operation. A retroactive correction can affect earlier segments and any derived results, so follow its dependencies rather than limiting review to the latest two points. Method matching and export preparation are local work; model calls are reserved for source material that still requires interpretation. Keep full export integrity checks even when analytical review is incremental.

## Evidence basis

[CDC surveillance evaluation guidance](https://www.cdc.gov/mmwr/preview/mmwrhtml/rr5013a1.htm) identifies standardized case definitions, data quality, representativeness, sensitivity, timeliness and stability as relevant to interpreting surveillance. Its [analysis guidance](https://www.cdc.gov/surv-manual/php/table-of-contents/chapter-20-analysis-of-surveillance-data.html) recommends examining completeness, reporting delays and application of case definitions. These support review of the reporting process alongside matching measurement fields.

[WHO's surveillance data notes](https://data.who.int/dashboards/covid19/data) describe retrospective revisions and differences in definitions and reporting practices. Their implication for ATLAS is to preserve data versions and distinguish reported totals from estimates of disease occurrence. The connection rules are an ATLAS implementation informed by this guidance; they are not a validated statistical estimator.
