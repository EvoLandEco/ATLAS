# Reassessing links as the archive grows

Use this procedure for historical expansion, weekly production, source corrections and editorial decisions. Its unit of work is an evidence assessment, not every possible pair of reports. Unchanged evidence retains its recorded assessment; new evidence can trigger a separate review of the relationship it concerns.

This is an agent operating procedure using captured sources, saved annotations and the export tools. The geography scripts validate individual assessments and coverage. They do not discover historical dependencies, invalidate retained annotations or resolve competing interpretations automatically. Keep the run plan and decisions in private storage; the public export contracts retain their definitions.

## 1. Establish the comparison

Read the last validated export, its exact snapshot, source versions, annotations, adjudications and unresolved queue. Record the export ID, ledger head, requested publication interval and capture cutoff. Separate three sets:

- New publications or historical publications captured for the first time.
- Changed source versions, metadata, extracted claims, decisions or interpretation rules.
- Unchanged records with reusable assessments.

Compare source content hashes and interpretation metadata, including canonical publication identity, title and publication date. Retrieval failures are unchecked sources. A report leaving the selected display window is not a withdrawal. Preserve every capture and the original assessment inputs.

Before model calls, save a private run plan under `.local/link-review/RUN/`. For weekly jobs, reference it from `.runtime-state/weekly/CYCLE/`; historical runs reference it from their own receipt. Include the baseline export, input hashes, trigger for each selected record or relationship, relevant historical evidence, expected model work and pending decisions. Use a work key computed from the sorted input record/version references, candidate-set hashes, relevant decision IDs and method fingerprint. A run date alone does not justify another call. Record the reviewer, review time, disposition and output hash separately from that input key.

## 2. Separate source assessment from relationship review

**Source assessment** asks what a particular captured report says. Reuse it when the record, source text, interpretation metadata and assessment method match. Preserve negative outcomes such as no specific location and no stated relationship. A larger archive does not change the words in that report.

**Relationship review** asks how that statement relates to other captured evidence. Its inputs include supporting and opposing statements, explicit source references, reviewed episode assignments and relevant decisions. Repeat this review when those inputs change, even if every individual source assessment is cached.

Do not interpret `retained_review` as a completed historical comparison. The runner skips records present in the supplied location annotations. Cache fingerprints cover the supplied record, source text, prompt, schema and review version, with `codex-default` as the model label; they do not prove the identity of the model selected by the provider. Keep the original provider receipt. Reusing an unchanged saved result requires no call to the current model. A method comparison needs a recorded model identity or an explicit statement that it is unavailable.

Record a separate method fingerprint for relationship review: relationship rules, prompt, schema, vocabulary, normalization rules, software version and model identity when available. Keep coordinate-reference changes separate: moving a country reference point requires a map rebuild, not reinterpretation of a source statement. A retained assessment stays attributed to the method that produced it. A changed scientific rule requires a versioned evaluation and review of every assessment that used that rule. If its affected scope cannot be established, review the full relevant assessment set.

## 3. Find the affected evidence

Build lookups from the saved record, claim, quotation and relationship references. Establish a baseline catalogue of explicit source references and investigation/exposure keys once, recording which reports have been inspected. Extend it for new or changed records; do not claim archive-wide candidate retrieval for uncatalogued reports. A changed claim selects every location, link, assessment and decision that depends on it. Follow these recorded dependencies through derived assessments until no further dependent item is found. Do not traverse all topics in the same bulletin or all geographic neighbours.

For additions, retrieve historical candidates in both directions using explicit evidence keys:

| Key | Candidate retrieval | Required interpretation |
| --- | --- | --- |
| Canonical publication URL and explicit correction or follow-up references | All captured versions and cited publications, including references whose target has just arrived | Check whether the source identifies a correction, withdrawal or follow-up. |
| Authority and outbreak/investigation identifier | Reports carrying that authority's identifier | Check identifier namespace, episode and case scope. An article ID is a document key. |
| Named gathering, facility, vessel, exposure site or product batch | Reports naming that entity, retaining edition, year, batch and location qualifiers | Check that the entity describes the same exposure or episode. A recurring event name alone is insufficient. |
| Explicit journey or importation statement | Reports with the stated pathogen and named endpoints, retaining direction and reported episode dates | Inspect the source for the same journey, case group or follow-up; matching countries do not establish identity. |
| Open review question | Records matching the question's named investigation, source reference or exposure | Reopen it only when the evidence can address that question. |

Use Unicode normalization, case folding and whitespace normalization for textual lookup; preserve identifiers and scientific qualifiers. Use reviewed vocabulary mappings for aliases and record their version. Do not collapse subtypes, event editions or source namespaces. Lookup keys locate evidence; they do not assign outbreak identity or create geographic lines.

Search the entire captured archive for an explicit identifier or reference. Publication dates do not impose an epidemiological lookback. An older report captured today can clarify a link in a newer publication, and an older reference can point to a document arriving in a later run. Missing episode dates cannot safely exclude a candidate. Record ambiguous names, unresolved references and candidates exceeding the review budget as pending work. Do not silently keep only the first matches or declare an unmatched report unrelated.

Save the queried keys and the hash of each returned record set. This also tracks statements such as “no matching follow-up found”: an added member changes that review's inputs. A source-local statement such as “this report names no destination” remains reusable. Evidence references alone cannot detect a newly relevant report that was absent during the earlier review.

For example, an August report may cite a May investigation first captured in September. Its explicit reference selects the May report for review despite the publication gap. The May source can clarify the evidence packet without rewriting the August statement. The added evidence is available at a September capture cutoff, not a June cutoff. A shared country or disease without that source connection supplies no new link.

## 4. Review the affected relationships

Assemble one evidence packet per explicit investigation or unresolved question. Include exact source passages with context, dates, location roles, source origin, competing statements and the prior decision. Reuse captured text and source assessments. The current geography model contract assesses records separately; comparison across reports is an agent/editor review step using the existing annotation format.

Review every new or materially changed displayed link against its source. Check type, endpoints, direction, episode scope and certainty. Distinguish independent reporting from copied or syndicated statements; repetition does not increase confidence by itself. A later publication can contain an older assessment. A later date alone does not settle a conflict.

Record one disposition with its evidence and reason:

| Disposition in the private review record | Action |
| --- | --- |
| Retain | Preserve the link, its identifier and review provenance. Record the additional comparison without rewriting the source assessment. |
| Add | Create a source-supported link or panel assessment. Keep a separate source statement when it repeats an existing episode. |
| Amend | Correct an extraction or endpoint error using captured evidence; record the relationship between the original and corrected artifacts. |
| Contested | Preserve the competing source statements and an unresolved assessment. Do not select a winner from dates, report counts or model confidence. |
| Withdraw or supersede | Require an explicit source withdrawal/correction or an authorized editorial decision, and record its target and supporting evidence. |
| Pending | Record the missing evidence or decision and leave the question open. |

These are review dispositions, not additional public relationship types. Travel, shared event and source hypothesis retain their existing meanings. Direction describes reported movement; it does not imply who infected whom. Shared pathogen, country, season or bulletin remains insufficient for a geographic link. Event merges, splits and accepted identities require an editor's explicit decision.

Preserve unchanged link IDs. Do not regenerate retained links merely to reorder model output: generated IDs can depend on output order. For a material revision, record both IDs and the reason in the private adjudication history. A shared-country path A–B–C does not establish an A–C relationship.

## 5. Apply decisions without losing history

Work on a fresh copy of the saved preparation inputs. For each invalidated assessment, remove its carried-forward location annotations and generated links/assessments from that working copy before replacement. Include all recorded derivatives of the changed evidence, including dependents supported by several records. Preserve the original inputs and every adjudication. Leaving stale locations in the working annotations causes the runner to skip the record.

After replacement, rebuild derived places, memberships, metrics and the export from one consistent input set. Carry unaffected assessments forward unchanged. A dependency invalidation is a request for review, not an instruction to erase the source claim. Independently supported statements remain available. Do not apply a correction directly to a sealed bundle or rewrite the registry ledger.

Use the existing source assessment updates and reviewed assertion comparisons where their semantics fit. The geographic export has no automatic lifecycle field that suppresses a line after a withdrawal. Retain the source history and show the explicit later assessment; if the requested display requires suppression or reversal that the contract cannot express, put that change in the inbox and require a tested contract/selector change before publishing it. Do not claim that a private disposition changes consumer behaviour.

Preserve publication, observation, capture and review times. An April report first captured in September can appear in an April publication filter, but was unavailable at a June capture cutoff. The selector's date filters do not reconstruct every historical editorial decision. Use the sealed release available at that time when asking what ATLAS displayed then. Never backdate a review or replace historical exports.

## 6. Validate and complete the run

Before handoff, require every selected record and affected relationship to be accounted for: reused, reviewed or pending with a reason. Mechanical validity and scientific resolution are separate. Unanswered questions can remain in a completed review; unprocessed work must be reported as partial.

Run evidence, reference, coverage, schema and bundle checks on the whole export. Compare unaffected records, assertions, measurements, comparisons and source assessments with the baseline. Existing differences need an explicit reason. Test the affected link just before, on and after each relevant publication/capture boundary, a window containing all support, and windows missing each required support record. Check the full window and a knowledge cutoff before each historical addition was captured. Preserve figure selection and verify map points against eligible geographic memberships.

Keep these replay cases in the evaluation set: an earlier report clarifying a later link; a late correction; an unchanged rerun with no model calls; a mirrored report; a repeated festival in another year; an unknown destination; a rule-version change; and a withdrawal whose display treatment is unresolved. These are required scenarios for evaluating this procedure, not a claim that dedicated fixtures have all been implemented.

Audit a sample outside the affected set to look for missed dependencies and source-assessment errors. For routine weekly work, inspect up to 30 uniformly sampled unchanged assessments, including no-link outcomes in the sampling population. Save the population, seed, selected IDs and findings. Add targeted checks for known problem sources or layouts and report them separately. For a large population with 10% defective assessments, 30 uniform draws detect at least one with probability approximately 1 − 0.9³⁰, or 96%; sampling without replacement has at least this probability when the population supports that prevalence and sample size; this is a coarse detection check, not evidence of low error or complete retrieval. If an error is found, define its cause, review every assessment sharing the affected method/source condition and record any remaining backlog. Bound that follow-up separately rather than silently enlarging a model run.

Save a completion receipt containing input and method fingerprints; selected records and relationship IDs; dependency and candidate-set references; dispositions and adjudications; unchanged, added, amended, contested, withdrawn and pending counts; executed checks; actual model usage and elapsed time; and the final export reference. Link it from the weekly receipts and review inbox. Ignoring the inbox triggers no further processing. A supplied decision changes the relevant review inputs once and requires validation of its derivatives.

## Cost and stopping rules

Let N be archived records, D the new or changed records, E the recorded dependency references, A the affected references reached, K the candidate matches retrieved, and B the text sent for review. Reading and hashing source text costs O(S) in the bytes inspected. With bounded keys, building in-memory lookups costs O(N + E); dependency traversal costs O(A), and indexed candidate retrieval costs O(D + K) after reading the explicit keys. Those are algorithmic bounds for the review plan, not measured timings or a claim that a persistent index exists. Common or incomplete keys can make K large. No unrestricted all-pairs comparison is required.

Model use is proportional to the uncached evidence packets actually sent, including their outputs; it need not grow with every archived report on every run. Count bytes/tokens for supporting historical passages and the audit as well as new records. Local export generation and full integrity verification still visit the selected dataset, and sorting and quotation searches add their own costs. Do not describe the entire workflow as constant-time incremental processing.

Use the documented geographic call/input limits and a separate declared budget for relationship packets and audit work. If nothing changed and no audit is due, reuse the validated assessment results with zero model calls. Weekly audit work has its own receipt and cost. Stop when all triggered work is processed or explicitly pending, then rebuild and validate once. A failed download, absent model identity, large candidate set or unanswered editorial question must not cause an endless retry loop.

## Research basis

The dependency design follows the distinction between the source of a value and the inputs responsible for a derived result in [Buneman, Khanna and Tan, *Why and Where: A Characterization of Data Provenance* (2001)](https://homepages.inf.ed.ac.uk/opb/papers/ICDT2001.pdf). ATLAS also records candidate-set changes because a new report can matter without appearing in an existing link's provenance.

[Cochrane's guidance on maintaining reviews](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-iv) supports explicit surveillance, update criteria and versioned methods. Its application here is a workflow design choice, not validation of outbreak links. [Campbell et al. (2019)](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1006930) reconstruct transmission using contact, symptom and genomic data. Report-level reassessment supplies none of those missing inputs and therefore remains a review of source-described relationships.

## One Health dependencies

Apply the [One Health evidence procedure](ONE_HEALTH.md) to cross-domain relationships. Reuse a source assessment only while its text, quoted spans, interpreted context and review policy remain valid. Review an edge again when either endpoint, its source proposition, its supporting evidence or a relevant adjudication changes. Preserve exact candidate IDs and their set hash in the run review artifact; a changed candidate set requires an explicit relationship review. Relationship identifiers and source assertion references support dependency lookup without comparing every pair of archive records.
