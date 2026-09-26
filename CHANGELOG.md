# Changelog

## v0.1.0-alpha.8 — 2026-09-26

- Add an isolated compact digest trial with publication-version selection, claim evidence, persistent diagnostics, and usage reports.
- Permit the Codex transport to use a supplied extraction contract and prompt. The registry extraction contract remains unchanged.

## v0.1.0-alpha.7 — 2026-09-25

- Support an inclusive publication window in days; configure a 14-day workflow.
- Persist model attempt starts, outcomes, durations, and Codex diagnostic files. Report active work and failures during extraction.

## v0.1.0-alpha.6 — 2026-09-25

- Apply a six-calendar-month publication window to collection, extraction, review queues, and report evidence without removing ledger history.
- Record the publication window in report metadata. Exclude relationships and retained opportunities whose evidence falls outside the view.
- Data schema 0.1.2; report template 0.1.1.

## v0.1.0-alpha.5 — 2026-09-25

- Constrain extraction dates to complete ISO dates in the model schema. Retain month-only source dates as unknown day values with their precision described in the extraction.
- Record explicit editorial verification of numeric anchoring flags, including number words, while retaining the original flags. Missing source quotes remain blocking.
- Data schema version: 0.1.1.

## v0.1.0-alpha.4 — 2026-09-25

Source adapter 0.2.1 follows dated ECDC and EFSA archive pagination, selects ECDC PDFs by attachment title, and scopes EFSA collection through publisher topic labels. RIVM backfill uses its published sitemaps. FAO captures select the situation report body and retain edition dates and identify the historical coverage limit. Robots handling preserves query rules, wildcard precedence, merged groups, and crawl delays. Collection suspends hosts after authorization or rate-limit responses. The missing-only collection mode resumes backfills without downloading captured URLs. Ordinary collection reprocesses documents when the parser version differs from the cached text.

## v0.1.0-alpha.3 — 2026-09-25

Local Codex subscription extraction shares the chunk queue, evidence validation, and editorial review flow. Extraction cache identities include the provider.

## v0.1.0-alpha.2 — 2026-09-25

EpiWeekly provides the `epiweekly` package and command, `EPIWEEKLY_` deployment settings, a bounded backfill configuration, and local monthly source reading reports. Invalid XML feeds produce explicit source failures in collection coverage.
