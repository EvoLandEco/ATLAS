# Browser transport

Browser transport `0.3.0` separates an ATLAS selection index from source details. It accepts scientific site contracts `1.5.0`, `1.6.0`, `1.7.0` and `1.8.0`. The scientific export, its selector and its publication identity retain their exact hashes. Transport files have a separate manifest and selector hash. This is an experimental local transport; publication requires producer validation and consumer compatibility and memory checks.

## Build and verify

Use an empty output path and a sealed site bundle with its exact map snapshot. The export ID is checked against the sealed manifest and map hashes. The command verifies the scientific bundle before serialization. Node.js and the installed ATLAS environment are required.

```sh
node scripts/export_browser_transport.mjs \
  --site /path/to/structured/atlas-site.json \
  --map /path/to/snapshot.json \
  --export-id EXACT_EXPORT_ID \
  --out /path/to/browser-candidate
node scripts/verify_browser_transport.mjs \
  --directory /path/to/browser-candidate \
  --site /path/to/structured/atlas-site.json \
  --map /path/to/snapshot.json \
  --every-record \
  --out /path/to/transport-validation.json
```

Input files are bounded at 400 MB combined. Scientific site exports use compact canonical JSON, with complete values and references. Detail partitions are bounded at 2 MB; a single larger row stops serialization. The output directory is created once and files are never overwritten. A failed build remains available for diagnosis and is not a release candidate.

The verifier checks all asset bytes and hashes, source identity, complete collection reconstruction, array ordinals, entity lookup and full hydrated selection results. For site `1.5.0`, it also compares with the frozen scientific selector. Its cases include every record individually, source channels, comparison support sets and incomplete support, empty selection, capture dates, knowledge cutoff and One Health domain and observation filters. Consumer tests cover loading, cancellation, cache eviction, rendering and measured browser memory separately.

## Producer handoff

Run both commands for each browser release after the scientific export and exact map snapshot pass validation. The verifier's `--out` file is the private browser handoff, version `0.1.0`. A consumer sync requires `producer_ready: true`, `all_records_individually: true`, both source files in `source_files_compared` and successful reconstruction. Verification without either source file or without `--every-record` leaves `browser` null and cannot supply this handoff.

The stable `browser` field contains `transport_version`, `source_export_id`, `scientific_contract`, an absolute `directory`, the manifest's absolute `path`, SHA-256 and byte count, and the original `source` identities. The manifest lists every immutable asset, byte count and hash. Consumers recheck the handoff and manifest before staging, match the source identities against the scientific publication handoff, and upload every listed asset. Keep executable files pinned through reviewed consumer code. Public descriptors replace private paths with storage URLs.

Weekly browser distribution requires this matching attachment; a missing attachment blocks browser activation. Preserve the canonical scientific download and the active browser release while another candidate is incomplete. Consumer checks, adoption and publication authorization are recorded separately. The producer receipt initializes both `consumer_adoption` and `publication_authorized` to false.

## Core and detail contracts

`core.json` contains named tables with fixed columns and encodings, an exact string dictionary and ordered supporting-record lists. The [core schema](../schemas/browser-transport.schema.json), [manifest schema](../schemas/browser-manifest.schema.json), [table definitions](../src/atlas/assets/browser_tables.js) and [consumer types](../types/browser.d.mts) describe the format. Unknown versions, unexpected columns, truncated tuples and invalid references are errors.

All One Health rows and geographic places retain their full fields. Reviewed series retain all metadata, members and connections, with evidence IDs in place of evidence text. Measure summaries retain their exact values, units, dates, missingness, source record and evidence record lists. These summary types are distinct from complete scientific objects. Assertion and comparison details, source evidence and map claims load from detail partitions.

`prepareBrowserView(core, exportId)` returns `{data, select}`. The decoder creates summary rows whose repeated text refers to shared string values; the caller can release the input tuples. Retain the decoded data unchanged while its prepared selector is in use. `select` takes the same window and selection arguments as the scientific selector. Its series contain `evidence_ids`; `hydrateBrowserView(view, seriesById)` resolves those exact IDs from verified series detail. Missing detail is an error, never an empty scientific value.

Compact figure identities represent exact equality of the scientific selector's ordered field vector. An ungroupable measure has a null identity. Eligible contradictions, different-scope comparisons and unresolved associations still separate measures during each selection. The transport does not assign outbreak identity, establish comparability or change reviewed connections.

The independently loaded `detail-index.json` contains:

```text
partitions: array of immutable partition paths
collections: collection name -> ordered array of [entity ID or null, partition ordinal]
```

The position in a collection array is its original source ordinal. A detail row contains its collection, ordinal, stable ID and complete original value. A partition has one declared document, reviewed series or reconstruction owner. Ownership follows explicit source references. All original support references remain in the row, including support in other documents. A caller requests the entities needed for visible content; loading one partition does not authorize recursively fetching dependencies of unrelated rows.

Reconstruction metadata and collection counts preserve fields outside the browser projection. The verifier restores every scientific and map collection in source order and compares the resulting objects with the checksum-verified source files. Original scientific downloads remain the byte-level archive authority.

## Consumer adoption

Verify the manifest against the trusted release descriptor, then verify each asset's uncompressed byte count and SHA-256 before parsing. Keep the transport selector pinned in the consumer. Asset absence, corruption or a mismatched source export is a load failure. Do not combine assets from different candidates.

Deduplicate concurrent partition requests, cancel obsolete requests and bound retained detail bytes. Keep visible content and its explicit evidence pinned while in use. Cache eviction must preserve selection and interaction state. A candidate needs complete producer checks and consumer parity, interaction and memory checks before its descriptor is exposed through the release pointer. Transport validation does not approve new scientific findings or publication.

Measurement summaries retain each source quantity qualifier, including strict and inclusive bounds. Detail partitions retain the full scientific observation.

The `report_assessments` summary table retains the full assessment fields and uses the scientific selector for date, source support, review cutoff and supersession. Earlier scientific contracts supply an empty assessment table; their selected views retain their versioned shape.
