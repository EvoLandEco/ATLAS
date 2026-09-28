# Operations

For collection expansions and weekly production, follow [Geographic assessment and map preparation](GEOGRAPHIC_REVIEW.md) after digest extraction. Preserve dated outputs, require an assessment outcome for every report entry, and build the local map from the validated export snapshot before handing off the release.

## Reporting window
The configurations use `publication_window_days: 14`, inclusive of the report date. Collection, extraction, review queues, and report evidence share that window. Earlier captures and decisions remain in private state. The [weekly digest design](WORKFLOW.md) specifies compact extraction and selected detailed investigations; the isolated digest trial tests compact claims without accepting registry events.

## Local state
Run commands from the repository root. Global `--config PATH` and `--state PATH` options precede the subcommand. The default state is `.runtime-state/`. `ledger.sqlite` contains the append-only history; `objects/` contains captured bytes and text; `extractions/` stores model-response caches; `review/` contains editorial tasks; `reports/DATE/ID/` contains sealed outputs; `latest.json` points to the most recently sealed bundle.

`atlas run` collects, extracts within budget, exports the review queue, and seals a draft. A completed run receipt prevents a repeated automatic invocation for the same local date from repeating acquisition. `--force` explicitly starts a fresh acquisition. `seal` recomputes from recorded evidence and decisions without collecting again. Editorial revisions for the same date compare with the latest sealed report on an earlier date.

The initial report has all selected events labeled `new_to_registry`. Seed an initial lookback through collection and review, then begin weekly comparisons. Historical data imported later retain their actual capture time.

## Local subscription runs

Install Codex CLI and run `codex login` with ChatGPT on the machine that runs ATLAS. Confirm the account with `codex login status`. The `codex` provider requires ChatGPT authentication and excludes API key environment variables from the subprocess. Credentials remain in Codex's credential store.

```bash
export ATLAS_PROVIDER=codex
atlas run
```

`--model MODEL_ID` or `ATLAS_MODEL` selects a model available to that account. An empty model setting uses the Codex CLI default. ATLAS ignores user Codex configuration so project tools, hooks, and connected services do not participate in extraction. Use a current CLI supporting `exec --ignore-user-config --ephemeral --output-schema`.

The same command can run through a local scheduler under the signed-in user. The machine must be awake and connected. Configure the scheduler's working directory as the repository root and make both `.venv/bin` and the Codex executable available on its PATH. No local schedule is installed by the package.

The supplied GitHub workflow supports `none` and `openai`; it does not provision subscription credentials. Keep ChatGPT credentials out of the public code repository and its Actions secrets. See [Codex automation authentication](https://learn.chatgpt.com/docs/non-interactive-mode) for account and runner requirements.

## Scheduled jobs in Codex

The local schedule consists of three weekly tasks in the project chat: preceding-batch review at 07:00, production at 08:37 and the review inbox at 12:00 on Wednesday, Europe/Amsterdam. Their scopes and completion rules are in [Workflow](WORKFLOW.md#three-weekly-agent-jobs). Codex stores schedules outside the repository. Manage or pause them in the app's Scheduled view; editing a time in this document does not reschedule a task.

Use the existing checkout and `.runtime-state`, including validated results from earlier batches. Keep the computer awake, the app running and the project available. Local tasks use the machine's permissions and signed-in account. See [scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app). The package installer does not create app automations.

Keep one acquisition scheduler for a shared archive. The GitHub collector is a separate deployment route gated by `ATLAS_SCHEDULE_ENABLED`; do not enable it against the same operating state alongside local production. The earlier review job checks revisions and accuracy; it does not launch another complete weekly acquisition.

Check the scheduled cycle, predecessor receipts and live processes before resuming a delayed task. Record each status and input/output references in `.runtime-state/weekly/CYCLE/`. A scheduled start does not certify that earlier work finished. Use the CLI writer lock for ledger mutations and serialize scripts writing the same outputs. After interruption, check saved work and actual usage before retrying. Retain the original cycle date and record coverage shortfalls.

Production selects seven complete publication dates ending Tuesday through a private run configuration or explicit digest date bounds. The repository's 14-day default is a separate selection. Discovery for late reports and the preceding-batch review have their own scopes. Check selected dates before extraction. Historical pending issues remain in the inbox outside the production window.

For compact extraction, pass the computed Wednesday and Tuesday dates as `--since` and `--until`. Check reusable saved results before invoking the trial in a fresh output directory. For a requested detailed registry run, set `publication_window_days: 7` in the private configuration, remove any month-window setting and pass Tuesday as `run --report-date`. That report date is the publication-window end; the receipt separately records Wednesday's execution cycle and actual capture time. A seven-day configuration alone would include the execution day if no explicit report date were supplied.

Keep review reports and outputs under `reports/weekly/CYCLE/`, plus a backlog view linking to historical evidence. Receipts, evidence, decisions and generated reports stay private. Ignoring the inbox does not change scientific records or trigger retries. Apply explicit decisions once to their recorded evidence version and verify affected outputs. Partial acquisition and unanswered editorial questions remain separate statuses.

## Private deployment repository
Create a dedicated private repository for state, initialized with a README. Keep its access restricted to the operating group. Its default branch is the persistence branch; use one scheduled deployment writer for that branch. The public code repository can host the reusable implementation and approved published datasets.

Configure these values in the code repository:

| Kind | Name | Value |
| --- | --- | --- |
| Variable | `ATLAS_SCHEDULE_ENABLED` | `true` after a successful small trial |
| Variable | `ATLAS_STATE_REPO` | `owner/private-state-repository` |
| Variable | `ATLAS_PROVIDER` | `none` for editorial extraction or `openai` |
| Variable | `ATLAS_MODEL` | Model ID available to the API project |
| Secret | `ATLAS_STATE_TOKEN` | Fine-grained token with metadata read and contents read/write for the private state repository |
| Secret | `OPENAI_API_KEY` | Extraction API project key when enabled |

The weekly workflow verifies the state repository's privacy, checks out code and state separately, installs pins, runs the workflow, and saves and commits the operational state. Draft reports based on collected sources and raw evidence stay in the private repository. The public Actions summary contains an execution receipt, report date, and private state location. The file is scheduled for Wednesday 08:37 Europe/Amsterdam; GitHub's actual delivery and the recorded cutoff determine when collection takes place. `workflow_dispatch` supports a manual catch-up run.

Use the private state's latest report for the group scan. Its Markdown can be viewed in GitHub, and `dataset.zip` contains a locally viewable HTML report and analysis files. Review the source-coverage table before interpreting the briefing.

## Editorial loop on private state
Clone or pull the private state into `.runtime-state/`. Run `review-export`, inspect the captured sources, edit decisions, and use `review-apply`. Apply any relationships and opportunity updates. Seal the Wednesday report date, check the output, and create an approval manifest when distribution is intended. Commit and push the updated private state before another scheduled run. Coordinate editorial pushes with the single deployment writer.

## Prepare structured research outputs

Before carrying geographic annotations into a weekly or historical run, follow [Link reassessment](LINK_REASSESSMENT.md). Keep its private plan, candidate references, adjudications and validation receipt with the run. The current runner retains annotated records; remove invalidated derivatives only from a fresh working copy and preserve their history before reassessment. Completion requires accounting for pending relationship reviews as well as processed reports.

Use `atlas handoff --cycle CYCLE` to generate the private [publication handoff](PUBLICATION_HANDOFF.md) after the three job receipts are complete. Consumers regenerate it before each sync and check the exact cycle, ready status, export identity and asset hashes. The command also supports a separately labelled initial-publication candidate without creating weekly completion. Typed consumer interfaces are supplied in `types/atlas.d.ts`.

Use `atlas metrics` to prepare scoped measurements from saved selections and annotations, then `atlas site-export` to package the [structured research bundle](SITE_EXPORT.md). These commands process captured evidence locally. The annotation files, source snapshot, acquisition results and metric export must refer to the same records. Keep raw sources and authored review inputs in private storage.

Write each export to an empty directory and run `atlas site-verify` before analytical reuse or application loading. Retain the bundle manifest, software version, input hashes and a receipt of checks actually executed. Review pending candidates, geographic gaps and unresolved comparisons alongside the figures. A schema-valid research preview still carries its stated editorial review status.

Supply the weekly workflow file when exporting schedule metadata. The next planned collection date is calculated from the snapshot's latest capture and the declared timezone. The metadata records scheduler activation as unverified; operational checks establish whether a scheduled run actually occurred. Publication depends on editorial review and approval.

### Partial datasets for interface testing

A validated partial dataset can support local interface development while evidence review is paused. Finish in-flight calls, hold further dispatch, and export the completed annotations into a separate directory. Retain the full record inventory and an entry-level worklist distinguishing source review, annotation completion and pending scientific questions. Record the exact snapshot, manifest, selector and type hashes, executed checks, resource usage and resume instructions alongside the bundle.

Label the handoff as a partial local test candidate. The consumer can test panels, filters and evidence displays against that fixed export. Keep the adopted dataset and public pointer intact. Partial coverage does not complete a weekly job or authorize publication; unprocessed entries remain pending until review resumes.

## Approved public distribution
The `publish-approved.yml` workflow reads a bundle and approval from private state, verifies their matching hashes, and creates a GitHub release containing the complete dataset and approval. Create a GitHub environment named `outbreak-publication` with required reviewers. The publishing job uses contents-write permission only for that operation. The workflow validates submitted paths against the private state directory before copying output.

The CLI approval records a named editor and exact bundle hash; repository permissions and the protected publication environment establish approval authority. Approval JSON is a content-bound receipt rather than a cryptographic identity signature. A revised report gets its own receipt. The canonical report keeps the editorial state it had when sealed; distribute its approval sidecar with it.

## Budgets and source checks
Defaults limit each source to 18 documents per run, each response to 16 MB, extraction attempts to 36, and source input to 650,000 characters. The API provider requests at most 10,000 output tokens per call. The Codex provider allows 1,200 seconds per invocation and accepts a final JSON file up to 1,000,000 bytes, configured through `codex_timeout_seconds` and `codex_output_bytes` under `limits`.

For Codex, `max_model_calls` counts CLI invocations, not internal model requests; the CLI can make multiple requests in one invocation. The byte limit validates the returned JSON and is not a token spending cap. Subscription limits still apply. API cost depends on model pricing and usage; set the API project's spending limit separately. Begin with a two-attempt budget and compare extracted claims with source text. Failed and budget-exhausted chunks remain in the extraction queue. Preserve the result file and event log when a review fails. Separate a missing model response from a schema or evidence-reference error in a completed response. A recorded source review can repair a reference or encoding error without another model call; retain the original output and validate the derived result. For a timeout, inspect connection errors and input/output size before assigning a bounded retry. Report unavailable usage for interrupted calls as unknown.

Review core-source failures, extraction backlog, stale source publication dates, contradictory totals, and ambiguous identity matches each Wednesday. `documents_with_some_extraction` indicates that at least one extraction exists; chunk tasks and the extraction-run receipt provide completion detail. An image-only PDF page enters layout review. Editors also inspect visually complex PDF tables where native text order may be misleading.

## Recovery and maintenance
For missing downloads and incomplete articles, follow [Source recovery](SOURCE_RECOVERY.md). Record host-specific failures and retry times, use documented access routes, and preserve partial captures. A connected Consensus plugin is required for the Consensus literature-discovery branch; standard configured collection uses the package's source adapters.

Back up the private repository and separately retain approved bundles. Each model attempt appends its start and outcome to the ledger. Codex diagnostics remain in `extraction_attempts/`; `review/extraction_progress.json` records active work, completed chunks, failures, and the latest error. Check completed chunks and attempt outcomes to assess extraction progress. After an interruption, regenerate the queue from saved evidence before interpreting its remaining count.

After a failed run, inspect the ledger, retained attempt diagnostics, source checks, extraction tasks, and receipt. Successful captured objects and model caches are reusable. Re-run only after understanding the failure and the actual budget consumed. If no completed date receipt exists, a retry resumes from the persisted evidence and caches; new collection may still make requests. Protect against missed state commits by checking that the private branch advanced.

Scheduled runs can be delayed or skipped by their hosting platform. Monitor Actions failure notifications and the last successful report date; manual dispatch is the recovery route. Configure organization-level alerts for a missing Wednesday artifact where available. The alpha does not install a separate external heartbeat service.

For a state restore, clone to a fresh directory, run ledger verification, verify the latest report bundle, and reproduce it from sealed JSON. For a code update, create a pull request, run tests, review schema diffs, compare a frozen replay, run a small collection trial, then deploy. Keep event keys stable. Versioned state migrations and large-scale object storage are roadmap items; back up state before experimental-version upgrades.

### Large annotation files

`atlas metrics --max-annotation-bytes N` sets the annotation file allowance for one local export. The default is 16,000,000 bytes; the maximum is 64,000,000 bytes. Record the chosen allowance and input size in the run receipt. Use compact JSON first and verify that it reconstructs the complete annotation object. This allowance does not affect source retrieval, model calls or the export contract.

`atlas site-export --max-input-bytes N` sets the per-file allowance for prepared local inputs. The default is 64,000,000 bytes; the maximum is 128,000,000 bytes. Record the chosen limit and actual input sizes in the run receipt. Use compact JSON with exact object reconstruction before increasing the allowance. Source retrieval, model input and model call budgets have separate limits.
