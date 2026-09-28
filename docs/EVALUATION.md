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

## Direct-source adapter validation

The 26 September 2026 validation of source adapter 0.3.0 passed 116 tests. Fixtures exercise PDF byte validation, publication and attachment URL separation, NCDC edition-date parsing, unavailable disease series, and WHO publication dates. The synthetic report bundle and its replay each passed verification with eleven tables, 58 rows, and 22 checksummed files.

The acquisition window from 26 June through 26 September 2026 yielded six WHO Africa bulletins, four PAHO reports, and fourteen NCDC reports. WHO's emergency category exposed 25 publications whose document host failed access checks. The GDELT discovery probe returned HTTP 429. Archive gaps, invalid edition labels, and unavailable NCDC series remain explicit coverage limits. Public archive access is not a measure of global surveillance recall.

The existing 67-publication corpus supplies the comparison baseline. All 24 added publications completed compact extraction in 24 subscription calls, using 464,164 input tokens and 64,966 output tokens. Quote and URL anchoring checks reported no flags. The map contains 34 tracks, 114 report selections from 49 source documents, and 13 relationship assessments; its JavaScript replay checks pass. These checks do not replace semantic review. Compact extraction uses the same prompt and contract for the added publications; source collections and output counts do not establish semantic accuracy. The private reading library and map retain source evidence and review status. Registry acceptance and transmission confirmation require editorial decisions.

## ATLAS release validation

Version 0.1.0a10 passed 117 tests on Python 3.14.0, including command configuration through `ATLAS_PROVIDER` and `ATLAS_MODEL`. The installed distribution passed dependency checks. Schema generation changed only the report title; extraction prompts, analysis assets, and vocabulary retained their hashes.

The synthetic bundle and its replay each passed verification with eleven tables, 58 rows, and 22 checksummed files. Their ZIP archives were byte identical. The 1,394-record operational ledger retained its verified head hash, and all 2,620 protected evidence and history files retained their bytes. The map checks exercised temporal cutoffs, capture visibility, conflicting reports, playback, and relationship evidence gates. No collection or model calls were needed for these checks.

## Exploratory map checks

Version 0.1.0a11 passed 117 Python tests and the JavaScript checks for disease groups, shared documents, duplicate support and absent endpoints. Demo checks exercised all 119 exploratory links, the type filter, place selection, source details and both replay date settings. The final view contains 48 same-disease links and 71 same-bulletin links. These counts describe comparisons available in the selected corpus. Editorial review determines epidemiological relationships.

## Reporting window and source link checks

Version 0.1.0a12 passed 117 Python tests and the JavaScript checks for typed source links, quoted support, endpoint precision and inclusive reporting windows. Demo checks covered a single-day window, crossing handles, fixed-width playback, both date settings, link filtering and source evidence. The full-window map contains seven geographic links: four reported journeys or importations, one shared event and two source hypotheses. The 13 source assessments remain available. The [technical review](LINK_REVIEW.md) assesses epidemiological relevance and the evaluation still needed.

## Structured output evaluation

Validate the [research export](SITE_EXPORT.md) at three levels. Contract checks cover schemas, stable identities, entity references, source hashes, exact evidence spans and indexed memberships. Selection checks cover inclusive publication and capture windows, source filters, missing observation dates, zero values, retained conflicts and correction eligibility. Source review checks whether each assertion and comparison has the stated meaning, scope and evidential support.

Include comparisons within one claim and across documents. Test contradictions, explicit corrections, supersessions, independent corroboration, republication, different scope and unresolved associations. Check that repeated reports remain distinct evidence and that a later correction cannot alter an earlier reporting window. Geographic cases should cover occurrence, exposure, travel origin, destination, neutral location labels and incomplete role extraction.

Measure how often structured preparation assigns an incorrect scope, comparison kind, participant or geographic role. Record pending review coverage alongside extraction coverage. Analytical reuse also needs an assessment of compatible periods, populations, case definitions and denominators. Keep executed test results and snapshot findings in the export's validation receipt; these checks do not replace an epidemiological reference set.

## Export performance and equivalence

The export benchmark uses saved inputs for 202 publications, 785 records, 2,069 assertions and 705 topics. It compares repeated list scans and source normalization with per-invocation claim indexes, grouped memberships, normalized source text and cached quotation spans. Both implementations use the same evidence and eligibility rules. Measurements were taken on 26 September 2026, on macOS ARM64 with Python 3.14.0, with three fresh processes per stage and implementation.

| Stage | Repeated scans, median | Indexed processing, median | Runtime ratio | Peak memory, repeated / indexed |
| --- | ---: | ---: | ---: | ---: |
| Metrics export | 1.465 sec | 0.173 sec | 8.44× | 144 / 126 MiB |
| Structured export with validation | 1.026 sec | 0.720 sec | 1.42× | 175 / 189 MiB |
| Structured bundle verification | 0.224 sec | 0.092 sec | 2.43× | 108 / 108 MiB |

Elapsed time excludes interpreter startup and imports; peak process memory includes them. Filesystem caches may be warm. Source acquisition, model extraction, editorial work and browser rendering are outside these measurements. The memory figures are the largest observed peak across three runs. Temporary indexes and quotation matches retain extra objects during structured export; they are released with the invocation. No model calls were made, and no token reduction is attributed to this optimization.

With the clock and software-version field held constant, every file in the metric and structured bundles matched byte for byte, including schemas, HTML, selection code and manifests. This comparison preserves array order, identifiers, evidence spans and checksums, rather than comparing counts alone. Real exports retain their actual generation time and software provenance.

Validation executed for version 0.1.0a15: 146 Python tests, both JavaScript rule checks, schema regeneration with no schema differences, and a synthetic demonstration whose replay ZIP matched exactly. The performance fixtures check single source normalization, panel membership with multiple supporting records, repeated support references, stable ordering, quotation occurrences, Unicode offsets, PDF page boundaries and rejection of invalid memberships.

The principal membership joins build indexes in proportion to input entities and relationship participants, then visit matching members. Panel candidates retain all-support eligibility checks and are sorted into input order. Source normalization is proportional to captured text size rather than repeating that pass per quotation. Distinct quotation searches still scan source text; some place expansion and revision graph traversal remain dependent on graph size. Collection history scans and whole-batch progress writes remain separate scaling limits. The measured ratios describe this dataset, not a guaranteed speedup for a complete weekly run or a larger archive.

## Compact figure selection

Compact grouping interface 1.0.0 is checked against all 5,778 inclusive publication windows formed by the six-month dataset's 107 publication dates. Capture windows, reporting-channel selections and knowledge cutoffs bring the audit to 5,794 selections. Every existing selector field matches the context-based reference selection; the compact fields supply a separate display view.

The audit found two repeated display figures in the DRC topic: 7,890 confirmed cases and 3,799 related deaths. Each retains two source measures, from ECDC and WHO. No other multi-measure compact groups appeared in the audited selections. These are facts about the captured dataset and display selection, not a claim of independent confirmation or accepted event identity.

Synthetic selector tests cover grouping before the card limit, source attribution, partial windows, source filters, cutoffs, corrections, zero, missing dates and values, conflict flags, explicit disagreement and scope comparisons, and differences across measurement context fields. The bundle comparison preserves all dataset content apart from software provenance and generation time. Version 0.1.0a16 passed 146 Python tests, both JavaScript checks, unchanged data schemas and structured bundle verification.

## Geographic preparation evaluation

The six-month assessment covers 785 saved report entries dated 26 March through 26 September 2026. It retains 112 source geographic reviews and assesses 673 further entries: 571 assessed, 73 without a specific location and 29 unresolved. The prepared data contain 594 mapped reporting topics, 1,275 topic-location entries and 127 source geographic links: 110 reported movements, eight shared events and nine source hypotheses. Several entries can describe the same occurrence; these counts are not independent outbreaks or transmission chains.

Content comparison preserves all 785 report entries, 2,069 source assertions, 84 measurements, seven numerical comparisons, measurement contexts, existing evidence and ledger history. Geographic preparation has its own review timestamp and preserves the reviewer and time on retained comparisons. All 5,778 inclusive publication windows, plus capture windows, source selections and knowledge cutoffs, compare map topic-point eligibility with structured geographic memberships and preserve existing figure selections across 5,794 checks.

Version 0.1.0a18 passes 167 Python tests, both JavaScript rule suites and strict TypeScript declaration checks. Offline DOM checks cover the full date range, country selection, the Kent meningococcal report quotation, inclusive windows, fixed-width playback, capture dates and finite coordinates. Browser visual inspection is not included in these checks. A two-entry prompt evaluation covers a named travel origin with no destination and a training report whose quotation supplies no country: neither produces an unsupported geographic line.

The main assessment used 59 successful subscription-provider batches, with 963,841 input tokens, including 145,152 cached input tokens, and 222,752 output tokens. The two-entry prompt evaluation used 11,393 input tokens, including 8,064 cached input tokens, and 423 output tokens. Saved per-entry results, prompts, model receipts and source-review adjudications support replay. No acquisition or repeated digest extraction was required. These usage figures describe this run; they do not establish geographic accuracy. The chronological reference corpus below remains the method for measuring extraction and linkage quality.

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

## Evaluating link reassessment

The [reassessment procedure](LINK_REASSESSMENT.md#6-validate-and-complete-the-run) defines required replay scenarios, an audit of unchanged assessments and completion receipts. Evaluate candidate retrieval recall separately from correctness of link type, endpoints, direction and uncertainty. An empty candidate set does not establish that no relevant report exists. Record scoped review coverage and model usage alongside content-preservation checks. These procedural scenarios require their own execution receipts; the six-month geographic validation does not establish their performance.

## Selector and geographic export scaling

Version 0.1.0a20 retains site contract 1.1.0 and metrics 0.2.0. The selector benchmark uses the captured graph at 1×, 2×, 4× and 8× with independent identities. Five warmups and eleven timed calls produce a median for full and source-filtered selections. The benchmark script checks complete output equality against a supplied reference. The stress test excludes JSON loading, graph construction, rendering and model extraction; it is not an end-to-end capacity claim.

Real-data parity covers 5,795 inclusive date, capture-cutoff and source selections. A membership-order fixture preserves document order when a coverage edge lists records in a different order. Geographic export checks retain the complete structured output, including identifiers, evidence and array order, after removing only the generation timestamp. Fresh Python processes provide three timing samples per phase. Verification memory includes untimed preparation of its matching input.

The implementation indexes record selection and geographic memberships. It does not reduce model tokens, alter scientific selection rules, change schemas or create a persistent cache. Exact source quotation search, serialization, source discovery, full archive scans and browser rendering require separate measurements. Record current run counts and timings in the corresponding benchmark artifacts.

## One Health export validation

Version 0.1.0a23 passes 225 Python tests plus the JavaScript selector and map checks. The One Health fixtures check source support, explicit endpoints, content identities, negative findings, genomic direction, host requirements, incomplete reviews, source selection, capture cutoffs, observation dates and exact proposition corrections. Sealed site 1.2.0 and 1.3.0 verification fixtures preserve their original bytes.

A private nine-month enrichment run retained all baseline measurements, comparisons, geographic memberships and relationships, reviewed chains and reviewed series. Its 107 selected views preserved the baseline geographic and longitudinal results. These checks establish contract and selection consistency; complete archive review and extraction sensitivity remain separate evaluation tasks.

The selector stress test includes disease, chain and One Health evidence arrays. On Node 25.2.1 on the local Mac, the full-window median was 15.6 ms for 1,624 entries, 29.9 ms for 3,248, 63.8 ms for 6,496 and 138.3 ms for 12,992. Each size uses independent copies with distinct identities, five warmups and eleven measured calls. JSON loading, rendering, collection and source interpretation are outside the timing. The metric build took 0.68 seconds and the structured export build 2.00 seconds on the captured input. These are measurements on this input, not predictions of future source complexity.

The One Health analytical panel checks cover date precision, reporting cutoffs, undated findings, explicitly matched sampling denominators, zero tested counts, clinical count exclusion, exact proposition corrections and source selection. Run `python -m pytest -q tests/test_one_health_panels.py tests/test_site_versions.py` for these fixtures and sealed contract compatibility. Run `bash scripts/check_types.sh` with TypeScript available on `PATH`, or set `TSC` to its executable path, to compile the public declarations with library checking enabled. Python model validation does not check TypeScript declaration collisions.
