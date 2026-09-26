# EpiWeekly

**Experimental release v0.1.0-alpha.8** · Python package `0.1.0a8` · Data schema `0.1.2`

EpiWeekly produces a Wednesday research-group briefing from configured outbreak intelligence sources. It maintains a longitudinal event registry, records changes in the evidence, and surfaces questions and resources relevant to the group's research. Each briefing includes a fixed-layout report and a documented analytical dataset.

The initial research profile covers One Health, temporal networks, spatial spread, inference, phylodynamics, and observation processes. Source selection, relevance weights, retrieval budgets, and the reporting timezone live in versioned configuration.

## Workflow design

The [weekly digest design](docs/WORKFLOW.md) prioritizes important developments and source-backed research leads, with detailed extraction for selected investigations. It specifies compact model output and selection of one captured version per publication. An isolated trial supports compact claims and evidence for selected publication versions; registry expansion and selective detailed extraction require implementation and evaluation. The CLI described below performs full-schema extraction. The [evaluation protocol](docs/EVALUATION.md) defines the comparison before a batch run.

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
                               content-bound release approval
```

The included GitHub Actions schedule requests a run every Wednesday at **08:37 Europe/Amsterdam**. Each run records its actual knowledge cutoff. An overlapping 21-day discovery window and bounded revisits capture delayed reporting and page revisions. The ongoing registry carries previously reviewed events into subsequent briefings.

An editor reviews extracted mentions, assigns stable event identities, and resolves corrections. The workflow produces an initial draft and a private review queue. Applying decisions and sealing the same reporting date creates a revised briefing against the preceding week's snapshot.

## Quick start

Use Python 3.11 or later. The reference validation environment uses Python 3.13.5.

```bash
bash scripts/install.sh
source .venv/bin/activate
epiweekly demo --out demo-output
epiweekly verify --bundle demo-output/reports/2026-09-23
```

Open `demo-output/reports/2026-09-23/report.html` and its accompanying `dataset.zip`. The demonstration follows three fictional Wednesday briefings: repeated reports, a corrected cumulative total, a continuing animal event, a resolved human event, and an ambiguous mention queued for review.

## Collect and review

```bash
epiweekly init
epiweekly doctor
epiweekly run --provider none
epiweekly review-export
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
epiweekly run --provider codex
```

To extract sources already collected, use `epiweekly extract --provider codex`. Supply `--model MODEL_ID` to select a model available to your Codex account; otherwise the CLI selects its default. EpiWeekly uses a private attempt directory, schema-constrained output, and a read-only sandbox with shell, browser, apps, and plugins disabled. Subscription usage limits apply. API keys are not passed to this provider.

For API extraction, configure a model available to your API project and set `OPENAI_API_KEY` through your secret manager or shell environment:

```bash
epiweekly run --provider openai --model YOUR_API_MODEL_ID
```

`EPIWEEKLY_PROVIDER` and `EPIWEEKLY_MODEL` set the command defaults. Both model providers share the chunk queue, evidence checks, and editorial review process. Extraction does not accept events or approve publication.

```bash
epiweekly review-export
```

Edit the decision template under `.runtime-state/review/`, apply the decisions, and seal the report:

```bash
epiweekly review-apply .runtime-state/review/decisions.json
epiweekly seal --report-date 2026-09-30
```

The command emits the dated bundle path. `docs/EDITORIAL_GUIDE.md` covers event identities, source evidence, corrections, related events, and opportunity ownership. `examples/import/` contains the document and extraction contracts for authorized local imports.

## Event and measurement semantics

A document version contains extracted mentions. Reviewed mentions are assigned to persistent events. Source observations retain their time interval, case classification and definition, host, geography, population, stratum, numeric qualifier, and originating authority.

Matching authority identifiers and matching scopes generate review suggestions. Explicit editorial decisions establish event identity. Separate event relationships describe source-reported links, analytical hypotheses, and identity changes.

`event_metrics` selects one current representation for each measurement context. Repeated equal totals preserve their supporting observations. Conflicting totals carry `N/A` with `conflicting` status. Cumulative differences are labeled changes in reported totals; source-reported incident observations carry their own intervals. Missing values use JSON `null` or CSV `N/A` together with an explicit reason. Zero remains a reported numeric value.

## Reports and datasets

Every report uses eight sections: weekly scan; event developments; continuing watchlist; learning and contribution opportunities; review and data quality; source coverage; dataset and analysis; methods and versions.

Each bundle includes HTML and Markdown reports, canonical JSON, eleven CSV tables, JSON Schema, a column-level data dictionary, a data-package descriptor, Python and R analysis examples, a run manifest, and SHA-256 checksums. `dataset.zip` carries the complete bundle. Historical event views and individual claims support longitudinal analysis.

Replay uses the frozen structured snapshot and the matching software version:

```bash
epiweekly replay demo-output/reports/2026-09-23/report.json --out replay-output
epiweekly verify --bundle replay-output
```

## Sources

| Source | Workflow role | Initial access route |
| --- | --- | --- |
| WHO Disease Outbreak News | International official reporting | Experimental website OData adapter |
| ECDC CDTR | European and international threat synthesis | Dated archive and primary report PDF |
| EFSA | One Health evidence, publications, and data calls | Topic archives and publisher topic labels |
| FAO avian influenza updates | Animal-health and zoonotic context | Versioned situation-update page |
| RIVM | Dutch national context | Official RSS; published sitemaps for backfill |
| WOAH WAHIS | Official animal-health notifications | Authorized document or export import |
| BEACON | Curated discovery and errata | Authorized document or export import |

The [source catalog](docs/SOURCES.md) records access evidence, scope, adapter behavior, and onboarding checks. The report exposes collection coverage and source-specific gaps for each run.

## Deployment and maintenance

Keep the reusable code in this repository and operational state in a dedicated private repository. The supplied workflows preserve the registry between runs and support explicit publication of approved bundles. `docs/OPERATIONS.md` specifies the repository variables, secrets, scheduler setup, review loop, and recovery process.

Software, schema, prompts, vocabulary, configuration, and report-template versions travel with each run. Dependency pins, commit-pinned Actions, continuous integration, synthetic fixtures, and a chronological evaluation protocol support maintenance. The code uses the MIT license; source attribution and reuse conditions are recorded separately.

### Project documentation

[Architecture](docs/ARCHITECTURE.md) · [Editorial guide](docs/EDITORIAL_GUIDE.md) · [Operations](docs/OPERATIONS.md) · [Sources](docs/SOURCES.md) · [Data semantics](docs/DATA_SEMANTICS.md) · [Evaluation](docs/EVALUATION.md)

## Two-week source scan

Run from the repository root with the virtual environment active:

```bash
epiweekly --config config/backfill.yaml collect --since 2026-09-12
epiweekly --config config/backfill.yaml extract --provider none
epiweekly --config config/backfill.yaml seal
python scripts/reading_reports.py --since 2026-09-12 --until 2026-09-25
```

Open `reports/index.html` for monthly source reading reports with captured text and source links. To resume an interrupted backfill, use `collect --since 2026-09-12 --missing-only`. This reuses captured URLs without checking them for revisions; ordinary collection revisits source pages.

Both configurations use `publication_window_days: 14`. Collection, extraction, review queues, and report evidence use 14 publication dates ending on the reporting date, inclusive. Undated publications stay outside that view until their dates are established. Earlier captures and decisions remain in the ledger. A calendar-month window can be set with `publication_window_months` instead of `publication_window_days`.

Each model call records its start and outcome in the ledger. Codex event logs, error output, and model responses remain private under `extraction_attempts/` in the state directory. `review/extraction_progress.json` records the active document, attempted calls, successes, failures, and latest error. A running process alone does not establish progress. `max_output_tokens` applies to the API provider; Codex uses a 20-minute call timeout and a completed-response byte limit. Model candidates require source review before acceptance.

The backfill configuration permits 40 pages per index and 2,000 documents per source. EFSA collection covers its Animal health and Biological hazards topics, including foodborne disease, zoonoses, and antimicrobial resistance. Data calls use the topic labels on each call. RIVM sitemap modification dates guide discovery; article publication dates determine the reading month. RSS feeds and mutable situation pages may cover only part of the requested period. Inspect source coverage before interpreting the result. Collection alone does not create reviewed outbreak events. Captures retain their actual retrieval time; they do not reconstruct what was known in each historical week.

Local reports, captured evidence, and installation records are excluded from Git. Hosted collection requires the repository variables and secrets in [Operations](docs/OPERATIONS.md); the schedule is gated by `EPIWEEKLY_SCHEDULE_ENABLED`.

## Compact digest trial

Run a separate digest experiment against captured publications:

```bash
python scripts/digest_trial.py --since 2026-08-26 --until 2026-09-26 --out reports/month-trial
```

The trial selects the latest captured version of each publication, retains full source text, and writes claims with evidence references, diagnostics, usage, and an HTML review report. It makes at most 36 subscription calls with a 10-minute limit per call and checks a 200,000-byte completed response limit. Input is bounded at 650,000 characters overall and 100,000 per publication; oversized sources are reported without truncation. Results do not enter the accepted registry. Quote matching is a mechanical check, and an editor must assess meaning and briefing coverage. Use a separate output directory for an independent repeat.
