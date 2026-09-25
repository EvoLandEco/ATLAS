# Changelog

## v0.1.0-alpha.4 — 2026-09-25

Source adapter 0.2.1 follows dated ECDC and EFSA archive pagination, selects ECDC PDFs by attachment title, and scopes EFSA collection through publisher topic labels. RIVM backfill uses its published sitemaps. FAO captures select the situation report body and retain edition dates and identify the historical coverage limit. Robots handling preserves query rules, wildcard precedence, merged groups, and crawl delays. Collection suspends hosts after authorization or rate-limit responses. The missing-only collection mode resumes backfills without downloading captured URLs. Ordinary collection reprocesses documents when the parser version differs from the cached text.

## v0.1.0-alpha.3 — 2026-09-25

Local Codex subscription extraction shares the chunk queue, evidence validation, and editorial review flow. Extraction cache identities include the provider.

## v0.1.0-alpha.2 — 2026-09-25

EpiWeekly provides the `epiweekly` package and command, `EPIWEEKLY_` deployment settings, a bounded backfill configuration, and local monthly source reading reports. Invalid XML feeds produce explicit source failures in collection coverage.
