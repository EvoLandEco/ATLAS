# How ATLAS works

## Workflow
The [weekly digest design](WORKFLOW.md) separates concise source extraction from detailed investigation. The isolated digest trial exercises a compact model contract and publication-version selection; registry expansion and selective detailed extraction require implementation and evaluation. The components described here cover the installed registry workflow and preparation of structured research exports. Registry validation, evidence preservation, editorial identity decisions, and publication approval also apply to the digest design.

## Collection, extraction and review
The workflow coordinates collection, extraction, editorial review and report creation. The collector selects configured source adapters, captures content-addressed versions, records retrieval coverage, and revisits recent URLs. The extraction agent converts bounded text chunks into a strict schema through the OpenAI API or local Codex CLI. Provider and model selection are part of the cache identity. Mechanical validators check field types, missingness consistency, dates, numerical ranges, and evidence anchors. The linker proposes existing event identities. An editor accepts, rejects, or defers a mention and supplies the persistent event key.

The report builder selects events and measurements from the evidence available at the chosen cutoff. Evidence-tag rules generate persistent research opportunities, ranked by the group's versioned relevance profile and explicit resource availability. A fixed renderer creates the human report and analytical bundle. A separate approval binds publication to a checksummed artifact.

## Components
The `atlas-surveillance` distribution contains the `atlas` package in `src/atlas`. The `atlas` command reads `config/atlas.yaml`; provider and deployment settings use the `ATLAS_` environment prefix. Private operational state lives in `.runtime-state`.

`models.py` defines input contracts; `sources.py` implements bounded retrieval and source versions; `extraction.py` implements provider selection and frozen caches; `codex.py` runs local subscription extraction; `registry.py` applies editorial decisions; `store.py` provides the immutable ledger; `semantics.py` defines normalization and comparability; `snapshot.py` reduces known evidence; `tables.py` defines output columns; `render.py` and `export.py` create fixed outputs; `metrics.py` prepares scoped measurements and qualitative findings; `site_export.py` packages structured research entities and validates their references; `assets/site_view.js` applies reporting-window selection; `workflow.py` and `cli.py` provide operating commands.

The workflow uses a bounded extraction agent inside an explicit state machine. The remaining stages use testable deterministic operations. This keeps source selection, measurement arithmetic, identity acceptance, publication, and resource usage inspectable.

## Private state and public exports
The private state contains SQLite ledger records, captured text and original bytes, cached model outputs, review tasks, decisions, and sealed reports. Each record includes a previous-record hash and its own content hash. SQLite triggers block record updates and deletions through ordinary writes. The hash chain detects changed history against a retained trusted head; external backups and access control establish the trust boundary.

The public export contains a defined set of tables and fields. It retains source URLs, dates, hashes, reviewed paraphrases, measurements, relationships, and opportunity status. Raw source bodies, extraction payloads, and private review rationales remain in deployment state. Distribution approval remains a human editorial operation.

## Structured research preparation

The [structured export](SITE_EXPORT.md) reads captured sources, selected findings and reviewed annotations. It builds canonical document entities, assertion-level evidence references, comparison groups, geographic roles and source-coverage memberships. Metrics retain their measurement context and partial review status. Source interpretation belongs to this preparation step, allowing analyses and visualizations to reuse the same definitions.

The bundle includes a versioned schema, exact evidence spans, checksums and a portable selector. Validation checks both field contracts and references between entities. The selector applies inclusive reporting windows and evidence requirements to assertions, comparisons, relationships and compact figures. Revision lineage is active only when the supporting records are eligible. Registry acceptance and public distribution use their separate editorial processes.

## Event identity
An event represents a case, cluster, outbreak or surveillance aggregate assembled from reviewed reports. A stable editor-defined key hashes to a persistent public ID. Explicit authority outbreak identifiers produce the strongest identity suggestion; matching disease, host, geographic scope, and entity category produce a lower-strength review suggestion. Matching suggests events for review. Epidemiological relationships record the evidence linking cases, hosts or places.

A single case may develop into a cluster or outbreak within the same identity. Surveillance aggregates and context records stay distinct from individual outbreak entities. Host-specific entities can share a `part_of` parent or a reviewed cross-host relationship. Disease reclassification requires an explicit review flag. Merge and split operations reassign selected mentions and append an identity relationship; previous snapshots retain their earlier assignments.

## Reproducibility
Acquisition replay, extraction replay, and report replay are distinct operations. A live source or a fresh model call can change. Source bodies, extraction results, prompts, model receipts, vocabulary, decisions, configuration, versions, and cutoffs are therefore persisted. Given the same sealed JSON and matching renderer/dependencies, table ordering, Markdown/HTML, manifests, and ZIP bytes reproduce exactly in the tested environment.

Frozen report replay requires no source fetch or model call. Recomputing a historical state uses the historical cutoff and matching source code/configuration. A current model rerun constitutes a new extraction record, not the original historical result.

## Initial capacity model
The alpha uses one writer, a local SQLite database, and a small-group private Git state repository. The CLI file lock and GitHub concurrency group serialize ordinary runs. Review database and archive sizes monthly. Object storage, database migration tooling, concurrent workers, and calibrated automatic matching are later milestones. Store backups and retained report bundles separately from the working copy.
