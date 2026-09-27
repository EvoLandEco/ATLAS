# Weekly digest workflow

## Purpose and implementation

The weekly digest answers three questions: what deserves attention, what changed, and which sources or research resources merit a closer look. Detailed extraction covers concrete analytical opportunities found during review, using the relevant captured sections.

This document specifies the workflow design. The installed CLI supports collection, the 14-day publication window, full-schema extraction, attempt records, evidence checks, editorial review, and sealed reports. The isolated `scripts/digest_trial.py` experiment supports compact claims, evidence references, and selection of one captured version per publication. Expansion into registry records and selective detailed extraction require implementation and evaluation. The commands in the README invoke the installed workflow; they do not select a digest extraction mode. The structured export commands process saved selections and reviewed annotations into versioned research datasets. They run as a separate preparation step using captured evidence.

The reference workflow runs in Codex with GPT-6 Astra and High reasoning. Other harnesses and LLMs can implement the documented contracts, but the complete workflow has only been tested in Codex. Record the actual model and prompt for each extraction, and evaluate any different setup before operational use.

Less capable LLMs can miss evidence, misread measurement scope or introduce unsupported links. Claude Opus 5.5 is a safer substitute to evaluate than a less capable model, based on the [benchmark comparison in the README](../README.md#agent-setup). It has not been validated in ATLAS. Compare a candidate model on identical captured sources using the [evaluation protocol](EVALUATION.md), record omissions and unsupported claims, and retain all evidence and editorial checks.

Weekly production maintains reviewed longitudinal series through the procedure in [Longitudinal analysis](LONGITUDINAL_ANALYSIS.md). Reuse valid measurements, assess new observations and source revisions, and review affected comparison edges before export. Candidate enrichment opportunities remain pending until their measurements and comparisons have passed this review.

Follow [Chain review](CHAIN_REVIEW.md) when captured evidence supports a transmission, contact, travel or reporting sequence. Review episode membership and exact connections, retain dates and location precision, and reassess affected chains during weekly work and historical expansion. Record unsupported or unresolved candidates in the review receipt.

## Numeric enrichment and coverage

Digest completion means that the selected findings and their quotations were prepared. It does not mean that every table, subgroup or measurement was extracted. Keep three questions separate: was the document collected, which numeric sections were reviewed, and which comparisons were reviewed for analysis? Count distinct documents separately from report entries; a publication can supply several entries.

Numeric enrichment is a required production step for concrete opportunities identified during source review. Process every identified opportunity through extraction, evidence review and export preparation within its defined source scope. A list of promising fields is an inventory, not a completed analysis. Carry historical opportunities into the next production pass and reuse validated work.

Read retained enrichment receipts under `.runtime-state/enrichment/` before production and keep a dated source-bound receipt for each batch. Reuse its validated input annotations and source hashes; write a new receipt for later review so earlier outcomes remain traceable. Each item records a stable reference, document and source hashes, section or table, requested fields, existing annotation keys, added measurement and series IDs, review outcome and unresolved questions. An item is complete when its supported values are exported and its comparisons are assessed. Where a source cannot support a value or comparison, record the specific missing evidence and the investigation needed; do not invent a value or leave the item as an unexplained future suggestion. Silence on a scientific decision leaves that question pending while supported extraction continues.

Choose a defined source programme and analytical question for numeric enrichment. Read the captured table headers, reporting periods, definitions and revision notes, then add only missing measurement annotations. Retain existing values and IDs. Record the reviewed document IDs, sections, fields and unresolved questions in the batch receipt. Unknown numeric coverage remains unknown; a completed digest is not a certificate of exhaustive extraction.

Prioritize repeated tables with explicit periods, followed by useful single-report counts and source-described subgroup or exposure findings. A table can support separate observations before it supports a continuous series. Follow [longitudinal review](LONGITUDINAL_ANALYSIS.md) before connecting those observations. Preserve different case classifications, suspected cases investigated versus reported cases, animal detections versus affected animals, and source-reported ratios versus calculated risks.

Reuse validated digest findings and captured source text. Enrichment requires targeted interpretation of the selected sections rather than another acquisition or a full archive extraction. Record API or CLI extraction calls separately from agent-session review; an absence of external extraction calls does not measure the session's token use. Keep run-specific inventories and candidate examples with the research artifacts.

## Collection and document selection

Use the configured publication window, containing 14 dates ending on the report date, inclusive. Preserve every captured version, its source dates, and its actual capture time. An older event remains relevant when a publication within the window reports developments about it.

For the digest, select the latest captured version of each canonical publication available at the knowledge cutoff. Record that choice. Reuse extraction only when the captured text and interpretation context match, including source identity, title, publication date, model, prompt, and extraction contract. A corrected date can change interpretation even when the body text is identical.

Distinct publications remain distinct evidence, including reports that repeat the same outbreak total. Document selection does not establish event identity or permit addition of overlapping counts. Earlier versions remain available for correction review and historical analysis.

## Three weekly agent jobs

The Codex schedule uses three jobs in the project chat: a preceding-batch review on Wednesday at 07:00, weekly production at 08:37, and the review inbox at 12:00, all in Europe/Amsterdam. These are agent operating instructions using existing collection, extraction, review and export tools. The package does not install this schedule or provide a single command for the three jobs.

### Shared scope and run records

Use the scheduled Wednesday as the cycle date. Production covers the seven complete local publication dates from the preceding Wednesday through Tuesday, inclusive. For the 30 September 2026 cycle, that is 23–29 September. A delayed run retains its intended cycle and records its actual capture and completion times. Keep publication, observation, capture and review dates separate.

The default CLI configuration selects 14 publication dates. For these jobs, use a private run configuration or explicit digest date bounds for the seven-date selection and check selected documents before extraction. Preserve the default configuration for other uses. Discovery can examine a wider interval for delayed publications and revision notices; separate those additions from the week's publication cohort. The discovery interval must not silently expand the extraction queue.

Read preceding receipts and sealed bundles before acting. Save job receipts under `.runtime-state/weekly/CYCLE/` as `review.json`, `production.json` and `inbox.json`. Record the cycle, publication window, capture cutoff, starting and ending ledger heads, document IDs and hashes, extraction contract, reused and processed counts, usage, checks performed, pending work and output paths. Execution status is `running`, `completed`, `partial` or `blocked`. A completed review can still contain unanswered editorial questions. Identify unchecked sources and unprocessed documents explicitly.

Use the [handoff receipt fields](PUBLICATION_HANDOFF.md#receipt-fields) for machine-readable completion. Production records the review receipt hash and its export reference. The inbox records both predecessor receipt hashes, the final validated export and any unapplied user decisions. Write a completed inbox receipt even when the review requires no action, then regenerate `reports/publication-handoff.json` with `atlas handoff --cycle CYCLE`. This records execution only; unanswered questions remain pending. The consumer gates weekly sync on this freshly validated handoff.

Reuse a completed receipt only when its inputs and outputs still match. Resume partial work from saved results without forcing acquisition or repeating successful model calls. Scheduled times are start requests, not dependency guarantees. Inspect predecessor receipts and active processes before shared writes. Respect the writer lock and avoid overlapping export writers. Continue independent work when a predecessor is partial, identifying affected outputs and their unreviewed status. Ledger corruption or evidence-integrity failure blocks dependent writes.

For geographic links, use the [reassessment procedure](LINK_REASSESSMENT.md) across all three jobs. The review job identifies changed evidence and affected dependencies; production assesses new reports and their relevant historical context; the inbox presents unresolved link interpretations and applies supplied decisions. Historical expansion follows the same procedure with a wider acquisition interval and its actual capture cutoff.

### 1. Review the preceding batch

Select documents from the preceding production receipt, including late captures and revised versions. On the first cycle without that receipt, use documents captured or revised during the preceding seven complete local dates and record this initial scope. Do not reopen the entire archive each week.

Revisit canonical sources through authorized adapters for publisher corrections, withdrawals, changed attachments and follow-up notices. Compare metadata and content with saved versions. `--missing-only` skips captured URLs and therefore cannot perform this check. Preserve changed source objects and capture times. Failed retrieval is an access gap, not evidence of an unchanged source.

Review findings against quotations and surrounding context. Check material omissions, numeric values, units, case definitions, populations, geography, date roles, cumulative versus incident reporting and duplicate totals. Inspect PDF pages and tables when text order is uncertain. Check identifiers, comparison participants, correction lineage, map endpoints, date filtering and bundle checksums. Record semantic and layout review coverage; quotation matching alone does not complete it.

Correct reproducible extraction or software errors through recorded corrections and focused validation, preserving original evidence and sealed outputs. A software fix needs a failing fixture before changing semantics. Re-extract only changed or invalid findings and rebuild affected derivatives. Accepted event identity, merges, splits, disputed interpretation and unresolved count scope require an explicit editor decision. Put those questions in the inbox. Produce a concise report of source changes, verified repairs, unchecked material and issues carried forward.

### 2. Produce the recent week's outputs

Collect configured sources within their access and request limits. Keep EFSA within the agreed One Health topics. BEACON and WOAH WAHIS are possible sources, not used: collaboration is not established and no authorized route is available. Keep both disabled; retain recorded institutional-access and historical-coverage questions for other sources. Source caps, failed downloads and inaccessible attachments remain coverage gaps.

Select the latest captured version of each eligible publication at the cutoff. Reuse validated extractions across batches when source metadata, text, provider/model context, prompt and schema match, and check evidence references. An unrecorded model identity is not a proven match for a model comparison. Compact digests and detailed registry extractions remain separate contracts.

Use local Codex subscription extraction for concise findings from unprocessed or changed publications. Retain documented call, input and response limits; report excess work instead of silently increasing budgets. Do not switch to paid API calls or run a second detailed extraction of every digest. Process the concrete enrichment inventory using the saved sources and the numeric coverage rules below; unrelated detailed investigation requires a specific question. Label source corrections and late arrivals with their dates.

Complete the concrete enrichment inventory, including retained historical items. Prepare the briefing, coverage report, review queue, scoped metrics, structured dataset and map/network preview from saved inputs and reviewed annotations. Record supported observations even when comparison review leaves them unconnected. Reassess geographic evidence affected by added claims, validate the exact export and send its release reference to an authorized consuming project; record adoption separately from sending the handoff. Reuse established preparation code, checking date and path constants in private batch scripts before execution. Write dated outputs under `reports/weekly/CYCLE/` and preserve historical exports. Validate evidence, schemas, references, comparison lineage, geographic roles and checksums. Refresh the local demo from a validated export, keeping historical context distinct from weekly findings.

Record captured, reused, extracted, failed and pending counts, measured usage and output links. Model findings remain drafts until reviewed. Production completion does not imply acceptance of every event or approval for public release.

### 3. Present the review inbox and apply decisions

Read both job receipts, source gaps, incomplete extractions, digest flags, export annotations and the historical review backlog. The CLI review export is date filtered; inspect the full registry review queue and unresolved annotations to include historical issues without re-extracting those documents.

Give each issue a stable reference based on its document, candidate or assertion and the question. Retain first-seen and last-changed dates, evidence links, impact, status and supplied decisions. Group repeated symptoms of the same issue. Prioritize integrity failures, interpretation conflicts, missing evidence and research questions. Present a short list of new or materially changed issues, with a link to the full backlog and counts of unchanged items.

Explain what needs checking, suggest concrete actions and state the decision needed. Suggestions are not decisions. No response leaves an issue pending: do not alter evidence, accept candidates, assign events, resolve conflicts or rerun work because the user has not replied. A request to stop surfacing an issue changes its presentation, not its scientific status. Do not repeatedly prompt for unchanged items.

Record clear user decisions with the issue reference, exact instruction, user attribution, time, affected IDs and evidence version. Apply each decision once through the supported review or correction path, then verify and rebuild affected selections, metrics, bundles and views. Use `seal` for a registry report revision without acquisition. If evidence has changed, check that the decision still applies; ask about material ambiguity rather than extending its scope. Preserve original versions and decision history. Collection or extraction requires a source change, failed extraction or explicit investigation need, not merely an inbox reply.

The inbox does not approve publication or contact external parties. With no new findings and no unapplied decisions, take no further action.

## One concise extraction per source

Ask the model for briefing facts from the selected source: relevant events and developments, key measurements, uncertainty, and research resources. Do not add a separate model call merely to classify relevance. An irrelevant source can return an empty result with a short reason in the same call.

Retain:

- Disease or pathogen, host, place, and the source's event description.
- Material developments such as geographic spread, a correction, a change in reported status, or an explicit transmission finding.
- Counts needed to describe those developments, with units, case classification, reporting period, date basis, scope, qualifiers, and denominators where relevant.
- Source-backed uncertainty, contradictions, and limits that affect interpretation.
- Relevant data releases, research calls, and resources with their source URLs and deadlines when stated.
- Verbatim evidence for each retained claim, including enough context to interpret a number.

Historical examples, general disease descriptions, repeated prose, and routine recommendations do not become separate digest events unless they explain a material development. Detailed subgroup tables belong to a selected investigation unless the subgroup result itself is central to the weekly update. There is no fixed top-N cutoff that silently discards relevant events.

Use complete article text when it fits the input budget. For longer bulletins, process identifiable sections and preserve their headings and source positions. Account for every section as processed, awaiting extraction, or requiring layout review. Do not claim full-source coverage for a partial extraction.

## Compact model output

The model supplies facts and evidence; Python supplies identifiers, provenance, database structure, and report formatting. Keep the model-facing contract separate from the full registry contract.

Represent ordinary reported values as scalars. Represent repeated evidence text once and reference it from the claims it supports. Shared measurement context may be stated once for a group of observations when its applicability is explicit. Each observation must resolve to an unambiguous scope and evidence reference.

Define missing-value encodings in the contract. A field deliberately left for detailed extraction is `not_extracted`, not `not_reported`. Explicitly unknown, inapplicable, conflicting, and unverified values retain their distinct meanings. Preserve zero and Namibia's country code `NA`.

Expansion into registry records must be deterministic and validated. It may restore declared defaults and references; it may not infer missing scientific facts, repair unsupported claims, or invent dates. Reject unresolved references or inconsistent context for review. A compact representation must reconstruct every retained claim with its original meaning and evidence.

## Editorial review and detailed extraction

Review the digest against captured sources before accepting events. Resolve event continuity, duplicate reporting, conflicting totals, and corrections explicitly. Mechanical quote checks support this review but do not establish scientific accuracy.

Request detailed extraction for a specific source or event when a question needs subgroup measurements, complete time series, detailed case definitions, transmission evidence, genomic resources, or another clearly stated analysis. Record the question and requested fields. Unrequested detail remains in the captured source rather than consuming model output on every weekly run.

Detailed extraction uses the full evidence and measurement requirements. It does not automatically accept candidates or replace reviewed claims. Apply corrections and identity decisions through the existing editorial process.

## Briefing and analytical data

The briefing presents developments, source dates, evidence links, uncertainty, research leads, and unresolved coverage. Distinguish source statements from analyst questions. Label the analytical dataset as the reviewed claims selected for the digest; it is not an exhaustive transcription of all source measurements.

Keep outbreak entities, individual cases, surveillance aggregates, and research context separate. Never sum overlapping cumulative counts or describe their differences as incident cases without supporting source evidence. Absence from the digest does not establish absence of disease or resolution of an event.

## Structured data preparation and export

ATLAS prepares analysis-ready outputs that researchers can reuse across evidence reviews, quantitative investigations, maps and interactive applications. The [export contract](SITE_EXPORT.md) defines entities, fields, source references and selection rules. Structured preparation preserves scientific context alongside each value and makes the scope of completed review visible.

1. Select captured documents and retain their publication, observation and capture dates. Record document and claim identifiers, source hashes and exact quoted spans.
2. Review the measurements needed for the question. Preserve units, case definitions, classifications, populations, geography, periods and denominators. Leave fields awaiting extraction explicitly marked `not_extracted`; retain qualitative findings where numerical review is incomplete.
3. Review related assertions together. Distinguish contradictions, corrections, supersessions, independent corroboration, republication, different scope and unresolved associations. Record the participants, source sections, reason, evidence and review status. A numerical difference alone does not establish a conflict.
4. Prepare document, topic, reporting-channel and geographic memberships. Use neutral reporting-location names and codes, with explicit roles such as occurrence, exposure and travel origin. Source coverage describes reporting activity; epidemiological links require their own evidence.
5. Build the metric export and structured bundle from the saved inputs. Validate schemas, entity references, evidence spans, comparison lineage and checksums. Record review coverage and pending source questions in the bundle.
6. Select the relevant reporting window and measurement context for reuse. The supplied selector applies both date boundaries, exact evidence requirements and eligible corrections to figures. Analysts and applications use these definitions consistently across reports, maps and research views.

The export carries separate source assertions through disagreements and revisions. A later correction affects an earlier assertion only when its supporting evidence is eligible in the selected view. Publication and capture windows describe reporting activity; observation dates describe the underlying findings. Historical source filtering remains distinct from reconstructing historical editorial decisions.

Analysis readiness means that identifiers, provenance, measurement context and review states are available for inspection and selection. Aggregation and statistical modeling still require compatible observations and appropriate denominators. Repeated cumulative totals remain separate source assertions, and missing observations do not become zeros.

Snapshot metadata records the latest capture and the next planned collection with its timezone. The plan is independent of display filters and the reader's clock. Collection, review and public release have separate statuses.

Export preparation uses temporary claim and membership lookups within each invocation. It normalizes each source text once, reuses quotation searches within that document and resolves page numbers from source markers. Every referenced claim still passes the same evidence and eligibility checks. Output order, identifiers, fields and scientific interpretation stay fixed. These are local processing steps and consume no model tokens. See the [performance evaluation](EVALUATION.md#export-performance-and-equivalence).

Review numeric continuity using [Longitudinal analysis](LONGITUDINAL_ANALYSIS.md) before connecting observations in Trends. Preserve measurement IDs and source facts, attach captured method evidence, and approve exact adjacent pairs for the stated analytical use. Weekly runs review the new report and its neighbours; historical expansion also reviews the boundary with the existing series. A corrected measurement or method change requires reassessment of its dependent connections. Missing periods remain gaps. Export and test both date bounds, source selection and capture cutoff before release. Numeric coverage describes reviewed measurements separately from collected reports and geographic coverage.

Compact information cards use the selector's [compact figures](SITE_EXPORT.md#compact-figures). Matching recorded figures can occupy one display position with all eligible sources retained. Apply this grouping after evidence and date selection and before limiting the number of cards. Keep conflicting, differently scoped and undated measures separate. Display grouping does not alter source assertions, event identity, editorial acceptance or statistical comparability.

## Validation before a batch run

Compare the compact workflow with full extraction on the same captured sources. Include a WHO outbreak report, an ECDC bulletin, a relevant EFSA or RIVM article, and an irrelevant article. Include repeated captures and at least one document with ambiguous count scope or missing dates.

Measure missed important developments, numeric and date errors, scope and missingness errors, evidence support, input and output tokens, elapsed time, failures, and editor effort. Check exact expansion of retained claims separately from the editorial choice of which claims to retain.

Keep the same provider and model during this comparison. Choose a faster model only after the compact contract passes the content checks, then compare models on the same sources. Concurrency can shorten a batch but does not reduce its token use.

Require source verification of retained claims and no missed developments judged essential to the briefing before processing the complete queue. Record intentional omissions of analytical detail. Report observed savings rather than assuming that a smaller payload guarantees a particular speedup. See [Evaluation](EVALUATION.md) for the checks and measured baseline.

## Exploring the map

Geographic assessment and map preparation are required post-processing stages. Follow the [geographic review procedure](GEOGRAPHIC_REVIEW.md) for each production window. Account for every report entry with retained review, assessed locations, no specific location or an unresolved question. Apply the source relationship rules to added findings; reusing an earlier map is not evidence that the added reports contain no links. Build the map from the exact snapshot used for the validated structured export, check the displayed date extent, and record the build receipt before marking the run complete.

Use the reporting window to compare periods and follow source-described connections. The map displays travel or importation, shared events and explicit source hypotheses. Each link retains its source quotation, named endpoints, location precision and degree of certainty. The source network connects documents to the topics they cover.

Both date boundaries are inclusive. The selected date basis is publication or edition date, or capture date. Every supporting report entry must fall within the window for a link to appear. Playback advances the window at a fixed width. Observation and travel dates remain in the findings.

Keep outbreak follow-up, transmission, exposure and unresolved questions in the evidence panel. Use local diagrams when geographic endpoints are unknown. The [relationship rules](RELATIONSHIP_RULES.md) define each link; the [technical review](LINK_REVIEW.md) explains the research basis and data requirements.

## Language for docs and interfaces

Write for a reader who understands public health but may be unfamiliar with the software. Start with the finding, purpose or action. Use short sentences and familiar epidemiological terms. Prefer “reporting period” to “temporal scope”, “source quotation” to “evidence anchor”, and “reporting topic” to “track” in interface text. Keep exact field names in technical documentation where readers need them.

Describe what the data show. Use “suspected transmission” when that is the source assessment, and name the uncertainty that matters. Present a limitation once beside the relevant result. Put detailed methods and coverage information in their own sections. Avoid repeated statements defending the workflow or contrasting it with claims nobody has made.

Interface labels should guide exploration: “Explore connections”, “Shared event”, “Reported exposure”, “Read the source”. Keep the main view brief and place longer explanations in expandable panels. Source quotations, extracted findings, report contents and scientific identifiers retain their wording during a docs or interface edit.
