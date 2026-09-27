# Geographic assessment and map preparation

Geographic assessment is part of post-processing for every production window. A larger collection is complete only when its added findings have been assessed and the map has been built from the same validated snapshot as the structured export. An unchanged number of pins or links is a valid result when the assessment supports it.

## Reassessment across runs

Apply the [link reassessment procedure](LINK_REASSESSMENT.md) before carrying geographic annotations into a weekly or expanded historical run. Check changed evidence, its recorded dependents and historical candidates identified by new source references. Retained location annotations alone do not establish that a link remains consistent with the accumulated evidence. The procedure records review scope, adjudications, temporal checks and pending decisions.

## Assess saved findings

Use `scripts/review_geography.py` with the prepared snapshot, its matching annotations, captured source directory and a private results directory. The script retains existing source geographic assignments and uses the tool-free Codex provider for entries awaiting assessment. Cached assessments are bound to the record, source text, prompt, schema and review version. New collection and repeated digest extraction are not required.

```bash
python scripts/review_geography.py \
  --snapshot INPUT/snapshot.json --annotations INPUT/annotations.json \
  --source-dir BATCH/sources --out PRIVATE/geography
```

The stage uses at most four concurrent calls, twelve entries and 30,000 input characters per normal batch. A single entry may use up to 100,000 characters. A run is bounded to 1,000 entries and 12 million input characters; each call has a 600 second timeout and a 200,000 byte response limit. Failures retain their record IDs and diagnostic files. Resume with the same inputs and results directory. The `--limit` argument supports a small evaluation before processing the remaining entries.

Each entry receives one outcome:

- **Assessed:** the evidence supports geographic assignments or a completed assessment with no relationship to display.
- **No specific location:** the evidence describes a broad region or gives insufficient geographic detail; retain the reason without inventing country pins.
- **Unresolved:** named locations may be usable, but a source, layout or semantic question remains in the review queue.
- **Retained review:** existing source assignments and relationship assessments carry forward with their supporting records.

Location roles distinguish occurrence, reporting scope, exposure, travel origin, travel destination and context. A source's headquarters or a background country mention does not locate an event. Records covering several places retain several memberships. A primary country is supplied only when the entry has a clear main location. Context-only entries have no primary location. An explicit travel origin can locate a report even when its destination is unknown. Country coordinates come from Natural Earth 1:50m label reference points; they are not patient locations. The bundled reference file records its source version and checksum. Natural Earth data are [public domain](https://www.naturalearthdata.com/about/terms-of-use/).

The [relationship rules](RELATIONSHIP_RULES.md) govern travel, shared events and source hypotheses. Review link candidates against their quotations, including direction, disease, named endpoints and uncertainty. When travel-associated cases are reported without a stated itinerary, do not infer the reporting country as the journey's origin. Preserve separate reporting topics and leave event identity decisions to the editorial workflow.

## Prepare and validate

```bash
python scripts/prepare_geography.py \
  --snapshot INPUT/snapshot.json --annotations INPUT/annotations.json \
  --reviews PRIVATE/geography/results.json --source-dir BATCH/sources \
  --out PREPARED
```

The output directory must be empty. Review source assignments and record any adjudication with its reason before preparing the release. Preserve the original model results alongside the reviewed input. Each finding must have an assessment outcome. Missing results, stale input fingerprints, invalid country codes and missing source quotations stop preparation.

Use `PREPARED/snapshot.json` for both metrics preparation and structured export, with the matching geographic annotations. Retain the existing metric annotations and record IDs. The snapshot includes `geographic_review` with coverage outcomes and `map_places` with every supported topic location. These fields supplement the map snapshot; structured data contract 1.0.0 and metric contract 0.1.0 retain their definitions.

```bash
python scripts/build_map.py \
  --snapshot PREPARED/snapshot.json --bundle RELEASE/structured \
  --source-dir BATCH/sources --land PRIVATE/land.geojson \
  --coverage BATCH/coverage.html --out RELEASE/map
```

The map builder verifies the structured export and source snapshot hashes, complete geographic assessment coverage, place membership and captured text paths. Its date controls use the actual publication and capture extent. Several topics sharing the same coordinates appear at one selectable reference point; this visual grouping does not merge their identities. Each reference point is visible only when its supporting records pass the selected date and source filters. Sharing a topic does not supply geographic evidence for every reporting period. Findings without coordinates remain in the chronology and source network.

Inspect both date boundaries, an added location, an added link when present, a record with no specific location and the source quotations. Preserve the dated release and record its checks. Refresh the local preview from that release, then generate the [publication handoff](PUBLICATION_HANDOFF.md). An explicitly authorized correction to distributed data uses the correction route, with the replaced export ID and the exact validated reference. Report reviewed entries, mapped and unmapped entries, unresolved questions, geographic links and reference points separately. Unanswered editorial questions remain pending and do not authorize a merge or a new transmission claim.
