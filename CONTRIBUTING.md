# Contributing

Open a focused issue describing the source adapter, scientific behavior, or operational improvement. Use synthetic minimal examples in public issues. Add an offline fixture and regression test before changing semantic behavior. Submit code, schema/dictionary changes, documentation, and a changelog entry together. Run `python -m pytest -q` and a deterministic replay. Run `node tests/test_map_links.cjs` and `node tests/test_site_view.cjs` to check geographic links and export selection. Describe source collection and model checks actually performed in the pull request.

Reviewers check provenance, missingness, temporal cutoffs, event identity, compatible measurement contexts, source access, and public/private output boundaries. Dependency updates and hosted Actions are reviewed through separate maintenance pull requests. Use the terms in the data dictionary. Follow the language guidance in [Workflow](docs/WORKFLOW.md) for docs and interface text.

Keep generated data, reports, captured sources and operational state out of commits. Use `reports/`, `.local/` or `.runtime-state/` for local work. The root allowlist in `.gitignore` admits the software and its documentation; add a root entry only when it belongs in the ATLAS source release. Keep synthetic fixtures in `tests/` and reusable synthetic examples in `examples/`. Check `git status --short` before committing.
