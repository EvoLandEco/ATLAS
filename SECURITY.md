# Security and operational data

Source documents are untrusted input. Retrieval uses allowlisted HTTPS hosts, public-address checks, bounded redirects and bodies, and robots-aware requests. The extraction model has a fixed schema and no external action tools. Evidence is mechanically checked and reviewed before registry acceptance. Exported HTML disables source HTML and active script content; CSV string cells receive spreadsheet-formula protection.

Review source bodies, summaries, relationship rationales, and resource links before public distribution. Public source documents may themselves contain personal details. Keep source objects, model caches, credentials, private decisions, and raw operational state in a restricted deployment repository. Source retention follows the group's access and licensing arrangements.

Use a narrowly scoped private-state token and an API project with an explicit budget. Protect the publication environment with required reviewers. A content-bound approval JSON authenticates a bundle hash; editor authority comes from the group's access-control process. For sensitive issues, use the repository's private vulnerability reporting when the maintainer enables it. Rotate exposed tokens and preserve an incident record after a credential event.

DNS validation and request-time hostname resolution are separate operations in the alpha; a deployment network egress policy supplies stronger address-level control against DNS rebinding. The default trust boundary assumes configured official domains and operator-reviewed source changes. External PDF parsers and model providers remain dependencies requiring maintenance and appropriate deployment controls.
