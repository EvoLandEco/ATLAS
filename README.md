<h1><img src="docs/figures/atlas-logo.svg" alt="ATLAS" width="560"></h1>

**Agentic Tracking and Longitudinal Analysis for Surveillance**

One Health outbreak intelligence across sources, places, and time.

![Release](https://img.shields.io/badge/release-v0.1.0--alpha.54-orange)
![Stage](https://img.shields.io/badge/stage-research_preview-orange)
[![Tests](https://github.com/EvoLandEco/ATLAS/actions/workflows/ci.yml/badge.svg)](https://github.com/EvoLandEco/ATLAS/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

ATLAS brings outbreak and surveillance reporting into a shared framework for One Health research. It collects publications, extracts findings with supporting evidence, and organizes observations across sources, locations and reporting periods.

Researchers can follow developments, inspect the evidence behind a finding, and examine numerical trends and geographic relationships. Human review governs outbreak identities, interpretation and publication. Source observations, analytical hypotheses and research questions remain distinct.

[Explore ATLAS](https://qtj.me/atlas/)

## Capabilities

- **Surveillance briefings.** Weekly reports and daily Trends bring together recent findings, developments to watch and research questions.
- **Traceable evidence.** Findings retain source quotations, publication and observation dates, measurement context and uncertainty.
- **Longitudinal and geographic analysis.** Reviewed comparisons connect compatible measurements and source-supported travel, exposure and transmission relationships.
- **One Health perspectives.** Human, animal, environmental and food observations retain their sampling context and supporting evidence.
- **Research datasets.** Versioned exports carry consistent identifiers, provenance and selection rules for analysis and visualization. Sealed reports support reproducible replay.

## Workflow

[![ATLAS workflow: source collection, evidence extraction, scientific review and research exploration.](docs/figures/atlas-workflow-figure.png)](docs/figures/atlas-workflow-figure.pdf)

Dual-provider extraction is being tested. [Download the workflow figure](docs/figures/atlas-workflow-figure.pdf).

## Sources

ATLAS draws on 17 configured source profiles spanning international agencies, national surveillance and news reporting.

| Group | Sources |
| --- | --- |
| WHO | Disease Outbreak News; WHO Africa outbreak bulletins; emergency situation updates |
| Regional and international | ECDC Communicable Disease Threats Reports; PAHO alerts and updates; UN Geneva public health briefings |
| National | Nigeria NCDC; UKHSA; RIVM; Santé publique France; Robert Koch Institute; China CDC; US CDC MMWR |
| Animal and food health | EFSA; FAO avian influenza situation updates |
| News | CBS News Health; IRK.ru |

Coverage varies by source, reporting period and access conditions. The [source catalog](docs/SOURCES.md) describes collection routes and coverage limits.

## Quick start

Use Python 3.11 or later and Node.js 20 or later with npm. From the repository root:

```bash
bash scripts/install.sh
source .venv/bin/activate
atlas init
atlas doctor
atlas demo --out demo-output
```

The demo uses synthetic evidence and requires an empty output directory. See [Operations](docs/OPERATIONS.md) for collection, extraction and report generation.

## Documentation

- [Data semantics](docs/DATA_SEMANTICS.md): observations, dates, missing values and comparison rules.
- [Scientific review](docs/EDITORIAL_GUIDE.md): evidence assessment and outbreak identity.
- [Structured exports](docs/SITE_EXPORT.md): datasets, provenance and analytical selection.
- [Evaluation](docs/EVALUATION.md): fixtures, benchmarks and validation.
- [Contributing](CONTRIBUTING.md): development and contributions.

ATLAS is an experimental research release under the [MIT license](LICENSE). Source reuse and redistribution follow the publisher's terms.
