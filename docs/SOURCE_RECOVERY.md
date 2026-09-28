# Recovering missing source documents

Use this procedure when a weekly run or historical expansion discovers a report but cannot collect its evidence. It is agent operated: the package collector does not search literature services or institutional repositories automatically.

## Diagnose before retrying

Read source checks, captured objects and extraction receipts. Record the failed URL, host, HTTP status, failure stage, reporting window and last attempt. Check the index, article page and download host separately. An accessible index does not establish access to its attachments.

Distinguish access failure, rate limiting, an obsolete endpoint, incomplete content, a parser error and an extraction limit. HTTP 403 is an access failure; HTTP 429 is a rate limit. A failure to retrieve a host's robots policy leaves that route under review. Stop requests to a suspended host, preserve `Retry-After`, and arrange a bounded later retry. Do not rotate identities, hosts or sessions to evade a restriction.

A robots-file failure is distinct from a refusal of the document URL. Record which request returned the error. When the user explicitly authorizes direct retrieval of a public document, a bounded agent download can omit that failed preliminary check for the named source and run. Preserve HTTPS host checks, request spacing, response limits and capture provenance. A direct document response of 401, 403 or 429 suspends that route; record its status without attributing it to every unrequested document. This approval does not change the scheduled collector or authorize access to protected content.

An archive warning can concern an old or excluded document. Inspect its edition date and scope before counting it as a gap in the selected window. Keep the exclusion evidence and the original warning.

## Find an authorized copy

1. Search the exact title and DOI. Start with the publisher and named coauthor agencies. For joint EFSA–ECDC reports, inspect ECDC's publication page and its primary attachment. A news summary is a separate document.
2. Search licensed repositories by DOI. The [Europe PMC REST API](https://europepmc.org/RestfulWebService) supplies metadata and XML for its open access subset. Verify the DOI inside the article, its licence and the presence of the report body.
3. For a repository record whose full article is supplied as a PDF, use the documented [PMC Cloud Service](https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/). Follow its [dataset specification](https://pmc-oa-opendata.s3.amazonaws.com/README.txt): list the specific PMCID's available versions, inspect the metadata, and retrieve the declared file. Check the licence, manuscript status, retraction status, DOI and file checksum. Multiple versions require a content comparison; a larger version number alone does not select the appropriate edition. The legacy PMC OA service is retired.
4. Use Consensus for literature discovery when publisher and repository searches leave gaps. This branch requires a connected **Consensus plugin** with search and paper-fetch tools. Search an exact title as well as a DOI: a DOI query can return related papers. Fetch the matching paper record before using its metadata, compare the DOI and title with the source index, then follow the authors' institutional repository or another authorized full-text route. Save the query, fetched record and resulting source URL. Consensus abstracts and generated takeaways do not replace the paper's tables or methods.
5. If no authorized complete copy is available, preserve the gap with a specific request for institutional access, a provider export or a retained source edition. BEACON and WAHIS remain unused without an authorized route.

An official coauthor copy or licensed repository deposit is a distinct access route. Verify that it represents the required report and edition. Preserve the publisher URL, DOI, repository URL, version, licence, actual capture time and source hashes. Record publication dates as supplied by each edition; do not substitute the repository deposit date or a search engine's date.

A public copy hosted outside an institutional repository requires the same identity check and explicit publisher permission to reproduce the report. Inspect the licence and front matter in the downloaded file, compare its DOI and title with the official index, and retain the hosting URL separately from the publisher URL. Search snippets and secondary summaries remain discovery evidence. Record whether Consensus supplied only metadata or helped locate a full copy through a subsequent search.

## Check completeness and interpretation

A successful download is a captured object. Closing a report gap also requires checking its contents. Repository XML can contain only an abstract, notes or references even when its metadata labels the article open access. Inspect the main text and declared article files. Preserve table headers, spans, footnotes, units and missing-value notation. Keep the original XML or PDF alongside any text representation.

Record separate outcomes for metadata, abstract, main text, attachments, layout review and extraction. Preserve every captured version. A corrected or more complete capture creates a new record and a source-copy review; it does not rewrite the earlier object. Related papers and mirrored reports must not inflate outbreak or case totals.

Large articles require a recorded allocation and identifiable sections within the model input limit. Account for every section as processed, outside the selected analytical scope, pending extraction or requiring layout review. A concise digest can be complete for its stated scope while detailed tables remain unreviewed. Keep collection coverage, extraction coverage and analytical comparability separate.

Reuse validated extractions for unchanged evidence. Review added findings against their quotations, then reassess affected geographic links, chains and longitudinal comparisons. Prepare exports from the exact validated snapshot. Collection recovery supplies private evidence and draft outputs; publication requires its own approval.

When an excerpt omits the disease, location or measurement scope, inspect the surrounding captured section. Attach the passage that establishes the missing context, including table headings where relevant. A document title or nearby number alone does not establish that context. Preserve the original extraction and record the source review separately. If the full section remains ambiguous, keep the finding unresolved.

## Recovery receipt and deferred retry

Keep the experiment record with the dated private run. Include queries and candidate URLs, exact-match checks, access results, content coverage, licences, source and parser hashes, reused and recovered document IDs, request counts, extraction usage and unresolved actions. Documentation describes the method; run receipts hold measured results.

A deferred retry keeps the original publication window and records its actual capture cutoff. Check live processes and writer locks, read the last receipt, probe the failed origin once, and stop again if the restriction persists. Use sequential requests, provider delays and bounded document, response and model budgets. Reuse successful captures rather than restarting the archive. Keep a one-off recovery schedule separate from the three weekly jobs and remove it after execution.
