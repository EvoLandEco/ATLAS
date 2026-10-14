# English presentation of source text

Source text contract 0.1.0 supplies English titles and quotation translations as a separate presentation export. It binds the scientific export ID, site checksum, manifest checksum and map snapshot checksum. Site 1.8.0, metrics 0.4.0 and browser transport 0.3.0 retain their scientific definitions and selection rules.

Original titles, quotations, offsets, evidence IDs and attribution remain in the scientific bundle. The presentation export contains language reviews and translations. It creates no assertions, measurements, diagnoses, geographic links or event identities.

## Identity and provenance

`texts` accounts for every document title, report-entry title and evidence span. Each row has a stable `id`, a `kind` (`document_title`, `record_title` or `evidence`) and the exact original `target_ids`. Evidence rows with the same document, source hash, text hash and offsets share one text identity, even when several scientific sections cite them. Different occurrences and different documents retain distinct identities. Report-entry titles and publisher titles have separate bindings.

The original text is read from the bound scientific entity. `original_text_sha256` uses UTF-8 bytes. `source_text_sha256` binds the captured document. Quotations also retain their original Unicode offsets. A changed source or title requires its own text review.

`english_translation_id` points to one row in `translations`. That row names its `original_text_id`, English text, creation time, creator, method version and review status. Creation time records preparation of the translation record; the source publication and capture times remain in the scientific export. An ID includes the translation content and provenance. Keep sealed text exports and their annotation inputs as the history of revisions.

`origin` distinguishes `atlas_generated` from `publisher_provided`. An ATLAS translation preserves source statements, uncertainty, negation, attribution, numerical bounds and dates. Its review status is `unreviewed` until a recorded comparison with the original has been completed. `source_checked` records that comparison; `human_approved` requires an actual named human review. A model's own drafting pass is not human approval.

A publisher translation requires the exact captured English text identity, the same publisher, evidence of the original-to-English pairing, and a completed review. An English report about the same event cannot establish that pairing. An English link label alone does not establish an English translation of the linked article. The validator checks source identities and exact English text; the reviewer checks the meaning and the publisher's pairing statement.

## Language and coverage

`language_tag` uses a lowercase ISO 639 language code as a BCP 47 primary language tag, such as `nl`, `ru` or `en`. `mul` denotes a text with multiple languages. `und` denotes undetermined language. Region subtags are outside this contract. Record the basis, reason, reviewer and time for each exact text. The language of a title does not automatically establish the language of every quotation.

Rows awaiting language review carry `und`, `language_status: not_reviewed` and a reason. A reviewed uncertainty carries `language_status: unresolved`. English originals have `translation_status: not_required`; identified non-English originals awaiting translation have `pending`. `available` means a translation record exists and retains its independent review status.

Coverage counts distinct original texts and their evidence and title bindings. All original bindings must be present, including untranslated and unreviewed text. Completeness of this catalogue does not mean that language review or translation review is complete.

Languages are not countries. Use a language name or code for a badge. Source-country metadata is not part of this contract; the geographic memberships in the scientific bundle describe the reviewed reporting locations and roles. They do not identify a publisher's country or a quotation's language. Do not infer a flag from a language tag, domain name or epidemiological location.

## Producer workflow

1. Verify the exact scientific bundle and snapshot. Build the catalogue with `atlas.source_text.text_catalog(site)`. It returns binding rows and their original text for the private review packet.
2. Inspect the title or quotation in its captured context. Save language reviews and translations in a private `TextAnnotations` document. Reuse reviews by exact text ID; record stale or absent IDs in the work receipt instead of silently applying them to another source.
3. Reuse daily reviews with `atlas.source_text.reuse_daily_reviews(site, annotations, daily_reviews, daily_documents)`. Match document identity, source hash, exact title or quotation and quotation offsets. A retained language review without a translation still needs this check. Preserve completed translations and their recorded provenance; investigate conflicting language reviews. Record reused text IDs and daily review hashes.
4. For overlapping quotations, a private packet may partition source text at every quoted boundary. Translate each exact segment in context, retain its original offsets, and require lossless reconstruction of every original quotation before assembling its English translation. This is a text preparation method, not a new scientific extraction. Preserve the segment packet for review.
5. Check attribution, negation, uncertainty, names, units, numerical bounds and dates in the complete assembled quotations. Keep formatting and numerical inventory checks separate from semantic review. A title summary or an extracted finding cannot stand in for a translation of the original quotation.
6. Build and verify an empty presentation directory:

```bash
atlas text-export --bundle RELEASE/structured --snapshot RELEASE/snapshot.json \
  --annotations PRIVATE/text-annotations.json --out RELEASE/source-text
atlas text-verify --bundle RELEASE/structured --snapshot RELEASE/snapshot.json \
  --presentation RELEASE/source-text
```

`atlas schemas` writes `source-text.schema.json` and `text-annotations.schema.json`. Annotation input is bounded to 16 MB. The commands reuse captured material and make no retrieval or model calls. A changed translation method requires a version and comparison on retained source text. Private translation generation must use bounded, tool-free input and output, with model identity and usage recorded when available.

During weekly review, inspect language and translation dependencies for changed titles or evidence. During production and historical expansion, catalogue added text, reuse exact reviews, and account for pending translations. Text-only preparation preserves the sealed scientific bundle and its geographic preview; verify their matching identity and full date extent in the handoff. A scientific source correction follows the scientific review and export workflow.

## Consumer integration

Verify the descriptor's byte counts and checksums, the schema and the exact `source_export_id` before use. Load this sidecar alongside the scientific release. It is independent of browser transport. Index the explicit original bindings and translation IDs:

```js
const translations = new Map(text.translations.map(t => [t.id, t]));
const originalBindings = new Map(text.texts.flatMap(t =>
  t.target_ids.map(id => [`${t.kind}:${id}`, t])));
const presentation = (kind, id) => {
  const original = originalBindings.get(`${kind}:${id}`);
  return {original, english: translations.get(original?.english_translation_id)};
};
```

Resolve a publisher title with `document_title:<document_id>`, an entry title with `record_title:<record_id>` and a quotation with `evidence:<evidence_id>`. The browser detail evidence retains the same IDs. This lookup serves reports, report assessments, comparisons, geographic relationships, reviewed chains and One Health panels. Follow their assertion and evidence references; never match translations by quotation text, disease, country or display order. Method evidence embedded in `metrics.reviewed_series` has its own identities and is outside this catalogue.

Show an English title with the original title available beside it. For a non-English quotation, show the original followed immediately by its bound English text. Give both a language label and connect the pair visually. Use `lang` attributes and accessible labels such as “Original quotation in Dutch” and “English translation, ATLAS draft”; a visual line alone does not express the relationship. Render translation text as plain text. The source link and attribution belong to the pair. Label publisher English and ATLAS translation distinctly, including draft status.

Attach translations only after the original is eligible under the scientific selector. Translation creation and review times do not change publication windows, knowledge cutoffs, report counts or confirmation status. A translation can clarify selected historical text without claiming to reconstruct a historical editorial state. Unselected source text cannot become visible through a translation lookup. Missing translations retain the original and their recorded pending state.

The handoff includes the text manifest and all file hashes, coverage, review limitations and the unchanged scientific export reference. Consumer delivery and adoption have separate receipts. Local preparation does not authorize publication.

## Compact browser presentation

Text display contract 0.1.1 is a verified projection of the complete text export. It retains every translation and every reviewed or unresolved text row, including all original IDs, language provenance, source hashes and translation review status. It omits only rows whose `language_status` is `not_reviewed`; the declared state for an unlisted, valid original in this catalogue is `und`, `not_reviewed`, `language_unresolved`, with its stated reason. This omission has no scientific meaning and does not establish English as the language.

`texts` and `translations` keep their complete parent fields. `full_coverage`, `omitted_text_count` and `omission_rule` account for the projection. `source_text_sha256` binds the complete parent file. `catalogue_scope` restricts the declared unlisted state to site document titles, record titles and scientific evidence quotations.

`claim_bindings` supplies exact lookup for map claims and metric evidence references. Each row names `record_id`, `claim_index`, `quote_index`, `evidence_ids`, `text_id` and `status`. Bindings come from the scientific evidence fields and the bound map snapshot. Contract 0.1.1 compares the original snapshot quotation only with evidence under the same explicit record, claim and quotation indexes. If exact text matches resolve one source text identity, the `bound` row names that identity and only its evidence IDs. Other occurrences remain in the scientific evidence and complete text catalogue. If exact matches resolve several source occurrences, all candidate references remain with `ambiguous_source_spans` and a null `text_id`. When there is no exact match, a single explicit source span can still bind; several spans remain ambiguous. No source is selected by whitespace normalization or text similarity. Sealed contract 0.1.0 uses all explicit claim references and retains ambiguity whenever they resolve several source text identities. Claim tuples with only unreviewed language rows follow the same declared unlisted state.

```js
const claims = new Map(display.claim_bindings.map(b =>
  [JSON.stringify([b.record_id, b.claim_index, b.quote_index]), b]));
```

`unmapped_scopes` explicitly lists embedded series method evidence and the undated supplement. Their source quotations remain available through their own contracts, but they have no bindings in this projection. Do not reuse the site's lookup by matching their text or infer their language. The complete presentation export also excludes these scopes.

```bash
atlas text-display-export --bundle RELEASE/structured --snapshot RELEASE/snapshot.json \
  --presentation RELEASE/source-text --out RELEASE/source-text-display
atlas text-display-verify --bundle RELEASE/structured --snapshot RELEASE/snapshot.json \
  --presentation RELEASE/source-text --display RELEASE/source-text-display
```

The independent verifier checks the complete parent export, scientific source, exact retained rows, translations, claim bindings and omissions. The compact file has its own schema, manifest and validation receipt. Browsers can load it without retaining the full text catalogue. The full parent remains the audit artifact. ATLAS-generated translations may be rendered before independent bilingual review when they retain the original text and their explicit draft label; rendering does not promote their review status or authorize public activation.

## Completion accounting

Scientific preparation and English presentation have separate completion records. Before claiming complete English presentation, account for every title and quotation in the exact catalogue by kind, publisher, language, translation availability and review status. List missing translations, unresolved languages and unreviewed drafts with their exact text IDs. Structural export validation confirms bindings and provenance; it does not establish translation completeness or bilingual review. Require zero pending translations and unresolved languages for a complete presentation claim, and zero unreviewed translations for a completed bilingual review claim. Preserve unresolved text and explicit partial status when those checks fail.
