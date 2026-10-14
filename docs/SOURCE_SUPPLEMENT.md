# Private source evidence

Reports require a source-supported publication, issue or release date. Documents without that date remain outside extraction, workflow review queues, public report exports, counts and watch selections. Private captures and review history retain `missing_publication_date` exclusions. Capture timestamps and dates in source URLs do not establish publication. Public handoffs omit source supplements and their collections.

Notification, sampling and surveillance datasets retain their own date fields, exact evidence and missingness states. A notification date or observation period does not establish a report publication date. Their use requires a contract matching the represented observations.

## Retained evidence format

Source supplement 0.1.0 preserves captured evidence whose publication date is not reported. Each document retains publisher, title, source and content URLs, capture timestamp, raw object hash and text hash. Publication remains null with status `not_reported`. Claims reference complete quotations with source text offsets and hashes. Measurements retain their metric fields and exact claim references. Review timestamps and disclosures accompany each record.

`atlas.source_supplement.validate_supplement` verifies identities, quotation hashes, offsets, measurement anchors and revision dependencies. With `source_dir`, it compares quotations and text hashes against captured sources. These checks establish artifact integrity; they do not establish report eligibility.

## Private collections

Source supplement collection 0.1.0 binds distinct evidence files to a scientific export reference for private audit. The catalogue retains document metadata and record summaries. Each component preserves exact bytes, document and record identities, schemas, checksums and counts. The format accepts at most 128 components, 16 MB per component and 128 MB in total.

```bash
atlas supplement-collection --source-export-id EXPORT_ID \
  --supplement first/source-supplement.json --supplement second/source-supplement.json \
  --source-dir captured-text --out private-collection
atlas supplement-collection-verify private-collection --source-dir captured-text
```

Verification checks payloads, schemas, component identities, totals and catalogue rows. Missing files, duplicate identities and different export bindings are errors. Captured-source verification also checks exact offsets and hashes. Collection generation requires captured sources; verification records whether those sources were checked. The export reference identifies the audit context and does not authorize public inclusion.
