<h1><img src="docs/figures/atlas-logo.svg" alt="ATLAS" width="560"></h1>

**Agentic Tracking and Longitudinal Analysis for Surveillance**

One Health outbreak intelligence across sources, places, and time.

![Release](https://img.shields.io/badge/release-v0.1.0--alpha.21-orange)
![Stage](https://img.shields.io/badge/stage-research_preview-orange)
[![Tests](https://github.com/EvoLandEco/ATLAS/actions/workflows/ci.yml/badge.svg)](https://github.com/EvoLandEco/ATLAS/actions/workflows/ci.yml)
![Export contract](https://img.shields.io/badge/export_contract-1.2.0-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Python package `0.1.0a21` · Core data schema `0.1.2` · Metrics contract `0.2.0`

ATLAS automates weekly outbreak surveillance and longitudinal analysis for research groups, with human review of scientific decisions. It collects public health and animal health reports, extracts evidence, follows reported counts over time, and prepares geographic relationships for analysis. Its products are reports and versioned, analysis-ready exports that other applications can present and explore.

The research profile covers One Health, disease spread over time and space, transmission networks, genomic epidemiology and surveillance. Configuration files specify sources, research priorities, collection limits and the reporting timezone.

## What ATLAS offers

- **Automated weekly work, with people in control.** Scheduled agent jobs carry collection, extraction, evidence checks and report preparation from source to export. A review inbox brings unresolved questions to an editor. People decide disputed interpretations, outbreak identities and release approval; routine work continues while unanswered questions remain pending.
- **Longitudinal analysis maintained each week.** The weekly procedure reviews source revisions, adds eligible observations to reviewed surveillance series and reassesses affected comparisons. Reporting periods, case definitions, gaps and conflicting figures travel with the data. [Explicit comparison rules](docs/LONGITUDINAL_ANALYSIS.md) determine which observations can be connected.
- **Scaling considered at each stage.** Saved extractions and geographic assessments avoid repeated model work. Indexed memberships, shared source normalization and cached quotation searches reduce local processing costs. [Measured benchmarks and documented scaling limits](#rescanning-and-archive-growth) guide archive expansion and targeted reassessment.
- **Geographic assessment and evidence networks.** Location roles, source-described travel, shared exposures and epidemiological hypotheses connect reports across places and time. Exported endpoints, dates and quoted support let interfaces show maps and temporal replay, with a [reassessment procedure](docs/LINK_REASSESSMENT.md) for historical additions and weekly updates.
- **Stable outputs and reproducible analysis.** Frozen source snapshots, saved model responses, reviewed annotations and fixed software versions support deterministic scientific content and replay. Stable identifiers, versioned schemas and preserved decision history keep releases traceable; generation timestamps record each run. Analysis-ready exports support reuse without repeating extraction.
- **Open methods and collaboration.** The [MIT-licensed](LICENSE) code, prompts, schemas, workflow rules and evaluation methods make the process inspectable. Source references and documented decisions support scrutiny of the findings. [Contributions](CONTRIBUTING.md), scientific review, source improvements and corrections are welcome.

## Workflow design

The [weekly digest guide](docs/WORKFLOW.md) describes a concise briefing focused on important developments and research leads. The digest trial extracts short findings and source quotations from saved publications. The commands below perform detailed extraction for the event registry. Converting digest findings into registry records remains under development. The [evaluation protocol](docs/EVALUATION.md) describes how to assess extraction quality.

## Agent setup

The reference agent setup uses **GPT-6 Astra with High reasoning in Codex**. Codex is the only agent harness tested for the complete workflow. Individual extraction runs record their actual model and prompt versions; this setup does not describe every historical run.

**Model capability matters.** Less capable LLMs can produce poorer results, including missed evidence, incorrect measurement scope and unsupported links. **Claude Opus 5.5 is a safer substitute to evaluate than a less capable model**, based on its strong [general benchmark performance](https://artificialanalysis.ai/articles/claude-opus-5-5). This is a model selection recommendation; Opus 5.5 has not been validated in ATLAS. Assess substitutions with the same captured sources and [extraction evaluation protocol](docs/EVALUATION.md) before operational use.

ATLAS's workflow rules, evidence contracts, import formats and export schemas can in principle be used with any agent harness or LLM capable of following them. A different setup requires an adapter or contract-based import and evaluation against the same fixtures and evidence checks. Compatibility and extraction quality with other harnesses and models are untested. The installed extraction providers are listed under [Collect and review](#collect-and-review).

![Selected recent LLMs on the Artificial Analysis Intelligence Index, 27 September 2026. Claude Opus 5.5 high with fallback: 54; GPT-6 Astra high: 51; Muse Spark 1.3 max: 48; GPT-6 Sol max: 48; Grok 4.7 xhigh: 46; Qwen3.8 Max 0902: 45; Gemini 3.8 Flash high: 41; DeepSeek V4.1 Flash max: 39.](docs/figures/model-capabilities.svg)

Source: [Artificial Analysis leaderboard](https://artificialanalysis.ai/leaderboards/models), accessed **27 September 2026**. The [Intelligence Index v4.3.2](https://artificialanalysis.ai/articles/artificial-analysis-intelligence-index-v4-3) combines ten evaluations of agents, coding, general tasks and scientific reasoning. The figure shows selected models and configurations, including ATLAS's reference reasoning setting. Scores are index points, not extraction accuracy. Reasoning settings differ across vendors and do not imply equal computing budgets. Opus's “with fallback” label denotes [Anthropic's default model substitution during evaluation](https://artificialanalysis.ai/articles/claude-opus-5-5). These results guide model selection; ATLAS evidence review remains necessary.

## Weekly jobs in Codex

Three scheduled jobs share the local evidence archive and return to the project chat. They run on Wednesdays in **Europe/Amsterdam** time:

| Time | Job | Result |
| --- | --- | --- |
| 07:00 | Review the preceding batch | Check source revisions, extraction accuracy and derived outputs; record corrections and questions requiring an editor. |
| 08:37 | Prepare the weekly briefing | Collect the seven complete publication dates ending Tuesday, reuse valid extractions, process new or changed sources, and produce the briefing, structured dataset and map/network preview. |
| 12:00 | Present the review inbox | Bring together new questions and unresolved historical issues, with evidence, suggested actions and the decisions needed. |

The review inbox is advisory. Ignoring an item leaves it pending and does not trigger edits, acceptance or more processing. An explicit decision is recorded and applied to its named evidence; only affected outputs are rebuilt. Unchanged historical items remain accessible without repeated prompts. A pending decision affects the relevant findings, while unrelated weekly work continues.

These are agent tasks using the installed tools and saved preparation scripts. They do not add a three-stage CLI command. The [job rules](docs/WORKFLOW.md#three-weekly-agent-jobs) define windows, dependencies, correction handling and completion checks; [Operations](docs/OPERATIONS.md#scheduled-jobs-in-codex) describes their local execution. Keep the computer awake and the app running. The GitHub Actions collector is a separate deployment route; use one acquisition scheduler for a shared archive.

## Installed workflow

```text
Wednesday collection → source snapshots → structured extraction
                                           ↓
                                 evidence checks and event matches
                                           ↓
                                    editorial decisions
                                           ↓
                          event registry and measurement changes
                                           ↓
                    report + dataset + research-opportunity register
                                           ↓
                               approval of the report and dataset
```

The included GitHub Actions schedule requests a run every Wednesday at **08:37 Europe/Amsterdam**. Each run records its actual knowledge cutoff. An overlapping 21-day discovery window and bounded revisits capture delayed reporting and page revisions. The ongoing registry carries reviewed events into subsequent briefings.

An editor reviews extracted mentions, assigns stable event identities, and resolves corrections. The workflow produces an initial draft and a private review queue. Applying decisions and sealing the same reporting date creates a revised briefing against the preceding week's snapshot.

## Quick start

Use Python 3.11 or later. The Python distribution is `atlas-surveillance`; the import package and command are `atlas`.

```bash
bash scripts/install.sh
source .venv/bin/activate
atlas init
atlas doctor
```

These commands prepare local state and check the installation. Continue with [Collect and review](#collect-and-review) to collect sources. Explore exported results through the [website interface](https://qtj.me/atlas/). Synthetic fixtures exercise evidence review and deterministic replay in the test suite.

## Collect and review

```bash
atlas init
atlas doctor
atlas run --provider none
atlas review-export
```

Choose an extraction provider for `run` or `extract`:

| Provider | Access | Use |
| --- | --- | --- |
| `none` | No model account | Collect sources for manual extraction and review |
| `codex` | Codex CLI signed in with ChatGPT | Local extraction using your subscription allowance |
| `openai` | OpenAI API key | Extraction billed to your API project |

For Codex, install the [Codex CLI](https://learn.chatgpt.com/docs/non-interactive-mode), sign in with ChatGPT, and run:

```bash
codex login
codex login status
atlas run --provider codex
```

To extract sources already collected, use `atlas extract --provider codex`. Supply `--model MODEL_ID` to select a model available to your Codex account; otherwise the CLI selects its default. ATLAS uses a private attempt directory, schema-constrained output, and a read-only sandbox with shell, browser, apps, and plugins disabled. Subscription usage limits apply. API keys are not passed to this provider.

For API extraction, configure a model available to your API project and set `OPENAI_API_KEY` through your secret manager or shell environment:

```bash
atlas run --provider openai --model YOUR_API_MODEL_ID
```

`ATLAS_PROVIDER` and `ATLAS_MODEL` set the command defaults. Both model providers share the chunk queue, evidence checks, and editorial review process. Extraction does not accept events or approve publication.

```bash
atlas review-export
```

Edit the decision template under `.runtime-state/review/`, apply the decisions, and seal the report:

```bash
atlas review-apply .runtime-state/review/decisions.json
atlas seal --report-date 2026-09-30
```

The command emits the dated bundle path. `docs/EDITORIAL_GUIDE.md` covers event identities, source evidence, corrections, related events, and opportunity ownership. `examples/import/` contains the document and extraction contracts for authorized local imports.

## Structured, analysis-ready outputs

[Geographic post-processing](docs/GEOGRAPHIC_REVIEW.md) assesses every report entry for location scope and source-described relationships, reuses saved assessments and records unmapped or unresolved findings. The map and structured bundle share one validated snapshot. Completion checks cover assessment coverage, source references, date extent and the rendered map, so expanding the reporting window includes geographic review of the added findings.

The agent workflow uses [targeted link reassessment](docs/LINK_REASSESSMENT.md) for weekly updates and historical expansion. It reuses unchanged source assessments, reviews relationships affected by changed evidence, and checks explicit references against the full archive. Review receipts preserve decisions, unresolved questions and actual processing costs. This is an operating procedure; the geography runner does not automatically invalidate historical annotations or resolve conflicts.

ATLAS turns source reports into [versioned research datasets](docs/SITE_EXPORT.md) for evidence review, analysis, maps and other applications. Stable identifiers connect documents, individual assertions, measurements and relationships to their exact source evidence. Measurements retain their population, case classification, reporting period and denominator, so researchers can select the relevant observations without extracting the same facts again.

[Longitudinal review](docs/LONGITUDINAL_ANALYSIS.md) prepares comparable sequences of reported counts within a defined surveillance programme. Reviewed series retain case definitions, reporting periods, cumulative baselines and source evidence, with explicit connections between eligible observations. Trends preserve missing periods, conflicting values and reporting revisions. These permissions describe reported counts; incidence, rates and fatality-risk comparisons require further evidence.

The export distinguishes conflicting assertions, explicit corrections, independent corroboration, repeated reporting and differences in scope. Geographic roles and reporting dates support consistent filtering across analyses and visualizations. Review status, missing values and extraction coverage accompany the data; statistical comparisons require suitable populations, periods and denominators.

The supplied selector prepares [compact figures](docs/SITE_EXPORT.md#compact-figures) for information cards. Matching recorded figures appear once with all eligible reporting sources and measure IDs attached. Conflicts and differences in scope remain separate. The full assertions and source-specific contexts remain available for inspection and analysis.

Consumers can use the [export handoff](docs/PUBLICATION_HANDOFF.md) to check completion of all three weekly jobs and identify the exact validated data, map snapshot and selector hashes. Initial publication and explicitly authorized corrections remain separate from weekly completion. Small [TypeScript declarations](types/atlas.d.ts) describe the data and selector interfaces without importing report JSON.

`atlas metrics` prepares scoped measurements and qualitative findings. `atlas site-export` packages the structured entities, evidence, comparison groups and selection rules. `atlas site-verify` checks the schema, references and checksums before reuse. Snapshot metadata records the latest capture and the next planned collection, with its timezone. Editorial approval governs public release.

A completed digest is a concise selection of findings, not an exhaustive extraction of every numeric field. [Numeric enrichment](docs/WORKFLOW.md#numeric-enrichment-and-coverage) is part of weekly production: it processes every concrete opportunity identified during review, reuses captured sources, exports supported measurements and assesses their longitudinal comparisons. Each opportunity receives a recorded outcome, with source questions retained for investigation. Collection coverage, numeric review coverage and longitudinal comparability remain distinct. A publication may supply several report entries; count documents and entries separately.

[Reviewed chains](docs/CHAIN_REVIEW.md) export source-established transmission, reported contact, travel itineraries and consecutive reports as distinct graphs. Stable nodes, explicit connections, dates and quoted evidence support downstream maps. Selection preserves unknown locations and removes unsupported connections without bridging gaps.

## From exports to a web interface

[qtj.me/atlas](https://qtj.me/atlas/) is the example interface implementation for ATLAS exports. It presents maps, evidence networks, reporting windows and Trends from the prepared dataset. ATLAS produces exported results; the separate website project owns the web interface and its deployment.

The website's weekly job checks the ATLAS completion receipts, export contracts and exact file hashes, then distributes the authorized release. **Cloudflare R2 stores the dataset and a Cloudflare Worker relays it to the browser.** Immutable release files and a verified release pointer let the interface consume a dataset without rebuilding the website. Source interpretation, geographic assessments and longitudinal comparison permissions remain in ATLAS; the website handles presentation and filtering.

**Cross-thread agent coordination** connects the ATLAS and interface projects in Codex. The ATLAS agent sends the validated release reference and compatibility details; the interface agent checks the consuming code and records adoption. The [handoff contract](docs/PUBLICATION_HANDOFF.md) binds this exchange to exact files, completion evidence and distribution approval.

## Events and measurements

Each saved document contains extracted findings, called mentions in the data model. An editor assigns reviewed mentions to events. Measurements retain their reporting period, case definition and classification, host, location, population, subgroup, qualifiers and reporting authority.

Matching authority identifiers and matching scopes generate review suggestions. Explicit editorial decisions establish event identity. Separate event relationships describe source-reported links, analytical hypotheses, and identity changes.

`event_metrics` selects one current representation for each measurement context. Repeated equal totals preserve their supporting observations. Conflicting totals carry `N/A` with `conflicting` status. Cumulative differences are labeled changes in reported totals; source-reported incident observations carry their own intervals. Missing values use JSON `null` or CSV `N/A` together with an explicit reason. Zero remains a reported numeric value.

## Reports and datasets

Every report uses eight sections: weekly scan; event developments; continuing watchlist; learning and contribution opportunities; review and data quality; source coverage; dataset and analysis; methods and versions.

Each sealed report bundle includes HTML and Markdown reports, canonical JSON, eleven CSV tables, JSON Schema, a column-level data dictionary, a data-package descriptor, Python and R analysis examples, a run manifest, and SHA-256 checksums. `dataset.zip` carries the complete bundle. Historical event views and individual claims support longitudinal analysis.

Replay uses the frozen structured snapshot and the matching software version:

```bash
atlas replay /path/to/sealed-bundle/report.json --out replay-output
atlas verify --bundle replay-output
```

## Exploring connections

The [website interface](https://qtj.me/atlas/) follows reports across places and time. Reporting windows and temporal replay show the selected evidence. Geographic lines represent source-described travel, shared events and epidemiological hypotheses, with quotations and location details available for review. The source network connects documents to reporting topics. See the [link rules](docs/RELATIONSHIP_RULES.md) and [technical review](docs/LINK_REVIEW.md).

## Sources

| Source | Workflow role | Collection route |
| --- | --- | --- |
| WHO Disease Outbreak News | International official reporting | Experimental website OData adapter |
| ECDC CDTR | European and international threat synthesis | Dated archive and primary report PDF |
| WHO Africa | Regional outbreak and emergency bulletins | Dated archive and linked PDF |
| Nigeria NCDC | National disease situation reports | Disease series and dated PDF editions |
| PAHO | Regional alerts and epidemiological updates | Dated archive and linked PDF |
| UKHSA | Global outbreak monitoring summaries | Annual archive and dated HTML editions |
| WHO situation updates | International emergency reporting | Publisher category and linked PDF |
| EFSA | One Health evidence, publications, and data calls | Topic archives and publisher topic labels |
| FAO avian influenza updates | Animal-health and zoonotic context | Versioned situation-update page |
| RIVM | Dutch national context | Official RSS; published sitemaps for backfill |

**Possible sources, not used:** WOAH WAHIS could contribute animal health notifications; BEACON could contribute curated signals and errata. Collaboration with either provider is not established, and ATLAS has no authorized retrieval or import route for them. Both are disabled in the supplied configurations. Their listing does not imply a partnership or data contribution.

The [source catalog](docs/SOURCES.md) records access evidence, scope, adapter behavior, and onboarding checks. Each report describes source coverage and collection gaps.

## Deployment and maintenance

This repository distributes ATLAS software, workflow documentation, schemas and synthetic examples. Generated datasets and reports are available through [qtj.me/atlas](https://qtj.me/atlas/). Source captures, review queues, operational state and generated outputs stay outside the Git release. The root allowlist in `.gitignore` keeps new output folders local by default.

Keep the reusable code in this repository and operational state in a dedicated private repository. The supplied workflows preserve the registry between runs and support explicit publication of approved bundles. `docs/OPERATIONS.md` specifies the repository variables, secrets, scheduler setup, review loop, and recovery process.

Software, schema, prompts, vocabulary, configuration, and report-template versions travel with each run. Dependency pins, commit-pinned Actions, continuous integration, synthetic fixtures, and a chronological evaluation protocol support maintenance. The code uses the MIT license; source attribution and reuse conditions are recorded separately.

### Project documentation

[Architecture](docs/ARCHITECTURE.md) · [Editorial guide](docs/EDITORIAL_GUIDE.md) · [Operations](docs/OPERATIONS.md) · [Sources](docs/SOURCES.md) · [Data semantics](docs/DATA_SEMANTICS.md) · [Evaluation](docs/EVALUATION.md)

## Two-week source scan

Run from the repository root with the virtual environment active:

```bash
atlas --config config/backfill.yaml collect --since 2026-09-12
atlas --config config/backfill.yaml extract --provider none
atlas --config config/backfill.yaml seal
python scripts/reading_reports.py --since 2026-09-12 --until 2026-09-25
```

Open `reports/index.html` for monthly source reading reports with captured text and source links. To resume an interrupted backfill, use `collect --since 2026-09-12 --missing-only`. This reuses captured URLs without checking them for revisions; ordinary collection revisits source pages.

Both configurations use `publication_window_days: 14`. Collection, extraction, review queues, and report evidence use 14 publication dates ending on the reporting date, inclusive. Undated publications stay outside that view until their dates are established. Earlier captures and decisions remain in the ledger. A calendar-month window can be set with `publication_window_months` instead of `publication_window_days`.

Each model call records its start and outcome in the ledger. Codex event logs, error output, and model responses remain private under `extraction_attempts/` in the state directory. `review/extraction_progress.json` records the active document, attempted calls, successes, failures, and latest error. Use completed chunks and the latest attempt outcome to assess progress. `max_output_tokens` applies to the API provider; Codex uses a 20-minute call timeout and a completed-response byte limit. Model candidates require source review before acceptance.

The backfill configuration permits 40 pages per index and 2,000 documents per source. EFSA collection covers its Animal health and Biological hazards topics, including foodborne disease, zoonoses, and antimicrobial resistance. Data calls use the topic labels on each call. RIVM sitemap modification dates guide discovery; article publication dates determine the reading month. RSS feeds and mutable situation pages may cover only part of the requested period. Inspect source coverage before interpreting the result. Editorial review assigns findings to outbreak events. Historical collection records the date each source was retrieved.

Local reports, captured evidence, and installation records are excluded from Git. Hosted collection requires the repository variables and secrets in [Operations](docs/OPERATIONS.md); the schedule is gated by `ATLAS_SCHEDULE_ENABLED`.

## Compact digest trial

Run a separate digest experiment against captured publications:

```bash
python scripts/digest_trial.py --since 2026-08-26 --until 2026-09-26 --out reports/month-trial
```

The trial selects the latest captured version of each publication, retains full source text, and writes claims with evidence references, diagnostics, usage, and an HTML review report. It makes at most 36 subscription calls with a 10-minute limit per call and checks a 200,000-byte completed response limit. Input is bounded at 650,000 characters overall and 100,000 per publication; oversized sources are reported without truncation. Results do not enter the accepted registry. Quote matching is a mechanical check, and an editor must assess meaning and briefing coverage. Use a separate output directory for an independent repeat.

### Consumption and cost estimates

One task means compact extraction of one captured publication, before editorial review. The reference trial processed 22 publications dated 26 August through 26 September 2026, covering 32 publication dates. The weekly estimate scales that source mix by 7/32; the month row is the measured trial workload, not a complete source census.

| Workload | Publications | Input tokens | Output tokens | Model time | Extra charge within subscription allowance | Illustrative API cost (USD) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Average task | 1 | 15,567 | 1,396 | 47 sec | $0 | $0.043 |
| Weekly estimate | ~5 | 74,917 | 6,716 | 3.7 min | $0 | $0.20 |
| Month trial | 22 | 342,477 | 30,704 | 17.1 min | $0 | $0.94 |

API estimates apply GPT-6 Sol Standard short context rates of $2 input, $0.20 cached input, and $10 output per million tokens, checked on 26 September 2026. They retain the trial's 31,232 cached input tokens and assume no cache writes. These are illustrative equivalents, not charges incurred or a model comparison: the subscription trial did not record its returned model identifier. See [API pricing](https://developers.openai.com/api/docs/pricing).

These figures cover extraction calls only, excluding collection, development chats, retries, editorial work, and detailed registry extraction. Source length and reporting volume change consumption. The subscription fee is separate; additional credits may incur charges after the included allowance is exhausted. Tokens and credit prices do not directly determine the remaining subscription percentage. Estimate capacity from the allowance consumed by a representative batch with other activity excluded: `remaining publications = batch publications × remaining percentage / batch percentage consumed`. See [subscription usage and credit pricing](https://learn.chatgpt.com/docs/pricing) and the [evaluation findings](docs/EVALUATION.md).

## Rescanning and archive growth

Reusing a validated extraction avoids another model call. It does not avoid source discovery, revision checks, reading saved data or rebuilding an export. Model consumption therefore depends mainly on new or changed publications, while local work also depends on the accumulated archive and the selected reporting window.

### Model consumption

For a rescan, extraction token use is proportional to the source tokens requiring extraction, repeated instructions for each call, generated output and retries. Saved reports are not all appended to each model request. With a steady flow of new publications and matching saved results, total extraction consumption grows roughly linearly with time. Re-extracting the entire growing archive every week would instead produce quadratic cumulative consumption.

The [registry extractor](src/atlas/extraction.py) keys reuse by document identity, chunk content, provider, requested model, prompt, schema and vocabulary. A new document version can invalidate every chunk in that document. Pin the model explicitly: an unspecified model does not identify changes to a provider's default. Long documents also repeat overlapping text between chunks; 28,000-character chunks with 1,200-character overlap add about 4.5% to source input for long documents, before instructions and schema.

Compact digests and detailed registry extraction have separate contracts and caches. The six-month digest batch imports saved results and checks source metadata, text, prompt, schema and evidence before reuse. Its fingerprint does not include the model, so a model comparison needs a distinct extraction version and output set. The standalone [digest trial](scripts/digest_trial.py) reuses results in its output directory; a fresh directory does not automatically inherit results from other trials.

The six-month batch covering 26 March through 26 September 2026 selected 202 publications, reused 91 results and completed 111 model turns. Those turns reported 1,559,969 input tokens, including 499,712 cached tokens, and 167,296 output tokens: about 14,054 input and 1,507 output tokens per completed publication. There were 114 attempts; these totals exclude usage not reported by the three interrupted attempts. They also exclude development chats and editorial work.

At that source mix, ten publications needing extraction would use about 141,000 input and 15,100 output tokens. An unchanged selection with matching validated results needs zero further extraction tokens. Source length, extraction contract and retries matter more than publication count alone.

Application result reuse and API prompt caching serve different purposes. Result reuse skips the call. Prompt caching discounts eligible input in a call that still runs; cache availability is time limited, and output is still generated. Do not assume a weekly rescan retains a provider's prompt cache. See [prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching).

For rates per million tokens, estimate API cost as `(uncached input × input rate + cached input × cached rate + cache writes × write rate + output × output rate) / 1,000,000`. The three input categories are mutually exclusive; cached tokens are part of total input. Using the Standard rates above and zero cache writes, the six-month recorded workload has an illustrative API equivalent of $3.89. It was a subscription run, not an API invoice, and direct API extraction can have a different input and output profile. Rates and cache write charges are model dependent; see [API pricing](https://developers.openai.com/api/docs/pricing).

### Local processing

Let `D` be all stored document versions, `F` the source entries visited in a scan, `N` the selected publications, `Δ` those needing extraction, `R` exported records, `A` assertions and `T` topics. The main costs in the implementation are:

| Stage | Work as the archive grows |
| --- | --- |
| Discovery and retrieval | Archive pages, network latency, request spacing and parsing determine elapsed time. The standard collector repeatedly loads document history for visited entries, adding about `O(F × D)` metadata work. Retrieval also scans fetch receipts. The six-month batch uses a URL lookup for captured publications, reducing those repeat scans on reuse. |
| Saved extraction validation | Reads document metadata across the archive, then selected text and saved results. Hashing and parsing grow with the bytes read; evidence checks search source text for each quotation. A narrow date window does not eliminate the metadata scan. |
| Digest progress output | The six-month runner rewrites the growing results file at each call's start and completion. This writes about `O(Δ × N)` result data; a batch built from scratch can write a quadratic cumulative volume. Sorting adds work. |
| Metrics and structured export | Source text is normalized once per document. Claim indexes select panel candidates, then check all supporting claims. Record, document, topic and coverage memberships are grouped once for export and validation. These joins scale with their input and emitted memberships, plus sorting. Place preparation joins topic records, endpoint relationships and record locations through indexes, retaining source order. Evidence searches depend on source length and distinct quotations. |
| Interactive selection | Record IDs are indexed once per call. Source coverage visits declared memberships and sorts selected record positions to preserve document order. Work follows records and membership references plus sorting, rather than rescanning all records for every coverage edge. Cards, evidence and reviewed connections are still filtered each time. |
| Ledger verification and packaging | The ledger hash pass reads the whole ledger. Serialization and compression process the bytes exported. These passes grow with data size, even when extraction is fully reused. |

These are costs of the loops in [collection](src/atlas/sources.py), [metrics](src/atlas/metrics.py) and [structured export](src/atlas/site_export.py), not a claim that every stage has the same complexity. SQLite has indexes for record lookup, but collection still loads whole record lists repeatedly. A fourfold increase in comparable data can mean roughly sixteenfold work in remaining quadratic sections; it does not imply sixteenfold total runtime.

Export lookups last for one invocation, so a source or annotation change receives a fresh validation pass. Quotation spans are searched once per document and distinct whitespace pattern; each evidence reference retains its occurrence, source offsets, page and section. Page lookup uses a sorted list of source markers. Panel selections retain input order and require every supporting claim. These operations preserve the export fields, identifiers, source assertions, review states and scientific rules. They reduce local processing work without changing model prompts, extraction budgets or token consumption.

An offline benchmark on 27 September 2026 used the captured six-month graph with 785 report entries and 284 measurements, on macOS ARM64. The portable selector has these median times for complete selections:

| Report entries | Repeated scans | Indexed selection | Speed ratio |
| --- | ---: | ---: | ---: |
| 785 | 11.7 ms | 3.1 ms | 3.8× |
| 1,570 | 37.0 ms | 6.2 ms | 6.0× |
| 3,140 | 107.7 ms | 13.8 ms | 7.8× |
| 6,280 | 414.9 ms | 27.7 ms | 15.0× |

Larger workloads replicate the graph with distinct identities. Five warmups and eleven timed calls measure selector computation; file loading, browser rendering and model work are excluded. These workloads test scaling, not future epidemiological coverage.

On the captured dataset, structured export took 2.75 seconds with repeated place-membership scans and 0.93 seconds with indexed joins, measured across three fresh Python processes. Peak process memory was about 265 and 260 MiB. Scientific output and ordering matched; generation timestamps differ. Metrics preparation took 0.28 seconds and bundle verification 0.16 seconds. These figures exclude startup and imports. The [evaluation methods](docs/EVALUATION.md#selector-and-geographic-export-scaling) describe the checks and limits.

Most stages hold their selected datasets in memory. Parsing, validation, serialization and compression still grow with data size. Retaining a full growing export every week produces quadratic cumulative storage at a steady publication rate. Metric input limits are 32 MB for the snapshot and 16 MB for annotations; structured-export inputs are bounded at 64 MB each and source text at 4 MB per document. A replicated selector graph is not an end-to-end capacity test.

### Operating at larger scale

Keep the complete evidence archive and use bounded reporting windows for routine exports. Collect new publications, revisit sources for revisions, and schedule gap checks separately. `--missing-only` saves retrieval work but cannot detect revisions to captured URLs. Ordinary collection can download and parse attachments again even when extraction results remain reusable. More concurrent model calls can reduce waiting time; they do not reduce tokens and can increase memory use.

Before expanding frequent exports across years, further engineering work should target source metadata lookup and saving individual extraction results without rewriting the whole batch on every completion. These are recommendations, not implemented guarantees. Preserve the append-only ledger and evidence validation throughout. The six-month runner's limits of 500 publications and 12 million input characters bound a batch; they do not establish capacity for an unrestricted historical scan.
