<h1><img src="docs/figures/atlas-logo.svg" alt="ATLAS" width="560"></h1>

**Agentic Tracking and Longitudinal Analysis for Surveillance**

One Health outbreak intelligence across sources, places, and time.

![Release](https://img.shields.io/badge/release-v0.1.0--alpha.54-orange)
![Stage](https://img.shields.io/badge/stage-research_preview-orange)
[![Tests](https://github.com/EvoLandEco/ATLAS/actions/workflows/ci.yml/badge.svg)](https://github.com/EvoLandEco/ATLAS/actions/workflows/ci.yml)
![Export contract](https://img.shields.io/badge/export_contract-1.9.0-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Python package `0.1.0a54` · Core data schema `0.1.2` · Metrics contract `0.5.0` · Inbox contract `1.0.0`

ATLAS collects outbreak and surveillance reports, extracts evidence, and prepares reviewed research datasets. It follows reported counts, geographic relationships and One Health evidence across publications. People resolve scientific questions, assign outbreak identities and approve releases.

[Explore ATLAS](https://qtj.me/atlas/) · [Workflow guide](docs/WORKFLOW.md)

## What ATLAS offers

- **Weekly surveillance and daily Trends.** Briefings, recent source findings, reports to watch and research opportunities, with explicit review status.
- **Evidence linked to each finding.** Captured sources, exact quotations, publication and observation dates, English source presentation and recorded uncertainty.
- **Longitudinal and geographic analysis.** Reviewed numerical comparisons, travel and exposure relationships, chains and evidence networks, with reporting periods and measurement scope preserved.
- **One Health review.** Human, animal, environmental and food observations retain their source context, sampling details and supporting relationships.
- **Reproducible outputs.** Versioned datasets, schemas, evidence references, decision history and replayable reports support analysis and independent interfaces.

## Workflow design

[![ATLAS workflow: evidence capture, extraction, field matching, human review and exploration, supported by contracts and an append-only ledger.](docs/figures/atlas-workflow-figure.png)](docs/figures/atlas-workflow-figure.pdf)

Dual-provider extraction is being tested. [View the workflow figure as a PDF](docs/figures/atlas-workflow-figure.pdf).

The [weekly workflow](docs/WORKFLOW.md#three-weekly-agent-jobs) separates review of the preceding batch, production for seven complete publication dates, and the historical review inbox. [Daily Trends](docs/DAILY_TRENDS.md) uses a separate archive and retains pending weekly reconciliation. Validated extractions are reused; changed evidence triggers review of affected findings. [Operations](docs/OPERATIONS.md#scheduled-jobs-in-codex) covers schedules, state and recovery.

## Reviewer inbox

The hosted reviewer inbox is ATLAS's internal workspace for reviewing evidence and recording decisions. Reviewers can inspect captured sources, filter unresolved questions, submit decisions and follow application and validation receipts. It uses the ATLAS visual style and requires Cloudflare Access sign-in. Access details are shared within the review team.

The inbox stays online while the ATLAS runner is offline. Versioned export and import commands synchronize exact issue revisions and attributed decisions with the scientific ledger. Unanswered questions remain pending. ATLAS applies explicit decisions once and validates affected outputs; publication requires a separate approval. See the [inbox guide](docs/REVIEWER_INBOX.md) for access, synchronization and deployment.

## Current sources

The [monitoring configuration](config/atlas.yaml) and [historical collection configuration](config/backfill.yaml) contain 17 enabled source profiles:

| Group | Sources |
| --- | --- |
| WHO reporting | Disease Outbreak News; WHO Africa outbreak bulletins; emergency situation updates |
| Regional and international reporting | ECDC Communicable Disease Threats Reports; PAHO alerts and updates; UN Geneva public health briefings |
| National reporting | Nigeria NCDC; UKHSA; RIVM; Santé publique France; Robert Koch Institute; China CDC; US CDC MMWR |
| Animal and food health | EFSA publications, news and data calls; FAO avian influenza situation updates |
| News reporting | CBS News Health; IRK.ru local reporting |

IRK.ru requires authorized manual captures. The other enabled profiles use configured website, feed or document collection routes. Source receipts record access failures, archive gaps and collection bounds; an enabled profile does not establish complete coverage. **WOAH WAHIS and BEACON are disabled and contribute no data.** The [source catalog](docs/SOURCES.md) describes each route, attribution and access requirements.

## Quick start

Use Python 3.11 or later and Node.js 20 or later with npm. Run from the repository root:

```bash
bash scripts/install.sh
source .venv/bin/activate
atlas init
atlas doctor
```

To explore the workflow with synthetic evidence:

```bash
atlas demo --out demo-output
```

Use an empty output directory. Source captures, model caches, review queues and operational databases stay outside the public repository.

### Collect and review

```bash
atlas run --provider none
atlas review-export
```

`none` collects sources for manual extraction. The `codex` provider uses a locally authenticated Codex CLI; `openai` uses an API key from the environment. Set `--model MODEL_ID` explicitly for model-based extraction. The reference agent workflow uses GPT-6 Astra with High reasoning in Codex; assess other setups with the [evaluation protocol](docs/EVALUATION.md).

Review and seal instructions, credentials, budgets and recovery are in [Operations](docs/OPERATIONS.md) and the [editorial guide](docs/EDITORIAL_GUIDE.md). Collection and extraction prepare drafts; they do not approve publication.

## Documentation and contributions

| Topic | Guide |
| --- | --- |
| Workflow and operation | [Weekly work](docs/WORKFLOW.md), [Daily Trends](docs/DAILY_TRENDS.md), [Operations](docs/OPERATIONS.md), [Reviewer inbox](docs/REVIEWER_INBOX.md) |
| Sources and evidence | [Source catalog](docs/SOURCES.md), [Source recovery](docs/SOURCE_RECOVERY.md), [Data semantics](docs/DATA_SEMANTICS.md) |
| Scientific review | [Editorial decisions](docs/EDITORIAL_GUIDE.md), [Geography](docs/GEOGRAPHIC_REVIEW.md), [Longitudinal analysis](docs/LONGITUDINAL_ANALYSIS.md), [Chains](docs/CHAIN_REVIEW.md), [One Health](docs/ONE_HEALTH.md) |
| Data and interfaces | [Structured exports](docs/SITE_EXPORT.md), [Network analysis](docs/NETWORK_ANALYSIS.md), [Publication handoff](docs/PUBLICATION_HANDOFF.md) |
| Development | [Architecture](docs/ARCHITECTURE.md), [Evaluation and benchmarks](docs/EVALUATION.md), [Changelog](CHANGELOG.md), [Contributing](CONTRIBUTING.md) |

ATLAS is an experimental research release under the [MIT license](LICENSE). Scientific review, source improvements and corrections are welcome. Source reuse and redistribution follow the publisher's terms.
