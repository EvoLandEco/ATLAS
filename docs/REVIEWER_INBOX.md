# Hosted reviewer inbox

The reviewer service provides an internal inbox whose address and access details are shared within the review team. Cloudflare Access authenticates reviewers, a Worker serves the interface and API, D1 records issue versions and decisions, and a private R2 bucket holds captured source text.

The hosted service remains available while the ATLAS runner is offline. Scientific application waits for the runner. ATLAS retains the scientific ledger, source interpretation, validation and publication approvals. The service records reviewer instructions and their application receipts.

## Contract 1.0.0

`atlas schemas` writes five contracts: `inbox`, `inbox-decision`, `inbox-decisions`, `inbox-receipts` and `inbox-supplement`. Each schema file ends in `.schema.json`.

An issue has a stable identifier, an exact revision hash, a review type, question, impact, affected identifiers, dependency hashes and captured evidence. Publication, capture, first-seen and issue-change times have separate fields. Evidence identifies its source, publication date, capture time, SHA-256, byte count and exact quotations. Packets contain references to private UTF-8 text objects; local paths stay in the producer archive.

Registry issues cover every pending dated candidate, including historical candidates. Their revision covers the current candidate review, event suggestions, supporting reviews and captured versions of the same publication. A changed dependency invalidates a decision against an earlier revision. Missing publication dates exclude a report from the review packet.

Other scientific workflows supply `inbox-supplement` packets. Each packet includes source text and issue records for geography, numerical comparisons, chains, One Health, extraction, sources or research. The producer verifies source host allowlists, byte hashes and exact quotations before registration. The supplying workflow owns the interpretation and dependency references. It must register a changed revision whenever those dependencies change. Omitting an issue from a later supplement leaves it pending.

Source text uploads use content hashes. D1 retains immutable issue versions, decisions and receipts. A packet identifies the complete active issue set. Its sequence comes from the producer ledger, and a lower sequence cannot replace a later packet. Removed issues retain their decision history. The producer checks its canonical snapshot hash; the service also records a checksum of its received JSON representation.

Limits are explicit: 200 issues per packet, 8 MB per JSON transfer, 16 MB per evidence object, 40 source references per issue and 200 decisions per synchronization pass. Oversized packets fail without truncation. Use a Workers plan whose D1 query allowance supports these bounds. No raw source object, private packet, decision file or operational database belongs in the public repository.

## Decisions and receipts

Reviewers submit `accept`, `reject` or `defer` for registry candidates. Acceptance retains the existing event-key, supersession, disease-reclassification and numeric-evidence requirements. Other review types accept an exact scientific instruction or a deferral. Instructions enter their named ATLAS review workflow; they do not execute shell commands or modify annotation files through the website.

The service supplies the authenticated reviewer and submission time. A decision names its packet, issue revision, predecessor decision and unique decision ID. Concurrent submissions require a fresh review of the issue. A decision awaiting application or validation cannot be silently superseded.

| Status | Meaning |
| --- | --- |
| Submitted | The service saved the decision; ATLAS has not returned a receipt. |
| Recorded | ATLAS retained a scientific instruction; application remains pending. |
| Applied | ATLAS wrote the registry review; affected output validation remains pending. |
| Deferred | A scientific question remains pending by explicit decision. |
| Stale | Evidence or editorial context changed before application. |
| Invalid | ATLAS rejected the decision and retained its reason. |
| Completed | The producer recorded completion against an exact validated output. |

ATLAS commits a registry review and its receipt in one database transaction. Repeated imports return the recorded receipt, including after later editorial work. A changed payload cannot reuse the same decision ID. Application receipts precede completion receipts during synchronization. Decision and receipt history remain available after an issue leaves the active packet.

`inbox-complete` is a producer attestation after the named scientific work and affected-output checks. For a registry decision, it verifies a sealed report created after application and checks that the relevant review remains current. For other workflows, it verifies the structured export and its exact map snapshot and checks the registered issue revision. Scientific validation does not approve public distribution.

## Producer commands

Run from the ATLAS checkout with its Python environment active. Keep one writer for the archive.

```bash
atlas --state .runtime-state inbox-export \
  --archive-id atlas --out .local/inbox/packet-001

atlas --state .runtime-state inbox-export \
  --archive-id atlas --issues .local/review-issues.json \
  --out .local/inbox/packet-002
```

The output directory must be empty. A packet contains `inbox.json` and `evidence/HASH.txt`. The export records its exact packet in the private ledger. Reuse these saved files when retrying an upload.

Set `ATLAS_INBOX_URL`, `ATLAS_INBOX_CLIENT_ID` and `ATLAS_INBOX_CLIENT_SECRET` through the runner's environment or secret store. The URL identifies the internal inbox, including its path. The client uses HTTPS and rejects redirects. Keep deployment addresses in private settings and the service secret out of shell history and logs.

```bash
atlas inbox-push .local/inbox/packet-002/inbox.json
atlas --state .runtime-state inbox-sync
```

`inbox-sync` imports up to 200 submitted decisions and sends application and completion receipts. Run it again if more submitted decisions remain. It performs no acquisition, extraction, sealing or publication. The command reports instructions awaiting application and registry edits awaiting output validation.

For a file-based review exchange:

```bash
atlas --state .runtime-state inbox-import .local/decisions.json \
  --out .local/application-receipts.json
```

After a registry decision, seal and check the affected report date, then record completion:

```bash
atlas --state .runtime-state seal --report-date 2026-10-14
atlas --state .runtime-state inbox-complete DECISION_ID \
  --bundle .runtime-state/reports/DATE/REPORT_ID \
  --note 'Reviewed the affected findings and validated the sealed report.' \
  --out .local/completion-receipt.json
```

For an instruction handled by a geographic, numerical or other scientific workflow, finish that workflow and its affected outputs, then use `inbox-complete` with both `--bundle STRUCTURED_EXPORT` and `--snapshot EXACT_MAP_SNAPSHOT`. Supply a note describing the work performed. Synchronize receipts and export a fresh packet after processing decisions.

The weekly inbox job synchronizes decisions before building its completion receipt. Record unapplied instructions and pending output checks in `unapplied_decision_ids`. A stored decision changes the ledger head, so earlier weekly handoffs require validation against their resulting outputs. Follow the existing weekly receipt and publication requirements.

## Cloudflare deployment

Use Node.js 24 or later. From `backstage/`:

```bash
npm ci
npm test
npm run check
```

Deployment needs access to the Cloudflare account serving the inbox: Workers scripts, D1 and R2. Cloudflare Access application, policy and service-token administration is required for access setup. Scope deployment credentials to this account. The runtime receives bindings and Access identifiers, not a Cloudflare management token.

1. Create a D1 database named `atlas-reviewer-inbox` and a private R2 bucket named `atlas-review-evidence`. Leave R2 public access disabled and attach no public bucket domain.
2. Create a Cloudflare Access self-hosted application covering the internal inbox hostname and all paths. Allow the review team's approved email addresses through the configured identity provider and use the same list in `REVIEWER_EMAILS`. Create a service token and a **Service Auth** policy for the ATLAS runner in that same application. Keep the token's secret in the runner's secret store.
3. Supply `CLOUDFLARE_ACCOUNT_ID`, `ATLAS_INBOX_DATABASE_ID`, `INBOX_ORIGIN`, `ACCESS_ISSUER`, `ACCESS_AUD` and `SYNC_SERVICE_TOKEN_ID` as environment variables. `INBOX_ORIGIN` is the internal HTTPS origin without a path or trailing slash. The issuer is `https://TEAM.cloudflareaccess.com`; the audience is the application's AUD value; the service token ID is its Client ID. Run `node configure.mjs` to write the ignored `wrangler.local.json`. It contains deployment identifiers and the internal address, not authentication secrets.
4. Apply the migration and deploy:

```bash
npx wrangler d1 migrations apply atlas-reviewer-inbox --remote --config wrangler.local.json
npm run deploy
```

The service uses the protected `workers.dev` hostname with preview URLs disabled. The Worker accepts `/atlas/review/` and its descendants. The interface uses the ATLAS logo, self-hosted Geist fonts, shared color values and light and dark themes. A route on `qtj.me` requires that domain to be proxied through Cloudflare; its DNS remains managed separately. Every request, including static assets and evidence downloads, requires a verified Access JWT. Human requests require membership in `REVIEWER_EMAILS`; synchronization requires the named service identity. Browser writes require the configured origin and review header. Responses use private no-store caching and a restrictive content policy.

The Reports panel opens Cloudflare sign-in in a separate window and embeds the authenticated reviewer interface. Cloudflare Access must allow iframe use and set its application cookie to `SameSite=None` with `HttpOnly` enabled. The Worker limits framing to `https://qtj.me`; review requests require their own origin and the review header. The sign-in window sends a completion signal to ATLAS without credentials or reviewer data. The enclosing page checks the sender's origin and window, then exchanges theme, readiness and Close messages with the embedded interface. The loaded portal uses one toolbar for navigation, search, filters, account and Close. Browsers that block cross-site cookies can prevent the portal from loading. Closing the panel restores the report view and preserves an unsubmitted draft for the current page session.

Before loading research data, check that an unauthenticated request is denied, the named reviewer can sign in, another identity is denied, and the service token can synchronize a synthetic packet but cannot submit human decisions. Then upload the selected private research packet. Keep D1 recovery and periodic database exports configured according to the account's retention policy; retain the producer ledger and packet archive independently.

## Validation

The Python tests cover historical evidence, source revisions, exact decision binding, stale reviews, repeated imports, interruption rollback, supplemental questions and completion checks. Service tests cover JWT verification, permissions, request bounds, same-origin writes, concurrent submissions and immutable receipt transitions. The integration test runs the bundled Worker in Cloudflare's local runtime with D1 and R2, using a packet exported by Python and receipts imported back into ATLAS.

`node backstage/tests/preview.mjs` serves disposable synthetic evidence on loopback for browser inspection. Its test identity exists only in the preview process. Stop it with Ctrl-C. Production authentication has no preview bypass.

Live deployment, identity-provider sign-in, cloud backup restoration and production synchronization require checks in the configured Cloudflare account. Local runtime checks do not establish those outcomes.
