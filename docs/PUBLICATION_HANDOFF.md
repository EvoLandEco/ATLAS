# Export handoff

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

## TypeScript consumers

[types/atlas.d.ts](../types/atlas.d.ts) declares `AtlasSiteBundle`, `AtlasMapSnapshot`, `AtlasSelectionView`, `AtlasPublicationHandoff`, their core entities and the selector signature. It imports no report data. [types/view.d.mts](../types/view.d.mts) supplies declarations for a colocated `view.mjs`; copy both declaration files alongside the trusted selector. Runtime JSON still requires integrity and schema checks. Types describe the interface and do not validate downloaded bytes.
