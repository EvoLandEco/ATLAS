# Operations

## Local state
Run commands from the repository root. Global `--config PATH` and `--state PATH` options precede the subcommand. The default state is `.runtime-state/`. `ledger.sqlite` contains the append-only history; `objects/` contains captured bytes and text; `extractions/` stores model-response caches; `review/` contains editorial tasks; `reports/DATE/ID/` contains sealed outputs; `latest.json` points to the most recently sealed bundle.

`epiweekly run` collects, extracts within budget, exports the review queue, and seals a draft. A completed run receipt prevents a repeated automatic invocation for the same local date from repeating acquisition. `--force` explicitly starts a fresh acquisition. `seal` recomputes from recorded evidence and decisions without collecting again. Editorial revisions for the same date compare with the latest sealed report on an earlier date.

The initial report has all selected events labeled `new_to_registry`. Seed an initial lookback through collection and review, then begin weekly comparisons. Historical data imported later retain their actual capture time.

## Local subscription runs

Install Codex CLI and run `codex login` with ChatGPT on the machine that runs EpiWeekly. Confirm the account with `codex login status`. The `codex` provider requires ChatGPT authentication and excludes API key environment variables from the subprocess. Credentials remain in Codex's credential store.

```bash
export EPIWEEKLY_PROVIDER=codex
epiweekly run
```

`--model MODEL_ID` or `EPIWEEKLY_MODEL` selects a model available to that account. An empty model setting uses the Codex CLI default. EpiWeekly ignores user Codex configuration so project tools, hooks, and connected services do not participate in extraction. Use a current CLI supporting `exec --ignore-user-config --ephemeral --output-schema`.

The same command can run through a local scheduler under the signed-in user. The machine must be awake and connected. Configure the scheduler's working directory as the repository root and make both `.venv/bin` and the Codex executable available on its PATH. No local schedule is installed by the package.

The supplied GitHub workflow supports `none` and `openai`; it does not provision subscription credentials. Keep ChatGPT credentials out of the public code repository and its Actions secrets. See [Codex automation authentication](https://learn.chatgpt.com/docs/non-interactive-mode) for account and runner requirements.

## Private deployment repository
Create a dedicated private repository for state, initialized with a README. Keep its access restricted to the operating group. Its default branch is the persistence branch; use one scheduled deployment writer for that branch. The public code repository can host the reusable implementation and approved published datasets.

Configure these values in the code repository:

| Kind | Name | Value |
| --- | --- | --- |
| Variable | `EPIWEEKLY_SCHEDULE_ENABLED` | `true` after canary acceptance |
| Variable | `EPIWEEKLY_STATE_REPO` | `owner/private-state-repository` |
| Variable | `EPIWEEKLY_PROVIDER` | `none` for editorial extraction or `openai` |
| Variable | `EPIWEEKLY_MODEL` | Model ID available to the API project |
| Secret | `EPIWEEKLY_STATE_TOKEN` | Fine-grained token with metadata read and contents read/write for the private state repository |
| Secret | `OPENAI_API_KEY` | Extraction API project key when enabled |

The weekly workflow verifies the state repository's privacy, checks out code and state separately, installs pins, runs the workflow, and commits the updated state. Draft source-derived reports and raw evidence stay in the private repository. The public Actions summary contains an execution receipt, report date, and private state location. The file is scheduled for Wednesday 08:37 Europe/Amsterdam; GitHub's actual delivery and the recorded cutoff determine the realized acquisition time. `workflow_dispatch` supports a manual catch-up run.

Use the private state's latest report for the group scan. Its Markdown can be viewed in GitHub, and `dataset.zip` contains a locally viewable HTML report and analysis files. Review the source-coverage table before interpreting the briefing.

## Editorial loop on private state
Clone or pull the private state into `.runtime-state/`. Run `review-export`, inspect the captured sources, edit decisions, and use `review-apply`. Apply any relationships and opportunity updates. Seal the Wednesday report date, check the output, and create an approval manifest when distribution is intended. Commit and push the updated private state before another scheduled run. Coordinate editorial pushes with the single deployment writer.

## Approved public distribution
The `publish-approved.yml` workflow reads a bundle and approval from private state, verifies their matching hashes, and creates a GitHub release containing the complete dataset and approval. Create a GitHub environment named `outbreak-publication` with required reviewers. The publishing job uses contents-write permission only for that operation. The workflow validates submitted paths against the private state directory before copying output.

The CLI approval records a named editor and exact bundle hash; repository permissions and the protected publication environment establish approval authority. Approval JSON is a content-bound receipt rather than a cryptographic identity signature. A revised report gets its own receipt. The canonical report keeps the editorial state it had when sealed; distribute its approval sidecar with it.

## Budgets and source checks
Defaults limit each source to 18 documents per run, each response to 16 MB, extraction attempts to 36, and source input to 650,000 characters. The API provider requests at most 10,000 output tokens per call. The Codex provider allows 180 seconds per invocation and accepts a final JSON file up to 1,000,000 bytes, configured through `codex_timeout_seconds` and `codex_output_bytes` under `limits`.

For Codex, `max_model_calls` counts CLI invocations, not internal model requests; the CLI can make multiple requests in one invocation. The byte limit validates the returned JSON and is not a token spending cap. Subscription limits still apply. API cost depends on model pricing and usage; set the API project's spending limit separately. Begin with a two-attempt budget and compare extracted claims with source text. Failed and budget-exhausted chunks remain in the extraction queue.

Review core-source failures, extraction backlog, stale source publication dates, contradictory totals, and ambiguous identity matches each Wednesday. `documents_with_some_extraction` indicates that at least one extraction exists; chunk tasks and the extraction-run receipt provide completion detail. An image-only PDF page enters layout review. Editors also inspect visually complex PDF tables where native text order may be misleading.

## Recovery and maintenance
Back up the private repository and separately retain approved bundles. After a failed run, inspect the last committed ledger, source checks, extraction tasks, and receipt. Successful captured objects and model caches are reusable. Re-run only after understanding the failure and the actual budget consumed. If no completed date receipt exists, a retry resumes from the persisted evidence and caches; new collection may still make requests. Protect against missed state commits by checking that the private branch advanced.

Scheduled runs can be delayed or skipped by their hosting platform. Monitor Actions failure notifications and the last successful report date; manual dispatch is the recovery route. Configure organization-level alerts for a missing Wednesday artifact where available. The alpha does not install a separate external heartbeat service.

For a state restore, clone to a fresh directory, run ledger verification, verify the latest report bundle, and reproduce it from sealed JSON. For a code update, create a pull request, run tests, review schema diffs, compare a frozen replay, run a low-budget source canary, then deploy. Keep event keys stable. Versioned state migrations and large-scale object storage are roadmap items; back up state before experimental-version upgrades.
