# Wednesday editorial guide

## Digest scope
The [weekly digest design](WORKFLOW.md) selects important developments and the measurements needed to explain them. Detailed extraction is requested for a named investigation. Reviewers check whether any omitted fact would change the briefing's interpretation. An unexamined detail is not evidence that the source omitted it. The installed extraction commands produce the full schema; the isolated digest trial writes a separate review report.

## Review an extracted finding
Read the saved source and check its publication date and observation period. For PDFs, compare relevant pages and tables with the extracted text. Check host, geography, case definition, classification, count kind, date basis, population, stratum, qualifier, and originating authority. Inspect the source quote and the complete surrounding context. Automatic checks match quotations and numbers to the source; the editor checks their meaning and context.

Examine the proposed event matches and prior event history. Accept into an existing event only when reporting establishes continuity. Create a new stable key for a distinct event. Use `defer` for ambiguous linkage or extraction and `reject` for an irrelevant or duplicate candidate. Exact article duplication and epidemiological event identity are separate decisions.

```json
[
  {
    "candidate_id": "COPY_FROM_QUEUE",
    "action": "accept",
    "event_key": "authority-outbreak-stable-key",
    "reviewer": "Group editor",
    "rationale": "The official follow-up identifies the continuing outbreak and its scope.",
    "public_rationale": "Official follow-up assigned to the existing event.",
    "supersedes_candidate_ids": [],
    "allow_disease_reclassification": false
  }
]
```

A numeric anchoring flag can arise when the source spells out a number or uses a different decimal notation. After checking the complete quote, an editor can add `numeric_evidence_reviews` to an acceptance decision: a mapping from the exact numeric flag in the queue to a source-specific explanation. Every numeric flag needs its own verification. Missing quotes, incorrect values, and other extraction errors require a corrected extraction; they cannot be cleared through this field. The ledger retains both the original flag and the editor’s explanation.

Save this list as `decisions.json`, then run `atlas review-apply decisions.json`. The private ledger retains the rationale and effective time. Create a corrected editorial extraction when a quoted value or schema field is wrong; the original extraction remains preserved.

## Weekly review inbox

The [weekly jobs](WORKFLOW.md#three-weekly-agent-jobs) present questions from the recent batch and unresolved historical evidence in the project chat. Each issue identifies affected records, links to sources, explains its impact and states the decision needed. Historical questions remain in the backlog outside the current reporting window.

Reply with the issue reference and intended action, such as “Defer ISSUE_ID until the observation period is confirmed” or “Use the corrected value in the cited revised bulletin for ISSUE_ID.” Acceptance and event assignments still require the evidence and fields in the review contract. If a reply leaves them unclear, the agent asks about that issue while unrelated work continues.

Ignoring the inbox leaves records pending. A suggestion, elapsed time or silence does not authorize acceptance, rejection, a merge or conflict resolution. Hiding a reminder changes its presentation only. The agent records explicit decisions with user attribution, time, affected identifiers and evidence version, applies each decision once and validates rebuilt outputs. Original evidence and report revisions remain preserved. Public release requires its own matching approval manifest.

## Corrections and evolving events
A new total with a later measurement end date naturally enters the same measurement series. A correction to the same time coordinate explicitly lists the replaced candidate IDs in `supersedes_candidate_ids`. Inspect mirrored reports to identify all replaced claims. A lower corrected total receives a downward-revision label.

A single case can become a cluster or outbreak within the existing event. A disease diagnosis change can be accepted with `allow_disease_reclassification: true` and a documented rationale. Different hosts retain separate identities linked by a relationship. A new outbreak in the same place and with the same disease can receive a distinct key even when the linker suggests the earlier event.

For a merge, reassign affected candidates to the retained event key using new review decisions, then append `merged_into` with `basis: editorial_identity`. For a split, reassign the appropriate candidates to new keys and append `split_from`. The identity catalog and prior report bundles preserve the earlier representation. `relation-apply` accepts a list conforming to the `Relation` model.

A `reported_link` uses `basis: source_reported` and cites the accepted candidate containing that claim. `possible_link` with `basis: analyst_hypothesis` describes an analytical lead. Spatial or temporal co-occurrence alone remains a hypothesis. `part_of` groups related local or host-specific entities under an explicitly reviewed broader context.

## Review assertions for structured export

For a structured research bundle, identify each assertion by document, record, claim and exact quoted span. A claim containing two competing totals needs two participants with their source-section labels. Check metric, case class, definition, population, geography, period and denominator before calling the values contradictory. Review statements and dates with the same attention to the proposition being compared.

Use a correction or supersession only when evidence identifies the revision. Distinguish independent corroboration from repeated publication of the same authority's figures. Different periods, populations or definitions belong in a scope comparison. Keep unresolved questions visible and preserve the source's uncertainty.

Record comparison evidence and review status in the [export annotations](SITE_EXPORT.md). Keep publication, capture, observation and review dates distinct. Review geographic roles using neutral location labels, and separate the reporting channel from an authority quoted in the text. Mark incomplete numerical or geographic review explicitly. Acceptance into the event registry follows its own recorded decisions.

## Authorized local imports
`examples/import/document.json` provides the source ID, allowed canonical URL, title, source date/precision, and captured text. Replace its synthetic content with a provider-authorized document or export, then use `import-document`. The CLI returns the document ID. Supply a schema-valid extraction using `import-extraction DOCUMENT_ID extraction.json --editor "Name"`, then review its candidates normally. BEACON and WOAH WAHIS are possible sources, not used. Collaboration is not established; an authorized route must be documented before either source is enabled for import.

## Opportunities and publication
Inspect the fixed relevance rules and supporting source records. Check linked resources, access conditions, sampling coverage, and any formal call's actual deadline. Assign an owner and a concrete next action using `opportunity-apply`; status choices are suggested, triaged, investigating, completed, and declined.

Seal the same report date after decisions. Review the report's data-quality and source-coverage sections, its unresolved values, and every proposed public relationship. Approve the exact bundle:

```bash
atlas approve PATH_TO_BUNDLE --editor "Group editor" \
  --note "Reviewed evidence, scope, and distribution." \
  --out .runtime-state/approvals/REPORT_ID.json
atlas verify-approval PATH_TO_BUNDLE .runtime-state/approvals/REPORT_ID.json
```

Approval records the editor and the exact dataset bundle hash. The frozen snapshot retains its creation status; the receipt records its subsequent distribution approval. A changed bundle requires a new approval.

## Model extraction and review

Use `atlas extract --provider codex` for local extraction through Codex signed in with ChatGPT, or `atlas extract --provider openai --model MODEL_ID` for API extraction. `atlas run` accepts the same provider settings and includes collection, extraction, review export, and a draft report.

Both providers read captured text in bounded chunks and return the extraction schema. ATLAS validates the result, records provenance and usage, and stores the output in a provider-specific cache. Incomplete chunks remain in `.runtime-state/review/extraction_tasks.json`. Repeating extraction processes the remaining chunks within the configured budget.

Run `atlas review-export` after extraction. Inspect the original evidence and event assignments before applying decisions and sealing the report. Model findings enter the review queue before an editor accepts them. `import-extraction` also accepts JSON prepared by an editor or another tool.
