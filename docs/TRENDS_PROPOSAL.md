# Trends discussion proposal

The navigation design puts Reported observations in Analysis and Journeys & connections in Geographic links. Trends has three rows: Reporting activity counts and the Reporting attention ring in the first row, Events to watch in the second, and Latest reports in the third. The [watch contract](WATCH.md) supplies explicitly reviewed report selections. This document describes their evidence rules and the further requirements for event identity and meaningful change summaries. Hazard ranking and scientific triage are outside the implemented watch contract.

## Placement

Analysis can present the selector's reported measures, compact figures and `reviewed_series` beside the existing analytical products. Observation dates, reported intervals, missingness, case definitions and review coverage remain visible. Series require their reviewed endpoint connections; a graph cannot connect observations merely because they share a disease or location. Cumulative reporting changes retain that meaning.

Geographic links can contain reviewed travel, contact, transmission and reporting sequences. Keep these categories distinct. A chain with unknown locations can use a local diagram in that section, with its geographic gaps stated. Filtering must preserve explicit edges and cannot bridge an excluded intermediate node. A reporting sequence describes publication order, not a transmission chain.

## Evidence available for Trends

| Display need | Existing evidence | Limit |
| --- | --- | --- |
| Recent reporting | Document publication, capture, publication basis and source hashes | A recent capture can be an old report. Publication recency does not establish a recent event. |
| Event timing | Observation dates, period labels, reviewed One Health timing and chain node dates | Unknown or coarse dates remain visible as such. |
| Confirmation status | `report_assessments` separates authenticity, diagnostic status, official responses and expert appraisals, with exact assertions and evidence | Coverage is partial. An absent assessment is unreviewed, not automatically unconfirmed. Source authentication does not establish diagnosis. |
| A changed assessment | Explicit assessment `supersedes`, scope, reviewer and review time | A later report or stronger headline alone does not establish a status change. |
| Corrected source information | Documented correction or supersession comparisons with lineage and supporting evidence | The correction's evidence must be eligible in the selected window. Different numbers alone do not establish a correction. |
| A new observation | Exact measurement, finding, source and observation period | Repeated cumulative totals and copied statements are not new cases or independent confirmation. |
| A disagreement | Contradiction or unresolved-association review with explicit participants and scope | Disagreement calls for review; it is not a measure of hazard. |
| A geographic or One Health development | A reviewed proposition with endpoint evidence, source certainty and dates | Shared pathogen names, places or timing do not establish spread, transmission or spillover. |
| Coverage gaps | Collection receipts, section review coverage and pending items | More reports measure reporting activity. They do not establish greater hazard. |

## Events to watch

Use an explicitly reviewed watch list, without a numerical urgency score. Each item needs a clear reason for attention, exact supporting assertion or relationship IDs, a named review scope and review time. Possible reasons for discussion include a source-reported investigation awaiting a stated result, a documented change in a relevant measurement, an official assessment change, or a reviewed geographic development. The reason should describe the evidence and the unresolved question, using the source's level of certainty.

A reporting topic can include unrelated episodes. Before calling an item an event, require an accepted event identity or reviewed episode membership with a stated scope. Items without that basis can appear as named reports under investigation, without combining their people, counts or locations. Keep an authenticated report of an unconfirmed illness distinct from a confirmed diagnosis. Unresolved suspicion does not justify an “urgent” badge.

The watch sidecar records a selected report, exact evidence, an attention reason, a follow-up question, diagnostic status and review provenance. Its scope is a single report and its event identity is unassigned. Each immutable export preserves its selection decisions. A subsequent removal requires an explicit review; missing follow-up does not close an event. Accepted event identity and event-level closure require a further contract and review. The watch export carries no priority rank.

Show at most three eligible reviewed items, with “Why this is listed”, source status and the next unresolved question. The watch selector preserves explicit review order and applies all supporting-record eligibility before the display limit. A text search or count threshold cannot substitute for that decision. Metric card `priority` is a display preference and must not become an urgency score.

## Latest reports and meaningful updates

Latest reports is a publication chronology. Exclude the documents or records in the displayed watch cards, preserving their appearance when they are not featured. A further meaningful-update view needs a named baseline release and the current exact export. Distinguish these kinds of update:

- A newly available report, with its publication and capture dates.
- A new source observation, with its observation period and scientific scope.
- A reviewed assessment change, with the superseded assessment and supporting evidence.
- A documented source correction, with exact before and after assertions.
- A reviewed geographic or One Health proposition, with its own evidence and uncertainty.
- A source-access or review-coverage change, labelled as a workflow development.

The first category can support a publication chronology with the existing contract. Calling an item a meaningful event update requires the relevant identity and comparison review. An added export row may be historical enrichment, another quotation from the same source, or repeated information. Preserve the distinction. Translation preparation, capture repetition and schema changes belong to release information, not epidemiological updates.

Show publication, observation and review dates beside their own meanings; do not combine them into one “last updated” timestamp. A newly captured historical report can be labelled “Added to ATLAS” while retaining its original publication date. Filtering follows both date bounds and all supporting records. Evidence for a status change outside the selected window cannot silently alter the in-window assessment.

## Decisions needed before implementation

A report watch list and publication chronology are supported. Before extending them to event-level selections, agree the event-identity threshold, review ownership and explicit closure rules. Before implementing meaningful change summaries, choose the baseline release and permitted comparison kinds. Hazard ranking and automatic urgency require a separate scientific proposal and agreement.
