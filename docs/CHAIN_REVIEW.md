# Chain review

ATLAS prepares reviewed chains as structured evidence for analysis and presentation. The [site export contract](SITE_EXPORT.md#reviewed-chains) distinguishes source-established transmission, reported contact or exposure, travel itineraries and reporting sequences. These categories require different evidence and retain their own labels.

## Establish membership

Identify a named episode or journey and inspect the captured source passages. Assign stable keys to the chain, its nodes and explicit connections. Record the source's identifiers or descriptive roles and the evidence that establishes each member's identity. Keep unrelated episodes separate, including reports that explicitly deny a connection. Do not use disease, country, date proximity or topic grouping to establish membership.

Transmission requires source-established endpoint relationships. A source's statement that an outbreak includes a single transmission chain does not identify every infector and recipient. Preserve group descriptions when individuals cannot be identified. Contact follow-up, quarantine, a shared exposure and travel remain their stated relationship types.

Reporting sequences require a reviewed common episode and distinct publication dates. Connect only the reviewed successive reports in the selected review scope. State whether the scope covers all captured reports or a documented subset. Publication order describes reporting. Event and observation dates retain their separate meanings.

## Preserve evidence and geography

Supply exact captured quotations for each node's membership and each connection. Include evidence needed to identify locations, dates and direction. Unknown days remain null with a reason. A location reference retains the precision of its coordinates; never place a case at a precise address from a country-level reference point. Leave unknown or broad locations unplaced, including intermediate nodes.

Record the review time, reviewer, scope and material uncertainty. Chain review does not accept registry events, merge records or authorize publication. Export a research preview with its stated review status.

## Maintain the review

During weekly production and historical expansion, inspect new or revised evidence for each affected episode. Reuse reviews only when their source hashes and interpretation dependencies remain valid. Review new members and explicit connections; an earlier publication may require a different adjacency in a reporting sequence. Preserve stable keys for unchanged entities and record the reason and evidence for additions, withdrawals, splits or changed direction in the private decision history. Prepare a new annotated release without rewriting sealed exports.

Include chain review among the concrete analytical opportunities in the workflow. Account for reviewed examples and unresolved candidates in the run receipt. The absence of exported transmission chains is a review outcome, not evidence that no transmission occurred.

## Verify and hand off

Run schema and graph validation, source-span checks, date and record-selection tests, and the authoritative selector. Confirm that removing a source, topic, time interval or intermediate node cannot create a new connection. Preserve branches, unplaced nodes and disconnected portions of a filtered view. Check the full export against the preceding release for unintended changes to numerical and geographic content.

Hand off the candidate bundle, matching selector and types, exact hashes, review coverage and supported examples. The consumer owns map projection, geographic extent fitting, dateline handling and visual design. Publishing a candidate follows the existing approval process.

Chain preparation reuses captured sources and performs no model calls. Validation indexes assertion references once and caches the supporting records of each referenced place. Graph checks visit nodes and edges directly. Selection builds a node lookup per chain and filters explicit edges against the visible record set; it does not compare every pair of locations or reports.
