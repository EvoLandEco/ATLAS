# Daily Trends

Daily Trends follows recent public health reporting. It presents source findings, developments and questions to watch while the Wednesday workflow completes scientific review and reconciliation. A source can report a suspected disease or an unresolved cause. Each finding retains its attribution, diagnostic status, observation period and exact quotation.

## Schedule and scope

The daily job runs at 06:00 Europe/Amsterdam. It discovers the preceding seven complete publication dates plus publications on the run date, recording its actual capture cutoff. The saved daily catalogue retains earlier reports; moving the discovery window does not remove pending work. Automatic duplicate acquisition returns its receipt. An interrupted acquisition requires inspection before an explicit `--force` run. The separate daily archive preserves the weekly ledger and completion receipts.

Reports require a source-supported publication, issue or release date. A missing publication date excludes a report from extraction, review queues, report counts, exports and watch selection. Capture dates, observation dates and dates in URLs do not establish publication. Captures and review history remain in the private archive with `missing_publication_date` exclusions. Notification and sampling datasets retain their own date fields and evidence; these dates do not turn a dataset into a dated report.

Run one acquisition scheduler for the daily archive. Wednesday production imports exact captured objects and document identities from the daily archive, retaining original capture times, and checks sources for revisions. It reuses suitable evidence and extractions. A concise daily finding does not establish scientific integration or replace numeric, geographic, comparison, chain or One Health review.

## Daily commands

Use the installed `atlas` command from the repository environment. The acquisition command reads the weekly archive supplied by `--state` and writes the distinct archive supplied by `--daily-state`.

```bash
atlas daily-capture --daily-state .local/daily-trends/state --since YYYY-MM-DD --until YYYY-MM-DD
atlas daily-extract --daily-state .local/daily-trends/state --acquisition ACQUISITION.json --out .local/daily-trends/extractions
atlas daily-export --daily-state .local/daily-trends/state --acquisition ACQUISITION.json --annotations ANNOTATIONS.json --bundle WEEKLY_BUNDLE --snapshot SNAPSHOT.json --out DAILY_BUNDLE
atlas daily-verify --daily-state .local/daily-trends/state --acquisition ACQUISITION.json --annotations ANNOTATIONS.json --bundle WEEKLY_BUNDLE --snapshot SNAPSHOT.json --daily DAILY_BUNDLE
```

The acquisition path is recorded in `.local/daily-trends/state/daily-latest.json`. Extraction uses the signed-in Codex provider with tools disabled and bounded input, output and calls. Saved draft results bind source metadata, text, model request, prompt and schema. The agent checks drafts against captured source context and writes `daily-annotations.schema.json` records. A failed or unresolved draft remains pending. Cached failures require inspection; an automatic rerun does not spend more calls on them.

Daily review distinguishes source statements, attributed hypotheses and analyst hypotheses. Every finding requires an exact quotation. Unknown fields retain a missingness state; explicit zeros and country code NA remain values. Original titles and quotations accompany reviewed English translations. Source authenticity and diagnostic certainty are separate properties.

## Watch selection

Source monitoring and watch selection are separate decisions. Every enabled source contributes to discovery and the report catalogue. Publisher, country, language, publication volume and recent onboarding carry no selection weight. A small or empty board is valid.

Method `daily-watch-1.0.2` screens the complete set of reviewed daily findings, including recent captured reports from established sources. Each candidate names exact findings, a dated development, its time basis, a concrete follow-up question, supporting criteria and counterevidence. An agent checks those judgments against source context. The exporter applies the following decision rules to the reviewed inputs:

1. Require a source-dated development with reviewed current relevance and evidence supporting an active follow-up need. The publication date may describe a source's current assessment; it must not replace the onset or observation date. An older development remains eligible when source review establishes an active follow-up need. Elapsed days do not retire a card. A new publication about an old event does not qualify on that basis alone.
2. Keep routine surveillance, service announcements, retrospective accounts, resolved episodes and signals with unknown current relevance in Reports. Record the reason for exclusion. Routine increases require evidence of meaningful consequences or a specific change in spread before promotion.
3. Assign **Urgent follow-up** when an attributed authority statement establishes time-sensitive public health action. Assign **Heightened attention** when severe impact accompanies a documented change in spread or a response gap. Assign **Watch** for another supported current significance criterion: severe impact, a change in spread, an unusual event or a response gap. A missing criterion means the evidence does not establish it; it is not a zero risk estimate.
4. Order selected items by attention category, then the date of the supported development. Source count and mirrored reports do not raise priority. Group report support only after reviewing its subject and temporal scope; this presentation grouping assigns no outbreak identity. Preserve earlier or parallel reports as context rather than duplicate cards.
5. Reassess daily. The review due time schedules work; cards remain selected until a subsequent reviewed release explicitly replaces or retires them. A missed review does not remove a card or establish resolution. Re-reading a source does not advance its development date.

The daily review schedule is an editorial setting. It is not a clinical threshold or a validated disease-risk model. Source certainty, diagnostic certainty and editorial attention remain separate. An unconfirmed cause can warrant a watch item; conflicting or reassuring evidence must remain visible.

This approach draws on WHO's distinction between detection, verification and assessment, and the severity, unusualness and spread considerations in its [risk-assessment guidance](https://www.who.int/emergencies/risk-assessment). ECDC's [rapid-assessment guidance](https://www.ecdc.europa.eu/en/publications-data/operational-guidance-rapid-risk-assessment-methodology) supports explicit evidence appraisal and uncertainty. The ATLAS decision rules are an editorial selection method, not an implementation of either authority's formal risk assessment.

`watch_assessments` records every candidate and its decision, including exclusions. Every reviewed finding must be accounted for. Only qualifying assessments appear in `watch_items`. Each selected item supplies a concise reason for attention, a source-supported location and diagnostic label, and up to three short facts bound to exact findings. These fields together have a 55-word editorial budget; essential qualifiers, dates, units and attribution take priority over another fact. The consumer presents those texts and does not generate urgency or compress a diagnosis from a headline. Detailed findings, original quotations, translations and the follow-up question remain accessible together.

## Report status

Watch cards can show suspected disease, diagnostic developments, reported counts, geographic extent, source-described spatial links, response measures and possible sources. Selection assigns no outbreak identity, numerical risk score or scientific connection.

Each daily report carries **Weekly review pending**. This processing label is separate from suspected, confirmed or unresolved source findings. It clears only for the exact daily review version after all three Wednesday job receipts and the corresponding scientific export pass validation. A new source version or changed daily interpretation requires its own reconciliation. Wednesday's arrival does not clear the label.

The inbox records a reconciliation as `integrated`, `reviewed_not_exported` or `pending`, with its rationale, reviewer, time, weekly export ID and inbox receipt hash. Integrated reviews name exact scientific record IDs from the same captured document and source text. Pending editorial issues remain pending. Retain dated annotation files, receipts and exports as review history.

## Export and website handoff

The daily 0.2.2 bundle contains `daily.json`, its JSON schema, `daily-view.mjs`, validation receipt and manifest. It binds the scientific export ID and exact scientific manifest, site payload and map snapshot hashes. `daily-verify` reconstructs findings from captured text and review annotations, checks raw objects and pins the schema and selector. Verification of immutable 0.2.1 bundles uses their preserved selection rules, schema and selector.

Export preparation retains the supplied annotation file and records excluded document, review and watch identities in the private archive under `review/publication-exclusions/`. An assessment supported entirely by excluded reports stays outside the candidate. An assessment mixing dated and undated support requires review of its dated findings. Its attention judgment cannot be transferred by dropping evidence references.

`selectDaily` applies both date bounds, publication or capture basis, knowledge cutoff, sources and countries. A watch selection appears only when every supporting document and finding is eligible. The eighth selector argument, `asOf`, supplies the live assessment time. Without it, an explicit knowledge cutoff or the export knowledge cutoff supplies a reproducible assessment time. Historical views use their explicit knowledge time. The selector retains selected cards after their review due time and also returns overdue items for work planning. A reviewed release controls selection; elapsed time does not retire a card. Scientific review-derived fields remain unavailable before their review time; current-release publication identity metadata is described below. Publication, capture and review times describe different stages.

The acquisition receipt records its capture cutoff; the daily knowledge cutoff also accounts for completed source and reconciliation reviews. Explicit `channel_id` values use the scientific export's acquisition-source mapping. `base_document_ids` identifies scientific versions of the same dated publisher publication for report presentation. Equal publisher URLs and publication dates supply direct bindings. Publisher URL aliases require an explicit whole-publication review in `publication_bindings` within the daily annotations.

Each publication binding names exact document versions with raw and text hashes, every scientific assertion and its evidence, reviewed republication comparisons, a reason, reviewer and time. All versions must share a publisher channel and publication date, and at least one must be an eligible daily document. Comparison evidence must connect the versions and cover their findings; assertion republication alone does not assign whole-publication identity. A changed source hash, incomplete evidence scope or different dated edition requires a separate review. The binding retains every scientific record, source version, measurement and interpretation status. It supplies presentation membership, not equal source text or scientific acceptance. Consumers retain the scientific versions and their evidence while showing the daily version's processing state. Reports outside the daily catalogue cannot be attached to unrelated daily rows.

Publication identity is metadata for the current release. It does not reconstruct the history of identity adjudication. The binding review keeps its actual reviewer, time and captured comparison provenance in the private annotations; it does not change source, finding, watch or reconciliation review times or the scientific knowledge cutoff. Daily contract 0.2.2 and its selector retain their schema and selection rules. Consumers apply date, capture and evidence eligibility to each scientific version before grouping eligible report rows. Annotations with no publication bindings retain their canonical hash. Display grouping does not combine analytical observations, infer event identity or resolve source conflicts.

Keep daily reports and evidence separate from scientific panels, accepted event identities, geographic graphs and analysis totals. Shared document IDs allow the report list to combine references without counting a captured publication twice. Scientific disease, topic and relationship filters require reviewed bindings; daily reports without those bindings cannot satisfy them.

Website distribution uses an independent daily release pointer bound to a specific scientific base. Validate the complete candidate and consumer before activation. Preserve immutable payloads and an exact approval manifest. Weekly publication and daily publication have separate receipts; a daily release does not establish Wednesday completion.

## Sources and coverage

The daily scheduler uses the complete `config/atlas.yaml` source list. Acquisition visits every enabled profile and records failed, partial, empty and manual-access outcomes. Saved captures can enter review while live acquisition remains incomplete. Each source check retains its recorded time; a reassessment does not advance that time. Unknown times remain null. A source enabled in the monitoring configuration but excluded from the acquisition is `not_checked`.

Compare the configured source list with acquisition receipts before claiming coverage. Account for every eligible captured document as reviewed or pending, then account for every reviewed finding in watch assessments. These are separate stages: a complete candidate review does not establish complete source discovery. Preserve source gaps in the private review inbox even when the website hides acquisition controls.

The source profiles include Santé publique France news, Robert Koch Institute Epidemiologisches Bulletin, China CDC respiratory and notifiable disease surveillance, and US CDC MMWR Weekly. National archive editions require year review when the calendar changes. WHO Disease Outbreak News, WHO bulletins, UN Geneva, ECDC and the other configured agencies provide additional official reporting. CBS News and IRK.ru retain their news-reporting roles and named attributions.

French news is a news archive, not complete regional surveillance. China CDC's archive date is the publication date; dates in URL paths are not a substitute. CDC MMWR dates come from issue headings. IRK.ru uses provider-authorized captures with an explicit manual-access gap. RSS retention, page limits, source changes, inaccessible routes and failed downloads remain coverage findings. An empty eligible window does not mean absence of disease activity.

Historical expansion uses fixed publication bounds and publisher archives. It includes these source IDs in the three-month backfill, reuses captured sources and records unavailable intervals. Daily summaries can support that work; scientific reconciliation follows the full weekly review rules.
