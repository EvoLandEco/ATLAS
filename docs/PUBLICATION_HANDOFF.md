# Export handoff

Report eligibility requires a source-supported publication, issue or release date. Exclude undated reports from extraction, review queues, dated counts, exports and watch selections. Keep captures and review history private with a missing-publication exclusion. Capture, observation and URL dates do not supply publication dates. Notification and sampling datasets retain their own date semantics. Public handoffs omit undated source supplements and collections.

The handoff identifies a validated local export for a consumer. It separates completion of the three weekly jobs, unresolved editorial questions and distribution approval. It does not collect sources, call a model, accept findings or upload files.

## Example interface and agent coordination

The separate [qtj.me/atlas](https://qtj.me/atlas/) interface implementation consumes ATLAS exports for maps, evidence networks and Trends. Its website job verifies the release and distributes approved assets through Cloudflare R2 and a read-only Cloudflare Worker. ATLAS owns the evidence interpretation and export definitions; the interface owns presentation, filtering and website deployment.

The ATLAS and interface agents coordinate across Codex threads. Send the exact export reference, contract versions, trusted selector hash, validation receipt and any required consumer changes. The receiving agent verifies those artifacts and records adoption against the export ID. A sent message does not establish adoption, publication or scientific acceptance. Record these outcomes separately. Other consumers can implement the same handoff without Codex or Cloudflare.

## Generate the reference

Run from the project root for the intended Wednesday cycle:

```bash
atlas --state .runtime-state handoff --cycle 2026-09-30 \
  --out reports/publication-handoff.json
```

Generate this file on every sync attempt. Require a successful command and the requested `cycle`; do not use an earlier file after a command failure. `weekly_ready: false` is a normal result when work is incomplete. In that case, leave the consumer's current data untouched.

The command holds the state writer lock, verifies the ledger and reads `.runtime-state/weekly/CYCLE/review.json`, `production.json` and `inbox.json`. The gate requires:

1. Three schema-valid receipts for the same cycle, each with execution status `completed` and a completion timestamp on or after its scheduled cycle. Completion timestamps respect predecessor order.
2. The production receipt names the exact review receipt hash. The inbox receipt names the exact review and production receipt hashes.
3. Production identifies its export. The inbox identifies the final export after processing supplied decisions, with `post_review_validation: "passed"` and a matching `reviewed_export_id`.
4. The inbox's ending ledger hash equals the verified current ledger head, and its `unapplied_decision_ids` is empty.
5. The final structured bundle passes verification. Its original map snapshot matches both the saved source-file hash and record hash. The final files and export identity match the inbox reference.

An unanswered editorial question can remain in `unresolved_issue_ids` with all jobs completed. A supplied decision awaiting application is different: it blocks the handoff. Before applying a later decision or changing review inputs, mark the affected inbox receipt `running` or `partial`. Revalidate and replace that receipt after rebuilding the affected export. Retain decision and artifact history. A completed inbox review writes its cycle receipt even when it finds no new questions; that execution record does not alter scientific records or trigger a rerun.

## Receipt fields

The required receipt structure is defined by [weekly-receipt.schema.json](../schemas/weekly-receipt.schema.json). Jobs can include their counts, selected document IDs, source hashes, checks, usage and report paths alongside these fields.

| Field | Use |
| --- | --- |
| `schema_version` | `1.0.0` |
| `cycle`, `job`, `status` | Wednesday date; `review`, `production` or `inbox`; `running`, `completed`, `partial` or `blocked` |
| `completed_at` | Timestamp with timezone for completed work |
| `ledger_head` | Ledger hash at job completion |
| `dependencies` | Map from predecessor job name to SHA-256 of its exact receipt file |
| `export` | Required for completed production and inbox: absolute `bundle_path`, absolute `map_snapshot_path`, `manifest_sha256`, `map_snapshot_sha256` and `export_id` |
| `unresolved_issue_ids` | Questions awaiting editorial decisions |
| `unapplied_decision_ids` | Explicit decisions awaiting application |
| `reviewed_export_id`, `post_review_validation` | Inbox confirmation of the final export and `passed`, `pending` or `failed` validation |

`atlas.handoff.inspect_export(bundle_path, snapshot_path)` validates the files and returns the export reference and asset hashes. Use its values when preparing receipt fields. The export ID is SHA-256 of the canonical JSON object containing `manifest_sha256` and `map_snapshot_sha256`, using ATLAS's `digest` function. The inbox export can differ from production when decisions require a revised bundle; it must identify the final validated artifacts.

## Consumer fields and integrity

The handoff has `handoff_version: "1.0.0"`, `generated_at`, `cycle`, `timezone`, `weekly_ready`, `execution_status`, per-job statuses and receipt references, `blocking_reasons`, and the verified ledger head. `current_export` is null unless the weekly gate passes.

An export reference contains absolute local paths and SHA-256 references for `manifest`, `structured_data`, `map_snapshot`, `selector` and every bundle file under `files`. Each file reference has `path`, `sha256` and `bytes`. It also includes the export ID, contract and software versions, capture time, publication window, release status and verification result.

Recheck file hashes immediately before upload and publish a consumer pointer only after all referenced data objects are available. Keep executable selector code in the consumer's trusted codebase. Compare its SHA-256 with `selector.sha256`; a mismatch requires a reviewed code import, not execution of remotely supplied JavaScript. Preserve immutable export identities so a partial upload cannot replace a working dataset.

Browser consumers also require the [browser transport handoff](BROWSER_TRANSPORT.md#producer-handoff) for this exact export. Generate its partitions and run the verifier with both source files and `--every-record`. The resulting receipt's `browser` field binds the manifest and all assets to the scientific source identities. Stage it alongside the canonical archive and matching analysis attachments; missing transport or incomplete consumer tests block browser activation. A weekly sync must retain the active browser release until these checks pass.

The handoff is a private control file containing local paths. A public data pointer should contain storage URLs and hashes rather than those paths. `publication_approval: "not_evaluated"` means the handoff checks technical readiness; it does not create distribution approval or change a `research_preview` into an accepted dataset. Apply the distribution route's approval requirements to the exact exported content.

## Initial publication

An explicitly selected existing export can be inspected without claiming a weekly cycle completed:

```bash
atlas handoff --cycle 2026-09-23 \
  --initial-bundle reports/six-month/compact-figures-v1/structured \
  --initial-snapshot .local/six-month/export-inputs/snapshot.json
```

The verified reference appears under `initial_candidate` with `mode: "initial_publication_candidate"` and `counts_as_weekly_completion: false`. This does not satisfy or override `weekly_ready`. Initial publication is a separate, explicitly selected consumer action. The chosen snapshot must be the structured bundle's exact original input, not another map file with similar records. No acquisition, extraction or weekly receipt is created by this command.

## Correcting a distributed release

A correction outside the weekly schedule has its own authorization record. It names the exact export being replaced, the user instruction authorizing distribution, and the complete validated reference returned by `inspect_export`:

```json
{
  "correction_version": "1.0.0",
  "replaces_export_id": "SHA256_OF_CURRENT_EXPORT",
  "reason": "Source geographic assessment and map preparation",
  "authorization": {
    "thread_id": "AUTHORIZING_CHAT_ID",
    "instruction": "USER_INSTRUCTION"
  },
  "export": { "export_id": "VALIDATED_EXPORT_ID", "...": "COMPLETE_INSPECT_EXPORT_REFERENCE" }
}
```

Keep this control file private. Its authorization records the user's distribution decision; it is not a digital signature or scientific acceptance. The consumer validates the complete export, exact source snapshot, geographic coverage and trusted selector. Immediately before publishing, recheck the authorization bytes, referenced file hashes and current export ID. Replace the pointer only if it still identifies `replaces_export_id`. A mismatch requires review of the intervening release.

Preserve the replaced release's initial or weekly provenance. Add a correction reference containing `replaces_export_id` and the authorization file's SHA-256. Keep both immutable exports available. A correction does not create weekly receipts, complete an unfinished cycle, resolve unanswered editorial questions or change research drafts into accepted outbreak events.

## Analysis attachment

The Analysis panel requires an Intelligence contract `0.2.0` export from the exact site bundle being released. Its `source_export_id`, `input_identity.site_sha256` and `input_identity.selector_sha256` must match the release identity, site file and trusted selector. A base export without this matching attachment leaves Analysis unavailable. Never carry an analysis descriptor across a source change without regeneration and validation.

For each authorized release that includes Analysis, run the [Intelligence producer and replay checks](INTELLIGENCE_EXPERIMENT.md#reproduce-and-validate) against the selected bundle. Use saved inputs and retain existing scientific decisions. Verify model eligibility, source evidence, component outputs and historical availability; retain partial coverage and retrospective labels. Record the experiment ID, schema version, file sizes, SHA-256 values and validation receipt in the content-bound publication authorization.

The consumer stages `intelligence.json` and `contract.schema.json` under `intelligence/EXPERIMENT_ID/`. Its release descriptor includes:

```json
{
  "intelligence": {
    "experiment_id": "EXPERIMENT_ID",
    "schema_version": "0.2.0",
    "asset": { "sha256": "INTELLIGENCE_FILE_SHA256", "bytes": 12345 }
  }
}
```

The example byte count is illustrative; use the actual file length. Consumers verify bytes, schema, experiment identity and all three source bindings before displaying results. A release containing network analysis must also have a transport descriptor bound to the same site export. Stage every referenced asset and complete consumer checks before activating the pointer. A base-only sync does not publish these attachments. Keep the sealed release descriptor and record public activation separately from staging or local adoption.

An authorized partial release can include reviewed outputs while other review remains pending. Export that coverage explicitly. Publishing saved results does not resume collection, extraction or weekly jobs, accept scientific findings, or remove an execution hold.

## Presentation attachments

English source text and reviewed watch selections use separate attachments bound to the exact scientific export. Follow [Source text](SOURCE_TEXT.md) and [Watch](WATCH.md) to generate and independently verify their files. Preserve the full text catalogue, annotations and review history privately. The browser text payload is `source-text-display.json` with `source-text-display.schema.json`; the watch payload is `watch.json` with `watch.schema.json`.

Each attachment's `pointer_descriptor` contains `version`, `source_export_id`, `path`, `schema_path`, `sha256`, `bytes` and `schema_sha256`. For source text, `version` is the display contract version, and `catalogue_sha256` binds the complete parent text file through the payload's `source_text_sha256`. For watch, `version` is `watch_version`. Paths name the payload and schema within the attachment directory. Hashes and byte counts describe the exact staged files.

The content-bound publication authorization carries `presentation.source_text` and `presentation.watch`. Each contains its `pointer_descriptor`, a `data` file reference and a `schema` file reference. Each file reference includes its local `path`, `sha256` and `bytes`. Stage the immutable files beneath `releases/EXPORT_ID/presentation/PAYLOAD_SHA256/`. Validate both schemas, their matching source export IDs and their exact bytes before pointer activation. Vendor the reviewed watch selector in consumer code; do not execute a downloaded selector.

ATLAS-generated translations retain their original text, provenance and draft review label. Text lookup follows scientific selection. A watch item requires all supporting records and its review to satisfy the selection; apply any display limit afterwards. Record consumer checks and adoption separately from artifact delivery and public activation. Approval names the exact attachments as well as the scientific release.

## TypeScript consumers

[types/atlas.d.ts](../types/atlas.d.ts) declares `AtlasSiteBundle`, `AtlasMapSnapshot`, `AtlasSelectionView`, `AtlasPublicationHandoff`, their core entities and the selector signature. It imports no report data. [types/view.d.mts](../types/view.d.mts) supplies declarations for a colocated `view.mjs`; copy both declaration files alongside the trusted selector. Runtime JSON still requires integrity and schema checks. Types describe the interface and do not validate downloaded bytes.
