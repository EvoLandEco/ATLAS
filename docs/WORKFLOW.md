# Weekly digest workflow

## Purpose and implementation

The weekly digest answers three questions: what deserves attention, what changed, and which sources or research resources merit a closer look. Detailed extraction serves selected investigations rather than every captured article.

This document specifies the workflow design. The installed CLI supports collection, the 14-day publication window, full-schema extraction, attempt records, evidence checks, editorial review, and sealed reports. The isolated `scripts/digest_trial.py` experiment supports compact claims, evidence references, and selection of one captured version per publication. Expansion into registry records and selective detailed extraction require implementation and evaluation. The commands in the README invoke the installed workflow; they do not select a digest extraction mode.

## Collection and document selection

Use the configured publication window, containing 14 dates ending on the report date, inclusive. Preserve every captured version, its source dates, and its actual capture time. An older event remains relevant when a publication within the window reports developments about it.

For the digest, select the latest captured version of each canonical publication available at the knowledge cutoff. Record that choice. Reuse extraction only when the captured text and interpretation context match, including source identity, title, publication date, model, prompt, and extraction contract. A corrected date can change interpretation even when the body text is identical.

Distinct publications remain distinct evidence, including reports that repeat the same outbreak total. Document selection does not establish event identity or permit addition of overlapping counts. Earlier versions remain available for correction review and historical analysis.

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

## Validation before a batch run

Compare the compact workflow with full extraction on the same captured sources. Include a WHO outbreak report, an ECDC bulletin, a relevant EFSA or RIVM article, and an irrelevant article. Include repeated captures and at least one document with ambiguous count scope or missing dates.

Measure missed important developments, numeric and date errors, scope and missingness errors, evidence support, input and output tokens, elapsed time, failures, and editor effort. Check exact expansion of retained claims separately from the editorial choice of which claims to retain.

Keep the same provider and model during this comparison. Choose a faster model only after the compact contract passes the content checks, then compare models on the same sources. Concurrency can shorten a batch but does not reduce its token use.

Require source verification of retained claims and no missed developments judged essential to the briefing before processing the complete queue. Record intentional omissions of analytical detail. Report observed savings rather than assuming that a smaller payload guarantees a particular speedup. See [Evaluation](EVALUATION.md) for the checks and measured baseline.
