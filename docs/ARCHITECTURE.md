# Architecture and decision boundaries

## Design boundary
The [weekly digest design](WORKFLOW.md) separates concise source extraction from detailed investigation. The isolated digest trial exercises a compact model contract and publication-version selection; registry expansion and selective detailed extraction require implementation and evaluation. The components described here are the installed full-schema workflow. Registry validation, evidence preservation, editorial identity decisions, and publication approval also apply to the digest design.

## Installed workflow graph
The orchestrator drives collection, extraction, review preparation, and sealing. The collector selects configured source adapters, captures content-addressed versions, records retrieval coverage, and revisits recent URLs. The extraction agent converts bounded text chunks into a strict schema through the OpenAI API or local Codex CLI. Provider and model selection are part of the cache identity. Mechanical validators check field types, missingness consistency, dates, numerical ranges, and evidence anchors. The linker proposes existing event identities. An editor accepts, rejects, or defers a mention and supplies the persistent event key.

A deterministic reducer constructs the event and measurement view at an explicit knowledge cutoff. Evidence-tag rules generate persistent research opportunities, ranked by the group's versioned relevance profile and explicit resource availability. A fixed renderer creates the human report and analytical bundle. A separate approval binds publication to a checksummed artifact.

## Components
`models.py` defines input contracts; `sources.py` implements bounded retrieval and source versions; `extraction.py` implements provider selection and frozen caches; `codex.py` runs local subscription extraction; `registry.py` applies editorial decisions; `store.py` provides the immutable ledger; `semantics.py` defines normalization and comparability; `snapshot.py` reduces known evidence; `tables.py` defines output columns; `render.py` and `export.py` create fixed outputs; `workflow.py` and `cli.py` provide operating commands.

The workflow uses a bounded extraction agent inside an explicit state machine. The remaining stages use testable deterministic operations. This keeps source selection, measurement arithmetic, identity acceptance, publication, and resource usage inspectable.

## Private state and public exports
The private state contains SQLite ledger records, captured text and original bytes, cached model outputs, review tasks, decisions, and sealed reports. Each record includes a previous-record hash and its own content hash. SQLite triggers block record updates and deletions through ordinary writes. The hash chain detects changed history against a retained trusted head; external backups and access control establish the trust boundary.

The public export is an allowlisted table projection. It retains source URLs, dates, hashes, reviewed paraphrases, measurements, relationships, and opportunity status. Raw source bodies, extraction payloads, and private review rationales remain in deployment state. Distribution approval remains a human editorial operation.

## Event identity
An event is a local epidemiological entity assembled from reviewed reporting. A stable editor-defined key hashes to a persistent public ID. Explicit authority outbreak identifiers produce the strongest identity suggestion; matching disease, host, geographic scope, and entity category produce a lower-strength review suggestion. Pattern matching establishes a candidate association. Epidemiological linkage is separately represented by evidence-bearing relationships.

A single case may develop into a cluster or outbreak within the same identity. Surveillance aggregates and context records stay distinct from individual outbreak entities. Host-specific entities can share a `part_of` parent or a reviewed cross-host relationship. Disease reclassification requires an explicit review flag. Merge and split operations reassign selected mentions and append an identity relationship; previous snapshots retain their earlier assignments.

## Reproducibility
Acquisition replay, extraction replay, and report replay are distinct operations. A live source or a fresh model call can change. Source bodies, extraction results, prompts, model receipts, vocabulary, decisions, configuration, versions, and cutoffs are therefore persisted. Given the same sealed JSON and matching renderer/dependencies, table ordering, Markdown/HTML, manifests, and ZIP bytes reproduce exactly in the tested environment.

Frozen report replay requires no source fetch or model call. Recomputing a historical state uses the historical cutoff and matching source code/configuration. A current model rerun constitutes a new extraction record, not the original historical result.

## Initial capacity model
The alpha uses one writer, a local SQLite database, and a small-group private Git state repository. The CLI file lock and GitHub concurrency group serialize ordinary runs. Review database and archive sizes monthly. Object storage, database migration tooling, concurrent workers, and calibrated automatic matching are later milestones. Store backups and retained report bundles separately from the working copy.
